"""Agent registry — all AgentSpec entries and agent class lookups."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .runtime_models import AgentSpec

if TYPE_CHECKING:
    from .contract import AgentRole

# ---------------------------------------------------------------------------
# Agent specs — one per agent role
# ---------------------------------------------------------------------------

_SPECS: list[AgentSpec] = [
    # --- Control layer ---
    AgentSpec(
        role_id="discipline_matcher",
        display_name="Discipline Matcher",
        layer="article",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["discipline_matching"],
        input_contract={
            "entities.article_summary": "str — concise summary of article",
            "entities.region": "ru|international|... — registry slice",
        },
        output_contract={
            "DisciplineMatch": (
                "matched (≤4 ids + strength + why) + "
                "new_candidate (or null) + confidence + reasoning"
            ),
        },
        mvp_phase="v0.2",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="discipline_source_acquisition",
        display_name="Discipline Source Acquisition",
        layer="article",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["discipline_source_acquisition"],
        input_contract={
            "entities.discipline_name": "str — discipline to seed",
            "entities.region": "ru|international|...",
            "entities.hints": "optional list of source hints",
        },
        output_contract={
            "DisciplineSourceAcquisitionResult": (
                "packets (≤3 DisciplineSourcePackets) + reasoning"
            ),
        },
        mvp_phase="v0.2",
        first_workflows=["discipline_registry_growth"],
    ),
    AgentSpec(
        role_id="discipline_seeder",
        display_name="Discipline Seeder",
        layer="article",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["discipline_seeding"],
        input_contract={
            "entities.discipline_name": "str",
            "entities.region": "ru|international|...",
            "entities.packets": "list of DisciplineSourcePacket dicts",
        },
        output_contract={
            "DisciplineModel": "draft card with source_status=llm_draft",
        },
        mvp_phase="v0.2",
        first_workflows=["discipline_registry_growth"],
    ),
    AgentSpec(
        role_id="input_classifier",
        display_name="Input Classifier",
        layer="control",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["input_classification"],
        input_contract={"raw_text": "pasted/uploaded text"},
        output_contract={
            "InputClassification": (
                "input_type (manuscript|venue|review_letter|unknown) + "
                "confidence + needs_user_choice + language_detected"
            )
        },
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="intent_classifier",
        display_name="Intent Classifier",
        layer="control",
        implementation_status="operational_now",
        execution_mode="deterministic",
        input_contract={"raw_text": "user input string"},
        output_contract={"IntentClassification": "intent_type + confidence"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="scenario_prober",
        display_name="Scenario Prober",
        layer="control",
        implementation_status="operational_now",
        execution_mode="deterministic",
        prompt_family_ids=["scenario_interview"],
        input_contract={"raw_text": "user scenario description"},
        output_contract={"Scenario": "structured scenario model"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="research_planner",
        display_name="Research Planner",
        layer="control",
        implementation_status="operational_now",
        execution_mode="deterministic",
        input_contract={"entities": "current pipeline state"},
        output_contract={"ResearchPlan": "needed_steps list"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="status_job",
        display_name="Status Job",
        layer="control",
        implementation_status="operational_now",
        execution_mode="deterministic",
        input_contract={"entities": "pipeline entities dict"},
        output_contract={"StatusReport": "entity availability summary"},
        mvp_phase="v0.1",
    ),

    # --- Article layer ---
    AgentSpec(
        role_id="article_modeler",
        display_name="Article Modeler",
        layer="article",
        implementation_status="operational_now",
        execution_mode="deterministic",
        input_contract={"raw_text": "article/draft text"},
        output_contract={"ArticleModel": "structured article model"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning", "direct_manuscript_venue_fit"],
    ),
    AgentSpec(
        role_id="article_semantic_profiler",
        display_name="Article Semantic Profiler",
        aliases=["semantic_profiler"],
        layer="article",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["semantic_profiling"],
        input_contract={"entities.article": "ArticleModel dict"},
        output_contract={"ArticleSemanticProfile": "semantic dimensions"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="article_field_positioner",
        display_name="Article Field Positioner",
        layer="article",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["article_field_position"],
        input_contract={
            "entities.article": "ArticleModel dict",
            "entities.semantic_profile": "ArticleSemanticProfile dict (optional)",
            "raw_text": "manuscript text (optional)",
        },
        output_contract={"FieldPositionModel": "article position vectors (point)"},
        mvp_phase="v0.2",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="disciplinary_pathway_mapper",
        display_name="Disciplinary Pathway Mapper",
        aliases=["disciplinary_mapper"],
        layer="article",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["disciplinary_mapping"],
        input_contract={"entities.semantic_profile": "ArticleSemanticProfile dict"},
        output_contract={"DisciplinaryPathway[]": "list of pathways"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),

    # --- Venue layer ---
    AgentSpec(
        role_id="venue_identifier",
        display_name="Venue Identifier",
        layer="venue",
        implementation_status="operational_now",
        execution_mode="deterministic",
        input_contract={"venue_reference": "name/ISSN/URL dict or raw_text"},
        output_contract={"VenueIdentification": "identity candidate + resolution_status + unknowns"},
        mvp_phase="v0.1",
        first_workflows=["direct_manuscript_venue_fit"],
    ),
    AgentSpec(
        role_id="venue_discovery",
        display_name="Venue Discovery",
        layer="venue",
        implementation_status="operational_now",
        execution_mode="deterministic",
        input_contract={"entities.pathways": "DisciplinaryPathway[] dicts"},
        output_contract={"VenueModel[]": "matched venues + search tasks"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="venue_profiler",
        display_name="Venue Profiler",
        layer="venue",
        implementation_status="operational_now",
        execution_mode="deterministic",
        input_contract={"entities.venue": "VenueModel dict"},
        output_contract={"VenueModel": "enriched venue model"},
        mvp_phase="v0.1",
        first_workflows=["venue_deep_profile", "direct_manuscript_venue_fit"],
    ),
    AgentSpec(
        role_id="publication_regime_classifier",
        display_name="Publication Regime Classifier",
        layer="venue",
        implementation_status="executable_stub",
        execution_mode="llm_optional",
        prompt_family_ids=["publication_regime"],
        input_contract={"entities.venue": "VenueModel dict"},
        output_contract={"PublicationRegime": "regime classification"},
        mvp_phase="v0.1",
        first_workflows=["venue_deep_profile"],
    ),
    AgentSpec(
        role_id="corpus_sampler",
        display_name="Corpus Sampler",
        layer="venue",
        implementation_status="operational_now",
        execution_mode="deterministic",
        input_contract={"entities.venue": "VenueModel dict"},
        output_contract={"CorpusSample": "PublishedArticleCorpus + sampling notes"},
        mvp_phase="v0.1",
        first_workflows=["venue_deep_profile"],
    ),
    AgentSpec(
        role_id="venue_publication_profile_builder",
        display_name="Venue Publication Profile Builder",
        layer="venue",
        implementation_status="operational_now",
        execution_mode="deterministic",
        input_contract={"entities.venue": "VenueModel dict"},
        output_contract={"VenuePublicationProfile": "full publication profile"},
        mvp_phase="v0.1",
        first_workflows=["venue_deep_profile", "uc1_draft_to_venue_pool_positioning"],
    ),

    AgentSpec(
        role_id="venue_field_positioner",
        display_name="Venue Field Positioner",
        layer="venue",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["venue_field_position"],
        input_contract={
            "entities.venue": "VenueModel dict",
            "entities.editorial_board": "editorial board dict (optional)",
            "entities.corpus_summary": "corpus summary dict (optional)",
            "entities.venue_guidelines_text": "guidelines text (optional)",
        },
        output_contract={"FieldPositionModel": "venue position envelope (region)"},
        mvp_phase="v0.2",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),

    # --- Fit layer ---
    AgentSpec(
        role_id="fit_assessor",
        display_name="Fit Assessor",
        layer="fit",
        implementation_status="operational_now",
        execution_mode="deterministic",
        input_contract={"entities.article": "ArticleModel", "entities.venue": "VenueModel"},
        output_contract={"FitAssessment": "fit score + dimensions"},
        mvp_phase="v0.1",
        first_workflows=["direct_manuscript_venue_fit", "uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="mismatch_mapper",
        display_name="Mismatch Mapper",
        layer="fit",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["mismatch_mapping"],
        input_contract={"entities.article": "ArticleModel", "entities.venue": "VenueModel",
                        "entities.fit_assessment": "FitAssessment"},
        output_contract={"MismatchMap": "mismatches with severity"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="rewrite_planner",
        display_name="Rewrite Planner",
        layer="fit",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["rewrite_planning"],
        input_contract={"entities.mismatch_map": "MismatchMap"},
        output_contract={"RewritePlan": "ordered adaptation actions"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="citation_planner",
        display_name="Citation Planner",
        layer="fit",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["citation_ecology"],
        input_contract={"entities.article": "ArticleModel", "entities.venue": "VenueModel"},
        output_contract={"CitationEcologyReport": "citation gaps + recommendations"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),

    # --- Submission layer ---
    AgentSpec(
        role_id="risk_officer",
        display_name="Risk Officer",
        layer="submission",
        implementation_status="operational_now",
        execution_mode="llm_optional",
        prompt_family_ids=["risk_reporting"],
        input_contract={"entities.article": "ArticleModel", "entities.venue": "VenueModel"},
        output_contract={"RiskReport": "risk items + severity"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="compliance_auditor",
        display_name="Compliance Auditor",
        layer="submission",
        implementation_status="operational_now",
        execution_mode="deterministic",
        prompt_family_ids=["compliance_checklist"],
        input_contract={"entities.article": "ArticleModel", "entities.venue": "VenueModel"},
        output_contract={"ComplianceChecklist": "checklist items + missing"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="submission_pack_builder",
        display_name="Submission Pack Builder",
        layer="submission",
        implementation_status="operational_now",
        execution_mode="deterministic",
        prompt_family_ids=["submission_pack"],
        input_contract={"entities.article": "ArticleModel", "entities.venue": "VenueModel"},
        output_contract={"SubmissionPack": "readiness + assembled pack"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),

    # --- Review layer (all contract-only) ---
    AgentSpec(
        role_id="reviewer_simulation",
        display_name="Reviewer Simulation",
        layer="review",
        implementation_status="contract_only",
        execution_mode="llm_required",
        prompt_family_ids=["review_outcome"],
        input_contract={"entities.article": "ArticleModel", "entities.venue": "VenueModel"},
        output_contract={"SimulatedReview": "predicted reviewer feedback"},
        mvp_phase="future",
        first_workflows=["review_loop"],
    ),
    AgentSpec(
        role_id="review_outcome_analyst",
        display_name="Review Outcome Analyst",
        layer="review",
        implementation_status="contract_only",
        execution_mode="llm_required",
        prompt_family_ids=["review_outcome"],
        input_contract={"entities.review_data": "raw review text/JSON"},
        output_contract={"ReviewOutcomeAnalysis": "structured interpretation"},
        mvp_phase="future",
        first_workflows=["review_loop"],
    ),
    AgentSpec(
        role_id="revision_planner",
        display_name="Revision Planner",
        layer="review",
        implementation_status="contract_only",
        execution_mode="llm_required",
        input_contract={"entities.review_analysis": "ReviewOutcomeAnalysis"},
        output_contract={"RevisionPlan": "prioritized revision actions"},
        mvp_phase="future",
        first_workflows=["review_loop"],
    ),
    AgentSpec(
        role_id="rebuttal_architect",
        display_name="Rebuttal Architect",
        layer="review",
        implementation_status="contract_only",
        execution_mode="llm_required",
        input_contract={"entities.review_analysis": "ReviewOutcomeAnalysis"},
        output_contract={"RebuttalStrategy": "structured rebuttal plan"},
        mvp_phase="future",
        first_workflows=["review_loop"],
    ),
    AgentSpec(
        role_id="tacit_signal_structurer",
        display_name="Tacit Signal Structurer",
        layer="review",
        implementation_status="contract_only",
        execution_mode="llm_required",
        input_contract={"entities.review_data": "raw review text"},
        output_contract={"TacitSignalReport": "implicit signals decoded"},
        mvp_phase="future",
        first_workflows=["review_loop"],
    ),
    AgentSpec(
        role_id="venue_memory_keeper",
        display_name="Venue Memory Keeper",
        layer="review",
        implementation_status="contract_only",
        execution_mode="llm_required",
        input_contract={"entities.review_outcome": "ReviewOutcomeAnalysis"},
        output_contract={"VenueMemoryUpdate": "accumulated experience"},
        memory_policy="append_to_venue_memory",
        mvp_phase="future",
        first_workflows=["review_loop"],
    ),

    # --- Evidence layer ---
    AgentSpec(
        role_id="evidence_auditor",
        display_name="Evidence Auditor",
        layer="evidence",
        implementation_status="operational_now",
        execution_mode="deterministic",
        prompt_family_ids=["evidence_audit"],
        input_contract={
            "entities.article": "ArticleModel",
            "entities.venue": "VenueModel",
            "entities.fit_assessment": "FitAssessment",
            "entities.mismatch_map": "MismatchMap",
            "entities.risk_report": "RiskReport",
            "entities.compliance": "ComplianceChecklist",
        },
        output_contract={"QualityGateResult": "gate status + findings"},
        mvp_phase="v0.1",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
    AgentSpec(
        role_id="reference_verifier",
        display_name="Reference Verifier",
        layer="evidence",
        implementation_status="operational_now",
        execution_mode="deterministic",
        input_contract={
            "entities.bibliography_profile": "BibliographyProfile (or raw_text fallback)",
        },
        output_contract={"ReferenceVerificationResult": "per-ref integrity checks + aggregates"},
        mvp_phase="v0.2",
        first_workflows=["uc1_draft_to_venue_pool_positioning"],
    ),
]


# ---------------------------------------------------------------------------
# Lookup structures
# ---------------------------------------------------------------------------

AGENT_SPEC_REGISTRY: dict[str, AgentSpec] = {s.role_id: s for s in _SPECS}


def _build_agent_class_map() -> dict[str, type]:
    """Lazy import to avoid circular deps — maps role_id to AgentRole subclass."""
    from .article_field_positioner import ArticleFieldPositionerAgent
    from .article_modeler import ArticleModelerAgent
    from .discipline_matcher import DisciplineMatcherAgent
    from .discipline_source_acquisition import DisciplineSourceAcquisitionAgent
    from .discipline_seeder import DisciplineSeederAgent
    from .input_classifier import InputClassifierAgent
    from .semantic_profiler import ArticleSemanticProfilerAgent
    from .disciplinary_mapper import DisciplinaryPathwayMapperAgent
    from .fit_assessor import FitAssessorAgent
    from .venue_field_positioner import VenueFieldPositionerAgent
    from .venue_profiler import VenueProfilerAgent
    from .control import (
        IntentClassifierAgent, ScenarioProberAgent,
        ResearchPlannerAgent, StatusJobAgent,
    )
    from .venue import (
        CorpusSamplerAgent, VenueIdentifierAgent, VenueDiscoveryAgent,
        PublicationRegimeClassifierAgent, VenuePublicationProfileBuilderAgent,
    )
    from .fit import (
        MismatchMapperAgent, RewritePlannerAgent, CitationPlannerAgent,
    )
    from .submission import (
        RiskOfficerAgent, ComplianceAuditorAgent, SubmissionPackBuilderAgent,
    )
    from .review import (
        ReviewerSimulationAgent, ReviewOutcomeAnalystAgent,
        RevisionPlannerAgent, RebuttalArchitectAgent,
        TacitSignalStructurerAgent, VenueMemoryKeeperAgent,
    )
    from .evidence import EvidenceAuditorAgent, ReferenceVerifierAgent

    return {
        "discipline_matcher": DisciplineMatcherAgent,
        "discipline_source_acquisition": DisciplineSourceAcquisitionAgent,
        "discipline_seeder": DisciplineSeederAgent,
        "input_classifier": InputClassifierAgent,
        "intent_classifier": IntentClassifierAgent,
        "scenario_prober": ScenarioProberAgent,
        "research_planner": ResearchPlannerAgent,
        "status_job": StatusJobAgent,
        "article_modeler": ArticleModelerAgent,
        "article_semantic_profiler": ArticleSemanticProfilerAgent,
        "article_field_positioner": ArticleFieldPositionerAgent,
        "disciplinary_pathway_mapper": DisciplinaryPathwayMapperAgent,
        "venue_identifier": VenueIdentifierAgent,
        "venue_discovery": VenueDiscoveryAgent,
        "venue_profiler": VenueProfilerAgent,
        "venue_field_positioner": VenueFieldPositionerAgent,
        "corpus_sampler": CorpusSamplerAgent,
        "publication_regime_classifier": PublicationRegimeClassifierAgent,
        "venue_publication_profile_builder": VenuePublicationProfileBuilderAgent,
        "fit_assessor": FitAssessorAgent,
        "mismatch_mapper": MismatchMapperAgent,
        "rewrite_planner": RewritePlannerAgent,
        "citation_planner": CitationPlannerAgent,
        "risk_officer": RiskOfficerAgent,
        "compliance_auditor": ComplianceAuditorAgent,
        "submission_pack_builder": SubmissionPackBuilderAgent,
        "reviewer_simulation": ReviewerSimulationAgent,
        "review_outcome_analyst": ReviewOutcomeAnalystAgent,
        "revision_planner": RevisionPlannerAgent,
        "rebuttal_architect": RebuttalArchitectAgent,
        "tacit_signal_structurer": TacitSignalStructurerAgent,
        "venue_memory_keeper": VenueMemoryKeeperAgent,
        "evidence_auditor": EvidenceAuditorAgent,
        "reference_verifier": ReferenceVerifierAgent,
    }


_CLASS_MAP: dict[str, type] | None = None


def get_agent_class(role_id: str) -> type[AgentRole]:
    global _CLASS_MAP
    if _CLASS_MAP is None:
        _CLASS_MAP = _build_agent_class_map()
    cls = _CLASS_MAP.get(role_id)
    if cls is None:
        raise KeyError(f"Unknown agent role_id: {role_id}")
    return cls


def get_agent_spec(role_id: str) -> AgentSpec:
    spec = AGENT_SPEC_REGISTRY.get(role_id)
    if spec is None:
        raise KeyError(f"Unknown agent role_id: {role_id}")
    return spec


def list_agent_specs() -> list[AgentSpec]:
    return list(_SPECS)


def list_agent_ids() -> list[str]:
    return [s.role_id for s in _SPECS]


def instantiate_agent(role_id: str) -> AgentRole:
    cls = get_agent_class(role_id)
    return cls()
