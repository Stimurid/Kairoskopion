"""Domain models for Kairoskopion MVP-0.

All models are plain dataclasses with to_dict()/from_dict() for JSON
serialization.  Fields follow the spec (Waves 1–5) but only MVP-minimal
fields are required; the rest default to None or empty.
"""

from __future__ import annotations

import dataclasses as dc
from datetime import datetime, timezone
from typing import Any

from .enums import (
    ArticleStage,
    AssessmentLevel,
    EntryChannel,
    EvidenceStatus,
    FieldCoreImpact,
    FitAxisValue,
    FitLabel,
    Genre,
    InputMode,
    LifecycleStatus,
    MethodStatus,
    MismatchSeverity,
    NoveltyMode,
    OutputLevel,
    PipelineRunStatus,
    RegimeType,
    RewriteDepth,
    StalenessStatus,
    SubmissionReadiness,
    VenueType,
)
from .ids import (
    article_model_id,
    bibliography_profile_id,
    candidate_evidence_matrix_id,
    citation_ecology_report_id,
    citation_plan_id,
    compliance_checklist_id,
    evidence_item_id,
    fit_assessment_id,
    manuscript_id,
    mismatch_map_id,
    pipeline_run_id,
    publication_regime_id,
    reference_item_id,
    rewrite_plan_id,
    risk_report_id,
    source_snapshot_id,
    submission_pack_id,
    submission_scenario_id,
    trajectory_report_id,
    venue_candidate_id,
    venue_candidate_pool_id,
    venue_candidate_screening_id,
    venue_claim_id,
    venue_discovery_query_id,
    venue_evidence_pack_id,
    venue_model_id,
    venue_publication_profile_id,
    venue_record_id,
    venue_source_id,
    article_semantic_profile_id,
    article_variant_id,
    citation_expectation_profile_id,
    disciplinary_pathway_id,
    editorial_board_profile_id,
    field_position_id,
    published_article_corpus_id,
    source_evidence_packet_id,
    protected_core_policy_id,
    evidence_policy_id,
    venue_profile_package_id,
    editorial_board_cloud_id,
    editorial_board_member_id,
    published_corpus_hull_id,
    method_expectation_profile_id,
    genre_move_profile_id,
    style_register_profile_id,
    author_eligibility_profile_id,
    time_review_profile_id,
    apc_access_profile_id,
    tacit_venue_signal_id,
    journal_model_id,
    section_model_id,
    special_issue_model_id,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _field(default=None):
    return dc.field(default=default)


def _list():
    return dc.field(default_factory=list)


def _dict():
    return dc.field(default_factory=dict)


# ---------------------------------------------------------------------------
# Base mixin
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
            if hasattr(v, "value"):
                return v.value
            return v
        return {k: _convert(v) for k, v in dc.asdict(self).items()}  # type: ignore[arg-type]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Any:
        field_names = {f.name for f in dc.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)


# ---------------------------------------------------------------------------
# Evidence & Source models (Wave 2 §6.2)
# ---------------------------------------------------------------------------

@dc.dataclass
class EvidenceItem(_DictMixin):
    evidence_id: str = dc.field(default_factory=evidence_item_id)
    source_id: str | None = _field()
    source_type: str | None = _field()
    url_or_file_ref: str | None = _field()
    title: str | None = _field()
    retrieved_at: str | None = _field()
    extracted_at: str | None = _field()
    excerpt_or_locator: str | None = _field()
    page_or_section: str | None = _field()
    claim_supported: str | None = _field()
    evidence_status: str = EvidenceStatus.UNKNOWN.value
    confidence: str | None = _field()
    used_in_entities: list[str] = _list()
    staleness_policy: str | None = _field()
    notes: str | None = _field()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class SourceSnapshot(_DictMixin):
    snapshot_id: str = dc.field(default_factory=source_snapshot_id)
    source_id: str | None = _field()
    url: str | None = _field()
    retrieved_at: str | None = _field()
    content_hash: str | None = _field()
    content_type: str | None = _field()
    parser_used: str | None = _field()
    raw_ref: str | None = _field()
    text_ref: str | None = _field()
    extraction_status: str | None = _field()
    extraction_errors: list[str] = _list()
    staleness_policy: str | None = _field()
    used_in_context_packs: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Article models (Wave 2 §6.3–6.4)
# ---------------------------------------------------------------------------

@dc.dataclass
class ArticleModel(_DictMixin):
    article_model_id: str = dc.field(default_factory=article_model_id)
    source_refs: list[str] = _list()
    title_current: str | None = _field()
    abstract_current: str | None = _field()
    language: str | None = _field()
    input_mode: str = InputMode.UNKNOWN.value if hasattr(InputMode, "UNKNOWN") else "mixed"
    article_stage: str = ArticleStage.UNKNOWN.value
    problem_statement: str | None = _field()
    research_question: str | None = _field()
    object_of_inquiry: str | None = _field()
    core_claims: list[str] = _list()
    genre_current: str = Genre.UNKNOWN.value
    disciplinary_register_current: str | None = _field()
    novelty_mode: str = NoveltyMode.UNKNOWN.value
    method_status: str = MethodStatus.UNKNOWN.value
    method_description: str | None = _field()
    theoretical_shoulders: list[str] = _list()
    citation_ecology_current: str | None = _field()
    protected_core: list[str] = _list()
    mutable_zones: list[str] = _list()
    unknowns: list[str] = _list()
    confidence: str | None = _field()
    evidence_refs: list[str] = _list()
    lifecycle_status: str = LifecycleStatus.DRAFT.value
    created_at: str = dc.field(default_factory=_now)
    updated_at: str = dc.field(default_factory=_now)
    # Sprint 2: practical diagnostic fields
    word_count: int | None = _field()
    section_count: int | None = _field()
    reference_count: int | None = _field()
    abstract_length: int | None = _field()
    has_references_section: bool | None = _field()
    has_methods_section: bool | None = _field()
    has_data_availability_statement: bool | None = _field()
    has_ai_disclosure: bool | None = _field()
    manuscript_stage: str | None = _field()
    protected_core_status: str | None = _field()
    extraction_status: str | None = _field()
    # LLM attempt audit (per llm.attempt_metadata.LLMAttemptMetadata).
    # None for purely-deterministic builds; populated for LLM agent runs.
    extraction_attempt: dict[str, Any] | None = _field()


@dc.dataclass
class ManuscriptModel(_DictMixin):
    manuscript_id: str = dc.field(default_factory=manuscript_id)
    article_model_id: str | None = _field()
    source_file_refs: list[str] = _list()
    title: str | None = _field()
    abstract: str | None = _field()
    keywords: list[str] = _list()
    sections: list[str] = _list()
    word_count: int | None = _field()
    language: str | None = _field()
    bibliography_refs: list[str] = _list()
    format: str | None = _field()
    version: int = 1
    unknowns: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)
    updated_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Venue models (Wave 2 §6.7–6.11)
# ---------------------------------------------------------------------------

@dc.dataclass
class VenueModel(_DictMixin):
    venue_model_id: str = dc.field(default_factory=venue_model_id)
    canonical_name: str | None = _field()
    venue_type: str = VenueType.JOURNAL.value
    official_urls: list[str] = _list()
    scope_summary: str | None = _field()
    author_guidelines_refs: list[str] = _list()
    article_types_supported: list[str] = _list()
    language_policy: str | None = _field()
    publication_regime_id: str | None = _field()
    publisher_or_owner: str | None = _field()
    source_refs: list[str] = _list()
    context_pack_refs: list[str] = _list()
    unknowns: list[str] = _list()
    confidence: str | None = _field()
    evidence_refs: list[str] = _list()
    staleness_status: str = StalenessStatus.UNKNOWN_FRESHNESS.value
    lifecycle_status: str = LifecycleStatus.DRAFT.value
    created_at: str = dc.field(default_factory=_now)
    updated_at: str = dc.field(default_factory=_now)
    # Sprint 2: enrichment fields (claims, not verified facts)
    aims_scope_summary: str | None = _field()
    indexing_claims: list[str] = _list()
    metrics_claims: list[str] = _list()
    open_access_status: str | None = _field()
    apc_policy: str | None = _field()
    review_process_claims: str | None = _field()
    word_limits: dict[str, Any] | None = _field()
    anonymization_policy: str | None = _field()
    ai_policy: str | None = _field()
    data_policy: str | None = _field()
    ethics_policy: str | None = _field()
    freshness_status: str | None = _field()


