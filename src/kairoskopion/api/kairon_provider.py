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
from ..kairon_provider.bibliography_resolver import resolve_manuscript_bibliography
from ..kairon_provider.fulltext import acquire_manifest_fulltexts
from ..kairon_provider.fulltext_models import extract_fulltext_article_models
from ..kairon_provider.fulltext_fallback import (
    FulltextEvidenceReturn,
    FulltextFallbackStore,
    apply_evidence_return,
)
from ..kairon_provider.models import (
    ArtiklStatePointer,
    CorpusArtifact,
    CorpusArtifactManifest,
    ProviderRunRecord,
    TargetPressureItem,
    TargetPressurePack,
)
from ..kairon_provider.round_trip import compare_round_trip
from ..kairon_provider.reconcile import reconcile_target_pressure_pack
from ..schema import ArticleModel, VenueModel
from ..kairon_provider.storage import ProviderRunStore, TargetWorldStore
from ..kairon_provider.target_world_catalog import TargetWorldCatalog
from ..kairon_provider.target_pages import build_target_page_bundle
from ..kairon_provider.target_world import build_target_world_snapshot
from ..kairon_provider.transition import propose_transition
from ..kairon_provider.submission_gate import (
    SubmissionPackageStore,
    assess_submission_package,
)

router = APIRouter(
    prefix="/kairon/provider",
    tags=["kairon-provider"],
    dependencies=[Depends(get_current_user)],
)
_data_root = Path(os.environ.get("KAIROSKOPION_DATA_DIR") or ".kairoskopion")
_store = TargetWorldStore(_data_root)
_run_store = ProviderRunStore(_data_root)
_catalog = TargetWorldCatalog(_data_root)
_submission_package_store = SubmissionPackageStore(_data_root)
_fulltext_fallback_store = FulltextFallbackStore(_data_root)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BibliographyVerifyRequest(BaseModel):
    article_id: str
    manuscript_revision: str
    manuscript_text: str
    live: bool = False


class PressurePackRequest(BaseModel):
    target_id: str
    snapshot_id: str
    fit: dict[str, Any] | None = None
    mismatch_map: dict[str, Any] | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class TargetWorldRequest(BaseModel):
    target_id: str
    openalex_source_id: str | None = None
    issn: str | None = None
    venue_profile_ref: str | None = None
    board_page_url: str | None = None
    max_works: int = 30
    max_editors: int = 10
    selection_strategy: str = "recent_articles"
    provider_commit: str | None = None


class TargetWorldCatalogImportRequest(BaseModel):
    package: dict[str, Any]


class TargetWorldCatalogPublishRequest(BaseModel):
    status: str = "PROVIDER_OBSERVED"
    origin: str = "KAIROSKOPION"
    source_ref: str | None = None
    display_name: str | None = None


class TargetPagesRequest(BaseModel):
    homepage_url: str


class SubmissionPackageFinalizeRequest(BaseModel):
    article_id: str
    manuscript_revision: str
    venue_id: str
    submission_pack: dict[str, Any]
    target_world_package_id: str
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    qa_receipts: list[dict[str, Any]] = Field(default_factory=list)
    route_status: str
    author_fields_status: str
    policy_snapshot_refs: list[str] = Field(default_factory=list)
    required_artifact_kinds: list[str] | None = None
    required_qa_types: list[str] | None = None
    external_blockers: list[str] = Field(default_factory=list)


class FulltextAcquireRequest(BaseModel):
    max_files: int = 10
    max_bytes_per_file: int = 25 * 1024 * 1024


class FulltextEvidenceReturnRequest(BaseModel):
    provider_class: str
    provider_attempt_id: str
    result_state: str
    provider_instance: str | None = None
    resolved_article_identity: dict[str, Any] = Field(default_factory=dict)
    exact_source_satisfied: bool | None = None
    reorientation_history: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
    location_ref: str | None = None
    human_action: dict[str, Any] | None = None
    artifact_ref: str | None = None
    content_hash: str | None = None
    media_type: str | None = None
    byte_size: int | None = None
    acquisition_path: str | None = None
    validation_state: str | None = None
    extraction_state: str | None = None
    source_registration_ref: str | None = None


class ReconcilePressureRequest(BaseModel):
    article: dict[str, Any]
    venue: dict[str, Any]
    pressure_pack: dict[str, Any]
    target_models: dict[str, Any] | None = None
    formal_profile: dict[str, Any] | None = None
    manuscript_surface: dict[str, Any] | None = None


