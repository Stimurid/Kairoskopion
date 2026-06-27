"""Source Authority Registry and Sufficiency Evaluator (P7.2).

SourceAuthorityRecord describes WHERE facts come from (source-of-sources).
SourceAuthoritySufficiencyEvaluator checks whether authority coverage is
sufficient for a given country/domain/task before creating factual
acquisition tasks.

Doctrine: before populating factual registries (journals, disciplines,
metrics), the system must know which authority sources are relevant
for the target country/domain. Missing authorities generate
SourceAuthorityDiscoveryTasks, not factual tasks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from ..ids import generate_id


def _authority_id() -> str:
    return generate_id("srcauth")


def _authority_task_id() -> str:
    return generate_id("authtask")


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# SourceAuthorityRecord
# ---------------------------------------------------------------------------

@dataclass
class SourceAuthorityRecord:
    authority_id: str = field(default_factory=_authority_id)
    authority_name: str = ""
    authority_type: str = "other"
    country: str | None = None
    region: str | None = None
    language: str | None = None
    domain_scope: str | None = None
    discipline_scope: str | None = None
    publication_scope: str | None = None
    source_url: str | None = None
    local_source_ref: str | None = None
    access_mode: str = "unknown"
    adapter_hint: str | None = None
    update_frequency: str | None = None
    freshness_requirement: str | None = None
    known_limitations: str | None = None
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    source_status: str = "provisional"
    review_status: str = "pending"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceAuthorityRecord:
        fields = cls.__dataclass_fields__
        return cls(**{k: d.get(k) for k in fields if k in d})


# ---------------------------------------------------------------------------
# SourceAuthorityDiscoveryTask
# ---------------------------------------------------------------------------

@dataclass
class SourceAuthorityDiscoveryTask:
    task_id: str = field(default_factory=_authority_task_id)
    target_country: str | None = None
    target_region: str | None = None
    target_domain: str | None = None
    target_discipline: str | None = None
    publication_scope: str | None = None
    missing_authority_type: str = "other"
    reason: str = ""
    search_queries: list[str] = field(default_factory=list)
    suggested_connectors: list[str] = field(default_factory=list)
    priority: str = "normal"
    status: str = "open"
    result_authority_ids: list[str] = field(default_factory=list)
    notes: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceAuthorityDiscoveryTask:
        fields = cls.__dataclass_fields__
        return cls(**{k: d.get(k) for k in fields if k in d})


# ---------------------------------------------------------------------------
# SourceAuthorityStore (JSONL-backed)
# ---------------------------------------------------------------------------

class SourceAuthorityStore:
    def __init__(self, jsonl_path: Path | None = None):
        self._path = jsonl_path
        self._by_id: dict[str, SourceAuthorityRecord] = {}
        if jsonl_path and jsonl_path.exists():
            self._load()

    def _load(self) -> None:
        if not self._path or not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = SourceAuthorityRecord.from_dict(json.loads(line))
            self._by_id[rec.authority_id] = rec

    def _persist(self, rec: SourceAuthorityRecord) -> None:
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    def add(self, rec: SourceAuthorityRecord) -> SourceAuthorityRecord:
        self._by_id[rec.authority_id] = rec
        self._persist(rec)
        return rec

    def get(self, authority_id: str) -> SourceAuthorityRecord | None:
        return self._by_id.get(authority_id)

    def list_all(self) -> list[SourceAuthorityRecord]:
        return list(self._by_id.values())

    def search(self, query: str, limit: int = 10) -> list[SourceAuthorityRecord]:
        q = query.lower()
        results = []
        for rec in self._by_id.values():
            searchable = f"{rec.authority_name} {rec.authority_type} {rec.domain_scope or ''} {rec.country or ''}"
            if q in searchable.lower():
                results.append(rec)
                if len(results) >= limit:
                    break
        return results

    def by_country(self, country: str) -> list[SourceAuthorityRecord]:
        c = country.upper()
        return [r for r in self._by_id.values() if (r.country or "").upper() == c]

    def by_type(self, authority_type: str) -> list[SourceAuthorityRecord]:
        return [r for r in self._by_id.values() if r.authority_type == authority_type]

    def export_snapshot(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._by_id.values()]


# ---------------------------------------------------------------------------
# SourceAuthorityDiscoveryTaskStore
# ---------------------------------------------------------------------------

class SourceAuthorityDiscoveryTaskStore:
    def __init__(self, jsonl_path: Path | None = None):
        self._path = jsonl_path
        self._by_id: dict[str, SourceAuthorityDiscoveryTask] = {}
        if jsonl_path and jsonl_path.exists():
            self._load()

    def _load(self) -> None:
        if not self._path or not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = SourceAuthorityDiscoveryTask.from_dict(json.loads(line))
            self._by_id[rec.task_id] = rec

    def _persist(self, rec: SourceAuthorityDiscoveryTask) -> None:
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    def add(self, rec: SourceAuthorityDiscoveryTask) -> SourceAuthorityDiscoveryTask:
        self._by_id[rec.task_id] = rec
        self._persist(rec)
        return rec

    def get(self, task_id: str) -> SourceAuthorityDiscoveryTask | None:
        return self._by_id.get(task_id)

    def list_all(self) -> list[SourceAuthorityDiscoveryTask]:
        return list(self._by_id.values())

    def list_open(self) -> list[SourceAuthorityDiscoveryTask]:
        return [t for t in self._by_id.values() if t.status in ("open", "in_progress")]

    def export_snapshot(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._by_id.values()]


# ---------------------------------------------------------------------------
# Authority type constants
# ---------------------------------------------------------------------------

AUTHORITY_TYPES = [
    "discipline_classification",
    "scientific_specialty_list",
    "national_journal_registry",
    "journal_index",
    "metric_source",
    "subject_category_source",
    "author_guidelines_source",
    "editorial_board_source",
    "journal_archive_source",
    "citation_database",
    "scholarly_search",
    "institutional_profile_source",
    "author_profile_source",
    "society_or_association_source",
    "other",
]

# Country-specific authority hints
COUNTRY_AUTHORITY_HINTS: dict[str, dict[str, list[str]]] = {
    "RU": {
        "discipline_classification": [
            "VAK nomenclature of scientific specialties",
            "ГРНТИ (State classification of scientific and technical information)",
        ],
        "national_journal_registry": [
            "eLibrary.ru / РИНЦ journal registry",
            "VAK journal list (Перечень ВАК)",
        ],
        "metric_source": [
            "РИНЦ / eLibrary indicators",
            "Scopus / SJR (if used)",
            "Web of Science / ESCI (if used)",
        ],
        "journal_archive_source": [
            "CyberLeninka (cyberleninka.ru)",
            "eLibrary.ru archive (requires auth)",
        ],
        "citation_database": [
            "OpenAlex",
            "Crossref",
            "OpenCitations",
        ],
    },
    "GENERIC": {
        "discipline_classification": [
            "National research classification",
            "OECD FORD classification",
        ],
        "national_journal_registry": [
            "National scholarly journal index",
            "Ministry/council journal list",
        ],
        "metric_source": [
            "Relevant indexing databases (Scopus, WoS, regional)",
        ],
        "journal_archive_source": [
            "DOAJ directory",
            "Journal official archives",
        ],
        "citation_database": [
            "OpenAlex",
            "Crossref",
        ],
    },
}


# ---------------------------------------------------------------------------
# Sufficiency criteria
# ---------------------------------------------------------------------------

MINIMUM_AUTHORITY_SET = {
    "discipline_classification": {
        "description": "Official discipline/specialty classification",
        "required_for": ["discipline_lookup", "venue_universe"],
    },
    "national_journal_registry": {
        "description": "National/regional journal list or registry",
        "required_for": ["venue_universe", "venue_discovery"],
    },
    "metric_source": {
        "description": "Journal metrics/indexing database",
        "required_for": ["shortlist", "venue_metrics"],
    },
    "author_guidelines_source": {
        "description": "Journal author guidelines / aims & scope",
        "required_for": ["deep_venue_model", "fit_assessment"],
    },
    "editorial_board_source": {
        "description": "Editorial board page",
        "required_for": ["deep_venue_model", "editor_background"],
    },
    "journal_archive_source": {
        "description": "Journal archive / recent issues",
        "required_for": ["deep_venue_model", "corpus_analysis"],
    },
    "citation_database": {
        "description": "Citation/reference database",
        "required_for": ["citation_ecology", "corpus_analysis"],
    },
}


# ---------------------------------------------------------------------------
# SourceAuthoritySufficiencyEvaluator
# ---------------------------------------------------------------------------

@dataclass
class SufficiencyResult:
    sufficient: bool = False
    missing_authority_types: list[str] = field(default_factory=list)
    usable_authorities: list[dict[str, Any]] = field(default_factory=list)
    tasks_to_create: list[dict[str, Any]] = field(default_factory=list)
    confidence: str = "low"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SourceAuthoritySufficiencyEvaluator:
    """Evaluate whether source authority coverage is sufficient
    for a given country/domain/task.
    """

    def __init__(self, authority_store: SourceAuthorityStore):
        self._store = authority_store

    def evaluate(
        self,
        *,
        target_country: str = "GENERIC",
        target_domain: str | None = None,
        target_discipline: str | None = None,
        publication_task_type: str = "venue_discovery",
        desired_outputs: list[str] | None = None,
    ) -> SufficiencyResult:
        result = SufficiencyResult()
        country = target_country.upper() if target_country else "GENERIC"

        required_types = self._required_authority_types(
            publication_task_type, desired_outputs or [],
        )

        existing = self._store.list_all()
        country_authorities = [
            a for a in existing
            if (a.country or "").upper() == country
            or a.country is None
            or (a.country or "").upper() == "INTERNATIONAL"
        ]

        covered: set[str] = set()
        for auth in country_authorities:
            if auth.source_status in ("accepted", "provisional"):
                covered.add(auth.authority_type)
                result.usable_authorities.append({
                    "authority_id": auth.authority_id,
                    "authority_name": auth.authority_name,
                    "authority_type": auth.authority_type,
                    "source_status": auth.source_status,
                    "access_mode": auth.access_mode,
                    "adapter_hint": auth.adapter_hint,
                })

        missing = [t for t in required_types if t not in covered]
        result.missing_authority_types = missing

        hints = COUNTRY_AUTHORITY_HINTS.get(
            country, COUNTRY_AUTHORITY_HINTS["GENERIC"],
        )

        for mt in missing:
            suggested = hints.get(mt, [])
            task_info = {
                "missing_authority_type": mt,
                "target_country": country,
                "target_domain": target_domain,
                "target_discipline": target_discipline,
                "reason": f"No {mt} authority for {country}/{target_domain or 'general'}",
                "search_queries": suggested,
                "suggested_connectors": self._suggest_connectors(mt, country),
            }
            result.tasks_to_create.append(task_info)

        if not missing:
            result.sufficient = True
            result.confidence = "medium"
        elif len(missing) <= 2 and "discipline_classification" not in missing:
            result.sufficient = False
            result.confidence = "low"
            result.warnings.append(
                f"Partial authority coverage — missing: {', '.join(missing)}"
            )
        else:
            result.sufficient = False
            result.confidence = "low"
            result.warnings.append(
                f"Insufficient authority coverage — missing {len(missing)} types: "
                f"{', '.join(missing)}"
            )

        if country != "RU" and any(
            "VAK" in (a.authority_name or "") or "РИНЦ" in (a.authority_name or "")
            for a in country_authorities
            if (a.country or "").upper() == country
        ):
            result.warnings.append(
                f"Russia-specific authorities (VAK/РИНЦ) present for "
                f"non-Russian target '{country}' — may be irrelevant"
            )

        return result

    def _required_authority_types(
        self,
        task_type: str,
        desired_outputs: list[str],
    ) -> list[str]:
        base = ["discipline_classification", "national_journal_registry"]

        if task_type in ("venue_discovery", "venue_universe"):
            base.append("citation_database")
        if task_type in ("shortlist", "venue_metrics") or "metrics" in desired_outputs:
            base.append("metric_source")
        if task_type in ("deep_venue_model", "fit_assessment") or "deep_model" in desired_outputs:
            base.extend([
                "author_guidelines_source",
                "editorial_board_source",
                "journal_archive_source",
            ])
        if "corpus" in desired_outputs:
            base.append("journal_archive_source")

        seen: set[str] = set()
        unique: list[str] = []
        for t in base:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique

    def _suggest_connectors(self, authority_type: str, country: str) -> list[str]:
        connectors = ["local_file", "manual_url"]
        if authority_type == "citation_database":
            connectors.extend(["openalex", "crossref"])
        if authority_type == "metric_source":
            connectors.extend(["openalex", "manual_url"])
        if authority_type in ("national_journal_registry", "discipline_classification"):
            connectors.append("web_search")
        if country == "RU":
            connectors.append("cyberleninka")
        return connectors
