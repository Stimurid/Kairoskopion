"""Run the UC-1 demo pack through the full pipeline and produce outputs.

Orchestrates: load demo pack → run UC-1 workflow → write artifacts to output dir.
All execution is offline and deterministic (no LLM, no network).

Three modes:
  1. Discovery mode (default when no venue entity): draft → profile → pathways → pool
  2. Selected-venue fit mode (--select-candidate N): discovery + promote candidate → full fit
  3. Full submission mode (legacy — venue entity provided): full pack
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .uc1_demo_loader import UC1DemoPack, load_uc1_demo_pack
from ..agents.orchestrator import run_workflow
from ..agents.workflows import get_workflow_spec

logger = logging.getLogger(__name__)


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
    mode: str = "discovery"
    selected_candidate: dict[str, Any] | None = None

    @property
    def is_success(self) -> bool:
        return self.workflow_status in ("completed", "partial") and not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_status": self.workflow_status,
            "mode": self.mode,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "step_results": self.step_results,
            "entity_keys": list(self.entities.keys()),
            "trace_log": self.trace_log,
            "errors": self.errors,
            "pack_summary": self.pack.to_dict(),
            "selected_candidate": self.selected_candidate,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_uc1_demo(
    pack_dir: Path | None = None,
    output_dir: Path | None = None,
    *,
    select_candidate_index: int | None = None,
    live_enabled: bool = False,
    cache_dir: str | None = None,
) -> UC1DemoResult:
    """Run the full UC-1 demo pipeline.

    Args:
        pack_dir: Path to demo pack directory (default: bundled fixtures).
        output_dir: If provided, write all artifacts here.
        select_candidate_index: If set, run discovery first, then promote
            the candidate at this 0-based index to ``venue`` entity and
            re-run the full fit/submission pipeline. Candidate must not
            have blocking conflicts.
        live_enabled: Enable live API queries for discovery.
        cache_dir: HTTP cache directory for live queries.

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

    if select_candidate_index is not None:
        return _run_selected_venue_mode(
            pack, result, output_dir,
            select_candidate_index=select_candidate_index,
            live_enabled=live_enabled,
            cache_dir=cache_dir,
        )

    return _run_discovery_mode(
        pack, result, output_dir,
        live_enabled=live_enabled,
        cache_dir=cache_dir,
    )


def _run_discovery_mode(
    pack: UC1DemoPack,
    result: UC1DemoResult,
    output_dir: Path | None,
    *,
    live_enabled: bool = False,
    cache_dir: str | None = None,
) -> UC1DemoResult:
    """Discovery mode: draft → profile → pathways → venue pool."""
    result.mode = "discovery"

    spec = get_workflow_spec("uc1_draft_to_venue_pool_positioning")

    initial_entities: dict[str, Any] = {}
    if pack.venue_seeds:
        initial_entities["venue_pool"] = pack.venue_seeds
    if pack.scenario:
        initial_entities["scenario"] = pack.scenario

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


def _run_selected_venue_mode(
    pack: UC1DemoPack,
    result: UC1DemoResult,
    output_dir: Path | None,
    *,
    select_candidate_index: int,
    live_enabled: bool = False,
    cache_dir: str | None = None,
) -> UC1DemoResult:
    """Selected-venue mode: discovery → select candidate → full fit pipeline."""
    result.mode = "selected_venue"

    # Phase 1: run discovery to get candidates
    discovery = _run_discovery_mode(
        pack,
        UC1DemoResult(pack=pack, started_at=result.started_at),
        None,
        live_enabled=live_enabled,
        cache_dir=cache_dir,
    )

    if discovery.workflow_status not in ("completed", "partial"):
        result.errors.append(f"Discovery failed: {discovery.workflow_status}")
        result.workflow_status = "discovery_failed"
        result.finished_at = _now()
        return result

    # Extract candidates from venue_pool entity
    venue_pool_entity = discovery.entities.get("venue_pool", {})
    pool = venue_pool_entity.get("pool", venue_pool_entity)
    candidates = pool.get("candidates", [])

    if not candidates:
        result.errors.append("No candidates discovered — cannot select venue")
        result.workflow_status = "no_candidates"
        result.entities = discovery.entities
        result.step_results = discovery.step_results
        result.finished_at = _now()
        return result

    if select_candidate_index < 0 or select_candidate_index >= len(candidates):
        result.errors.append(
            f"Candidate index {select_candidate_index} out of range "
            f"(0..{len(candidates) - 1})"
        )
        result.workflow_status = "invalid_selection"
        result.entities = discovery.entities
        result.step_results = discovery.step_results
        result.finished_at = _now()
        return result

    candidate = candidates[select_candidate_index]

    # Check for blocking conflicts
    conflicts = candidate.get("conflicts", [])
    blocking = [c for c in conflicts if c.get("severity") == "blocking"]
    if blocking:
        result.errors.append(
            f"Cannot promote candidate '{candidate.get('canonical_name')}' — "
            f"has {len(blocking)} blocking conflict(s): "
            + "; ".join(c.get("type", "?") for c in blocking)
        )
        result.workflow_status = "blocked_by_conflict"
        result.entities = discovery.entities
        result.step_results = discovery.step_results
        result.selected_candidate = candidate
        result.finished_at = _now()
        return result

    # Phase 2: promote candidate to venue entity and run full pipeline
    venue_entity = _candidate_to_venue_entity(candidate)
    result.selected_candidate = candidate

    spec = get_workflow_spec("uc1_draft_to_venue_pool_positioning")

    initial_entities: dict[str, Any] = {
        "venue": venue_entity,
        "venue_pool": pack.venue_seeds or [],
    }
    if pack.scenario:
        initial_entities["scenario"] = pack.scenario

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
    result.entities["_discovery"] = discovery.entities

    trace = getattr(wf_result, "_trace", None)
    if trace and hasattr(trace, "steps_log"):
        result.trace_log = list(trace.steps_log)

    result.finished_at = _now()

    if output_dir:
        _write_artifacts(result, output_dir)

    return result


def _candidate_to_venue_entity(candidate: dict[str, Any]) -> dict[str, Any]:
    """Convert a VenueCandidate dict to a venue entity for the fit pipeline."""
    raw = candidate.get("raw_adapter_data", {})

    venue: dict[str, Any] = {
        "name": candidate.get("canonical_name", ""),
        "canonical_name": candidate.get("canonical_name", ""),
        "issn": candidate.get("issn"),
        "issn_l": candidate.get("issn_l"),
        "official_urls": candidate.get("urls", []),
        "aliases": candidate.get("aliases", []),
        "_promoted_from_candidate": candidate.get("venue_candidate_id"),
        "_candidate_sources": candidate.get("sources", []),
        "_candidate_confidence": candidate.get("confidence", "low"),
    }

    for source_data in raw.values():
        if isinstance(source_data, dict):
            if source_data.get("publisher"):
                venue.setdefault("publisher", source_data["publisher"])
            if source_data.get("type"):
                venue.setdefault("venue_type", source_data["type"])
            if source_data.get("homepage_url"):
                venue.setdefault("official_urls", []).append(source_data["homepage_url"])

    return venue


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