@dc.dataclass
class PublicationRegimeModel(_DictMixin):
    publication_regime_id: str = dc.field(default_factory=publication_regime_id)
    regime_type: str = RegimeType.CLASSIC_JOURNAL_ARTICLE.value
    description: str | None = _field()
    review_model: str | None = _field()
    submission_gates: list[str] = _list()
    typical_article_forms: list[str] = _list()
    timeline_pattern: str | None = _field()
    evidence_refs: list[str] = _list()
    unknowns: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Submission scenario (Wave 2 §6.17)
# ---------------------------------------------------------------------------

@dc.dataclass
class SubmissionScenario(_DictMixin):
    submission_scenario_id: str = dc.field(default_factory=submission_scenario_id)
    article_model_id: str | None = _field()
    target_venue_ids: list[str] = _list()
    goal: str | None = _field()
    target_indexing: str | None = _field()
    prestige_priority: str | None = _field()
    speed_priority: str | None = _field()
    APC_constraints: str | None = _field()
    language_constraints: str | None = _field()
    deadline: str | None = _field()
    rewrite_depth_allowed: str = RewriteDepth.UNKNOWN.value
    reframe_depth_allowed: str | None = _field()
    risk_tolerance: str | None = _field()
    fallback_allowed: list[str] = _list()
    unknowns: list[str] = _list()
    lifecycle_status: str = LifecycleStatus.DRAFT.value
    created_at: str = dc.field(default_factory=_now)
    updated_at: str = dc.field(default_factory=_now)
    # feature/venue-fit-dossier-slice: when fit runs without an
    # operator-provided scenario, _run_fit_chain synthesizes a default
    # SubmissionScenario with this flag set. The dossier UI must
    # display a banner ("Scenario preliminary — answers from the
    # operator missing") so the fit verdict is not read as final.
    scenario_preliminary: bool = False


# ---------------------------------------------------------------------------
# Fit & Adaptation (Wave 2 §6.18–6.22)
# ---------------------------------------------------------------------------

@dc.dataclass
class FitAxis(_DictMixin):
    axis: str = ""
    value: str = FitAxisValue.UNKNOWN.value
    evidence_refs: list[str] = _list()
    unknowns: list[str] = _list()
    confidence: str | None = _field()
    notes: str | None = _field()


@dc.dataclass
class FitAssessment(_DictMixin):
    fit_assessment_id: str = dc.field(default_factory=fit_assessment_id)
    article_model_id: str | None = _field()
    venue_model_id: str | None = _field()
    submission_scenario_id: str | None = _field()
    assessment_level: str = AssessmentLevel.QUICK_SCAN.value
    overall_label: str = FitLabel.NOT_ENOUGH_DATA.value
    axes: list[dict[str, Any]] = _list()
    confidence: str | None = _field()
    evidence_refs: list[str] = _list()
    unknowns: list[str] = _list()
    mismatch_map_id: str | None = _field()
    recommendation: str | None = _field()
    lifecycle_status: str = LifecycleStatus.PRELIMINARY.value
    created_at: str = dc.field(default_factory=_now)
    # LLM attempt audit per llm.attempt_metadata.LLMAttemptMetadata.
    # Same vocabulary as ArticleModel and DisciplinaryPathway.
    extraction_attempt: dict[str, Any] | None = _field()


@dc.dataclass
class MismatchItem(_DictMixin):
    mismatch_id: str = ""
    axis: str = ""
    article_side: str | None = _field()
    venue_side: str | None = _field()
    description: str | None = _field()
    severity: str = MismatchSeverity.INFORMATIONAL.value
    evidence_refs: list[str] = _list()
    possible_actions: list[str] = _list()
    field_core_risk: str = FieldCoreImpact.UNKNOWN_CORE_IMPACT.value
    requires_user_acceptance: bool = False


@dc.dataclass
class MismatchMap(_DictMixin):
    mismatch_map_id: str = dc.field(default_factory=mismatch_map_id)
    fit_assessment_id: str | None = _field()
    mismatches: list[dict[str, Any]] = _list()
    summary: str | None = _field()
    critical_mismatches: list[str] = _list()
    unknowns: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)
    # V2-B1 diagnostic: populated by _run_fit_chain after MismatchNarrator
    # runs. Distinguishes "LLM returned empty" / "missing axes" / "axis
    # mismatch" / "parser failed" / "provider error" so 0/N narrator
    # coverage is observable instead of collapsed to one count.
    # Never contains raw LLM output. None when chain didn't run narrator.
    narrator_coverage: dict[str, Any] | None = None


@dc.dataclass
class RewritePlan(_DictMixin):
    rewrite_plan_id: str = dc.field(default_factory=rewrite_plan_id)
    article_model_id: str | None = _field()
    manuscript_id: str | None = _field()
    fit_assessment_id: str | None = _field()
    target_venue_id: str | None = _field()
    changes: list[dict[str, Any]] = _list()
    summary: str | None = _field()
    estimated_effort: str | None = _field()
    field_core_risk: str = FieldCoreImpact.UNKNOWN_CORE_IMPACT.value
    requires_user_acceptance: bool = True
    lifecycle_status: str = LifecycleStatus.DRAFT.value
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class CitationPlan(_DictMixin):
    citation_plan_id: str = dc.field(default_factory=citation_plan_id)
    article_model_id: str | None = _field()
    venue_model_id: str | None = _field()
    current_bibliography_status: str | None = _field()
    missing_bridge_categories: list[str] = _list()
    recommended_reference_search_tasks: list[str] = _list()
    dangerous_padding_warnings: list[str] = _list()
    evidence_refs: list[str] = _list()
    risk_flags: list[str] = _list()
    lifecycle_status: str = LifecycleStatus.DRAFT.value
    created_at: str = dc.field(default_factory=_now)
    # V2-D minimal-real fields
    fit_assessment_id: str | None = _field()
    status: str = "not_built"
    citation_gap_categories: list[str] = _list()
    verification_tasks: list[str] = _list()
    venue_citation_expectation_status: str | None = _field()
    unknowns: list[str] = _list()
    created_from: list[str] = _list()
    confidence: str | None = _field()


# ---------------------------------------------------------------------------
# Citation ecology (bibliography parsing + venue fit)
# ---------------------------------------------------------------------------

@dc.dataclass
class ReferenceItem(_DictMixin):
    reference_item_id: str = dc.field(default_factory=reference_item_id)
    raw_text: str = ""
    year: int | None = _field()
    doi: str | None = _field()
    source_kind: str = "unknown"
    author_fragment: str | None = _field()
    title_fragment: str | None = _field()
    venue_fragment: str | None = _field()
    is_self_citation: bool = False
    verification_status: str = "not_verified"


