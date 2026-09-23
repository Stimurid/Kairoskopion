"""Resumable runtime state for Kairon batch qualification.

This layer does not execute semantic transformations. It persists scheduler
progress for an already-built BatchQualificationPlan and makes restart/resume
safe and deterministic. Target-world work may be coalesced across cells that
share one frozen snapshot; article-specific pressure/transition work may not.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .batch import BatchQualificationPlan


BATCH_STAGE_ORDER = (
    "LOCAL_RESOLUTION",
    "TARGET_READY",
    "PRESSURE_READY",
    "TRANSITION_READY",
    "MATERIALIZED",
    "RETURN_EVALUATED",
    "FORMAL_CHECKED",
    "MEMORY_PERSISTED",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _plan_fingerprint(plan: BatchQualificationPlan) -> str:
    payload = {
        "batch_id": plan.batch_id,
        "cells": [
            {
                "cell_id": c.cell_id,
                "article_id": c.article_id,
                "article_state_id": c.article_state_id,
                "target_id": c.target_id,
                "target_snapshot_id": c.target_snapshot_id,
                "academic_world_path": c.academic_world_path,
            }
            for c in sorted(plan.cells, key=lambda x: x.cell_id)
        ],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class BatchCellRuntimeState:
    cell_id: str
    stage_status: dict[str, str] = field(default_factory=dict)
    stage_evidence: dict[str, list[str]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    blocked_reason: str | None = None
    updated_at: str = field(default_factory=_now)

    def next_stage(self) -> str | None:
        if self.blocked_reason:
            return None
        for stage in BATCH_STAGE_ORDER:
            if self.stage_status.get(stage) != "complete":
                return stage
        return None

    @property
    def complete(self) -> bool:
        return self.next_stage() is None and not self.blocked_reason


@dataclass
class BatchRunState:
    batch_id: str
    plan_fingerprint: str
    cell_states: dict[str, BatchCellRuntimeState]
    status: str = "running"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchRunState":
        states = {
            cell_id: BatchCellRuntimeState(**state)
            for cell_id, state in (data.get("cell_states") or {}).items()
        }
        return cls(
            batch_id=data["batch_id"],
            plan_fingerprint=data["plan_fingerprint"],
            cell_states=states,
            status=data.get("status", "running"),
            created_at=data.get("created_at") or _now(),
            updated_at=data.get("updated_at") or _now(),
        )


@dataclass
class BatchWorkItem:
    stage: str
    cell_ids: list[str]
    target_id: str | None = None
    target_snapshot_id: str | None = None
    coalesced: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BatchRunStore:
    def __init__(self, root: str | Path):
        self.root = Path(root) / "kairon_provider" / "batch_runs"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, batch_id: str) -> Path:
        digest = hashlib.sha256(batch_id.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def put(self, state: BatchRunState) -> BatchRunState:
        path = self._path(state.batch_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)
        return state

    def get(self, batch_id: str) -> BatchRunState | None:
        path = self._path(batch_id)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("batch_id") != batch_id:
            return None
        return BatchRunState.from_dict(data)

    def list_ids(self) -> list[str]:
        out: list[str] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if data.get("batch_id"):
                out.append(str(data["batch_id"]))
        return out


def initialize_batch_run(
    plan: BatchQualificationPlan,
    *,
    store: BatchRunStore | None = None,
) -> BatchRunState:
    fingerprint = _plan_fingerprint(plan)
    if store is not None:
        existing = store.get(plan.batch_id)
        if existing is not None:
            if existing.plan_fingerprint != fingerprint:
                raise ValueError("stored batch run does not match current plan fingerprint")
            expected = {c.cell_id for c in plan.cells}
            if set(existing.cell_states) != expected:
                raise ValueError("stored batch run cell set does not match current plan")
            return existing

    state = BatchRunState(
        batch_id=plan.batch_id,
        plan_fingerprint=fingerprint,
        cell_states={
            c.cell_id: BatchCellRuntimeState(cell_id=c.cell_id)
            for c in plan.cells
        },
    )
    if store is not None:
        store.put(state)
    return state


def _refresh_batch_status(state: BatchRunState) -> None:
    cell_states = list(state.cell_states.values())
    if cell_states and all(s.complete for s in cell_states):
        state.status = "complete"
    elif any(s.blocked_reason for s in cell_states):
        state.status = "partial"
    elif any("failed" in s.stage_status.values() for s in cell_states):
        state.status = "partial"
    else:
        state.status = "running"
    state.updated_at = _now()


def advance_cell_stage(
    state: BatchRunState,
    *,
    cell_id: str,
    stage: str,
    status: str = "complete",
    evidence_refs: list[str] | None = None,
    error: str | None = None,
    blocked_reason: str | None = None,
    store: BatchRunStore | None = None,
) -> BatchRunState:
    if stage not in BATCH_STAGE_ORDER:
        raise ValueError(f"unsupported batch stage: {stage}")
    if status not in {"complete", "failed", "blocked"}:
        raise ValueError(f"unsupported batch stage status: {status}")
    if cell_id not in state.cell_states:
        raise ValueError(f"unknown batch cell_id: {cell_id}")

    cell = state.cell_states[cell_id]
    current = cell.next_stage()

    if cell.stage_status.get(stage) == "complete" and status == "complete":
        if evidence_refs:
            refs = cell.stage_evidence.setdefault(stage, [])
            for ref in evidence_refs:
                if ref not in refs:
                    refs.append(ref)
        cell.updated_at = _now()
        _refresh_batch_status(state)
        if store is not None:
            store.put(state)
        return state

    if current != stage:
        raise ValueError(
            f"out-of-order stage for {cell_id}: expected {current!r}, got {stage!r}"
        )

    cell.stage_status[stage] = status
    if evidence_refs:
        cell.stage_evidence[stage] = list(dict.fromkeys(evidence_refs))
    if error:
        cell.errors.append(error)
    if status == "blocked":
        cell.blocked_reason = blocked_reason or error or f"blocked at {stage}"
    elif status == "failed":
        cell.blocked_reason = blocked_reason or error or f"failed at {stage}"
    cell.updated_at = _now()

    _refresh_batch_status(state)
    if store is not None:
        store.put(state)
    return state


def build_resume_work_items(
    plan: BatchQualificationPlan,
    state: BatchRunState,
) -> list[BatchWorkItem]:
    if state.plan_fingerprint != _plan_fingerprint(plan):
        raise ValueError("batch run does not match current plan fingerprint")

    cells_by_id = {c.cell_id: c for c in plan.cells}
    grouped: dict[tuple[str, str], list[str]] = {}
    singles: list[BatchWorkItem] = []

    for cell_id, runtime in sorted(state.cell_states.items()):
        stage = runtime.next_stage()
        if stage is None:
            continue
        cell = cells_by_id[cell_id]
        if stage == "LOCAL_RESOLUTION":
            key = (stage, cell.target_id)
            grouped.setdefault(key, []).append(cell_id)
        elif stage == "TARGET_READY":
            key = (stage, cell.target_snapshot_id)
            grouped.setdefault(key, []).append(cell_id)
        else:
            singles.append(
                BatchWorkItem(
                    stage=stage,
                    cell_ids=[cell_id],
                    target_id=cell.target_id,
                    target_snapshot_id=cell.target_snapshot_id,
                    coalesced=False,
                )
            )

    out: list[BatchWorkItem] = []
    for (stage, key), cell_ids in sorted(grouped.items()):
        first = cells_by_id[cell_ids[0]]
        out.append(
            BatchWorkItem(
                stage=stage,
                cell_ids=cell_ids,
                target_id=first.target_id,
                target_snapshot_id=first.target_snapshot_id,
                coalesced=len(cell_ids) > 1,
            )
        )
    out.extend(singles)
    return out


def advance_work_item(
    plan: BatchQualificationPlan,
    state: BatchRunState,
    item: BatchWorkItem,
    *,
    status: str = "complete",
    evidence_refs: list[str] | None = None,
    error: str | None = None,
    blocked_reason: str | None = None,
    store: BatchRunStore | None = None,
) -> BatchRunState:
    valid = {c.cell_id for c in plan.cells}
    unknown = [cell_id for cell_id in item.cell_ids if cell_id not in valid]
    if unknown:
        raise ValueError(f"work item contains unknown cells: {unknown}")
    for cell_id in item.cell_ids:
        advance_cell_stage(
            state,
            cell_id=cell_id,
            stage=item.stage,
            status=status,
            evidence_refs=evidence_refs,
            error=error,
            blocked_reason=blocked_reason,
            store=None,
        )
    if store is not None:
        store.put(state)
    return state