"""Agent executor — runs a single agent by role_id.

Handles: task creation, run tracking, deterministic/LLM dispatch,
result and trace assembly, failure capture.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Any

from .contract import AgentInput, AgentOutput
from .registry import get_agent_spec, instantiate_agent
from .runtime_models import (
    AgentFailure,
    AgentResult,
    AgentRun,
    AgentTask,
    AgentTrace,
)
from ..llm.provider import LLMProvider


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute_agent(
    role_id: str,
    inp: AgentInput,
    provider: LLMProvider | None = None,
    *,
    prefer_deterministic: bool = True,
) -> AgentResult:
    """Execute a single agent and return AgentResult with full trace."""
    spec = get_agent_spec(role_id)
    agent = instantiate_agent(role_id)

    task = AgentTask(
        agent_role_id=role_id,
        input_entity_refs=inp.input_entity_refs,
        raw_text=inp.raw_text,
        entities=inp.entities,
    )

    run = AgentRun(
        task_id=task.task_id,
        agent_role_id=role_id,
        status="running",
        started_at=_now(),
    )

    trace = AgentTrace(
        run_id=run.run_id,
        agent_role_id=role_id,
    )
    trace.steps_log.append(f"spec.implementation_status={spec.implementation_status}")

    try:
        use_deterministic = (
            prefer_deterministic
            or provider is None
            or spec.execution_mode == "deterministic"
        )

        if use_deterministic:
            trace.steps_log.append("dispatch=execute_deterministic")
            output = agent.execute_deterministic(inp)
        else:
            trace.steps_log.append("dispatch=execute(LLM)")
            output = agent.execute(inp, provider)

        run.status = "completed"
        run.finished_at = _now()

        out_dict = _output_to_dict(output)
        result = AgentResult(
            run_id=run.run_id,
            agent_role_id=role_id,
            output_entity_type=output.output_entity_type,
            output_entity=out_dict,
            evidence_refs=output.evidence_refs,
            unknowns=output.unknowns,
            confidence=output.confidence,
            evidence_status=output.evidence_status,
        )

        trace.steps_log.append(f"confidence={output.confidence}")
        trace.steps_log.append(f"evidence_status={output.evidence_status}")
        trace.final_status = "completed"
        result._trace = trace
        result._run = run
        result._task = task

        return result

    except Exception as exc:
        run.status = "failed"
        run.finished_at = _now()

        failure = AgentFailure(
            error_type=type(exc).__name__,
            error_message=str(exc),
            traceback=traceback.format_exc(),
        )

        trace.steps_log.append(f"FAILED: {type(exc).__name__}: {exc}")
        trace.final_status = "failed"

        result = AgentResult(
            run_id=run.run_id,
            agent_role_id=role_id,
            output_entity={},
            confidence="none",
            evidence_status="INACCESSIBLE",
            failure=failure,
        )
        result._trace = trace
        result._run = run
        result._task = task

        return result


def _output_to_dict(output: AgentOutput) -> dict[str, Any]:
    return {
        "output_entity_type": output.output_entity_type,
        "output_entity": output.output_entity,
        "evidence_refs": output.evidence_refs,
        "unknowns": output.unknowns,
        "assumptions": output.assumptions,
        "confidence": output.confidence,
        "warnings": output.warnings,
        "quality_gate_status": output.quality_gate_status,
        "evidence_status": output.evidence_status,
    }
