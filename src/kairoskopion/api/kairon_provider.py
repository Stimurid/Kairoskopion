"""Authenticated additive FastAPI surface for Kairoskopion as a Kairon provider."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import get_current_user
from ..kairon_provider.adapter import pressure_pack_from_diagnostics
from ..kairon_provider.fulltext import acquire_manifest_fulltexts
from ..kairon_provider.fulltext_models import extract_fulltext_article_models
from ..kairon_provider.models import (
    ArtiklStatePointer,
    CorpusArtifact,
    CorpusArtifactManifest,
    ProviderRunRecord,
    TargetPressureItem,
    TargetPressurePack,
)
from ..kairon_provider.round_trip import compare_round_trip
from ..kairon_provider.storage import ProviderRunStore, TargetWorldStore
from ..kairon_provider.target_pages import build_target_page_bundle
from ..kairon_provider.target_world import build_target_world_snapshot

router = APIRouter(
    prefix="/kairon/provider",
    tags=["kairon-provider"],
    dependencies=[Depends(get_current_user)],
)
_data_root = Path(os.environ.get("KAIROSKOPION_DATA_DIR") or ".kairoskopion")
_store = TargetWorldStore(_data_root)
_run_store = ProviderRunStore(_data_root)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PressurePackRequest(BaseModel):
    target_id: str
    snapshot_id: str
    fit: dict[str, Any] | None = None
    mismatch_map: dict[str, Any] | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class TargetWorldRequest(BaseModel):
    target_id: str
    openalex_source_id: str | None = None
    venue_profile_ref: str | None = None
    board_page_url: str | None = None
    max_works: int = 30
    max_editors: int = 10
    selection_strategy: str = "recent_articles"
    provider_commit: str | None = None


class TargetPagesRequest(BaseModel):
    homepage_url: str


class FulltextAcquireRequest(BaseModel):
    max_files: int = 10
    max_bytes_per_file: int = 25 * 1024 * 1024


class RoundTripRequest(BaseModel):
    call_id: str
    prior_state: dict[str, Any]
    current_state: dict[str, Any]
    prior_pack: dict[str, Any]
    current_pack: dict[str, Any]


class RunCreateRequest(BaseModel):
    call_id: str | None = None
    target_snapshot_id: str | None = None


class RunStageUpdateRequest(BaseModel):
    stage: str
    status: str
    evidence_ref: str | None = None
    error: str | None = None


def _state(d: dict[str, Any]) -> ArtiklStatePointer:
    return ArtiklStatePointer(**d)


def _pack(d: dict[str, Any]) -> TargetPressurePack:
    items = [
        item if isinstance(item, TargetPressureItem) else TargetPressureItem(**item)
        for item in (d.get("items") or [])
    ]
    return TargetPressurePack(
        target_id=d["target_id"],
        snapshot_id=d["snapshot_id"],
        items=items,
        unknowns=list(d.get("unknowns") or []),
        conflicts=list(d.get("conflicts") or []),
        created_at=d.get("created_at") or TargetPressurePack(
            target_id=d["target_id"], snapshot_id=d["snapshot_id"]
        ).created_at,
    )


def _manifest(d: dict[str, Any]) -> CorpusArtifactManifest:
    return CorpusArtifactManifest(
        target_id=d["target_id"],
        selection_strategy=d.get("selection_strategy") or "unknown",
        artifacts=[
            a if isinstance(a, CorpusArtifact) else CorpusArtifact(**a)
            for a in (d.get("artifacts") or [])
        ],
        time_range=d.get("time_range"),
        bias_notes=list(d.get("bias_notes") or []),
        unknowns=list(d.get("unknowns") or []),
        created_at=d.get("created_at") or _now(),
    )


@router.post("/pressure-pack")
def build_pressure_pack(req: PressurePackRequest):
    return pressure_pack_from_diagnostics(
        target_id=req.target_id,
        snapshot_id=req.snapshot_id,
        fit=req.fit,
        mismatch_map=req.mismatch_map,
        evidence_refs=req.evidence_refs,
    ).to_dict()


@router.post("/target-world")
def build_target_world(req: TargetWorldRequest):
    snapshot = build_target_world_snapshot(
        target_id=req.target_id,
        openalex_source_id=req.openalex_source_id,
        venue_profile_ref=req.venue_profile_ref,
        board_page_url=req.board_page_url,
        max_works=max(1, min(req.max_works, 100)),
        max_editors=max(0, min(req.max_editors, 30)),
        selection_strategy=req.selection_strategy,
        provider_commit=req.provider_commit,
    )
    data = snapshot.to_dict()
    _store.put(data)
    return data


@router.get("/target-world/{snapshot_id}")
def get_target_world(snapshot_id: str):
    data = _store.get(snapshot_id)
    if data is None:
        raise HTTPException(404, "target world snapshot not found")
    return data


@router.get("/target-world")
def list_target_worlds():
    return {"snapshot_ids": _store.list_ids()}


@router.post("/target-world/{snapshot_id}/pages")
def snapshot_target_pages(snapshot_id: str, req: TargetPagesRequest):
    data = _store.get(snapshot_id)
    if data is None:
        raise HTTPException(404, "target world snapshot not found")
    bundle = build_target_page_bundle(homepage_url=req.homepage_url)
    b = bundle.to_dict()
    data["page_bundle"] = b
    refs = list(data.get("evidence_refs") or [])
    refs.extend(p.get("url") for p in b.get("pages", []) if p.get("url"))
    data["evidence_refs"] = list(dict.fromkeys(refs))
    _store.put(data)
    return b


@router.post("/target-world/{snapshot_id}/acquire-fulltext")
def acquire_fulltext(snapshot_id: str, req: FulltextAcquireRequest):
    data = _store.get(snapshot_id)
    if data is None:
        raise HTTPException(404, "target world snapshot not found")
    raw_manifest = data.get("corpus_manifest")
    if not isinstance(raw_manifest, dict):
        raise HTTPException(409, "target world has no corpus manifest")
    manifest = _manifest(raw_manifest)
    result = acquire_manifest_fulltexts(
        manifest,
        output_dir=_data_root / "kairon_provider" / "artifacts",
        max_files=max(0, min(req.max_files, 50)),
        max_bytes_per_file=max(1024, min(req.max_bytes_per_file, 100 * 1024 * 1024)),
    )
    data["corpus_manifest"] = result["manifest"].to_dict()
    model_result = extract_fulltext_article_models(result["manifest"])
    target_models = dict(data.get("target_models") or {})
    target_models["article_models"] = model_result["article_models"]
    limitations = list(target_models.get("limitations") or [])
    if model_result["failures"]:
        limitations.append(
            f"fulltext structural extraction failures: {len(model_result['failures'])}"
        )
    target_models["limitations"] = list(dict.fromkeys(limitations))
    data["target_models"] = target_models
    _store.put(data)
    return {
        "attempted": result["attempted"],
        "acquired": result["acquired"],
        "validated": result["validated"],
        "modeled": model_result["modeled"],
        "model_failures": model_result["failures"],
        "errors": result["errors"],
        "snapshot_id": snapshot_id,
    }


@router.post("/runs")
def create_run(req: RunCreateRequest):
    if req.target_snapshot_id and _store.get(req.target_snapshot_id) is None:
        raise HTTPException(404, "target world snapshot not found")
    run = ProviderRunRecord(
        run_id=f"kaironrun:{uuid4().hex}",
        call_id=req.call_id,
        status="running",
        target_snapshot_id=req.target_snapshot_id,
    )
    data = run.to_dict()
    _run_store.put(data)
    return data


@router.get("/runs")
def list_runs():
    return {"run_ids": _run_store.list_ids()}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    data = _run_store.get(run_id)
    if data is None:
        raise HTTPException(404, "provider run not found")
    return data


@router.post("/runs/{run_id}/stage")
def update_run_stage(run_id: str, req: RunStageUpdateRequest):
    data = _run_store.get(run_id)
    if data is None:
        raise HTTPException(404, "provider run not found")
    stages = dict(data.get("stage_status") or {})
    stages[req.stage] = req.status
    data["stage_status"] = stages
    if req.evidence_ref:
        refs = list(data.get("evidence_refs") or [])
        refs.append(req.evidence_ref)
        data["evidence_refs"] = list(dict.fromkeys(refs))
    if req.error:
        errors = list(data.get("errors") or [])
        errors.append(req.error)
        data["errors"] = errors
    data["updated_at"] = _now()
    if req.status == "failed":
        data["status"] = "partial"
    _run_store.put(data)
    return data


@router.post("/re-evaluate")
def re_evaluate(req: RoundTripRequest):
    return compare_round_trip(
        call_id=req.call_id,
        prior_state=_state(req.prior_state),
        current_state=_state(req.current_state),
        prior_pack=_pack(req.prior_pack),
        current_pack=_pack(req.current_pack),
    ).to_dict()
