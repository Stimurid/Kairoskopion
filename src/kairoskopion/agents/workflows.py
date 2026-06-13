"""Predefined workflow specs for Kairoskopion agentic contour v0.1.

Four workflows:
1. direct_manuscript_venue_fit — fast path: article + known venue → fit
2. uc1_draft_to_venue_pool_positioning — full UC-1 pipeline
3. venue_deep_profile — venue enrichment sub-workflow
4. review_loop — post-submission review cycle (skeleton)
"""

from __future__ import annotations

from .runtime_models import AgenticWorkflowSpec


def _step(
    index: int,
    role_id: str,
    *,
    output_key: str = "",
    input_keys: list[str] | None = None,
    skip_if_missing: list[str] | None = None,
    required: bool = True,
    description: str = "",
) -> dict:
    return {
        "step_index": index,
        "agent_role_id": role_id,
        "output_key": output_key,
        "input_keys": input_keys or [],
        "skip_if_missing": skip_if_missing or [],
        "required": required,
        "description": description,
    }


# ---------------------------------------------------------------------------
# 1. Direct manuscript–venue fit (fast path)
# ---------------------------------------------------------------------------

DIRECT_MANUSCRIPT_VENUE_FIT = AgenticWorkflowSpec(
    workflow_id="direct_manuscript_venue_fit",
    display_name="Direct Manuscript–Venue Fit",
    description="Article + known venue → identity → evidence → fit + mismatch + rewrite + risk + compliance",
    implementation_status="executable",
    steps=[
        _step(0, "article_modeler",
              output_key="article",
              description="Parse draft into ArticleModel"),
        _step(1, "venue_identifier",
              output_key="venue_identity",
              input_keys=["venue"],
              skip_if_missing=["venue"],
              required=False,
              description="Resolve venue reference to identity candidate"),
        _step(2, "fit_assessor",
              output_key="fit_assessment",
              input_keys=["article", "venue"],
              description="Assess fit between article and venue"),
        _step(3, "mismatch_mapper",
              output_key="mismatch_map",
              input_keys=["article", "venue", "fit_assessment"],
              description="Map mismatches with severity"),
        _step(4, "rewrite_planner",
              output_key="rewrite_plan",
              input_keys=["article", "venue", "mismatch_map"],
              description="Plan adaptation actions"),
        _step(5, "citation_planner",
              output_key="citation_report",
              input_keys=["article", "venue"],
              description="Analyze citation ecology"),
        _step(6, "risk_officer",
              output_key="risk_report",
              input_keys=["article", "venue", "fit_assessment", "mismatch_map"],
              description="Assess submission risks"),
        _step(7, "compliance_auditor",
              output_key="compliance",
              input_keys=["article", "venue"],
              description="Check compliance requirements"),
        _step(8, "evidence_auditor",
              output_key="evidence_gate",
              input_keys=["article", "venue", "fit_assessment",
                          "mismatch_map", "risk_report", "compliance"],
              description="Audit evidence across pipeline outputs"),
    ],
)

# ---------------------------------------------------------------------------
# 2. UC-1: Draft → Venue Pool Positioning (full pipeline)
# ---------------------------------------------------------------------------

UC1_DRAFT_TO_VENUE_POOL_POSITIONING = AgenticWorkflowSpec(
    workflow_id="uc1_draft_to_venue_pool_positioning",
    display_name="UC-1: Draft → Venue Pool Positioning",
    description=(
        "Full UC-1: draft → ArticleModel → SemanticProfile → "
        "DisciplinaryPathways → VenueDiscovery → VenueProfiles → "
        "fit screening → mismatch/rewrite/citation/risk → evidence audit"
    ),
    implementation_status="executable",
    steps=[
        _step(0, "article_modeler",
              output_key="article",
              description="Parse draft into ArticleModel"),
        _step(1, "article_semantic_profiler",
              output_key="semantic_profile",
              input_keys=["article"],
              description="Build semantic profile"),
        _step(2, "disciplinary_pathway_mapper",
              output_key="pathways",
              input_keys=["semantic_profile"],
              description="Map disciplinary pathways"),
        _step(3, "venue_discovery",
              output_key="venue_pool",
              input_keys=["pathways", "semantic_profile", "scenario", "venue_pool"],
              description="Discover candidate venues via adapters and seed corpus"),
        _step(4, "fit_assessor",
              output_key="fit_assessment",
              input_keys=["article", "venue"],
              skip_if_missing=["venue"],
              description="Assess fit (requires venue entity — not from venue_pool)"),
        _step(5, "mismatch_mapper",
              output_key="mismatch_map",
              input_keys=["article", "venue", "fit_assessment"],
              skip_if_missing=["venue", "fit_assessment"],
              description="Map mismatches"),
        _step(6, "rewrite_planner",
              output_key="rewrite_plan",
              input_keys=["article", "mismatch_map"],
              skip_if_missing=["mismatch_map"],
              description="Plan rewrites"),
        _step(7, "citation_planner",
              output_key="citation_report",
              input_keys=["article", "venue"],
              skip_if_missing=["venue"],
              description="Citation ecology analysis"),
        _step(8, "risk_officer",
              output_key="risk_report",
              input_keys=["article", "venue", "scenario",
                          "fit_assessment", "mismatch_map"],
              skip_if_missing=["venue", "scenario", "fit_assessment", "mismatch_map"],
              description="Risk assessment"),
        _step(9, "compliance_auditor",
              output_key="compliance",
              input_keys=["article", "venue"],
              skip_if_missing=["venue"],
              description="Compliance check"),
        _step(10, "submission_pack_builder",
               output_key="submission_pack",
               input_keys=["article", "venue", "scenario",
                           "fit_assessment", "risk_report", "compliance"],
               skip_if_missing=["venue", "scenario"],
               description="Assemble submission pack"),
        _step(11, "evidence_auditor",
               output_key="evidence_gate",
               input_keys=["article", "venue", "fit_assessment",
                           "mismatch_map", "risk_report", "compliance"],
               skip_if_missing=["venue", "compliance"],
               description="Final evidence audit"),
    ],
)

