"""Operation trace recording for Kairoskopion (spec Wave 3 §19, Wave 5 §36)."""

from __future__ import annotations

import dataclasses as dc
from typing import Any

from .ids import operation_trace_id
from .schema import _DictMixin, _field, _list, _now


@dc.dataclass
class OperationTrace(_DictMixin):
    operation_id: str = dc.field(default_factory=operation_trace_id)
    operation_type: str = ""
    pipeline_run_id: str | None = _field()
    started_at: str = dc.field(default_factory=_now)
    ended_at: str | None = _field()
    user_or_agent: str | None = _field()
    inputs: list[str] = _list()
    sources_accessed: list[str] = _list()
    context_packs_used: list[str] = _list()
    adapters_called: list[str] = _list()
    entities_created: list[str] = _list()
    entities_updated: list[str] = _list()
    warnings: list[str] = _list()
    errors: list[str] = _list()
    quality_gate_status: str | None = _field()
    user_decisions: list[str] = _list()
    cost_estimate: str | None = _field()
    token_estimate: int | None = _field()
    notes: str | None = _field()


def start_trace(operation_type: str, *, pipeline_run_id: str | None = None) -> OperationTrace:
    return OperationTrace(
        operation_type=operation_type,
        pipeline_run_id=pipeline_run_id,
    )


def finish_trace(trace: OperationTrace) -> OperationTrace:
    trace.ended_at = _now()
    return trace
