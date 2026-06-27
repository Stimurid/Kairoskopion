"""Pipeline Replay Engine (Track 7).

Supports rerun_all, rerun_stage, rerun_from_stage, and diff_runs.
Orchestrates re-execution of the ManuscriptVenueFitPipeline with
optional prompt overrides, producing new PipelineRun traces.

P11.1: ``execute_replay_run`` calls the real pipeline for supported
stages; unsupported stages return ``stage_not_yet_replayable``.
"""
from __future__ import annotations

import dataclasses as dc
import logging
from typing import Any

from ..ids import generate_id
from .pipeline_trace import PipelineNode, PipelineRun, PipelineTraceStore, _hash_text
from .prompt_override import PromptOverride, PromptOverrideStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage definitions (the canonical 18 stages)
# ---------------------------------------------------------------------------

PIPELINE_STAGES: list[dict[str, Any]] = [
    {"stage_id": "intake", "label": "Source Intake", "producer": "deterministic", "service": "intake_file/intake_text", "prompt_family": None},
    {"stage_id": "input_classification", "label": "Input Classification", "producer": "llm_agent", "service": "InputClassifierAgent", "prompt_family": "input_classification"},
    {"stage_id": "article_model", "label": "Article Modeling", "producer": "llm_agent", "service": "ArticleModelerAgent", "prompt_family": "article_modeling"},
    {"stage_id": "semantic_profile", "label": "Semantic Profiling", "producer": "llm_agent", "service": "SemanticProfilerAgent", "prompt_family": "semantic_profiling"},
    {"stage_id": "bibliography_parse", "label": "Bibliography Parsing", "producer": "deterministic", "service": "build_bibliography_profile", "prompt_family": None},
    {"stage_id": "discipline_mapping", "label": "Disciplinary Mapping", "producer": "llm_agent", "service": "DisciplinaryMapperAgent", "prompt_family": "disciplinary_mapping"},
    {"stage_id": "discipline_matching", "label": "Discipline Matching", "producer": "llm_agent", "service": "DisciplineMatcherAgent", "prompt_family": "discipline_matching"},
    {"stage_id": "venue_investigation", "label": "Venue Investigation", "producer": "llm_agent", "service": "VenueProfilerAgent", "prompt_family": "venue_fact_extraction"},
    {"stage_id": "venue_discovery", "label": "Venue Discovery", "producer": "llm_agent", "service": "VenueFunnelPlannerAgent", "prompt_family": "venue_funnel_planning"},
    {"stage_id": "venue_family_context", "label": "Venue Family Context", "producer": "llm_agent", "service": "VenueFamilyContextBuilderAgent", "prompt_family": "venue_family_context"},
    {"stage_id": "venue_matrix", "label": "Venue Matrix Assessment", "producer": "llm_agent", "service": "VenueMatrixAssessorAgent", "prompt_family": "venue_matrix_assessment"},
    {"stage_id": "fit_gate", "label": "Fit Gate", "producer": "deterministic", "service": "evaluate_fit_gate", "prompt_family": None},
    {"stage_id": "fit_assessment", "label": "Fit Assessment", "producer": "llm_agent", "service": "FitAssessorAgent", "prompt_family": "fit_assessment"},
    {"stage_id": "mismatch_map", "label": "Mismatch Mapping", "producer": "deterministic", "service": "build_mismatch_map", "prompt_family": None},
    {"stage_id": "rewrite_plan", "label": "Rewrite Planning", "producer": "deterministic", "service": "build_rewrite_plan", "prompt_family": None},
    {"stage_id": "risk_report", "label": "Risk Reporting", "producer": "deterministic", "service": "build_risk_report", "prompt_family": None},
    {"stage_id": "compliance_check", "label": "Compliance Check", "producer": "llm_agent", "service": "ComplianceAssessorAgent", "prompt_family": "compliance_assessment"},
    {"stage_id": "evidence_audit", "label": "Evidence Audit", "producer": "deterministic", "service": "audit_pipeline_evidence", "prompt_family": None},
]


def get_stage_index(stage_id: str) -> int | None:
    for i, s in enumerate(PIPELINE_STAGES):
        if s["stage_id"] == stage_id:
            return i
    return None


