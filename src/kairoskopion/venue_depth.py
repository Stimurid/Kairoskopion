"""Venue Evidence Depth Model (ADR-15).

Defines the 8-level evidence depth model and demand-driven depth policies
for venue intelligence gathering.
"""

from __future__ import annotations

import dataclasses as dc
from enum import Enum
from typing import Any


class VenueEvidenceDepthLevel(str, Enum):
    L0_IDENTITY = "L0_IDENTITY"
    L1_OFFICIAL_FORMAL = "L1_OFFICIAL_FORMAL"
    L2_PUBLICATION_MODEL = "L2_PUBLICATION_MODEL"
    L3_CORPUS_SAMPLE = "L3_CORPUS_SAMPLE"
    L4_EDITORIAL_INTELLIGENCE = "L4_EDITORIAL_INTELLIGENCE"
    L5_POLICY_AND_INDEXING = "L5_POLICY_AND_INDEXING"
    L6_EXTERNAL_GRAPH = "L6_EXTERNAL_GRAPH"
    L7_USER_MEMORY_AND_OUTCOMES = "L7_USER_MEMORY_AND_OUTCOMES"


DEPTH_LEVEL_ORDER = list(VenueEvidenceDepthLevel)


class VenueAnalysisPurpose(str, Enum):
    QUICK_LOOK = "quick_look"
    FIT_ASSESSMENT = "fit_assessment"
    VENUE_DEEP_PROFILE = "venue_deep_profile"
    SUBMISSION_READY = "submission_ready"
    REVIEW_LOOP = "review_loop"
    MEMORY_REFRESH = "memory_refresh"


# Source roles relevant to each depth level
LEVEL_SOURCE_ROLES: dict[VenueEvidenceDepthLevel, list[str]] = {
    VenueEvidenceDepthLevel.L0_IDENTITY: [
        "openalex_source", "crossref_journal", "doaj_record", "issn_portal",
    ],
    VenueEvidenceDepthLevel.L1_OFFICIAL_FORMAL: [
        "official_homepage", "author_guidelines", "aims_scope", "policy_page",
        "submission_info",
    ],
    VenueEvidenceDepthLevel.L2_PUBLICATION_MODEL: [
        "openalex_works_metadata", "crossref_member", "doaj_record",
        "unpaywall_oa", "sherpa_policy",
    ],
    VenueEvidenceDepthLevel.L3_CORPUS_SAMPLE: [
        "openalex_works_sample", "published_article", "fulltext_corpus",
    ],
    VenueEvidenceDepthLevel.L4_EDITORIAL_INTELLIGENCE: [
        "editorial_board_page", "philpapers_category", "philevents_cfp",
        "hnet_announcement", "association_site",
    ],
    VenueEvidenceDepthLevel.L5_POLICY_AND_INDEXING: [
        "sherpa_policy", "doaj_record", "crossref_license",
        "scopus_snapshot", "wos_snapshot",
    ],
    VenueEvidenceDepthLevel.L6_EXTERNAL_GRAPH: [
        "semantic_scholar_recommendations", "opencitations_graph",
        "dimensions_record", "datacite_record",
    ],
    VenueEvidenceDepthLevel.L7_USER_MEMORY_AND_OUTCOMES: [
        "user_submission_outcome", "user_review_letter",
        "user_tacit_signal", "openreview_trace",
    ],
}

# Evidence statuses typically produced at each level
LEVEL_EVIDENCE_STATUSES: dict[VenueEvidenceDepthLevel, list[str]] = {
    VenueEvidenceDepthLevel.L0_IDENTITY: [
        "FACT_FROM_API_METADATA", "FACT_FROM_SOURCE",
    ],
    VenueEvidenceDepthLevel.L1_OFFICIAL_FORMAL: [
        "FACT_FROM_SOURCE", "VENDOR_CLAIM",
    ],
    VenueEvidenceDepthLevel.L2_PUBLICATION_MODEL: [
        "FACT_FROM_API_METADATA", "VENDOR_CLAIM", "INFERENCE",
    ],
    VenueEvidenceDepthLevel.L3_CORPUS_SAMPLE: [
        "CORPUS_OBSERVATION", "INFERENCE",
    ],
    VenueEvidenceDepthLevel.L4_EDITORIAL_INTELLIGENCE: [
        "INFERENCE", "CORPUS_OBSERVATION",
    ],
    VenueEvidenceDepthLevel.L5_POLICY_AND_INDEXING: [
        "FACT_FROM_API_METADATA", "FACT_FROM_SOURCE",
    ],
    VenueEvidenceDepthLevel.L6_EXTERNAL_GRAPH: [
        "FACT_FROM_API_METADATA", "INFERENCE",
    ],
    VenueEvidenceDepthLevel.L7_USER_MEMORY_AND_OUTCOMES: [
        "PRIOR_OUTCOME", "TACIT_SIGNAL", "USER_NOTE",
    ],
}