@dc.dataclass
class BibliographyProfile(_DictMixin):
    bibliography_profile_id: str = dc.field(default_factory=bibliography_profile_id)
    manuscript_id: str | None = _field()
    article_model_id: str | None = _field()
    total_references: int = 0
    references: list[dict[str, Any]] = _list()
    year_min: int | None = _field()
    year_max: int | None = _field()
    year_median: int | None = _field()
    doi_count: int = 0
    source_kind_distribution: dict[str, int] = _dict()
    recency_profile: str | None = _field()
    reference_style: str | None = _field()
    unknowns: list[str] = _list()
    disclaimer: str = "Bibliography parsed heuristically from text. Not externally verified."
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class CitationGap(_DictMixin):
    gap_id: str = ""
    gap_type: str = ""
    description: str | None = _field()
    severity: str = "informational"
    suggested_action: str | None = _field()
    venue_expectation: str | None = _field()


@dc.dataclass
class CitationTask(_DictMixin):
    task_id: str = ""
    task_type: str = ""
    description: str | None = _field()
    priority: str = "medium"
    related_gap_id: str | None = _field()
    requires_external_api: bool = False


@dc.dataclass
class CitationEcologyReport(_DictMixin):
    citation_ecology_report_id: str = dc.field(default_factory=citation_ecology_report_id)
    article_model_id: str | None = _field()
    venue_model_id: str | None = _field()
    bibliography_profile_id: str | None = _field()
    gaps: list[dict[str, Any]] = _list()
    tasks: list[dict[str, Any]] = _list()
    bridge_references_detected: list[str] = _list()
    warning_signals: list[str] = _list()
    unknowns: list[str] = _list()
    summary: str | None = _field()
    disclaimer: str = "Citation ecology analysis is heuristic. References not externally verified."
    lifecycle_status: str = LifecycleStatus.PRELIMINARY.value
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Compliance & Risk (Wave 2 §6.23–6.25)
# ---------------------------------------------------------------------------

@dc.dataclass
class RiskItem(_DictMixin):
    risk_id: str = ""
    risk_type: str = ""
    description: str | None = _field()
    severity: str | None = _field()
    likelihood: str | None = _field()
    evidence_refs: list[str] = _list()
    mitigation: str | None = _field()
    requires_user_action: bool = False


@dc.dataclass
class RiskReport(_DictMixin):
    risk_report_id: str = dc.field(default_factory=risk_report_id)
    article_model_id: str | None = _field()
    venue_model_id: str | None = _field()
    submission_scenario_id: str | None = _field()
    risk_items: list[dict[str, Any]] = _list()
    overall_risk_label: str | None = _field()
    blocking_risks: list[str] = _list()
    warnings: list[str] = _list()
    unknowns: list[str] = _list()
    evidence_refs: list[str] = _list()
    lifecycle_status: str = LifecycleStatus.DRAFT.value
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class ComplianceChecklist(_DictMixin):
    compliance_checklist_id: str = dc.field(default_factory=compliance_checklist_id)
    venue_model_id: str | None = _field()
    article_model_id: str | None = _field()
    publication_regime_id: str | None = _field()
    checklist_items: list[dict[str, Any]] = _list()
    guideline_sources: list[str] = _list()
    missing_items: list[str] = _list()
    blocking_items: list[str] = _list()
    warnings: list[str] = _list()
    evidence_refs: list[str] = _list()
    lifecycle_status: str = LifecycleStatus.DRAFT.value
    created_at: str = dc.field(default_factory=_now)
    # V2-D minimal-real fields
    submission_scenario_id: str | None = _field()
    status: str = "not_built"
    unknowns: list[str] = _list()
    created_from: list[str] = _list()
    confidence: str | None = _field()


@dc.dataclass
class SubmissionPack(_DictMixin):
    submission_pack_id: str = dc.field(default_factory=submission_pack_id)
    article_model_id: str | None = _field()
    manuscript_id: str | None = _field()
    venue_model_id: str | None = _field()
    submission_scenario_id: str | None = _field()
    compliance_checklist_id: str | None = _field()
    files: list[str] = _list()
    metadata: dict[str, Any] = _dict()
    statements: list[str] = _list()
    cover_letter: str | None = _field()
    missing_items: list[str] = _list()
    blocking_issues: list[str] = _list()
    warnings: list[str] = _list()
    ready_status: str = SubmissionReadiness.NOT_READY.value
    created_at: str = dc.field(default_factory=_now)
    updated_at: str = dc.field(default_factory=_now)
    # V2-D minimal-real fields
    citation_plan_id: str | None = _field()
    status: str = "not_built"
    next_actions: list[str] = _list()
    depends_on: list[str] = _list()
    created_from: list[str] = _list()
    unknowns: list[str] = _list()


# ---------------------------------------------------------------------------
# Publication Trajectory Report (Sprint 5)
# ---------------------------------------------------------------------------

@dc.dataclass
class PublicationTrajectoryReport(_DictMixin):
    """Comprehensive summary combining fit, risk, bibliography, and recommendations."""
    report_id: str = dc.field(default_factory=trajectory_report_id)
    article_model_id: str | None = _field()
    venue_model_id: str | None = _field()
    fit_summary: str | None = _field()
    risk_summary: str | None = _field()
    bibliography_summary: str | None = _field()
    strengths: list[str] = _list()
    weaknesses: list[str] = _list()
    critical_actions: list[str] = _list()
    optional_improvements: list[str] = _list()
    overall_recommendation: str | None = _field()
    confidence: str | None = _field()
    unknowns: list[str] = _list()
    lifecycle_status: str = LifecycleStatus.DRAFT.value
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Pipeline (Wave 5 §36.1)
# ---------------------------------------------------------------------------

@dc.dataclass
class PipelineRun(_DictMixin):
    pipeline_run_id: str = dc.field(default_factory=pipeline_run_id)
    pipeline_type: str | None = _field()
    entry_channel: str = EntryChannel.CLI.value
    status: str = PipelineRunStatus.CREATED.value
    input_refs: list[str] = _list()
    created_entity_ids: list[str] = _list()
    updated_entity_ids: list[str] = _list()
    source_ids_used: list[str] = _list()
    context_pack_ids_used: list[str] = _list()
    quality_gate_results: list[dict[str, Any]] = _list()
    warnings: list[str] = _list()
    errors: list[str] = _list()
    output_level: str = OutputLevel.PRELIMINARY.value
    started_at: str = dc.field(default_factory=_now)
    finished_at: str | None = _field()


# ---------------------------------------------------------------------------
# Venue Registry (venue-registry-source-collector v0)
# ---------------------------------------------------------------------------

@dc.dataclass
class VenueRecord(_DictMixin):
    venue_record_id: str = dc.field(default_factory=venue_record_id)
    canonical_name: str | None = _field()
    aliases: list[str] = _list()
    issn: str | None = _field()
    eissn: str | None = _field()
    publisher: str | None = _field()
    official_urls: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)
    updated_at: str = dc.field(default_factory=_now)


@dc.dataclass
class VenueSource(_DictMixin):
    venue_source_id: str = dc.field(default_factory=venue_source_id)
    venue_record_id: str | None = _field()
    source_url: str | None = _field()
    source_title: str | None = _field()
    source_type: str | None = _field()
    retrieved_at: str | None = _field()
    freshness_window_days: int | None = _field()
    extracted_by: str | None = _field()
    extraction_method: str | None = _field()
    notes: str | None = _field()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class VenueClaim(_DictMixin):
    venue_claim_id: str = dc.field(default_factory=venue_claim_id)
    venue_record_id: str | None = _field()
    venue_source_id: str | None = _field()
    claim_path: str | None = _field()
    claim_value: Any = _field()
    evidence_status: str | None = _field()
    confidence: str | None = _field()
    quote_or_summary: str | None = _field()
    conflict_group: str | None = _field()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class VenueEvidencePack(_DictMixin):
    evidence_pack_id: str = dc.field(default_factory=venue_evidence_pack_id)
    venue_record_id: str | None = _field()
    profile: dict[str, Any] = _dict()
    official_facts: list[str] = _list()
    external_claims: list[str] = _list()
    inferences: list[str] = _list()
    unknowns: list[str] = _list()
    conflicts: list[dict[str, Any]] = _list()
    stale_warnings: list[str] = _list()
    build_log: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# UC-1 Draft-to-Venue-Pool Positioning entities (GPT analysis 2026-06-12)