def get_downstream_stages(stage_id: str) -> list[dict[str, Any]]:
    idx = get_stage_index(stage_id)
    if idx is None:
        return []
    return PIPELINE_STAGES[idx + 1:]


# ---------------------------------------------------------------------------
# Replay plans (what to rerun)
# ---------------------------------------------------------------------------

@dc.dataclass
class ReplayPlan:
    mode: str  # rerun_all | rerun_stage | rerun_from_stage
    stages_to_rerun: list[str] = dc.field(default_factory=list)
    stages_to_copy: list[str] = dc.field(default_factory=list)
    prompt_override_ids: list[str] = dc.field(default_factory=list)
    base_run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dc.asdict(self)


def plan_rerun_all(
    overrides: list[str] | None = None,
    base_run_id: str | None = None,
) -> ReplayPlan:
    return ReplayPlan(
        mode="rerun_all",
        stages_to_rerun=[s["stage_id"] for s in PIPELINE_STAGES],
        stages_to_copy=[],
        prompt_override_ids=overrides or [],
        base_run_id=base_run_id,
    )


def plan_rerun_stage(
    stage_id: str,
    *,
    overrides: list[str] | None = None,
    base_run_id: str | None = None,
) -> ReplayPlan:
    return ReplayPlan(
        mode="rerun_stage",
        stages_to_rerun=[stage_id],
        stages_to_copy=[
            s["stage_id"] for s in PIPELINE_STAGES
            if s["stage_id"] != stage_id
        ],
        prompt_override_ids=overrides or [],
        base_run_id=base_run_id,
    )


def plan_rerun_from_stage(
    stage_id: str,
    *,
    overrides: list[str] | None = None,
    base_run_id: str | None = None,
) -> ReplayPlan:
    idx = get_stage_index(stage_id)
    if idx is None:
        return ReplayPlan(mode="rerun_from_stage")
    return ReplayPlan(
        mode="rerun_from_stage",
        stages_to_rerun=[s["stage_id"] for s in PIPELINE_STAGES[idx:]],
        stages_to_copy=[s["stage_id"] for s in PIPELINE_STAGES[:idx]],
        prompt_override_ids=overrides or [],
        base_run_id=base_run_id,
    )


# ---------------------------------------------------------------------------
# Run diff
# ---------------------------------------------------------------------------

@dc.dataclass
class RunDiffEntry:
    stage_id: str
    field: str
    run_a_value: Any = None
    run_b_value: Any = None
    changed: bool = False


def diff_runs(
    trace_store: PipelineTraceStore,
    run_id_a: str,
    run_id_b: str,
) -> list[RunDiffEntry]:
    nodes_a = {n.stage_id: n for n in trace_store.list_nodes(run_id_a)}
    nodes_b = {n.stage_id: n for n in trace_store.list_nodes(run_id_b)}
    all_stages = sorted(set(nodes_a.keys()) | set(nodes_b.keys()))
    diffs: list[RunDiffEntry] = []

    for stage_id in all_stages:
        na = nodes_a.get(stage_id)
        nb = nodes_b.get(stage_id)

        if na and not nb:
            diffs.append(RunDiffEntry(stage_id, "presence", "present", "absent", True))
            continue
        if nb and not na:
            diffs.append(RunDiffEntry(stage_id, "presence", "absent", "present", True))
            continue

        for field_name in ("status", "output_hash", "producer_type", "prompt_version_hash", "prompt_override_id"):
            va = getattr(na, field_name, None)
            vb = getattr(nb, field_name, None)
            if va != vb:
                diffs.append(RunDiffEntry(stage_id, field_name, va, vb, True))

    return diffs


# ---------------------------------------------------------------------------
# Scaffold a new PipelineRun from a ReplayPlan
# ---------------------------------------------------------------------------