# Agents that operate at each depth level
LEVEL_AGENTS: dict[VenueEvidenceDepthLevel, list[str]] = {
    VenueEvidenceDepthLevel.L0_IDENTITY: ["venue_identifier"],
    VenueEvidenceDepthLevel.L1_OFFICIAL_FORMAL: ["venue_profiler", "venue_snapshot_crawler"],
    VenueEvidenceDepthLevel.L2_PUBLICATION_MODEL: [
        "publication_regime_classifier", "venue_publication_profile_builder",
    ],
    VenueEvidenceDepthLevel.L3_CORPUS_SAMPLE: ["corpus_sampler", "corpus_analyzer"],
    VenueEvidenceDepthLevel.L4_EDITORIAL_INTELLIGENCE: [
        "editorial_board_analyzer", "community_signal_collector",
    ],
    VenueEvidenceDepthLevel.L5_POLICY_AND_INDEXING: [],
    VenueEvidenceDepthLevel.L6_EXTERNAL_GRAPH: [],
    VenueEvidenceDepthLevel.L7_USER_MEMORY_AND_OUTCOMES: [],
}


@dc.dataclass
class VenueDepthPolicy:
    """Controls how deep venue evidence collection goes for a given purpose."""

    purpose: str
    min_depth: VenueEvidenceDepthLevel
    target_depth: VenueEvidenceDepthLevel
    max_depth: VenueEvidenceDepthLevel
    required_source_roles: list[str] = dc.field(default_factory=list)
    optional_source_roles: list[str] = dc.field(default_factory=list)
    required_agents: list[str] = dc.field(default_factory=list)
    optional_agents: list[str] = dc.field(default_factory=list)
    stop_conditions: list[str] = dc.field(default_factory=list)
    degradation_rules: list[str] = dc.field(default_factory=list)
    max_api_calls: int = 50
    max_articles_to_sample: int = 30
    freshness_threshold_days: int = 90

    def to_dict(self) -> dict[str, Any]:
        return {
            "purpose": self.purpose,
            "min_depth": self.min_depth.value,
            "target_depth": self.target_depth.value,
            "max_depth": self.max_depth.value,
            "required_source_roles": self.required_source_roles,
            "optional_source_roles": self.optional_source_roles,
            "required_agents": self.required_agents,
            "optional_agents": self.optional_agents,
            "stop_conditions": self.stop_conditions,
            "degradation_rules": self.degradation_rules,
            "max_api_calls": self.max_api_calls,
            "max_articles_to_sample": self.max_articles_to_sample,
            "freshness_threshold_days": self.freshness_threshold_days,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VenueDepthPolicy:
        d = dict(data)
        d["min_depth"] = VenueEvidenceDepthLevel(d["min_depth"])
        d["target_depth"] = VenueEvidenceDepthLevel(d["target_depth"])
        d["max_depth"] = VenueEvidenceDepthLevel(d["max_depth"])
        return cls(**{k: v for k, v in d.items() if k in {f.name for f in dc.fields(cls)}})


def depth_level_index(level: VenueEvidenceDepthLevel) -> int:
    return DEPTH_LEVEL_ORDER.index(level)


def levels_in_range(
    min_depth: VenueEvidenceDepthLevel,
    max_depth: VenueEvidenceDepthLevel,
) -> list[VenueEvidenceDepthLevel]:
    lo = depth_level_index(min_depth)
    hi = depth_level_index(max_depth)
    return DEPTH_LEVEL_ORDER[lo : hi + 1]


# --- Default policies ---

QUICK_LOOK_POLICY = VenueDepthPolicy(
    purpose=VenueAnalysisPurpose.QUICK_LOOK.value,
    min_depth=VenueEvidenceDepthLevel.L0_IDENTITY,
    target_depth=VenueEvidenceDepthLevel.L2_PUBLICATION_MODEL,
    max_depth=VenueEvidenceDepthLevel.L2_PUBLICATION_MODEL,
    required_source_roles=["openalex_source", "crossref_journal"],
    optional_source_roles=["official_homepage", "doaj_record"],
    required_agents=["venue_identifier"],
    optional_agents=["venue_profiler", "publication_regime_classifier"],
    stop_conditions=["identity_resolved", "api_metadata_collected"],
    degradation_rules=[
        "If OpenAlex unavailable, use Crossref only",
        "If no API data, use provided VenueModel fields as-is",
    ],
    max_api_calls=10,
    max_articles_to_sample=0,
    freshness_threshold_days=180,
)

FIT_ASSESSMENT_POLICY = VenueDepthPolicy(
    purpose=VenueAnalysisPurpose.FIT_ASSESSMENT.value,
    min_depth=VenueEvidenceDepthLevel.L0_IDENTITY,
    target_depth=VenueEvidenceDepthLevel.L4_EDITORIAL_INTELLIGENCE,
    max_depth=VenueEvidenceDepthLevel.L4_EDITORIAL_INTELLIGENCE,
    required_source_roles=[
        "openalex_source", "crossref_journal",
        "official_homepage", "author_guidelines",
    ],
    optional_source_roles=[
        "openalex_works_sample", "editorial_board_page",
        "philpapers_category", "doaj_record",
    ],
    required_agents=[
        "venue_identifier", "venue_profiler",
        "publication_regime_classifier", "venue_publication_profile_builder",
    ],
    optional_agents=["corpus_sampler", "corpus_analyzer", "editorial_board_analyzer"],
    stop_conditions=[
        "identity_resolved", "guidelines_extracted",
        "publication_regime_classified", "profile_built",
    ],
    degradation_rules=[
        "If no corpus sample, mark L3 fields as UNKNOWN",
        "If no editorial board data, mark L4 fields as UNKNOWN",
        "Profile builder proceeds with available evidence only",
    ],
    max_api_calls=30,
    max_articles_to_sample=30,
    freshness_threshold_days=90,
)

VENUE_DEEP_PROFILE_POLICY = VenueDepthPolicy(
    purpose=VenueAnalysisPurpose.VENUE_DEEP_PROFILE.value,
    min_depth=VenueEvidenceDepthLevel.L0_IDENTITY,
    target_depth=VenueEvidenceDepthLevel.L6_EXTERNAL_GRAPH,
    max_depth=VenueEvidenceDepthLevel.L6_EXTERNAL_GRAPH,
    required_source_roles=[
        "openalex_source", "crossref_journal", "official_homepage",
        "author_guidelines", "openalex_works_sample",
    ],
    optional_source_roles=[
        "editorial_board_page", "philpapers_category",
        "sherpa_policy", "doaj_record", "unpaywall_oa",
        "semantic_scholar_recommendations",
    ],
    required_agents=[
        "venue_identifier", "venue_profiler",
        "publication_regime_classifier", "venue_publication_profile_builder",
        "corpus_sampler", "corpus_analyzer",
    ],
    optional_agents=["editorial_board_analyzer", "community_signal_collector"],
    stop_conditions=["corpus_profiled", "editorial_analyzed_or_unavailable"],
    degradation_rules=[
        "If no full-text articles, use metadata-only corpus analysis",
        "If editorial board page inaccessible, mark L4 as INACCESSIBLE",
    ],
    max_api_calls=50,
    max_articles_to_sample=50,
    freshness_threshold_days=60,
)

SUBMISSION_READY_POLICY = VenueDepthPolicy(
    purpose=VenueAnalysisPurpose.SUBMISSION_READY.value,
    min_depth=VenueEvidenceDepthLevel.L0_IDENTITY,
    target_depth=VenueEvidenceDepthLevel.L7_USER_MEMORY_AND_OUTCOMES,
    max_depth=VenueEvidenceDepthLevel.L7_USER_MEMORY_AND_OUTCOMES,
    required_source_roles=[
        "openalex_source", "crossref_journal", "official_homepage",
        "author_guidelines", "openalex_works_sample",
    ],
    optional_source_roles=[
        "editorial_board_page", "sherpa_policy", "doaj_record",
        "user_submission_outcome", "user_tacit_signal",
    ],
    required_agents=[
        "venue_identifier", "venue_profiler",
        "publication_regime_classifier", "venue_publication_profile_builder",
        "corpus_sampler", "corpus_analyzer",
    ],
    optional_agents=["editorial_board_analyzer"],
    stop_conditions=["submission_pack_viable"],
    degradation_rules=[
        "If fresh guidelines unavailable, warn but proceed with cached version",
        "If no prior outcomes, proceed without L7 data",
    ],
    max_api_calls=50,
    max_articles_to_sample=50,
    freshness_threshold_days=30,
)

DEFAULT_POLICIES: dict[str, VenueDepthPolicy] = {
    VenueAnalysisPurpose.QUICK_LOOK.value: QUICK_LOOK_POLICY,
    VenueAnalysisPurpose.FIT_ASSESSMENT.value: FIT_ASSESSMENT_POLICY,
    VenueAnalysisPurpose.VENUE_DEEP_PROFILE.value: VENUE_DEEP_PROFILE_POLICY,
    VenueAnalysisPurpose.SUBMISSION_READY.value: SUBMISSION_READY_POLICY,
}


def get_depth_policy(purpose: str) -> VenueDepthPolicy:
    if purpose in DEFAULT_POLICIES:
        return DEFAULT_POLICIES[purpose]
    raise ValueError(f"Unknown purpose: {purpose}. Available: {list(DEFAULT_POLICIES.keys())}")


@dc.dataclass
class LevelCoverage:
    """Coverage state for a single depth level."""

    level: VenueEvidenceDepthLevel
    status: str = "never_run"  # fresh | stale | partial | never_run | inaccessible
    source_count: int = 0
    claim_count: int = 0
    unknown_count: int = 0
    evidence_refs: list[str] = dc.field(default_factory=list)
    confidence: str = "none"  # none | low | medium | high

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "status": self.status,
            "source_count": self.source_count,
            "claim_count": self.claim_count,
            "unknown_count": self.unknown_count,
            "evidence_refs": self.evidence_refs,
            "confidence": self.confidence,
        }