# ---------------------------------------------------------------------------

@dc.dataclass
class ArticleSemanticProfile(_DictMixin):
    """Extended semantic profile beyond ArticleModel base fields.

    Captures disciplinary register, school/tradition affiliations,
    argument move type, theoretical shoulders, and the protected core —
    everything needed for Disciplinary Pathway Mapper and Venue Pool Discovery.
    """
    article_semantic_profile_id: str = dc.field(default_factory=article_semantic_profile_id)
    article_model_id: str | None = _field()
    # Disciplinary classification (multiple registers possible)
    disciplinary_registers: list[str] = _list()
    primary_discipline: str | None = _field()
    # School/tradition taxonomy
    schools_and_traditions: list[str] = _list()
    theoretical_shoulders: list[str] = _list()
    opponents_or_foils: list[str] = _list()
    # Argument structure
    argument_move_type: str | None = _field()
    argument_move_description: str | None = _field()
    # Citation ecology signals
    citation_bridges_needed: list[str] = _list()
    citation_ecology_description: str | None = _field()
    # Protected core (what must NOT be destroyed in adaptation)
    protected_core_candidates: list[str] = _list()
    mutable_zones: list[str] = _list()
    field_core_nonnegotiables: list[str] = _list()
    # Audience
    intended_audience: str | None = _field()
    audience_expertise_level: str | None = _field()
    # Meta
    unknowns: list[str] = _list()
    confidence: str | None = _field()
    evidence_refs: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)
    # LLM attempt audit per llm.attempt_metadata.LLMAttemptMetadata.
    # Same vocabulary as ArticleModel and DisciplinaryPathway.
    extraction_attempt: dict[str, Any] | None = _field()


@dc.dataclass
class DisciplinaryPathway(_DictMixin):
    """One possible disciplinary branch for an article.

    The Disciplinary Pathway Mapper produces a ranked list of these,
    each representing an academic world the article could enter.
    """
    disciplinary_pathway_id: str = dc.field(default_factory=disciplinary_pathway_id)
    article_model_id: str | None = _field()
    discipline_name: str | None = _field()
    fit_strength: str | None = _field()
    reasoning: str | None = _field()
    # What adaptation would this pathway require?
    required_adaptations: list[str] = _list()
    field_core_risk: str | None = _field()
    # Venue signals: which kinds of venues exist in this space
    venue_type_hints: list[str] = _list()
    example_venue_names: list[str] = _list()
    language_options: list[str] = _list()
    indexing_options: list[str] = _list()
    # Ranking
    rank: int | None = _field()
    strategic_value_notes: str | None = _field()
    unknowns: list[str] = _list()
    confidence: str | None = _field()
    created_at: str = dc.field(default_factory=_now)
    # LLM attempt audit per llm.attempt_metadata.LLMAttemptMetadata.
    # Same field name as ArticleModel.extraction_attempt for consistency.
    # None for purely-deterministic builds.
    extraction_attempt: dict[str, Any] | None = _field()


@dc.dataclass
class ArticleVariant(_DictMixin):
    """A publication-trajectory variant of the original article.

    One Field/Idea can have multiple publication fates: philosophical,
    STS-oriented, AI-ethics, conference, Russian-language, English-language.
    Each variant tracks what changed, what was preserved, and which
    venues it targets.
    """
    article_variant_id: str = dc.field(default_factory=article_variant_id)
    source_article_model_id: str | None = _field()
    variant_relation: str | None = _field()
    target_discipline: str | None = _field()
    target_venue_ids: list[str] = _list()
    # What changes from the original
    reframe_description: str | None = _field()
    changes_required: list[str] = _list()
    preserved_from_original: list[str] = _list()
    field_core_loss_risk: str | None = _field()
    # Variant properties
    estimated_effort: str | None = _field()
    language: str | None = _field()
    genre_target: str | None = _field()
    # Decision support
    same_article_rewrite_possible: bool | None = _field()
    deep_reframe_required: bool | None = _field()
    sibling_article_recommended: bool | None = _field()
    do_not_submit_as_one_piece: bool | None = _field()
    # Meta
    unknowns: list[str] = _list()
    confidence: str | None = _field()
    lifecycle_status: str = LifecycleStatus.DRAFT.value
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class VenuePublicationProfile(_DictMixin):
    """Symmetric profile of a venue on the same axes as ArticleSemanticProfile.

    Enables Article × Venue comparison as two-profile matching
    rather than article-vs-requirements checking.
    """
    venue_publication_profile_id: str = dc.field(default_factory=venue_publication_profile_id)
    venue_model_id: str | None = _field()
    # Disciplinary center of gravity
    disciplinary_center: list[str] = _list()
    primary_discipline: str | None = _field()
    # School/tradition distribution
    schools_and_traditions_distribution: list[dict[str, Any]] = _list()
    # What the venue actually publishes (from corpus analysis)
    genre_move_distribution: list[dict[str, Any]] = _list()
    method_expectations: list[str] = _list()
    accepted_argument_forms: list[str] = _list()
    # Citation patterns
    citation_ecology_expectations: str | None = _field()
    typical_reference_count_range: str | None = _field()
    dominant_citation_traditions: list[str] = _list()
    # Other
    novelty_modes_published: list[str] = _list()
    audience_description: str | None = _field()
    language_register_expectations: str | None = _field()
    # Evidence quality
    corpus_size: int | None = _field()
    corpus_period: str | None = _field()
    unknowns: list[str] = _list()
    confidence: str | None = _field()
    evidence_refs: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class EditorialBoardProfile(_DictMixin):
    """Disciplinary signal from the editorial board composition."""
    editorial_board_profile_id: str = dc.field(default_factory=editorial_board_profile_id)
    venue_model_id: str | None = _field()
    board_size: int | None = _field()
    disciplinary_center_of_gravity: str | None = _field()
    discipline_distribution: list[dict[str, Any]] = _list()
    institution_distribution: list[dict[str, Any]] = _list()
    geographic_distribution: list[dict[str, Any]] = _list()
    notable_members: list[str] = _list()
    unknowns: list[str] = _list()
    confidence: str | None = _field()
    evidence_refs: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Venue Discovery (Pool Discovery v0)
# ---------------------------------------------------------------------------

@dc.dataclass
class VenueDiscoveryQuery(_DictMixin):
    """A search plan for discovering venue candidates via a specific pathway."""
    venue_discovery_query_id: str = dc.field(default_factory=venue_discovery_query_id)
    article_model_id: str | None = _field()
    semantic_profile_id: str | None = _field()
    pathway_id: str | None = _field()
    query_text: str = ""
    source: str = ""
    constraints: dict[str, Any] = _dict()
    expected_authority_scopes: list[str] = _list()
    unknowns: list[str] = _list()


@dc.dataclass
class VenueCandidate(_DictMixin):
    """A discovered venue candidate with traceable evidence and authority."""
    venue_candidate_id: str = dc.field(default_factory=venue_candidate_id)
    canonical_name: str = ""
    aliases: list[str] = _list()
    issn: str | None = _field()
    issn_l: str | None = _field()
    urls: list[str] = _list()
    sources: list[str] = _list()
    discovery_reasons: list[str] = _list()
    authority_assessments: list[dict[str, Any]] = _list()
    adapter_result_refs: list[str] = _list()
    evidence_refs: list[str] = _list()
    conflicts: list[dict[str, Any]] = _list()
    status: str = "discovered"
    confidence: str = "low"
    unknowns: list[str] = _list()
    raw_adapter_data: dict[str, Any] = _dict()