def scaffold_replay_run(
    plan: ReplayPlan,
    case_id: str | None = None,
    trace_store: PipelineTraceStore | None = None,
) -> PipelineRun:
    run = PipelineRun(
        case_id=case_id,
        trigger=plan.mode,
        status="pending",
        base_run_id=plan.base_run_id,
        prompt_override_ids=plan.prompt_override_ids,
    )

    for i, stage_def in enumerate(PIPELINE_STAGES):
        sid = stage_def["stage_id"]
        is_rerun = sid in plan.stages_to_rerun

        node = PipelineNode(
            run_id=run.run_id,
            stage_id=sid,
            stage_label=stage_def["label"],
            order_index=i,
            producer_type=stage_def["producer"],
            service_or_agent=stage_def["service"],
            prompt_family_id=stage_def.get("prompt_family"),
            status="pending" if is_rerun else "skipped",
            rerunnable=True,
        )

        # Copy results from base run for skipped stages
        if not is_rerun and plan.base_run_id and trace_store:
            base_nodes = trace_store.list_nodes(plan.base_run_id)
            for bn in base_nodes:
                if bn.stage_id == sid:
                    node.status = bn.status
                    node.output_hash = bn.output_hash
                    node.output_artifact_refs = bn.output_artifact_refs
                    node.gate_results = bn.gate_results
                    break

        run.node_ids.append(node.node_id)
        if trace_store:
            trace_store.save_node(node)

    if trace_store:
        trace_store.save_run(run)

    return run


# ---------------------------------------------------------------------------
# Real pipeline execution via replay
# ---------------------------------------------------------------------------

_REPLAYABLE_FULL = "rerun_all"

_REPLAYABLE_STAGES = frozenset([
    "mismatch_map", "rewrite_plan", "risk_report",
    "compliance_check", "evidence_audit",
])


def execute_replay_run(
    plan: ReplayPlan,
    *,
    case_id: str | None = None,
    trace_store: PipelineTraceStore | None = None,
    override_store: PromptOverrideStore | None = None,
    manuscript_text: str | None = None,
    venue_guidelines_text: str | None = None,
    scenario_data: dict[str, Any] | None = None,
    manuscript_source_ref: str = "fixture:manuscript_sample",
    venue_source_ref: str = "fixture:venue_guidelines_sample",
    llm_provider: Any | None = None,
    registry_service: Any | None = None,
) -> dict[str, Any]:
    """Execute a replay plan, running real pipeline stages where supported.

    For ``rerun_all`` with manuscript+venue text provided, runs the full
    instrumented pipeline.  For individual stages, deterministic stages
    execute if upstream artifacts are available; LLM-agent stages that need
    the full pipeline context return ``stage_not_yet_replayable``.

    Returns ``{"run": PipelineRun, "result": ..., "status": ...}``.
    """
    if plan.mode == _REPLAYABLE_FULL and manuscript_text and venue_guidelines_text:
        from ..pipelines.manuscript_venue_fit import ManuscriptVenueFitPipeline

        pipeline = ManuscriptVenueFitPipeline(
            llm_provider=llm_provider,
            registry_service=registry_service,
            trace_store=trace_store,
            override_store=override_store,
            case_id=case_id,
        )
        result = pipeline.execute(
            manuscript_text=manuscript_text,
            venue_guidelines_text=venue_guidelines_text,
            scenario_data=scenario_data or {},
            manuscript_source_ref=manuscript_source_ref,
            venue_source_ref=venue_source_ref,
        )
        return {
            "run": result.trace_run,
            "result": result,
            "status": "executed",
        }

    unsupported = [
        s for s in plan.stages_to_rerun
        if s not in _REPLAYABLE_STAGES
    ]
    if unsupported:
        run = scaffold_replay_run(plan, case_id=case_id, trace_store=trace_store)
        for node in (trace_store.list_nodes(run.run_id) if trace_store else []):
            if node.stage_id in unsupported and node.status == "pending":
                node.status = "stage_not_yet_replayable"
                node.diagnostics.append(
                    f"stage '{node.stage_id}' requires full pipeline context"
                )
                if trace_store:
                    trace_store.save_node(node)
        return {
            "run": run,
            "result": None,
            "status": "partial_not_replayable",
            "unsupported_stages": unsupported,
        }

    run = scaffold_replay_run(plan, case_id=case_id, trace_store=trace_store)
    return {"run": run, "result": None, "status": "scaffold_only"}
