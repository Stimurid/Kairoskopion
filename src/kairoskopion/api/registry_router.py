"""Registry API router (P6 Track 14).

CRUD + search + accept/reject for all P6 registry types.
Mounted at /api/registry/ in app.py.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..registry.store import BaseRegistry, load_registry, _RECORD_TYPES
from ..registry.status import record_usage_status
from ..registry.services import RegistryHub

router = APIRouter(prefix="/api/registry", tags=["registry"])


def _data_dir() -> Path:
    return Path(
        os.environ.get("KAIROSKOPION_DATA_DIR") or ".kairoskopion"
    ) / "registry"


def _hub() -> RegistryHub:
    return RegistryHub(_data_dir())


# ---------------------------------------------------------------------------
# List available registry types
# ---------------------------------------------------------------------------

@router.get("/types")
def list_registry_types() -> list[str]:
    return list(_RECORD_TYPES.keys())


# ---------------------------------------------------------------------------
# Generic CRUD for any registry type
# ---------------------------------------------------------------------------

@router.get("/{record_type}")
def list_records(
    record_type: str,
    q: str = Query("", description="Search query"),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    _validate_type(record_type)
    reg = load_registry(record_type, _data_dir())
    if q:
        records = reg.search(q, limit=limit)
    else:
        records = reg.list_all()[:limit]
    return [
        {**rec.to_dict(), "_usage_status": record_usage_status(rec)}
        for rec in records
    ]


@router.get("/{record_type}/{record_id}")
def get_record(record_type: str, record_id: str) -> dict[str, Any]:
    _validate_type(record_type)
    reg = load_registry(record_type, _data_dir())
    rec = reg.get(record_id)
    if rec is None:
        raise HTTPException(404, f"Record {record_id} not found")
    return {**rec.to_dict(), "_usage_status": record_usage_status(rec)}


class AddProvisionalRequest(BaseModel):
    data: dict[str, Any]


@router.post("/{record_type}")
def add_provisional(record_type: str, req: AddProvisionalRequest) -> dict[str, Any]:
    _validate_type(record_type)
    reg = load_registry(record_type, _data_dir())
    cls = _RECORD_TYPES[record_type][0]
    rec = cls.from_dict(req.data)
    dup = reg.find_duplicate(rec)
    if dup is not None:
        return {
            "status": "duplicate",
            "existing": dup.to_dict(),
            "_usage_status": record_usage_status(dup),
        }
    result = reg.add_provisional(rec)
    return {
        "status": "created",
        "record": result.to_dict(),
        "_usage_status": record_usage_status(result),
    }


class ReviewRequest(BaseModel):
    note: str | None = None


@router.post("/{record_type}/{record_id}/accept")
def accept_record(
    record_type: str, record_id: str, req: ReviewRequest | None = None,
) -> dict[str, Any]:
    _validate_type(record_type)
    reg = load_registry(record_type, _data_dir())
    note = req.note if req else None
    rec = reg.accept(record_id, reviewer_note=note)
    if rec is None:
        raise HTTPException(404, f"Record {record_id} not found")
    return {**rec.to_dict(), "_usage_status": record_usage_status(rec)}


@router.post("/{record_type}/{record_id}/reject")
def reject_record(
    record_type: str, record_id: str, req: ReviewRequest | None = None,
) -> dict[str, Any]:
    _validate_type(record_type)
    reg = load_registry(record_type, _data_dir())
    note = req.note if req else None
    rec = reg.reject(record_id, reviewer_note=note)
    if rec is None:
        raise HTTPException(404, f"Record {record_id} not found")
    return {**rec.to_dict(), "_usage_status": record_usage_status(rec)}


# ---------------------------------------------------------------------------
# Review queue — all pending records across all types
# ---------------------------------------------------------------------------

@router.get("/review-queue")
def review_queue(
    limit: int = Query(100, ge=1, le=500),
) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    for record_type in _RECORD_TYPES:
        reg = load_registry(record_type, _data_dir())
        for rec in reg.list_all():
            status = record_usage_status(rec)
            if status in ("provisional_with_warning", "unknown"):
                entry = rec.to_dict()
                entry["_record_type"] = record_type
                entry["_usage_status"] = status
                pending.append(entry)
                if len(pending) >= limit:
                    break
        if len(pending) >= limit:
            break
    return pending


# ---------------------------------------------------------------------------
# Acquisition tasks
# ---------------------------------------------------------------------------

@router.get("/tasks/open")
def list_open_tasks() -> list[dict[str, Any]]:
    hub = _hub()
    return [t.to_dict() for t in hub.tasks.list_open()]


@router.get("/tasks/all")
def list_all_tasks(limit: int = Query(100, ge=1, le=500)) -> list[dict[str, Any]]:
    hub = _hub()
    return [t.to_dict() for t in hub.tasks.list_all()[:limit]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_type(record_type: str) -> None:
    if record_type not in _RECORD_TYPES:
        raise HTTPException(
            400,
            f"Unknown record_type: {record_type!r}. "
            f"Valid: {list(_RECORD_TYPES.keys())}",
        )