@dc.dataclass
class VenueCandidatePool(_DictMixin):
    """Complete pool of discovered venue candidates for an article."""
    venue_candidate_pool_id: str = dc.field(default_factory=venue_candidate_pool_id)
    article_model_id: str | None = _field()
    scenario_id: str | None = _field()
    pathway_ids: list[str] = _list()
    queries: list[dict[str, Any]] = _list()
    candidates: list[dict[str, Any]] = _list()
    dedupe_notes: list[str] = _list()
    rejected_candidates: list[dict[str, Any]] = _list()
    unknowns: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class VenueCandidateScreeningResult(_DictMixin):
    """Preliminary fit screening result for a single candidate."""
    venue_candidate_screening_id: str = dc.field(default_factory=venue_candidate_screening_id)
    candidate_id: str = ""
    article_model_id: str | None = _field()
    semantic_profile_id: str | None = _field()
    pathway_id: str | None = _field()
    preliminary_fit: str = "unknown"
    fit_axes: dict[str, str] = _dict()
    blocking_gaps: list[str] = _list()
    evidence_gaps: list[str] = _list()
    authority_warnings: list[str] = _list()
    recommended_next_actions: list[str] = _list()
    status: str = "pending"
    unknowns: list[str] = _list()


@dc.dataclass
class CandidateEvidenceMatrix(_DictMixin):
    """Cross-candidate evidence/gap/conflict summary."""
    candidate_evidence_matrix_id: str = dc.field(default_factory=candidate_evidence_matrix_id)
    pool_id: str = ""
    rows: list[dict[str, Any]] = _list()
    missing_evidence_by_candidate: dict[str, list[str]] = _dict()
    conflicts_by_candidate: dict[str, list[dict[str, Any]]] = _dict()
    authority_warnings_by_candidate: dict[str, list[str]] = _dict()
    unknowns: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class PublishedArticleCorpus(_DictMixin):
    """Summary of recent articles published by a venue — corpus-level features."""
    published_article_corpus_id: str = dc.field(default_factory=published_article_corpus_id)
    venue_model_id: str | None = _field()
    corpus_size: int | None = _field()
    collection_period: str | None = _field()
    genre_distribution: list[dict[str, Any]] = _list()
    method_distribution: list[dict[str, Any]] = _list()
    topic_clusters: list[dict[str, Any]] = _list()
    average_word_count: int | None = _field()
    average_reference_count: int | None = _field()
    language_distribution: list[dict[str, Any]] = _list()
    unknowns: list[str] = _list()
    confidence: str | None = _field()
    evidence_refs: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# FieldPositionModel — unified coordinate system (articles + venues)
# ---------------------------------------------------------------------------

@dc.dataclass
class DisciplineVector(_DictMixin):
    """Weighted vector of disciplinary membership (0.0–1.0 per dimension)."""
    components: dict[str, float] = _dict()

@dc.dataclass
class DisciplineEnvelope(_DictMixin):
    """Range [min, max] per discipline dimension — venue's accepted region."""
    ranges: dict[str, list[float]] = _dict()

@dc.dataclass
class SchoolAffiliationVector(_DictMixin):
    """Weighted vector of school/tradition membership."""
    components: dict[str, float] = _dict()

@dc.dataclass
class SchoolEnvelope(_DictMixin):
    """Range [min, max] per school dimension — venue's published range."""
    ranges: dict[str, list[float]] = _dict()

@dc.dataclass
class CitationNetworkSignature(_DictMixin):
    """Citation topology: who is cited, who is absent, who is avoided."""
    must_cite: list[str] = _list()
    typically_cite: list[str] = _list()
    never_cite: list[str] = _list()
    conspicuous_absence: list[str] = _list()
    bridge_traditions: list[str] = _list()
    self_citation_norm: str | None = _field()

@dc.dataclass
class OpponentsAndFoils(_DictMixin):
    """Intellectual opponents — explicit and implicit."""
    explicit_opponents: list[str] = _list()
    implicit_foils: list[str] = _list()
    published_polemics: list[str] = _list()
    avoided_polemics: list[str] = _list()

@dc.dataclass
class ArgumentMoveVector(_DictMixin):
    """Weighted vector of argument move types (12 types, 0.0–1.0 each)."""
    components: dict[str, float] = _dict()

@dc.dataclass
class ArgumentMoveEnvelope(_DictMixin):
    """Range [min, max] per argument move type — venue's accepted range."""
    ranges: dict[str, list[float]] = _dict()

@dc.dataclass
class NoveltyProfile(_DictMixin):
    """How the entity positions novelty."""
    mode: str | None = _field()
    novelty_claim_strength: float | None = _field()
    builds_on_or_opposes: str | None = _field()

@dc.dataclass
class EvidenceTypeProfile(_DictMixin):
    """Weighted distribution of evidence/data types used."""
    components: dict[str, float] = _dict()

@dc.dataclass
class MethodStance(_DictMixin):
    """Methodological positioning."""
    explicit_method: bool | None = _field()
    method_family: str | None = _field()
    method_specificity: str | None = _field()
    empirical_component: bool | None = _field()
    requires_explicit_method: bool | None = _field()
    accepted_method_families: list[str] = _list()
    rejected_method_families: list[str] = _list()

@dc.dataclass
class AudienceLevel(_DictMixin):
    """Audience expertise and accessibility."""
    expertise_required: str | None = _field()
    presupposed_knowledge: list[str] = _list()
    accessibility_index: float | None = _field()

@dc.dataclass
class LanguageRegister(_DictMixin):
    """Language, register, jargon density, expected length."""
    language: str | None = _field()
    register: str | None = _field()
    jargon_density: float | None = _field()
    expected_word_count_min: int | None = _field()
    expected_word_count_max: int | None = _field()

@dc.dataclass
class GenrePosition(_DictMixin):
    """Genre classification and formality."""
    genre: str | None = _field()
    genre_formality: float | None = _field()
    sections_expected: list[str] = _list()

@dc.dataclass
class GeographicAffinity(_DictMixin):
    """Geographic and regional positioning."""
    author_region: str | None = _field()
    intellectual_tradition_region: str | None = _field()
    target_audience_region: str | None = _field()
    language_of_publication: str | None = _field()
    editorial_board_regions: dict[str, float] = _dict()
    author_regions_published: dict[str, float] = _dict()
    anglophone_hegemony_index: float | None = _field()

@dc.dataclass
class InstitutionalSignals(_DictMixin):
    """Institutional context: prestige, indexing, access model."""
    prestige_tier: str | None = _field()
    indexing: list[str] = _list()
    open_access: str | None = _field()
    apc_range_usd_min: int | None = _field()
    apc_range_usd_max: int | None = _field()
    review_model: str | None = _field()
    typical_decision_weeks: int | None = _field()

@dc.dataclass
class TemporalPosition(_DictMixin):
    """Temporal characteristics of reference base and field."""
    recency_of_core_references: str | None = _field()
    median_reference_year: int | None = _field()
    reference_time_depth_years: int | None = _field()
    field_maturity: str | None = _field()

@dc.dataclass
class ArticleReadiness(_DictMixin):
    """Article-specific: manuscript stage and completeness."""
    manuscript_stage: str | None = _field()
    completeness: float | None = _field()
    word_count: int | None = _field()
    has_abstract: bool | None = _field()
    has_bibliography: bool | None = _field()
    has_methods_section: bool | None = _field()
    formal_compliance_score: float | None = _field()

