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
    venue_model_id,
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
