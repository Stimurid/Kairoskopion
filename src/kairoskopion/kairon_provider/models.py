"""Normalized data contracts for Kairoskopion as an ARTIKL.KAIRON provider.

These models intentionally avoid claiming semantic authority over Artikl state.
They transport pointers, evidence-backed target observations and provider
diagnostics across the incarnation boundary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class _DictModel:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArtiklStatePointer(_DictModel):
    state_id: str
    state_type: str
    article_seed_pointer: str | None = None
    manuscript_pointer: str | None = None
    branch_id: str | None = None
    version: str | None = None
    authority: str = "ARTIKL"
    source_refs: list[str] = field(default_factory=list)


@dataclass
class EditorScientificProfile(_DictModel):
    editor_id: str
    name: str
    editorial_roles: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    disciplines: list[str] = field(default_factory=list)
    research_topics: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    theoretical_traditions: list[str] = field(default_factory=list)
    key_works: list[dict[str, Any]] = field(default_factory=list)
    projects: list[dict[str, Any]] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    evidence_status: str = "unknown"
    confidence: str = "low"
    unknowns: list[str] = field(default_factory=list)
    last_checked_at: str = field(default_factory=_now)


@dataclass
class CorpusArtifact(_DictModel):
    source_ref: str
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    acquisition_state: str = "metadata_only"
    local_ref: str | None = None
    content_hash: str | None = None
    evidence_status: str = "unknown"
    notes: list[str] = field(default_factory=list)


@dataclass
class CorpusArtifactManifest(_DictModel):
    target_id: str
    selection_strategy: str
    artifacts: list[CorpusArtifact] = field(default_factory=list)
    time_range: str | None = None
    bias_notes: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)


@dataclass
class TargetPressureItem(_DictModel):
    pressure_id: str
    dimension: str
    observation: str
    evidence_refs: list[str] = field(default_factory=list)
    evidence_status: str = "inference"
    severity: str = "unknown"
    transformation_depth_hint: str = "unknown"
    uncertainty: list[str] = field(default_factory=list)
    source_kind: str = "provider_observation"


@dataclass
class TargetPressurePack(_DictModel):
    target_id: str
    snapshot_id: str
    items: list[TargetPressureItem] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)


@dataclass
class TargetModelBundle(_DictModel):
    """Corpus-derived publication-world models.

    These are provider observations, not canonical Artikl semantics.
    """
    genre_patterns: list[dict[str, Any]] = field(default_factory=list)
    argument_patterns: list[dict[str, Any]] = field(default_factory=list)
    method_patterns: list[dict[str, Any]] = field(default_factory=list)
    citation_patterns: dict[str, Any] = field(default_factory=dict)
    register_patterns: list[dict[str, Any]] = field(default_factory=list)
    novelty_patterns: list[dict[str, Any]] = field(default_factory=list)
    article_models: list[dict[str, Any]] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    confidence: str = "low"
    limitations: list[str] = field(default_factory=list)


@dataclass
class TargetWorldSnapshot(_DictModel):
    snapshot_id: str
    target_id: str
    provider_commit: str | None = None
    venue_profile_ref: str | None = None
    editor_profiles: list[EditorScientificProfile] = field(default_factory=list)
    corpus_manifest: CorpusArtifactManifest | None = None
    target_models: TargetModelBundle | None = None
    model_refs: dict[str, str] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    freshness: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)



@dataclass
class TargetPageSnapshot(_DictModel):
    role: str
    url: str
    access_status: str = "unknown"
    content_hash: str | None = None
    evidence_status: str = "unknown"
    extracted: dict[str, Any] = field(default_factory=dict)
    unknowns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    retrieved_at: str = field(default_factory=_now)


@dataclass
class TargetPageBundle(_DictModel):
    homepage_url: str
    pages: list[TargetPageSnapshot] = field(default_factory=list)
    discovered_urls: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)


@dataclass
class ProviderRunRecord(_DictModel):
    run_id: str
    call_id: str | None = None
    status: str = "pending"
    stage_status: dict[str, str] = field(default_factory=dict)
    target_snapshot_id: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


@dataclass
class VenueCandidateDisposition(_DictModel):
    candidate_key: str
    canonical_name: str
    disposition: str
    issn: str | None = None
    sources: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    evidence_gaps: list[str] = field(default_factory=list)
    merged_candidate_count: int = 1
    raw_candidate_refs: list[str] = field(default_factory=list)


@dataclass
class VenueCandidateScreeningBatch(_DictModel):
    raw_count: int
    unique_count: int
    dispositions: list[VenueCandidateDisposition] = field(default_factory=list)
    duplicate_groups: list[dict[str, Any]] = field(default_factory=list)
    semantic_terms: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)


@dataclass
class KaironTransitionDecision(_DictModel):
    """Proposal-level Kairon transition decision.

    This object may classify transformation depth, but it cannot adopt a
    semantic change. Adoption remains with ARTIKL.KAIRON / author governance.
    """
    decision_id: str
    call_id: str
    target_id: str
    snapshot_id: str
    primary_transition: str
    required_operations: list[str] = field(default_factory=list)
    alternative_transitions: list[str] = field(default_factory=list)
    pressure_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    blocking_evidence_debt: list[str] = field(default_factory=list)
    requires_identity_review: bool = False
    author_decision_required: bool = False
    adoption_status: str = "PROPOSAL_ONLY"
    authority_boundary: str = "ARTIKL.KAIRON/author"
    unknowns: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)


@dataclass
class KaironProviderRequest(_DictModel):
    call_id: str
    artikl_state: ArtiklStatePointer
    target_request: dict[str, Any]
    requested_outputs: list[str] = field(default_factory=list)
    depth: dict[str, Any] = field(default_factory=dict)
    budget: dict[str, Any] = field(default_factory=dict)
    source_policy: dict[str, Any] = field(default_factory=dict)


@dataclass
class KaironProviderResponse(_DictModel):
    call_id: str
    run_id: str
    provider_id: str = "KAIROSKOPION"
    provider_version: str | None = None
    provider_commit: str | None = None
    status: str = "partial"
    target_snapshot: TargetWorldSnapshot | None = None
    pressure_pack: TargetPressurePack | None = None
    diagnostic_refs: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class RoundTripComparison(_DictModel):
    call_id: str
    prior_state: ArtiklStatePointer
    current_state: ArtiklStatePointer
    target_snapshot_id: str
    prior_pressure_ids: list[str] = field(default_factory=list)
    current_pressure_ids: list[str] = field(default_factory=list)
    resolved_pressure_ids: list[str] = field(default_factory=list)
    persistent_pressure_ids: list[str] = field(default_factory=list)
    new_pressure_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