@dc.dataclass
class SubdisciplineAddress(_DictMixin):
    """Hierarchical address within the primary discipline."""
    primary: str | None = _field()
    niche: str | None = _field()
    working_area: str | None = _field()


@dc.dataclass
class FieldPositionModel(_DictMixin):
    """Unified coordinate model for articles AND venues in the same space.

    An article is a point (or compact region) in this space.
    A venue is an extended region (envelope) in the same space.
    Fit = containment / distance of article point within venue envelope.
    """
    field_position_id: str = dc.field(default_factory=field_position_id)
    entity_type: str = "article"
    entity_id: str | None = _field()

    # Group 1: Disciplinary positioning
    discipline_vector: dict[str, float] = _dict()
    discipline_envelope: dict[str, list[float]] | None = _field()
    subdiscipline_address: dict[str, str] = _dict()

    # Group 2: Camp/Tribe positioning
    school_affiliation_vector: dict[str, float] = _dict()
    school_envelope: dict[str, list[float]] | None = _field()
    citation_network_signature: dict[str, Any] = _dict()
    opponents_and_foils: dict[str, Any] = _dict()

    # Group 3: Argument profile
    argument_move_vector: dict[str, float] = _dict()
    argument_move_envelope: dict[str, list[float]] | None = _field()
    novelty_mode: dict[str, Any] = _dict()
    evidence_type_profile: dict[str, float] = _dict()

    # Group 4: Method
    method_stance: dict[str, Any] = _dict()
    formalization_level: float | None = _field()

    # Group 5: Audience & Register
    audience_level: dict[str, Any] = _dict()
    language_register: dict[str, Any] = _dict()
    genre_position: dict[str, Any] = _dict()

    # Group 6: Geo & Institutional
    geographic_affinity: dict[str, Any] = _dict()
    institutional_signals: dict[str, Any] = _dict()

    # Group 7: Temporal & Readiness
    temporal_position: dict[str, Any] = _dict()
    article_readiness: dict[str, Any] | None = _field()

    # Meta
    unknowns: list[str] = _list()
    confidence: str | None = _field()
    evidence_refs: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class CitationExpectationProfile(_DictMixin):
    """What citation patterns a venue expects, derived from corpus analysis."""
    citation_expectation_profile_id: str = dc.field(default_factory=citation_expectation_profile_id)
    venue_model_id: str | None = _field()
    typical_reference_count: str | None = _field()
    dominant_traditions: list[str] = _list()
    expected_bridge_references: list[str] = _list()
    self_citation_rate: str | None = _field()
    recency_bias: str | None = _field()
    canonical_works_expected: list[str] = _list()
    absent_traditions_risk: list[str] = _list()
    unknowns: list[str] = _list()
    confidence: str | None = _field()
    evidence_refs: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Publication Integrability Model v1 — Sprint α substrate (B1, B3)
# ---------------------------------------------------------------------------

@dc.dataclass
class SourceEvidenceEntry(_DictMixin):
    """One item inside a SourceEvidencePacket."""
    source_id: str | None = _field()
    source_type: str | None = _field()
    provenance: str | None = _field()
    access_status: str | None = _field()
    extraction_status: str | None = _field()
    granularity: str | None = _field()
    evidence_ref_id: str | None = _field()
    snapshot_ref_id: str | None = _field()
    note: str | None = _field()


@dc.dataclass
class SourceEvidencePacket(_DictMixin):
    """Per-case packet aggregating all sources, their access status, and
    evidence granularity classification (PIM v1 §2).

    The packet records *where the data came from* and *what status it has*.
    UNKNOWN must never be silently promoted to absent.
    """
    source_evidence_packet_id: str = dc.field(default_factory=source_evidence_packet_id)
    case_id: str | None = _field()
    input_sources: list[dict[str, Any]] = _list()
    evidence_refs: list[str] = _list()
    granularity_summary: dict[str, int] = _dict()
    unknowns: list[str] = _list()
    notes: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)
    updated_at: str = dc.field(default_factory=_now)


@dc.dataclass
class ProtectedCorePolicy(_DictMixin):
    """Typed policy guarding the article's protected core (PIM v1 §10).

    Used by the rewrite planner / core gate to refuse actions whose
    semantics match `forbidden_moves`, and to surface
    `acceptable_loss` / `unacceptable_loss` / `questions_for_author`
    to the operator.
    """
    protected_core_policy_id: str = dc.field(default_factory=protected_core_policy_id)
    article_model_id: str | None = _field()
    protected_core: list[str] = _list()
    mutable_zones: list[str] = _list()
    forbidden_moves: list[str] = _list()
    allowed_moves: list[str] = _list()
    forbidden_reframes: list[str] = _list()
    allowed_reframes: list[str] = _list()
    acceptable_loss: list[str] = _list()
    unacceptable_loss: list[str] = _list()
    questions_for_author: list[str] = _list()
    notes: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class EvidencePolicy(_DictMixin):
    """Typed policy describing required evidence levels and how UNKNOWN /
    INACCESSIBLE / CONFLICT must be surfaced (PIM v1 §2 evidence_policy).
    """
    evidence_policy_id: str = dc.field(default_factory=evidence_policy_id)
    case_id: str | None = _field()
    required_evidence_min_status: str | None = _field()
    unknown_handling: str = "preserve"
    inaccessible_handling: str = "mark_blocking"
    conflict_handling: str = "surface_both"
    require_evidence_for_claims: bool = True
    allow_inference_when_no_source: bool = True
    notes: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# VF-C2: VenueProfilePackage and subobjects (canon §2, rubric v2 §1)
# ---------------------------------------------------------------------------

@dc.dataclass
class EditorialBoardMember(_DictMixin):
    """One row in the editorial board cloud.

    Carries low/medium confidence per canon §3.E. Any derived signal
    (theoretical commitments) must be `inference`, not `external_claim`.
    """
    editorial_board_member_id: str = dc.field(default_factory=editorial_board_member_id)
    full_name: str | None = _field()
    role: str | None = _field()  # editor_in_chief | associate | section | board
    affiliation: str | None = _field()
    country: str | None = _field()
    orcid: str | None = _field()
    openalex_author_id: str | None = _field()
    research_concepts: list[str] = _list()  # OpenAlex machine-tagged, INFERENCE
    recent_works_count: int | None = _field()
    h_index: int | None = _field()
    evidence_status: str = "external_claim"
    source_url: str | None = _field()
    unknowns: list[str] = _list()


@dc.dataclass
class EditorialBoardCloud(_DictMixin):
    """Distribution of an editorial board's institutions × countries ×
    concepts; per-editor entries plus derived center-of-gravity signals
    marked `inference` with low/medium confidence."""

    editorial_board_cloud_id: str = dc.field(default_factory=editorial_board_cloud_id)
    venue_profile_package_id: str | None = _field()
    members: list[dict[str, Any]] = _list()
    members_sampled: int = 0
    members_total_known: int | None = _field()
    institutional_distribution: dict[str, int] = _dict()
    country_distribution: dict[str, int] = _dict()
    concept_distribution: dict[str, int] = _dict()
    coverage_ratio: float | None = _field()  # sampled / total_known
    derived_signals: dict[str, Any] = _dict()
    derived_signals_authority: str = "inference"
    derived_signals_confidence: str = "low"
    warnings: list[str] = _list()
    unknowns: list[str] = _list()
    extracted_at: str = dc.field(default_factory=_now)


