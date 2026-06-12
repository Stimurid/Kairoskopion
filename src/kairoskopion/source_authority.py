"""Source authority and evidence integrity domain models.

Encodes the architectural rule: full-text access is not metadata authority;
metadata authority is not publication-pattern authority; official venue claim
is not independent verification; corpus evidence is not formal policy;
user memory is not public fact.
"""

from __future__ import annotations

import dataclasses as dc
from datetime import datetime, timezone
from typing import Any

from .enums import (
    AuthorityStrength,
    ConflictResolutionStatus,
    ConflictSeverity,
    ConflictType,
    PriorVersionType,
    RetractionStatus,
    SourceAccessMode,
    SourceAuthorityScope,
)
from .ids import (
    citation_integrity_check_id,
    evidence_conflict_id,
    evidence_reconciliation_id,
    publication_history_id,
    reporting_guideline_selection_id,
    source_authority_assessment_id,
    source_authority_claim_id,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _field(default=None):
    return dc.field(default=default)


def _list():
    return dc.field(default_factory=list)


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
        return {k: _convert(v) for k, v in dc.asdict(self).items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Any:
        field_names = {f.name for f in dc.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)


# ---------------------------------------------------------------------------
# Source Authority Claim
# ---------------------------------------------------------------------------

@dc.dataclass
class SourceAuthorityClaim(_DictMixin):
    claim_id: str = dc.field(default_factory=source_authority_claim_id)
    source_ref: str = ""
    evidence_ref: str = ""
    access_mode: str = SourceAccessMode.MANUAL_NOTE.value
    authority_scope: str = SourceAuthorityScope.VENUE_IDENTITY.value
    claim_key: str = ""
    claim_value: Any = _field()
    authority_strength: str = AuthorityStrength.WEAK.value
    supported_entity_id: str = ""
    limitations: list[str] = _list()
    confidence: str = "medium"
    created_at: str = dc.field(default_factory=_now)
    unknowns: list[str] = _list()


# ---------------------------------------------------------------------------
# Source Authority Assessment
# ---------------------------------------------------------------------------

@dc.dataclass
class SourceAuthorityAssessment(_DictMixin):
    assessment_id: str = dc.field(default_factory=source_authority_assessment_id)
    source_ref: str = ""
    access_modes: list[str] = _list()
    authority_scopes: list[str] = _list()
    prohibited_scopes: list[str] = _list()
    supported_claims: list[dict[str, Any]] = _list()
    unsupported_claims: list[dict[str, Any]] = _list()
    notes: list[str] = _list()
    unknowns: list[str] = _list()
    assessed_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Evidence Conflict
# ---------------------------------------------------------------------------

@dc.dataclass
class EvidenceConflict(_DictMixin):
    conflict_id: str = dc.field(default_factory=evidence_conflict_id)
    entity_id: str = ""
    field_name: str = ""
    conflicting_claims: list[dict[str, Any]] = _list()
    conflict_type: str = ConflictType.VALUE_MISMATCH.value
    severity: str = ConflictSeverity.WARNING.value
    resolution_status: str = ConflictResolutionStatus.UNRESOLVED.value
    preferred_claim_id: str | None = _field()
    resolution_rationale: str = ""
    unknowns: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Evidence Reconciliation Result
# ---------------------------------------------------------------------------

@dc.dataclass
class EvidenceReconciliationResult(_DictMixin):
    reconciliation_id: str = dc.field(default_factory=evidence_reconciliation_id)
    entity_id: str = ""
    resolved_claims: list[dict[str, Any]] = _list()
    unresolved_conflicts: list[dict[str, Any]] = _list()
    downgraded_claims: list[dict[str, Any]] = _list()
    authority_notes: list[str] = _list()
    unknowns: list[str] = _list()
    reconciled_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Publication History Model
# ---------------------------------------------------------------------------

@dc.dataclass
class PriorVersion(_DictMixin):
    version_type: str = PriorVersionType.OTHER.value
    title: str = ""
    url: str = ""
    doi: str = ""
    date: str = ""
    overlap_description: str = ""
    language: str = ""
    repository: str = ""
    license: str = ""
    unknowns: list[str] = _list()


@dc.dataclass
class PublicationHistoryModel(_DictMixin):
    history_id: str = dc.field(default_factory=publication_history_id)
    article_model_id: str = ""
    manuscript_id: str = ""
    prior_versions: list[dict[str, Any]] = _list()
    preprint_status: str = "unknown"
    thesis_overlap: str = "unknown"
    conference_overlap: str = "unknown"
    working_paper_overlap: str = "unknown"
    prior_submission_history: list[dict[str, Any]] = _list()
    duplicate_publication_risks: list[str] = _list()
    novelty_statement: str = ""
    unknowns: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Citation Integrity Check
# ---------------------------------------------------------------------------

@dc.dataclass
class CitationIntegrityCheck(_DictMixin):
    check_id: str = dc.field(default_factory=citation_integrity_check_id)
    reference_id: str = ""
    citation_key: str = ""
    status: str = "not_checked"
    checked_sources: list[str] = _list()
    retraction_status: str = RetractionStatus.NOT_CHECKED.value
    expression_of_concern_status: str = "not_checked"
    pubpeer_signal: str = "not_checked"
    doi_resolution_status: str = "not_checked"
    citation_supports_claim: str = "not_checked"
    citation_padding_risk: str = "not_checked"
    notes: list[str] = _list()
    unknowns: list[str] = _list()
    checked_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Reporting Guideline Selection
# ---------------------------------------------------------------------------

@dc.dataclass
class ReportingGuidelineSelection(_DictMixin):
    selection_id: str = dc.field(default_factory=reporting_guideline_selection_id)
    article_model_id: str = ""
    article_type: str = ""
    candidate_guidelines: list[dict[str, Any]] = _list()
    selected_guidelines: list[str] = _list()
    rationale: str = ""
    unknowns: list[str] = _list()
    selected_at: str = dc.field(default_factory=_now)