@dc.dataclass
class VenueDepthCoverage:
    """Overall depth coverage for a venue."""

    venue_id: str
    purpose: str
    reached_depth: VenueEvidenceDepthLevel
    completed_levels: list[VenueEvidenceDepthLevel] = dc.field(default_factory=list)
    level_coverage: dict[str, LevelCoverage] = dc.field(default_factory=dict)
    missing_required_sources: list[str] = dc.field(default_factory=list)
    unavailable_sources: list[str] = dc.field(default_factory=list)
    stale_sources: list[str] = dc.field(default_factory=list)
    unknowns: list[str] = dc.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue_id": self.venue_id,
            "purpose": self.purpose,
            "reached_depth": self.reached_depth.value,
            "completed_levels": [l.value for l in self.completed_levels],
            "level_coverage": {k: v.to_dict() for k, v in self.level_coverage.items()},
            "missing_required_sources": self.missing_required_sources,
            "unavailable_sources": self.unavailable_sources,
            "stale_sources": self.stale_sources,
            "unknowns": self.unknowns,
        }

    @property
    def has_coverage_gaps(self) -> bool:
        return bool(self.missing_required_sources) or bool(self.unavailable_sources)

    @property
    def confidence_summary(self) -> str:
        if not self.completed_levels:
            return "none"
        confidences = [
            self.level_coverage[l.value].confidence
            for l in self.completed_levels
            if l.value in self.level_coverage
        ]
        if not confidences:
            return "none"
        if all(c == "high" for c in confidences):
            return "high"
        if any(c == "none" for c in confidences):
            return "low"
        return "medium"