class TransitionProposalRequest(BaseModel):
    call_id: str
    pressure_pack: dict[str, Any]
    protected_core: list[str] = Field(default_factory=list)
    allowed_change_classes: list[str] = Field(default_factory=list)


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


@router.post("/bibliography/verify")
def verify_bibliography(req: BibliographyVerifyRequest):
    result = resolve_manuscript_bibliography(
        article_id=req.article_id, manuscript_revision=req.manuscript_revision,
        manuscript_text=req.manuscript_text, mode="real" if req.live else "mock",
        cache_dir=str(_data_root / "kairon_provider" / "bibliography_cache"),
    )
    return result.to_dict()


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
        issn=req.issn,
        venue_profile_ref=req.venue_profile_ref,
        board_page_url=req.board_page_url,
        max_works=max(1, min(req.max_works, 100)),
        max_editors=max(0, min(req.max_editors, 30)),
        selection_strategy=req.selection_strategy,
        provider_commit=req.provider_commit,
    )
    data = snapshot.to_dict()
    _store.put(data)
    _catalog.ingest(
        data,
        origin="KAIROSKOPION",
        status="PROVIDER_OBSERVED",
        source_ref=f"targetworld-store:{data['snapshot_id']}",
    )
    return data


@router.get("/target-world-catalog")
def list_target_world_catalog(target_id: str | None = None):
    return {"entries": _catalog.list_entries(target_id)}


@router.get("/target-world-catalog/best/{target_id}")
def best_target_world_catalog(target_id: str):
    entry = _catalog.best_for_target(target_id)
    if entry is None:
        raise HTTPException(404, "target world not found in shared catalog")
    return entry


@router.get("/target-world-catalog/package/{package_id}")
def get_target_world_package(package_id: str):
    data = _catalog.get_package(package_id)
    if data is None:
        raise HTTPException(404, "target world exchange package not found")
    return data


@router.post("/target-world-catalog/import")
def import_target_world_package(req: TargetWorldCatalogImportRequest):
    try:
        return _catalog.import_package(req.package)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/target-world/{snapshot_id}/publish-catalog")
def publish_target_world_catalog(snapshot_id: str, req: TargetWorldCatalogPublishRequest):
    data = _store.get(snapshot_id)
    if data is None:
        raise HTTPException(404, "target world snapshot not found")
    return _catalog.ingest(
        data, origin=req.origin, status=req.status,
        source_ref=req.source_ref or f"targetworld-store:{snapshot_id}",
        display_name=req.display_name,
    )


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
    _catalog.ingest(
        data, origin="KAIROSKOPION", status="PROVIDER_OBSERVED",
        source_ref=f"targetworld-store:{snapshot_id}",
    )
    return b


