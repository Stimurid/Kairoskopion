"""Registry record models (P6).

All records follow the same pattern:
- Dataclass with to_dict()/from_dict()
- source_status + review_status lifecycle fields
- evidence_refs for provenance tracking
- ID generator for each type
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from ..ids import (
    discipline_record_id,
    epistemic_framework_record_id,
    venue_record_id,
    venue_section_record_id,
    classification_system_record_id,
    subject_category_record_id,
    venue_classification_record_id,
    venue_metric_record_id,
    source_evidence_packet_id,
    generate_id,
)

SOURCE_STATUSES = ("provisional", "accepted", "rejected", "unknown")
REVIEW_STATUSES = ("pending", "reviewed", "curator_confirmed", "rejected")
TASK_STATUSES = ("open", "in_progress", "completed", "blocked", "cancelled")
EVIDENCE_STATUSES = (
    "source_grounded", "corpus_grounded", "user_provided",
    "adapter_result", "llm_inference", "vendor_claim", "unknown",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _acquisition_task_id() -> str:
    return generate_id("acqtask")


def _source_packet_id() -> str:
    return source_evidence_packet_id()


# ---------------------------------------------------------------------------
# EvidenceRef — shared across all record types
# ---------------------------------------------------------------------------

@dataclass
class EvidenceRef:
    evidence_id: str = field(default_factory=lambda: generate_id("evref"))
    source_type: str | None = None
    source_id: str | None = None
    source_url: str | None = None
    source_title: str | None = None
    excerpt: str | None = None
    retrieval_date: str | None = None
    evidence_status: str = "unknown"
    confidence: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EvidenceRef:
        fields = cls.__dataclass_fields__
        return cls(**{k: d.get(k) for k in fields if k in d})


# ---------------------------------------------------------------------------
# SourcePacket — bridge between search/adapters and provisional records
# ---------------------------------------------------------------------------

@dataclass
class SourcePacket:
    packet_id: str = field(default_factory=_source_packet_id)
    packet_type: str | None = None
    query: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    source_url: str | None = None
    title: str | None = None
    excerpt: str | None = None
    retrieval_date: str | None = None
    adapter_name: str | None = None
    raw_ref: dict[str, Any] = field(default_factory=dict)
    confidence: str | None = None
    evidence_status: str = "unknown"
    warnings: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourcePacket:
        fields = cls.__dataclass_fields__
        return cls(**{k: d.get(k) for k in fields if k in d})

    def to_evidence_ref(self) -> EvidenceRef:
        return EvidenceRef(
            source_type=self.source_type,
            source_id=self.source_id,
            source_url=self.source_url,
            source_title=self.title,
            excerpt=self.excerpt,
            retrieval_date=self.retrieval_date,
            evidence_status=self.evidence_status,
            confidence=self.confidence,
        )


# ---------------------------------------------------------------------------
# SourceAcquisitionTask
# ---------------------------------------------------------------------------

@dataclass
class SourceAcquisitionTask:
    task_id: str = field(default_factory=_acquisition_task_id)
    task_type: str | None = None
    query: str | None = None
    reason: str | None = None
    target_sources: list[str] = field(default_factory=list)
    priority: str = "normal"
    status: str = "open"
    created_by_agent: str | None = None
    related_case_id: str | None = None
    related_record_id: str | None = None
    result_packet_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceAcquisitionTask:
        fields = cls.__dataclass_fields__
        return cls(**{k: d.get(k) for k in fields if k in d})


# ---------------------------------------------------------------------------
# _RegistryRecordMixin — shared fields for all registry records
# ---------------------------------------------------------------------------

def _evidence_refs_from_dict(raw: list[dict]) -> list[EvidenceRef]:
    return [EvidenceRef.from_dict(e) for e in raw]


# ---------------------------------------------------------------------------
# DisciplineRecord
# ---------------------------------------------------------------------------

@dataclass
class DisciplineRecord:
    discipline_id: str = field(default_factory=discipline_record_id)
    display_names: dict[str, str] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    source_status: str = "provisional"
    review_status: str = "pending"
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    legitimate_objects: list[str] = field(default_factory=list)
    boundary_objects: list[str] = field(default_factory=list)
    epistemic_regime_notes: str | None = None
    method_or_evidence_regimes: list[str] = field(default_factory=list)
    classification_links: list[str] = field(default_factory=list)
    provenance: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence_refs"] = [e.to_dict() for e in self.evidence_refs]
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DisciplineRecord:
        refs = _evidence_refs_from_dict(d.get("evidence_refs", []))
        return cls(
            discipline_id=d.get("discipline_id", discipline_record_id()),
            display_names=dict(d.get("display_names", {})),
            aliases=list(d.get("aliases", [])),
            source_status=d.get("source_status", "provisional"),
            review_status=d.get("review_status", "pending"),
            evidence_refs=refs,
            legitimate_objects=list(d.get("legitimate_objects", [])),
            boundary_objects=list(d.get("boundary_objects", [])),
            epistemic_regime_notes=d.get("epistemic_regime_notes"),
            method_or_evidence_regimes=list(d.get("method_or_evidence_regimes", [])),
            classification_links=list(d.get("classification_links", [])),
            provenance=d.get("provenance"),
            created_at=d.get("created_at", _now()),
            updated_at=d.get("updated_at", _now()),
        )

    @property
    def record_id(self) -> str:
        return self.discipline_id


# ---------------------------------------------------------------------------
# EpistemicFrameworkRecord
# ---------------------------------------------------------------------------

@dataclass
class EpistemicFrameworkRecord:
    framework_id: str = field(default_factory=epistemic_framework_record_id)
    label: str | None = None
    aliases: list[str] = field(default_factory=list)
    framework_kind: str | None = None
    applicability: str | None = None
    source_status: str = "provisional"
    review_status: str = "pending"
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    related_disciplines: list[str] = field(default_factory=list)
    boundary_notes: str | None = None
    provenance: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence_refs"] = [e.to_dict() for e in self.evidence_refs]
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EpistemicFrameworkRecord:
        refs = _evidence_refs_from_dict(d.get("evidence_refs", []))
        return cls(
            framework_id=d.get("framework_id", epistemic_framework_record_id()),
            label=d.get("label"),
            aliases=list(d.get("aliases", [])),
            framework_kind=d.get("framework_kind"),
            applicability=d.get("applicability"),
            source_status=d.get("source_status", "provisional"),
            review_status=d.get("review_status", "pending"),
            evidence_refs=refs,
            related_disciplines=list(d.get("related_disciplines", [])),
            boundary_notes=d.get("boundary_notes"),
            provenance=d.get("provenance"),
            created_at=d.get("created_at", _now()),
            updated_at=d.get("updated_at", _now()),
        )

    @property
    def record_id(self) -> str:
        return self.framework_id


# ---------------------------------------------------------------------------
# VenueRegistryRecord
# ---------------------------------------------------------------------------

@dataclass
class VenueRegistryRecord:
    venue_id: str = field(default_factory=venue_record_id)
    canonical_name: str | None = None
    aliases: list[str] = field(default_factory=list)
    issn: str | None = None
    eissn: str | None = None
    publisher: str | None = None
    official_urls: list[str] = field(default_factory=list)
    parent_venue_id: str | None = None
    source_status: str = "provisional"
    review_status: str = "pending"
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provenance: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence_refs"] = [e.to_dict() for e in self.evidence_refs]
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VenueRegistryRecord:
        refs = _evidence_refs_from_dict(d.get("evidence_refs", []))
        return cls(
            venue_id=d.get("venue_id", venue_record_id()),
            canonical_name=d.get("canonical_name"),
            aliases=list(d.get("aliases", [])),
            issn=d.get("issn"),
            eissn=d.get("eissn"),
            publisher=d.get("publisher"),
            official_urls=list(d.get("official_urls", [])),
            parent_venue_id=d.get("parent_venue_id"),
            source_status=d.get("source_status", "provisional"),
            review_status=d.get("review_status", "pending"),
            evidence_refs=refs,
            warnings=list(d.get("warnings", [])),
            provenance=d.get("provenance"),
            created_at=d.get("created_at", _now()),
            updated_at=d.get("updated_at", _now()),
        )

    @property
    def record_id(self) -> str:
        return self.venue_id


# ---------------------------------------------------------------------------
# VenueSectionRecord
# ---------------------------------------------------------------------------

SECTION_TYPES = (
    "section", "track", "special_issue", "issue_call",
    "proceedings_track", "edited_volume_section", "other", "unknown",
)

@dataclass
class VenueSectionRecord:
    section_id: str = field(default_factory=venue_section_record_id)
    parent_venue_id: str | None = None
    section_name: str | None = None
    section_type: str = "unknown"
    scope: str | None = None
    accepted_article_types: list[str] = field(default_factory=list)
    field_links: list[str] = field(default_factory=list)
    active_dates: str | None = None
    deadlines: str | None = None
    review_policy: str | None = None
    special_requirements: str | None = None
    source_status: str = "provisional"
    review_status: str = "pending"
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    provenance: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence_refs"] = [e.to_dict() for e in self.evidence_refs]
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VenueSectionRecord:
        refs = _evidence_refs_from_dict(d.get("evidence_refs", []))
        return cls(
            section_id=d.get("section_id", venue_section_record_id()),
            parent_venue_id=d.get("parent_venue_id"),
            section_name=d.get("section_name"),
            section_type=d.get("section_type", "unknown"),
            scope=d.get("scope"),
            accepted_article_types=list(d.get("accepted_article_types", [])),
            field_links=list(d.get("field_links", [])),
            active_dates=d.get("active_dates"),
            deadlines=d.get("deadlines"),
            review_policy=d.get("review_policy"),
            special_requirements=d.get("special_requirements"),
            source_status=d.get("source_status", "provisional"),
            review_status=d.get("review_status", "pending"),
            evidence_refs=refs,
            provenance=d.get("provenance"),
            created_at=d.get("created_at", _now()),
            updated_at=d.get("updated_at", _now()),
        )

    @property
    def record_id(self) -> str:
        return self.section_id


# ---------------------------------------------------------------------------
# ClassificationSystemRecord
# ---------------------------------------------------------------------------

@dataclass
class ClassificationSystemRecord:
    system_id: str = field(default_factory=classification_system_record_id)
    name: str | None = None
    region: str | None = None
    version_or_year: str | None = None
    source_status: str = "provisional"
    review_status: str = "pending"
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence_refs"] = [e.to_dict() for e in self.evidence_refs]
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ClassificationSystemRecord:
        refs = _evidence_refs_from_dict(d.get("evidence_refs", []))
        return cls(
            system_id=d.get("system_id", classification_system_record_id()),
            name=d.get("name"),
            region=d.get("region"),
            version_or_year=d.get("version_or_year"),
            source_status=d.get("source_status", "provisional"),
            review_status=d.get("review_status", "pending"),
            evidence_refs=refs,
            created_at=d.get("created_at", _now()),
            updated_at=d.get("updated_at", _now()),
        )

    @property
    def record_id(self) -> str:
        return self.system_id


# ---------------------------------------------------------------------------
# SubjectCategoryRecord
# ---------------------------------------------------------------------------

@dataclass
class SubjectCategoryRecord:
    category_id: str = field(default_factory=subject_category_record_id)
    classification_system_id: str | None = None
    code: str | None = None
    label: str | None = None
    parent_category_id: str | None = None
    source_status: str = "provisional"
    review_status: str = "pending"
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence_refs"] = [e.to_dict() for e in self.evidence_refs]
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SubjectCategoryRecord:
        refs = _evidence_refs_from_dict(d.get("evidence_refs", []))
        return cls(
            category_id=d.get("category_id", subject_category_record_id()),
            classification_system_id=d.get("classification_system_id"),
            code=d.get("code"),
            label=d.get("label"),
            parent_category_id=d.get("parent_category_id"),
            source_status=d.get("source_status", "provisional"),
            review_status=d.get("review_status", "pending"),
            evidence_refs=refs,
            created_at=d.get("created_at", _now()),
            updated_at=d.get("updated_at", _now()),
        )

    @property
    def record_id(self) -> str:
        return self.category_id


# ---------------------------------------------------------------------------
# VenueClassificationRecord
# ---------------------------------------------------------------------------

@dataclass
class VenueClassificationRecord:
    record_id: str = field(default_factory=venue_classification_record_id)
    venue_id: str | None = None
    section_id: str | None = None
    classification_system_id: str | None = None
    subject_category_id: str | None = None
    year_or_version: str | None = None
    source_ref: str | None = None
    evidence_status: str = "unknown"
    review_status: str = "pending"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VenueClassificationRecord:
        return cls(
            record_id=d.get("record_id", venue_classification_record_id()),
            venue_id=d.get("venue_id"),
            section_id=d.get("section_id"),
            classification_system_id=d.get("classification_system_id"),
            subject_category_id=d.get("subject_category_id"),
            year_or_version=d.get("year_or_version"),
            source_ref=d.get("source_ref"),
            evidence_status=d.get("evidence_status", "unknown"),
            review_status=d.get("review_status", "pending"),
            created_at=d.get("created_at", _now()),
            updated_at=d.get("updated_at", _now()),
        )


# ---------------------------------------------------------------------------
# VenueMetricRecord
# ---------------------------------------------------------------------------

METRIC_TYPES = (
    "quartile", "rank", "percentile", "impact_factor",
    "cite_score", "h_index", "other",
)

@dataclass
class VenueMetricRecord:
    metric_id: str = field(default_factory=venue_metric_record_id)
    venue_id: str | None = None
    section_id: str | None = None
    metric_system: str | None = None
    database: str | None = None
    subject_category_id: str | None = None
    year: str | None = None
    metric_type: str | None = None
    metric_value: str | None = None
    source_ref: str | None = None
    evidence_status: str = "unknown"
    retrieval_date: str | None = None
    review_status: str = "pending"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VenueMetricRecord:
        return cls(
            metric_id=d.get("metric_id", venue_metric_record_id()),
            venue_id=d.get("venue_id"),
            section_id=d.get("section_id"),
            metric_system=d.get("metric_system"),
            database=d.get("database"),
            subject_category_id=d.get("subject_category_id"),
            year=d.get("year"),
            metric_type=d.get("metric_type"),
            metric_value=d.get("metric_value"),
            source_ref=d.get("source_ref"),
            evidence_status=d.get("evidence_status", "unknown"),
            retrieval_date=d.get("retrieval_date"),
            review_status=d.get("review_status", "pending"),
            created_at=d.get("created_at", _now()),
            updated_at=d.get("updated_at", _now()),
        )