@dc.dataclass
class PublishedCorpusHull(_DictMixin):
    """Wrapper that pairs a CorpusAnalysisResult-derived venue FPM with
    its source meta (how many works, what time range, what source IDs).
    Built by `venue_corpus_miner` from real OpenAlex Works.
    """

    published_corpus_hull_id: str = dc.field(default_factory=published_corpus_hull_id)
    venue_profile_package_id: str | None = _field()
    venue_field_position_id: str | None = _field()  # ref to FieldPositionModel(venue)
    works_fetched: int = 0
    abstracts_available: int = 0
    references_available: int = 0
    year_range_min: int | None = _field()
    year_range_max: int | None = _field()
    source_used: str | None = _field()  # OpenAlex source id
    corpus_analysis_summary: dict[str, Any] = _dict()
    warnings: list[str] = _list()
    unknowns: list[str] = _list()
    extracted_at: str = dc.field(default_factory=_now)


@dc.dataclass
class VenueProfilePackage(_DictMixin):
    """Aggregating package per canon §2 (rubric v2 §1: 7 minimal subobjects).

    This is the durable cross-session venue model. Indexed by canonical
    name + ISSN in the venue_profile_registry. Future runs reuse what's
    here instead of re-discovering.
    """

    venue_profile_package_id: str = dc.field(default_factory=venue_profile_package_id)

    # 1. VenueIdentity (we reuse VenueModel fields by reference)
    venue_model_id: str | None = _field()
    canonical_name: str | None = _field()
    issns: list[str] = _list()
    publisher: str | None = _field()
    homepage_url: str | None = _field()
    languages: list[str] = _list()
    venue_type: str = "journal"

    # 2. VenueFieldPosition (composed)
    venue_field_position_id: str | None = _field()

    # 3. PublishedCorpusHull
    published_corpus_hull_id: str | None = _field()

    # 4. EditorialBoardCloud
    editorial_board_cloud_id: str | None = _field()

    # 5. FormalSubmissionProfile (reuse PublicationRegimeModel id)
    publication_regime_id: str | None = _field()

    # 6. CitationExpectationProfile (reuse existing dataclass)
    citation_expectation_profile_id: str | None = _field()

    # 7. SourceEvidencePacket (Sprint α)
    source_evidence_packet_id: str | None = _field()

    # Discovery + reuse metadata
    discovery_sources: list[str] = _list()
    discovery_clusters: list[str] = _list()
    openalex_source_id: str | None = _field()
    doaj_source_id: str | None = _field()
    crossref_member_id: str | None = _field()
    cyberleninka_source_id: str | None = _field()

    # VF-C3 sub-models (canon §2 supplementary subobjects, added 2026-06-14):
    method_expectation_profile_id: str | None = _field()
    genre_move_profile_id: str | None = _field()
    style_register_profile_id: str | None = _field()
    author_eligibility_profile_id: str | None = _field()
    time_review_profile_id: str | None = _field()
    apc_access_profile_id: str | None = _field()
    tacit_venue_signal_ids: list[str] = _list()  # 0..N tacit signals
    journal_model_id: str | None = _field()
    section_model_ids: list[str] = _list()
    special_issue_model_ids: list[str] = _list()

    # Lifecycle
    completeness: dict[str, str] = _dict()  # per-subobject: present|missing|partial
    confidence: str = "low"
    evidence_status: str = "external_claim"
    unknowns: list[str] = _list()
    warnings: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)
    updated_at: str = dc.field(default_factory=_now)
    last_refreshed_at: str | None = _field()


# ---------------------------------------------------------------------------
# VF-C3 (canon §2 supplementary subobjects)
#
# Each sub-model carries the rubric-standard four fields:
#   - evidence_refs:    list[str] of EvidenceItem/SourceSnapshot ids that
#                       support the populated fields;
#   - source_category:  one of VenueSourceCategory (canon §3 A-J) so an
#                       auditor can tell which source family the data
#                       came from;
#   - confidence:       "high" | "medium" | "low" | "unknown";
#   - evidence_status:  one of EvidenceStatus or "operator_seed_canonical"
#                       (for operator-curated entries) or "unknown";
#   - unknowns:         list of explicit UNKNOWN_NOT_FOUND / INACCESSIBLE /
#                       AUTH_REQUIRED / JS_ONLY markers per the rubric.
#
# Every model defaults to "thin": empty fields are honest unknowns, never
# silently inferred. Population is downstream services' job.
# ---------------------------------------------------------------------------


