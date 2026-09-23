"""Deterministic qualification planner for ARTIKL.KAIRON batch runs.

The planner owns no semantic adoption. It expands already-authoritative Artikl
article states against evidence-backed target snapshots and preserves the
academic-world path plus the local-first lookup receipt for every cell.

This module is deliberately additive to the existing provider surface. It does
not replace the legacy Case/venue-funnel pipeline and it never mutates a frozen
TargetWorld snapshot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
from typing import Any, Iterable

from .models import ArtiklStatePointer


ACADEMIC_WORLD_NODE_TYPES = (
    "WORLD",
    "REGION_ECOLOGY",
    "DISCIPLINE_FAMILY",
    "DISCIPLINE",
    "SUBDISCIPLINE",
    "SCHOOL_TRADITION_TRIBE",
    "DEBATE",
    "VENUE_FAMILY",
    "VENUE",
    "SECTION",
    "ISSUE",
    "CFP",
)


@dataclass
class _BatchDictModel:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AcademicWorldNode(_BatchDictModel):
    """Evidence-bearing node in the publication-world graph.

    parent_ids is intentionally plural: disciplines, schools and venue
    families may live in several regional/institutional ecologies at once.
    Region labels are data, not a closed civilizational enum.
    """

    node_id: str
    node_type: str
    names: dict[str, str] = field(default_factory=dict)
    parent_ids: list[str] = field(default_factory=list)
    adjacent_ids: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    institutional_regions: list[str] = field(default_factory=list)
    citation_ecology_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    source_status: str = "unknown"
    review_status: str = "unreviewed"
    confidence: str = "low"
    freshness: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("academic-world node_id must be non-empty")
        if self.node_type not in ACADEMIC_WORLD_NODE_TYPES:
            raise ValueError(
                f"unsupported academic-world node_type: {self.node_type!r}"
            )


@dataclass
class LocalFirstAuditReceipt(_BatchDictModel):
    """Proof that durable local knowledge was checked before network discovery."""

    target_id: str
    checked_discipline_registry: bool = False
    checked_venue_registry: bool = False
    checked_target_world_store: bool = False
    checked_venue_memory: bool = False
    local_hits: list[str] = field(default_factory=list)
    stale_local_refs: list[str] = field(default_factory=list)
    external_discovery_used: bool = False
    external_task_refs: list[str] = field(default_factory=list)
    persisted_refs: list[str] = field(default_factory=list)
    status: str = "pending"

    def validate(self) -> None:
        if not self.target_id.strip():
            raise ValueError("local-first receipt target_id must be non-empty")
        if self.external_discovery_used and not (
            self.checked_discipline_registry
            and self.checked_venue_registry
            and self.checked_target_world_store
        ):
            raise ValueError(
                "external discovery requires prior discipline, venue and "
                "TargetWorld local checks"
            )


@dataclass
class BatchArticleInput(_BatchDictModel):
    article_id: str
    artikl_state: ArtiklStatePointer
    protected_core: list[str] = field(default_factory=list)
    mutable_zones: list[str] = field(default_factory=list)
    allowed_change_classes: list[str] = field(default_factory=list)
    academic_world_path_hints: list[list[str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.article_id.strip():
            raise ValueError("article_id must be non-empty")
        if self.artikl_state.authority != "ARTIKL":
            raise ValueError("batch article state must retain ARTIKL authority")


@dataclass
class BatchTargetInput(_BatchDictModel):
    target_id: str
    snapshot_id: str
    academic_world_path: list[str] = field(default_factory=list)
    local_first_receipt: LocalFirstAuditReceipt | None = None
    freshness: dict[str, Any] = field(default_factory=dict)
    provider_commit: str | None = None

    def __post_init__(self) -> None:
        if not self.target_id.strip():
            raise ValueError("target_id must be non-empty")
        if not self.snapshot_id.strip():
            raise ValueError("target snapshot_id must be non-empty")
        if self.local_first_receipt is not None:
            if self.local_first_receipt.target_id != self.target_id:
                raise ValueError(
                    "local-first receipt target_id must match BatchTargetInput"
                )
            self.local_first_receipt.validate()


@dataclass
class BatchCell(_BatchDictModel):
    cell_id: str
    batch_id: str
    article_id: str
    article_state_id: str
    target_id: str
    target_snapshot_id: str
    academic_world_path: list[str] = field(default_factory=list)
    status: str = "pending"
    pressure_pack_id: str | None = None
    transition_decision_id: str | None = None
    target_variant_pointer: str | None = None
    round_trip_ref: str | None = None
    evidence_debt: list[str] = field(default_factory=list)
    author_decision_required: bool = False
    local_first_receipt: LocalFirstAuditReceipt | None = None


@dataclass
class BatchQualificationPlan(_BatchDictModel):
    batch_id: str
    article_ids: list[str]
    target_ids: list[str]
    cells: list[BatchCell]
    snapshot_reuse: dict[str, list[str]] = field(default_factory=dict)
    status: str = "planned"

    def cells_for_article(self, article_id: str) -> list[BatchCell]:
        return [c for c in self.cells if c.article_id == article_id]

    def cells_for_target(self, target_id: str) -> list[BatchCell]:
        return [c for c in self.cells if c.target_id == target_id]


def _ensure_unique(values: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    if duplicates:
        raise ValueError(f"duplicate {label}: {', '.join(sorted(duplicates))}")


def _cell_id(
    *,
    batch_id: str,
    article_id: str,
    article_state_id: str,
    target_id: str,
    snapshot_id: str,
) -> str:
    raw = "|".join(
        (batch_id, article_id, article_state_id, target_id, snapshot_id)
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"kaironbatchcell:{digest}"


def build_batch_qualification_plan(
    *,
    batch_id: str,
    articles: list[BatchArticleInput],
    targets: list[BatchTargetInput],
) -> BatchQualificationPlan:
    """Build the deterministic article x target qualification matrix.

    Target snapshots are referenced, never copied or mutated. Reuse is made
    explicit in snapshot_reuse so a scheduler can coalesce target-world work
    while preserving article-specific pressure/transition state.
    """

    if not batch_id.strip():
        raise ValueError("batch_id must be non-empty")
    if not articles:
        raise ValueError("batch requires at least one article")
    if not targets:
        raise ValueError("batch requires at least one target")

    _ensure_unique((a.article_id for a in articles), "article_id")
    _ensure_unique((t.target_id for t in targets), "target_id")

    cells: list[BatchCell] = []
    snapshot_reuse: dict[str, list[str]] = {}

    for article in articles:
        for target in targets:
            cid = _cell_id(
                batch_id=batch_id,
                article_id=article.article_id,
                article_state_id=article.artikl_state.state_id,
                target_id=target.target_id,
                snapshot_id=target.snapshot_id,
            )
            cell = BatchCell(
                cell_id=cid,
                batch_id=batch_id,
                article_id=article.article_id,
                article_state_id=article.artikl_state.state_id,
                target_id=target.target_id,
                target_snapshot_id=target.snapshot_id,
                academic_world_path=list(target.academic_world_path),
                local_first_receipt=target.local_first_receipt,
            )
            cells.append(cell)
            snapshot_reuse.setdefault(target.snapshot_id, []).append(cid)

    return BatchQualificationPlan(
        batch_id=batch_id,
        article_ids=[a.article_id for a in articles],
        target_ids=[t.target_id for t in targets],
        cells=cells,
        snapshot_reuse=snapshot_reuse,
    )