@router.post("/submission-packages/finalize")
def finalize_submission_package(req: SubmissionPackageFinalizeRequest):
    target_world_package = _catalog.get_package(req.target_world_package_id)
    if target_world_package is None:
        raise HTTPException(404, "target world exchange package not found")
    catalog_entry = next(
        (
            entry for entry in _catalog.list_entries()
            if entry.get("package_id") == req.target_world_package_id
        ),
        None,
    )
    if catalog_entry is None:
        raise HTTPException(409, "target world package has no catalog entry")
    # Exchange package bytes stay frozen. Current promotion status lives in
    # the catalog index and is bound ephemerally for finalization.
    target_world_package = {
        **target_world_package,
        "catalog_status": catalog_entry.get("status"),
    }
    try:
        manifest = assess_submission_package(
            article_id=req.article_id,
            manuscript_revision=req.manuscript_revision,
            venue_id=req.venue_id,
            submission_pack=req.submission_pack,
            target_world_package=target_world_package,
            artifacts=req.artifacts,
            qa_receipts=req.qa_receipts,
            route_status=req.route_status,
            author_fields_status=req.author_fields_status,
            policy_snapshot_refs=req.policy_snapshot_refs,
            required_artifact_kinds=req.required_artifact_kinds,
            required_qa_types=req.required_qa_types,
            external_blockers=req.external_blockers,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return _submission_package_store.put(manifest)


@router.get("/submission-packages/{manifest_id}")
def get_submission_package_manifest(manifest_id: str):
    manifest = _submission_package_store.get(manifest_id)
    if manifest is None:
        raise HTTPException(404, "submission package manifest not found")
    return manifest


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
        fallback_store=_fulltext_fallback_store,
        target_snapshot_id=snapshot_id,
        fallback_provenance_refs=["TRM-070"],
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
    _catalog.ingest(
        data, origin="KAIROSKOPION", status="PROVIDER_OBSERVED",
        source_ref=f"targetworld-store:{snapshot_id}",
    )
    return {
        "attempted": result["attempted"],
        "acquired": result["acquired"],
        "validated": result["validated"],
        "modeled": model_result["modeled"],
        "model_failures": model_result["failures"],
        "errors": result["errors"],
        "fallback_requests": [
            item.get("request_id") for item in result["fallback_requests"]
        ],
        "snapshot_id": snapshot_id,
    }


@router.get("/fulltext-fallback/requests")
def list_fulltext_fallback_requests(target_snapshot_id: str | None = None):
    return {
        "requests": _fulltext_fallback_store.list_requests(
            target_snapshot_id=target_snapshot_id,
        )
    }


@router.get("/fulltext-fallback/requests/{request_id}")
def get_fulltext_fallback_request(request_id: str):
    request = _fulltext_fallback_store.get_request(request_id)
    if request is None:
        raise HTTPException(404, "fulltext fallback request not found")
    return {
        "request": request.to_dict(),
        "returns": _fulltext_fallback_store.list_returns(request_id),
    }


@router.post("/fulltext-fallback/requests/{request_id}/return")
def receive_fulltext_fallback_return(
    request_id: str,
    req: FulltextEvidenceReturnRequest,
):
    request = _fulltext_fallback_store.get_request(request_id)
    if request is None:
        raise HTTPException(404, "fulltext fallback request not found")

    data = _store.get(request.target_snapshot_id)
    if data is None:
        raise HTTPException(409, "request target snapshot no longer exists")
    raw_manifest = data.get("corpus_manifest")
    if not isinstance(raw_manifest, dict):
        raise HTTPException(409, "target world has no corpus manifest")
    manifest = _manifest(raw_manifest)
    artifact = next(
        (a for a in manifest.artifacts if a.source_ref == request.source_ref),
        None,
    )
    if artifact is None:
        raise HTTPException(409, "request source artifact not found in target corpus")

    try:
        payload = (
            req.model_dump(exclude_none=True)
            if hasattr(req, "model_dump")
            else req.dict(exclude_none=True)
        )
        stored = _fulltext_fallback_store.put_return(
            request_id,
            payload,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

    evidence = FulltextEvidenceReturn(**stored)
    apply_evidence_return(artifact, evidence)
    data["corpus_manifest"] = manifest.to_dict()
    _store.put(data)
    _catalog.ingest(
        data,
        origin="KAIROSKOPION",
        status="PROVIDER_OBSERVED",
        source_ref=f"fulltext-fallback:{evidence.return_id}",
    )
    return {
        "request_id": request_id,
        "return": stored,
        "snapshot_id": request.target_snapshot_id,
        "source_ref": request.source_ref,
        "artifact_state": artifact.acquisition_state,
        "readable_local_ref": artifact.local_ref,
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


@router.post("/reconcile-pressure")
def reconcile_pressure(req: ReconcilePressureRequest):
    article = ArticleModel.from_dict(req.article)
    venue = VenueModel.from_dict(req.venue)
    pack = _pack(req.pressure_pack)
    return reconcile_target_pressure_pack(
        article=article,
        venue=venue,
        base_pack=pack,
        target_models=req.target_models,
        formal_profile=req.formal_profile,
        manuscript_surface=req.manuscript_surface,
    ).to_dict()


@router.post("/transition-proposal")
def transition_proposal(req: TransitionProposalRequest):
    pack = _pack(req.pressure_pack)
    return propose_transition(
        call_id=req.call_id,
        pressure_pack=pack,
        protected_core=req.protected_core,
        allowed_change_classes=req.allowed_change_classes,
    ).to_dict()


@router.post("/re-evaluate")
def re_evaluate(req: RoundTripRequest):
    return compare_round_trip(
        call_id=req.call_id,
        prior_state=_state(req.prior_state),
        current_state=_state(req.current_state),
        prior_pack=_pack(req.prior_pack),
        current_pack=_pack(req.current_pack),
    ).to_dict()