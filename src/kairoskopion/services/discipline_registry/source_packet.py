"""DisciplineSourcePacket — provenance container.

The seeder consumes a packet and emits a ``DisciplineModel`` card with
its ``evidence_refs`` already filled in from the packet. This enforces
the rule "no carded discipline without provenance" — there is no path
from raw web search to a registry row that bypasses a packet.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


VALID_SOURCE_TYPES = frozenset({
    "vak_passport",
    "erc_descriptor",
    "oecd_ford",
    "isced_f",
    "acm_ccs",
    "eric",
    "phil_papers",
    "apa",
    "case_observation",
    "llm_pretraining",
    "other",
})


@dataclass
class DisciplineSourcePacket:
    """Structured input for ``DisciplineSeederAgent``.

    The packet says: "here is a discipline-shaped thing I retrieved
    from <source_type>; here is what it looked like; please synthesize
    a ``DisciplineModel`` card for it." The seeder does the LLM
    synthesis; the packet does NOT.
    """

    source_type: str
    source_id: str
    candidate_display_name_ru: str | None = None
    candidate_display_name_en: str | None = None
    candidate_region: str | None = None
    source_url: str | None = None
    retrieved_at: str | None = None
    raw_excerpt: str | None = None
    raw_facets: dict[str, Any] = field(default_factory=dict)
    operator_hints: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.source_type not in VALID_SOURCE_TYPES:
            raise ValueError(
                f"Unknown source_type {self.source_type!r}; "
                f"valid: {sorted(VALID_SOURCE_TYPES)}"
            )
        if not self.source_id:
            raise ValueError("source_id is required (stable id within source)")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DisciplineSourcePacket":
        return cls(
            source_type=d["source_type"],
            source_id=d["source_id"],
            candidate_display_name_ru=d.get("candidate_display_name_ru"),
            candidate_display_name_en=d.get("candidate_display_name_en"),
            candidate_region=d.get("candidate_region"),
            source_url=d.get("source_url"),
            retrieved_at=d.get("retrieved_at"),
            raw_excerpt=d.get("raw_excerpt"),
            raw_facets=dict(d.get("raw_facets", {})),
            operator_hints=list(d.get("operator_hints", [])),
        )