@dc.dataclass
class MethodExpectationProfile(_DictMixin):
    """What methods/empirical stances the venue typically accepts.

    Reconstructed from corpus observation (which methods appear in the
    published article hull) and from author guidelines (which methods
    are explicitly required/forbidden). Authority depends on source.
    """

    method_expectation_profile_id: str = dc.field(default_factory=method_expectation_profile_id)
    venue_profile_package_id: str | None = _field()

    # Observed method distribution in the corpus (corpus_observation)
    method_distribution: dict[str, float] = _dict()  # method_name -> share 0..1
    dominant_methods: list[str] = _list()  # top-N method names
    forbidden_methods: list[str] = _list()  # from guidelines, if stated

    # Required vs accepted (from guidelines, source_category=A)
    required_method_statement: bool | None = _field()
    method_section_required: bool | None = _field()

    # Article-side fit consequences (rubric §6.X mappings)
    accepts_no_method_continental: bool | None = _field()
    accepts_textual_analysis_only: bool | None = _field()

    evidence_refs: list[str] = _list()
    source_category: str | None = _field()  # VenueSourceCategory
    confidence: str = "unknown"
    evidence_status: str = "unknown"
    unknowns: list[str] = _list()
    warnings: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class GenreMoveProfile(_DictMixin):
    """Argument-move distribution typical for the venue.

    Per canon §4 and rubric: which argument moves appear in venue corpus
    (concept_introduction, concept_reconstruction, case_study,
    empirical_test, polemic_response, position_paper, ...) and which
    move types are conspicuously absent.
    """

    genre_move_profile_id: str = dc.field(default_factory=genre_move_profile_id)
    venue_profile_package_id: str | None = _field()

    observed_moves: dict[str, float] = _dict()  # move_type -> share 0..1
    dominant_moves: list[str] = _list()
    conspicuously_absent_moves: list[str] = _list()

    # Article types from guidelines (research / review / essay / commentary / ...)
    declared_article_types: list[str] = _list()

    # Per-section move expectations (when SectionModel knows)
    per_section_moves: dict[str, list[str]] = _dict()

    evidence_refs: list[str] = _list()
    source_category: str | None = _field()
    confidence: str = "unknown"
    evidence_status: str = "unknown"
    unknowns: list[str] = _list()
    warnings: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class StyleRegisterProfile(_DictMixin):
    """Language register / jargon density / structural style observable
    from corpus + declared from guidelines."""

    style_register_profile_id: str = dc.field(default_factory=style_register_profile_id)
    venue_profile_package_id: str | None = _field()

    primary_language: str | None = _field()  # "en" / "ru" / ...
    abstract_languages: list[str] = _list()
    register: str | None = _field()  # academic_dense / accessible / popular
    jargon_density: float | None = _field()  # 0..1, corpus-observed
    avg_word_count: int | None = _field()
    typical_paragraph_length: int | None = _field()
    citation_style: str | None = _field()  # apa / chicago / vancouver / numeric / mla
    structured_abstract_required: bool | None = _field()

    evidence_refs: list[str] = _list()
    source_category: str | None = _field()
    confidence: str = "unknown"
    evidence_status: str = "unknown"
    unknowns: list[str] = _list()
    warnings: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class AuthorEligibilityProfile(_DictMixin):
    """§6.15 sibling axis: who may publish.

    Affiliation requirements (institutional ties / society membership),
    career-stage focus (ECR / senior), geographic restrictions,
    sponsorship/invitation-only entry. Honest unknown is the default.
    """

    author_eligibility_profile_id: str = dc.field(default_factory=author_eligibility_profile_id)
    venue_profile_package_id: str | None = _field()

    requires_institutional_affiliation: bool | None = _field()
    affiliation_constraints: list[str] = _list()
    requires_society_membership: bool | None = _field()
    society_membership_required: str | None = _field()

    career_stage_focus: list[str] = _list()  # "early_career" / "senior" / "any"
    geographic_constraints: list[str] = _list()  # country / region codes
    invitation_only: bool | None = _field()

    # Common gates
    requires_orcid: bool | None = _field()
    requires_funding_disclosure: bool | None = _field()
    requires_ethics_approval: bool | None = _field()

    evidence_refs: list[str] = _list()
    source_category: str | None = _field()
    confidence: str = "unknown"
    evidence_status: str = "unknown"
    unknowns: list[str] = _list()
    warnings: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class TimeReviewProfile(_DictMixin):
    """Time-to-decision and review-process expectations."""

    time_review_profile_id: str = dc.field(default_factory=time_review_profile_id)
    venue_profile_package_id: str | None = _field()

    review_type: str | None = _field()  # single_blind / double_blind / open / post_pub
    desk_rejection_rate_pct: float | None = _field()
    acceptance_rate_pct: float | None = _field()
    avg_days_to_first_decision: int | None = _field()
    avg_days_to_publication: int | None = _field()

    # Special-issue cadence
    special_issue_frequency_per_year: int | None = _field()
    next_special_issue_deadline: str | None = _field()

    # Anonymization / blinding requirements
    anonymized_submission_required: bool | None = _field()

    evidence_refs: list[str] = _list()
    source_category: str | None = _field()
    confidence: str = "unknown"
    evidence_status: str = "unknown"
    unknowns: list[str] = _list()
    warnings: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class APCAccessProfile(_DictMixin):
    """APC / OA / deposit / license terms."""

    apc_access_profile_id: str = dc.field(default_factory=apc_access_profile_id)
    venue_profile_package_id: str | None = _field()

    open_access_model: str | None = _field()  # gold / hybrid / diamond / closed
    apc_currency: str | None = _field()  # "USD" / "EUR" / "GBP" / ...
    apc_amount_min: float | None = _field()
    apc_amount_max: float | None = _field()
    apc_waiver_policy: str | None = _field()  # free-text description if found

    # License + deposit
    license: str | None = _field()  # "CC-BY" / "CC-BY-NC" / ...
    self_archiving_policy: str | None = _field()  # green/blue/yellow/white
    embargo_months: int | None = _field()

    # Author retains copyright?
    author_retains_copyright: bool | None = _field()

    evidence_refs: list[str] = _list()
    source_category: str | None = _field()
    confidence: str = "unknown"
    evidence_status: str = "unknown"
    unknowns: list[str] = _list()
    warnings: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class TacitVenueSignal(_DictMixin):
    """§6.16 — non-formal venue knowledge.

    Operator-reported, community-reported, or inferred-from-low-signal
    observations. **Not facts.** Each tacit signal carries source + date
    + scope + confidence. Per canon §3.J the rubric forbids mixing tacit
    signal with official policy.
    """

    tacit_venue_signal_id: str = dc.field(default_factory=tacit_venue_signal_id)
    venue_profile_package_id: str | None = _field()

    signal_kind: str | None = _field()  # "review_time" / "editor_says" /
                                         # "rejection_reason" / "submission_outcome"
    statement: str | None = _field()  # the actual claim, verbatim
    reporter: str | None = _field()  # operator id / community handle (opaque)
    reported_on: str | None = _field()  # ISO timestamp
    scope: str | None = _field()  # "personal_experience" / "second_hand" /
                                   # "community_consensus" / "single_anecdote"

    # Mandatory honest typing
    confidence: str = "low"  # tacit signals start low by default
    evidence_status: str = "tacit_signal"
    authority: str = "tacit_signal"  # never "official_fact"

    evidence_refs: list[str] = _list()
    source_category: str | None = _field()  # typically VenueSourceCategory.J
    unknowns: list[str] = _list()
    warnings: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class JournalModel(_DictMixin):
    """§6.8 — serial journal entity (the "old VenueModel" per canon §2.2).

    Canonical title, ISSN, publisher, URLs, scope, instructions URL,
    editorial board URL, indexing snapshot, declared metrics. NOT a
    citation/quality verdict on its own — that comes from VenueFieldPosition
    + CitationExpectationProfile.
    """

    journal_model_id: str = dc.field(default_factory=journal_model_id)
    venue_profile_package_id: str | None = _field()

    canonical_title: str | None = _field()
    aliases: list[str] = _list()
    issn_print: str | None = _field()
    issn_electronic: str | None = _field()
    publisher: str | None = _field()
    homepage_url: str | None = _field()
    submission_url: str | None = _field()
    guidelines_url: str | None = _field()
    editorial_board_url: str | None = _field()
    aims_scope_url: str | None = _field()

    declared_scope: str | None = _field()
    declared_disciplines: list[str] = _list()
    declared_languages: list[str] = _list()

    # Declared metrics (publisher self-report; vendor_claim authority)
    declared_metrics: dict[str, Any] = _dict()  # e.g. {"impact_factor": 1.8}
    indexing_claims: list[str] = _list()  # ["Scopus", "WoS", "DOAJ", "VAK"]

    evidence_refs: list[str] = _list()
    source_category: str | None = _field()
    confidence: str = "unknown"
    evidence_status: str = "unknown"
    unknowns: list[str] = _list()
    warnings: list[str] = _list()
    last_checked_at: str | None = _field()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class SectionModel(_DictMixin):
    """§6.9 — section / article type within a journal.

    Per canon §2.6: a journal as a whole can be wide but a specific
    section accepts only essays / review articles / forum pieces /
    methods papers / book reviews / case studies. Section-level fit is
    often more accurate than journal-level fit.
    """

    section_model_id: str = dc.field(default_factory=section_model_id)
    journal_model_id: str | None = _field()
    venue_profile_package_id: str | None = _field()

    section_name: str | None = _field()  # "Research Articles" / "Forum" / ...
    article_type: str | None = _field()  # "research" / "review" / "essay" / ...
    scope: str | None = _field()
    requirements: list[str] = _list()  # bullet-list of section-specific gates
    typical_structure: str | None = _field()  # IMRaD / argumentative / book-review
    editor_refs: list[str] = _list()  # ids into EditorialBoardCloud.members
    recent_article_refs: list[str] = _list()  # OpenAlex Work ids

    fit_notes: list[str] = _list()  # operator-curated notes (TacitVenueSignal-grade)

    evidence_refs: list[str] = _list()
    source_category: str | None = _field()
    confidence: str = "unknown"
    evidence_status: str = "unknown"
    unknowns: list[str] = _list()
    warnings: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class SpecialIssueModel(_DictMixin):
    """§6.10 — time-bound topical container / CFP."""

    special_issue_model_id: str = dc.field(default_factory=special_issue_model_id)
    journal_model_id: str | None = _field()
    venue_profile_package_id: str | None = _field()

    title: str | None = _field()
    theme: str | None = _field()
    description: str | None = _field()
    submission_deadline: str | None = _field()  # ISO date
    publication_target_date: str | None = _field()
    guest_editor_refs: list[str] = _list()  # EditorialBoardMember ids
    guest_editor_names: list[str] = _list()  # if no member ids resolved yet
    article_types_accepted: list[str] = _list()
    target_disciplines: list[str] = _list()
    expected_articles: int | None = _field()
    submission_url: str | None = _field()
    cfp_url: str | None = _field()

    status: str = "open"  # "open" / "closed" / "in_review" / "published"

    evidence_refs: list[str] = _list()
    source_category: str | None = _field()
    confidence: str = "unknown"
    evidence_status: str = "unknown"
    unknowns: list[str] = _list()
    warnings: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)
