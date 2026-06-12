"""Run the UC-1 demo pack through the full pipeline and produce outputs.

Orchestrates: load demo pack → run UC-1 workflow → write artifacts to output dir.
All execution is offline and deterministic (no LLM, no network).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .uc1_demo_loader import UC1DemoPack, load_uc1_demo_pack
from ..agents.orchestrator import run_workflow
from ..agents.workflows import get_workflow_spec


@dataclass
class UC1DemoResult:
    """Result of running the UC-1 demo."""

    pack: UC1DemoPack
    workflow_status: str = "not_run"
    workflow_result: Any = None
    step_results: list[dict[str, Any]] = field(default_factory=list)
    entities: dict[str, Any] = field(default_factory=dict)
    trace_log: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    @property
    def is_success(self) -> bool:
        return self.workflow_status in ("completed", "partial") and not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_status": self.workflow_status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "step_results": self.step_results,
            "entity_keys": list(self.entities.keys()),
            "trace_log": self.trace_log,
            "errors": self.errors,
            "pack_summary": self.pack.to_dict(),
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_uc1_demo(
    pack_dir: Path | None = None,
    output_dir: Path | None = None,
) -> UC1DemoResult:
    """Run the full UC-1 demo pipeline.

    Args:
        pack_dir: Path to demo pack directory (default: bundled fixtures).
        output_dir: If provided, write all artifacts here.

    Returns:
        UC1DemoResult with workflow outcome and all entities.
    """
    pack = load_uc1_demo_pack(pack_dir)
    result = UC1DemoResult(pack=pack, started_at=_now())

    if not pack.is_valid:
        result.errors.extend(pack.errors)
        result.workflow_status = "load_failed"
        result.finished_at = _now()
        return result

    spec = get_workflow_spec("uc1_draft_to_venue_pool_positioning")

    initial_entities: dict[str, Any] = {}

    if pack.venue_seeds:
        initial_entities["venue"] = pack.venue_seeds[0]
        initial_entities["venue_pool"] = pack.venue_seeds

    scenario = pack.scenario
    if scenario:
        initial_entities["scenario"] = scenario

    wf_result = run_workflow(
        spec,
        initial_entities=initial_entities,
        raw_text=pack.draft_text,
        provider=None,
        prefer_deterministic=True,
        stop_on_failure=False,
    )

    result.workflow_status = wf_result.status
    result.workflow_result = wf_result
    result.step_results = wf_result.step_results
    result.entities = wf_result.entities

    trace = getattr(wf_result, "_trace", None)
    if trace and hasattr(trace, "steps_log"):
        result.trace_log = list(trace.steps_log)

    result.finished_at = _now()

    if output_dir:
        _write_artifacts(result, output_dir)

    return result


def _write_artifacts(result: UC1DemoResult, output_dir: Path) -> None:
    """Write demo artifacts to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    workflow_trace_path = output_dir / "workflow_trace.json"
    workflow_trace_path.write_text(
        json.dumps({
            "workflow_id": "uc1_draft_to_venue_pool_positioning",
            "status": result.workflow_status,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "step_results": result.step_results,
            "trace_log": result.trace_log,
        }, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    for key, entity in result.entities.items():
        entity_path = output_dir / f"{key}.json"
        try:
            entity_path.write_text(
                json.dumps(entity, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except (TypeError, ValueError):
            entity_path.write_text(
                json.dumps({"_raw": str(entity)}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    from .uc1_report import generate_uc1_demo_report
    report_text = generate_uc1_demo_report(result)
    report_path = output_dir / "UC1_DEMO_REPORT.md"
    report_path.write_text(report_text, encoding="utf-8")
