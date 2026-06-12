"""Agentic runtime domain models (Agentic Contour v0.1).

AgentSpec, PromptFamilySpec, AgentTask, AgentRun, AgentResult,
AgentTrace, AgentFailure, AgentToolCall, WorkflowStepSpec,
AgenticWorkflowSpec, WorkflowRun, WorkflowResult, WorkflowTrace.

All models are plain dataclasses with to_dict()/from_dict() for JSON
round-trip.  Timestamps are ISO-8601 UTC strings.
"""

from __future__ import annotations

import dataclasses as dc
from datetime import datetime, timezone
from typing import Any, Callable

from ..ids import (
    agent_result_id,
    agent_run_id,
    agent_task_id,
    agent_trace_id,
    workflow_result_id,
    workflow_run_id,
    workflow_trace_id,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _list():
    return dc.field(default_factory=list)


def _dict():
    return dc.field(default_factory=dict)


# ---------------------------------------------------------------------------
# Serialization mixin (matches schema.py pattern)
# ---------------------------------------------------------------------------

class _DictMixin:
    def to_dict(self) -> dict[str, Any]:
        def _convert(v: Any) -> Any:
            if isinstance(v, _DictMixin):
                return v.to_dict()
            if isinstance(v, list):
                return [_convert(i) for i in v]
            if isinstance(v, dict):
                return {k: _convert(val) for k, val in v.items()}
            if hasattr(v, "value") and isinstance(v, type) is False:
                try:
                    return v.value
                except Exception:
                    return v
            if callable(v):
                return None
            return v
        return {k: _convert(v) for k, v in dc.asdict(self).items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Any:
        field_names = {f.name for f in dc.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)


# ---------------------------------------------------------------------------
# AgentSpec — static description of an agent role
# ---------------------------------------------------------------------------

@dc.dataclass
class AgentSpec(_DictMixin):
    role_id: str = ""
    display_name: str = ""
    aliases: list[str] = _list()
    layer: str = ""
    implementation_status: str = "future"
    execution_mode: str = "deterministic"
    prompt_family_ids: list[str] = _list()
    input_contract: dict[str, str] = _dict()
    output_contract: dict[str, str] = _dict()
    allowed_tools: list[str] = _list()
    evidence_policy: str = "preserve_all"
    unknown_policy: str = "propagate"
    failure_policy: str = "fail_explicit"
    memory_policy: str = "no_long_term"
    orchestration_notes: str = ""
    mvp_phase: str = ""
    first_workflows: list[str] = _list()


# ---------------------------------------------------------------------------
# PromptFamilySpec — static description of a prompt family
# ---------------------------------------------------------------------------

@dc.dataclass
class PromptFamilySpec(_DictMixin):
    family_id: str = ""
    family_name: str = ""
    version: str = "1.0.0"
    purpose: str = ""
    agent_role_id: str = ""
    input_contract: dict[str, str] = _dict()
    output_contract: dict[str, str] = _dict()
    system_prompt: str = ""
    user_template: str = ""
    output_schema: dict[str, Any] | None = None
    forbidden_behaviors: list[str] = _list()
    evidence_requirements: list[str] = _list()
    unknown_handling: str = "mark_unknown"
    validation_notes: str = ""


# ---------------------------------------------------------------------------
# AgentTask — input to executor
# ---------------------------------------------------------------------------

@dc.dataclass
class AgentTask(_DictMixin):
    task_id: str = dc.field(default_factory=agent_task_id)
    agent_role_id: str = ""
    workflow_run_id: str | None = None
    step_index: int | None = None
    operation_id: str = ""
    input_entity_refs: list[str] = _list()
    source_refs: list[str] = _list()
    raw_text: str | None = None
    entities: dict[str, Any] = _dict()
    user_constraints: dict[str, Any] = _dict()
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# AgentRun — execution record
# ---------------------------------------------------------------------------

@dc.dataclass
class AgentRun(_DictMixin):
    run_id: str = dc.field(default_factory=agent_run_id)
    task_id: str = ""
    agent_role_id: str = ""
    execution_mode: str = "deterministic"
    started_at: str = dc.field(default_factory=_now)
    finished_at: str | None = None
    status: str = "created"
    error_message: str | None = None


# ---------------------------------------------------------------------------
# AgentFailure
# ---------------------------------------------------------------------------

@dc.dataclass
class AgentFailure(_DictMixin):
    error_type: str = "unknown"
    error_message: str = ""
    message: str = ""
    recoverable: bool = False
    blocking: bool = True
    traceback: str = ""


# ---------------------------------------------------------------------------
# AgentToolCall
# ---------------------------------------------------------------------------

@dc.dataclass
class AgentToolCall(_DictMixin):
    tool_name: str = ""
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# AgentResult — output from executor
# ---------------------------------------------------------------------------

@dc.dataclass
class AgentResult(_DictMixin):
    result_id: str = dc.field(default_factory=agent_result_id)
    run_id: str = ""
    agent_role_id: str = ""
    output_entity_type: str = ""
    output_entity: dict[str, Any] = _dict()
    evidence_refs: list[str] = _list()
    unknowns: list[str] = _list()
    assumptions: list[str] = _list()
    confidence: str = "low"
    warnings: list[str] = _list()
    questions_for_user: list[str] = _list()
    quality_gate_status: str = "preliminary"
    evidence_status: str = "INFERENCE"
    failure: AgentFailure | None = None
    status: str = "success"
    llm_usage: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# AgentTrace — detailed execution trace
# ---------------------------------------------------------------------------

@dc.dataclass
class AgentTrace(_DictMixin):
    trace_id: str = dc.field(default_factory=agent_trace_id)
    run_id: str = ""
    agent_role_id: str = ""
    execution_mode: str = "deterministic"
    started_at: str = ""
    finished_at: str = ""
    tool_calls: list[dict[str, Any]] = _list()
    steps_log: list[str] = _list()
    final_status: str = ""
    notes: list[str] = _list()
    llm_usage: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Workflow models
# ---------------------------------------------------------------------------

@dc.dataclass
class WorkflowStepSpec(_DictMixin):
    step_index: int = 0
    agent_role_id: str = ""
    required: bool = True
    condition: str | None = None
    input_mapping: dict[str, str] = _dict()
    input_keys: list[str] = _list()
    output_key: str = ""
    skip_if_missing: list[str] = _list()
    description: str = ""


@dc.dataclass
class AgenticWorkflowSpec(_DictMixin):
    workflow_id: str = ""
    display_name: str = ""
    description: str = ""
    steps: list[dict[str, Any]] = _list()
    implementation_status: str = "executable"

    def get_steps(self) -> list[WorkflowStepSpec]:
        return [WorkflowStepSpec.from_dict(s) if isinstance(s, dict) else s
                for s in self.steps]


@dc.dataclass
class WorkflowRun(_DictMixin):
    run_id: str = dc.field(default_factory=workflow_run_id)
    workflow_id: str = ""
    started_at: str = dc.field(default_factory=_now)
    finished_at: str | None = None
    status: str = "created"
    total_steps: int = 0
    completed_steps: int = 0
    step_runs: list[dict[str, Any]] = _list()
    error_message: str | None = None


@dc.dataclass
class WorkflowResult(_DictMixin):
    result_id: str = dc.field(default_factory=workflow_result_id)
    run_id: str = ""
    workflow_id: str = ""
    status: str = "created"
    entities: dict[str, Any] = _dict()
    step_results: list[dict[str, Any]] = _list()
    final_outputs: dict[str, Any] = _dict()
    evidence_audit: dict[str, Any] | None = None
    unknowns: list[str] = _list()
    warnings: list[str] = _list()


@dc.dataclass
class WorkflowTrace(_DictMixin):
    trace_id: str = dc.field(default_factory=workflow_trace_id)
    run_id: str = ""
    workflow_id: str = ""
    step_traces: list[dict[str, Any]] = _list()
    steps_log: list[str] = _list()
    final_status: str = ""
    total_duration_ms: float = 0.0
    llm_usage_total: dict[str, Any] | None = None
