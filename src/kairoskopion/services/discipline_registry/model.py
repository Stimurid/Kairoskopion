"""DisciplineModel dataclass — runtime mirror of
``data/disciplinary_landscape/schema/discipline_model.schema.json``.

Kept in sync by hand. Schema is the canonical contract; this dataclass
is for ergonomic Python use. JSON round-trip via ``to_dict`` /
``from_dict`` so JSONL persistence stays trivial.

Working-tool fields (epistemic_regime, forms_of_evidence,
canonical_questions, typical_problem_forms, legitimate_objects,
illegitimate_or_borderline_objects, argument_styles, publication_genres,
institutional_forms, russian_specificity, international_mapping) are
optional — seed cards may have only some of them filled in at
``llm_draft`` status. Curator review fills the rest.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

SCHEMA_VERSION = "1.0.0"

REGIONS = ("ru", "international", "eu-fr", "eu-de", "en-us", "en-uk", "other")

SOURCE_STATUSES = (
    "llm_draft",
    "needs_review",
    "user_confirmed",
    "auto_enriched",
    "disputed",
    "merged",
    "deprecated",
    "rejected",
    "candidate",
)


@dataclass
class EvidenceRef:
    source_type: str
    source_id: str | None = None
    source_url: str | None = None
    retrieved_at: str | None = None
    excerpt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EvidenceRef":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class KeyAuthor:
    name: str
    role: str  # founder | classic | contemporary | boundary_setter | critic
    era: str | None = None
    discipline_relevance: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None or k in ("name", "role")}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "KeyAuthor":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class DisciplineModel:
    # Required identity
    discipline_id: str
    display_names: dict[str, str]
    region: str
    source_status: str
    last_updated: str
    schema_version: str = SCHEMA_VERSION
    model_version: str = "0.1.0"

    # Identity / aliases
    aliases: list[str] = field(default_factory=list)

    # Provenance + curator
    curator_notes: str | None = None
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    confidence_by_section: dict[str, str | None] = field(default_factory=dict)
    unknowns: list[str] = field(default_factory=list)
    disputed_fields: list[str] = field(default_factory=list)

    # Working-tool body
    paradigm: str | None = None
    epistemic_regime: str | None = None
    forms_of_evidence: list[str] = field(default_factory=list)
    canonical_questions: list[str] = field(default_factory=list)
    typical_problem_forms: list[str] = field(default_factory=list)
    legitimate_objects: list[str] = field(default_factory=list)
    illegitimate_or_borderline_objects: list[str] = field(default_factory=list)
    argument_styles: list[str] = field(default_factory=list)
    publication_genres: list[str] = field(default_factory=list)
    institutional_forms: list[str] = field(default_factory=list)
    russian_specificity: str | None = None
    international_mapping: list[str] = field(default_factory=list)

    # Methods / authors / history
    methods: list[str] = field(default_factory=list)
    instruments: list[str] = field(default_factory=list)
    ontologies: list[str] = field(default_factory=list)
    key_authors: list[KeyAuthor] = field(default_factory=list)
    history: str | None = None
    boundaries: str | None = None
    adjacent: list[str] = field(default_factory=list)
    typical_venues: list[str] = field(default_factory=list)

    # Stats
    first_seen_in_case: str | None = None
    times_seen: int = 0
    last_enriched: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "schema_version": self.schema_version,
            "model_version": self.model_version,
            "discipline_id": self.discipline_id,
            "display_names": dict(self.display_names),
            "region": self.region,
            "aliases": list(self.aliases),
            "source_status": self.source_status,
            "curator_notes": self.curator_notes,
            "evidence_refs": [e.to_dict() for e in self.evidence_refs],
            "confidence_by_section": dict(self.confidence_by_section),
            "unknowns": list(self.unknowns),
            "disputed_fields": list(self.disputed_fields),
            "paradigm": self.paradigm,
            "epistemic_regime": self.epistemic_regime,
            "forms_of_evidence": list(self.forms_of_evidence),
            "canonical_questions": list(self.canonical_questions),
            "typical_problem_forms": list(self.typical_problem_forms),
            "legitimate_objects": list(self.legitimate_objects),
            "illegitimate_or_borderline_objects": list(
                self.illegitimate_or_borderline_objects
            ),
            "argument_styles": list(self.argument_styles),
            "publication_genres": list(self.publication_genres),
            "institutional_forms": list(self.institutional_forms),
            "russian_specificity": self.russian_specificity,
            "international_mapping": list(self.international_mapping),
            "methods": list(self.methods),
            "instruments": list(self.instruments),
            "ontologies": list(self.ontologies),
            "key_authors": [a.to_dict() for a in self.key_authors],
            "history": self.history,
            "boundaries": self.boundaries,
            "adjacent": list(self.adjacent),
            "typical_venues": list(self.typical_venues),
            "first_seen_in_case": self.first_seen_in_case,
            "times_seen": self.times_seen,
            "last_updated": self.last_updated,
            "last_enriched": self.last_enriched,
        }
        # Drop None-valued top-level optionals so the JSONL stays tidy
        # but keep empty arrays/objects — they carry meaning ("we
        # looked and found nothing" vs "we didn't look").
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DisciplineModel":
        evidence_refs = [
            EvidenceRef.from_dict(e) for e in d.get("evidence_refs", [])
        ]
        key_authors = [KeyAuthor.from_dict(a) for a in d.get("key_authors", [])]
        return cls(
            discipline_id=d["discipline_id"],
            display_names=dict(d["display_names"]),
            region=d["region"],
            source_status=d["source_status"],
            last_updated=d["last_updated"],
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            model_version=d.get("model_version", "0.1.0"),
            aliases=list(d.get("aliases", [])),
            curator_notes=d.get("curator_notes"),
            evidence_refs=evidence_refs,
            confidence_by_section=dict(d.get("confidence_by_section", {})),
            unknowns=list(d.get("unknowns", [])),
            disputed_fields=list(d.get("disputed_fields", [])),
            paradigm=d.get("paradigm"),
            epistemic_regime=d.get("epistemic_regime"),
            forms_of_evidence=list(d.get("forms_of_evidence", [])),
            canonical_questions=list(d.get("canonical_questions", [])),
            typical_problem_forms=list(d.get("typical_problem_forms", [])),
            legitimate_objects=list(d.get("legitimate_objects", [])),
            illegitimate_or_borderline_objects=list(
                d.get("illegitimate_or_borderline_objects", [])
            ),
            argument_styles=list(d.get("argument_styles", [])),
            publication_genres=list(d.get("publication_genres", [])),
            institutional_forms=list(d.get("institutional_forms", [])),
            russian_specificity=d.get("russian_specificity"),
            international_mapping=list(d.get("international_mapping", [])),
            methods=list(d.get("methods", [])),
            instruments=list(d.get("instruments", [])),
            ontologies=list(d.get("ontologies", [])),
            key_authors=key_authors,
            history=d.get("history"),
            boundaries=d.get("boundaries"),
            adjacent=list(d.get("adjacent", [])),
            typical_venues=list(d.get("typical_venues", [])),
            first_seen_in_case=d.get("first_seen_in_case"),
            times_seen=int(d.get("times_seen", 0)),
            last_enriched=d.get("last_enriched"),
        )

    def summary_for_context(self, max_chars: int = 800) -> str:
        """Compact representation used by the matcher to feed
        candidate context into ``semantic_profiler`` prompts.

        This is NOT a full card. It's the minimum the consumer needs to
        recognize whether the article in front of them fits: name,
        legitimate objects, canonical questions, forms of evidence,
        what does NOT fit. Capped at ``max_chars``.
        """
        ru = self.display_names.get("ru", "")
        en = self.display_names.get("en", "")
        name = f"{ru} / {en}" if ru and en else (ru or en or self.discipline_id)
        parts = [f"[{self.discipline_id}] {name} (region: {self.region})"]
        if self.legitimate_objects:
            parts.append(
                "Legitimate objects: " + "; ".join(self.legitimate_objects[:6])
            )
        if self.canonical_questions:
            parts.append(
                "Canonical questions: "
                + "; ".join(self.canonical_questions[:4])
            )
        if self.forms_of_evidence:
            parts.append(
                "Forms of evidence: " + "; ".join(self.forms_of_evidence[:4])
            )
        if self.illegitimate_or_borderline_objects:
            parts.append(
                "NOT this discipline: "
                + "; ".join(self.illegitimate_or_borderline_objects[:3])
            )
        text = " | ".join(parts)
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."
