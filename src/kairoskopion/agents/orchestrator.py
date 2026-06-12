"""Workflow orchestrator — runs AgenticWorkflowSpec step by step.

Sequential execution only (v0.1). Each step's output feeds into the
shared entity pool for subsequent steps.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .contract import AgentInput
from .executor import execute_agent
from .runtime_models import (
    AgenticWorkflowSpec,
    WorkflowResult,
    WorkflowRun,
    WorkflowStepSpec,
    WorkflowTrace,
)
from ..llm.provider import LLMProvider


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_workflow(
    spec: AgenticWorkflowSpec,
    initial_entities: dict[str, Any] | None = None,
    raw_text: str | None = None,
    provider: LLMProvider | None = None,
    *,
    prefer_deterministic: bool = True,
    stop_on_failure: bool = True,
) -> WorkflowResult:
    """Execute all steps in a workflow spec sequentially."""
    entities: dict[str, Any] = dict(initial_entities or {})
    steps = spec.get_steps()

    wf_run = WorkflowRun(
        workflow_id=spec.workflow_id,
        status="running",
        started_at=_now(),
        total_steps=len(steps),
    )

    wf_trace = WorkflowTrace(
        run_id=wf_run.run_id,
        workflow_id=spec.workflow_id,
    )

    step_results: list[dict[str, Any]] = []
    completed = 0
    failed = 0

    for i, step in enumerate(steps):
        step_label = f"step[{i}] {step.agent_role_id}"
        wf_trace.steps_log.append(f"START {step_label}")

        if step.skip_if_missing:
            missing = [k for k in step.skip_if_missing if k not in entities]
            if missing:
                wf_trace.steps_log.append(
                    f"SKIP {step_label}: missing {missing}"
                )
                step_results.append({
                    "step_index": i,
                    "agent_role_id": step.agent_role_id,
                    "status": "skipped",
                    "reason": f"missing entities: {missing}",
                })
                continue

        inp = AgentInput(
            operation_id=f"{wf_run.run_id}_step{i}",
            agent_role_id=step.agent_role_id,
            input_entity_refs=list(entities.keys()),
            raw_text=raw_text if i == 0 else None,
            entities=_select_entities(entities, step),
        )

        result = execute_agent(
            step.agent_role_id,
            inp,
            provider,
            prefer_deterministic=prefer_deterministic,
        )

        if result.failure:
            failed += 1
            wf_trace.steps_log.append(
                f"FAIL {step_label}: {result.failure.error_message}"
            )
            step_results.append({
                "step_index": i,
                "agent_role_id": step.agent_role_id,
                "status": "failed",
                "error": result.failure.error_message,
            })
            if stop_on_failure:
                break
            continue

        completed += 1
        output = result.output_entity
        if step.output_key and output:
            entity_value = output.get("output_entity", output)
            entities[step.output_key] = entity_value
            wf_trace.steps_log.append(
                f"OK {step_label} -> entities[{step.output_key}]"
            )
        else:
            wf_trace.steps_log.append(f"OK {step_label} (no output_key)")

        step_results.append({
            "step_index": i,
            "agent_role_id": step.agent_role_id,
            "status": "completed",
            "confidence": result.confidence,
            "evidence_status": result.evidence_status,
        })

    wf_run.completed_steps = completed
    wf_run.finished_at = _now()

    if failed > 0 and stop_on_failure:
        wf_run.status = "failed"
    elif failed > 0:
        wf_run.status = "partial"
    else:
        wf_run.status = "completed"

    wf_trace.final_status = wf_run.status
    wf_trace.steps_log.append(
        f"DONE: {completed}/{len(steps)} completed, {failed} failed"
    )

    wf_result = WorkflowResult(
        run_id=wf_run.run_id,
        workflow_id=spec.workflow_id,
        status=wf_run.status,
        entities=entities,
        step_results=step_results,
    )
    wf_result._trace = wf_trace
    wf_result._run = wf_run

    return wf_result


def _select_entities(
    entities: dict[str, Any], step: WorkflowStepSpec
) -> dict[str, Any]:
    """Select the entities relevant to this step."""
    if step.input_keys:
        return {k: entities[k] for k in step.input_keys if k in entities}
    return dict(entities)