# ---------------------------------------------------------------------------
# 3. Venue Deep Profile (sub-workflow)
# ---------------------------------------------------------------------------

VENUE_DEEP_PROFILE = AgenticWorkflowSpec(
    workflow_id="venue_deep_profile",
    display_name="Venue Deep Profile",
    description="Enrich a venue: profiler + corpus sampling + regime classifier + publication profile builder",
    implementation_status="executable",
    steps=[
        _step(0, "venue_profiler",
              output_key="venue",
              input_keys=["venue"],
              description="Enrich venue model from corpus"),
        _step(1, "corpus_sampler",
              output_key="corpus",
              input_keys=["venue"],
              required=False,
              description="Sample venue corpus for pattern analysis"),
        _step(2, "publication_regime_classifier",
              output_key="publication_regime",
              input_keys=["venue"],
              description="Classify publication regime"),
        _step(3, "venue_publication_profile_builder",
              output_key="venue_publication_profile",
              input_keys=["venue", "corpus"],
              description="Build full publication profile from venue and corpus data"),
    ],
)

# ---------------------------------------------------------------------------
# 4. Review Loop (skeleton — all steps contract-only)
# ---------------------------------------------------------------------------

REVIEW_LOOP = AgenticWorkflowSpec(
    workflow_id="review_loop",
    display_name="Review Loop",
    description="Post-submission review cycle: simulate → analyze → revise → rebuttal",
    implementation_status="skeleton",
    steps=[
        _step(0, "reviewer_simulation",
              output_key="simulated_review",
              input_keys=["article", "venue"],
              description="Simulate reviewer feedback"),
        _step(1, "review_outcome_analyst",
              output_key="review_analysis",
              input_keys=["simulated_review"],
              description="Analyze review outcome"),
        _step(2, "tacit_signal_structurer",
              output_key="tacit_signals",
              input_keys=["simulated_review"],
              required=False,
              description="Decode implicit reviewer signals"),
        _step(3, "revision_planner",
              output_key="revision_plan",
              input_keys=["review_analysis", "article"],
              description="Plan revisions"),
        _step(4, "rebuttal_architect",
              output_key="rebuttal_strategy",
              input_keys=["review_analysis"],
              description="Architect rebuttal"),
        _step(5, "venue_memory_keeper",
              output_key="venue_memory",
              input_keys=["review_analysis", "venue"],
              required=False,
              description="Update venue memory from experience"),
    ],
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

WORKFLOW_REGISTRY: dict[str, AgenticWorkflowSpec] = {
    wf.workflow_id: wf
    for wf in [
        DIRECT_MANUSCRIPT_VENUE_FIT,
        UC1_DRAFT_TO_VENUE_POOL_POSITIONING,
        VENUE_DEEP_PROFILE,
        REVIEW_LOOP,
    ]
}


def get_workflow_spec(workflow_id: str) -> AgenticWorkflowSpec:
    spec = WORKFLOW_REGISTRY.get(workflow_id)
    if spec is None:
        raise KeyError(f"Unknown workflow_id: {workflow_id}")
    return spec


def list_workflow_specs() -> list[AgenticWorkflowSpec]:
    return list(WORKFLOW_REGISTRY.values())


def list_workflow_ids() -> list[str]:
    return list(WORKFLOW_REGISTRY.keys())
