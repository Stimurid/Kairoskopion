"""Additive FastAPI surface for Kairoskopion as a Kairon provider."""

from __future__ import annotations

from typing import Any
import os
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..kairon_provider.adapter import pressure_pack_from_diagnostics
from ..kairon_provider.models import (
    ArtiklStatePointer,
    TargetPressureItem,
    TargetPressurePack,
)
from ..kairon_provider.round_trip import compare_round_trip
from ..kairon_provider.target_world import build_target_world_snapshot
from ..kairon_provider.storage import TargetWorldStore

router = APIRouter(prefix="/kairon/provider", tags=["kairon-provider"])
_store = TargetWorldStore(Path(os.environ.get("KAIROSKOPION_DATA_DIR") or ".kairoskopion"))


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


class RoundTripRequest(BaseModel):
    call_id: str
    prior_state: dict[str, Any]
    current_state: dict[str, Any]
    prior_pack: dict[str, Any]
    current_pack: dict[str, Any]


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
        from fastapi import HTTPException
        raise HTTPException(404, "target world snapshot not found")
    return data


@router.get("/target-world")
def list_target_worlds():
    return {"snapshot_ids": _store.list_ids()}


@router.post("/re-evaluate")
def re_evaluate(req: RoundTripRequest):
    return compare_round_trip(
        call_id=req.call_id,
        prior_state=_state(req.prior_state),
        current_state=_state(req.current_state),
        prior_pack=_pack(req.prior_pack),
        current_pack=_pack(req.current_pack),
    ).to_dict()
