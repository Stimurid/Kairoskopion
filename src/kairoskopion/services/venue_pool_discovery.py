"""Venue pool discovery service.

Runs discovery queries against enabled adapters, collects VenueCandidate
objects with authority assessments. Supports fixture/offline and live modes.
No broad crawling. No fake recommendations.
"""

from __future__ import annotations

import logging
from typing import Any

from ..enums import (
    VenueCandidateReason,
    VenueCandidateStatus,
    VenueDiscoverySource,
)
from ..ids import venue_candidate_id, venue_candidate_pool_id
from ..schema import (
    VenueCandidate,
    VenueCandidatePool,
    VenueDiscoveryQuery,
)
from .venue_discovery_planner import plan_venue_discovery

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Discovery fixtures for offline/fixture mode
# ---------------------------------------------------------------------------

DISCOVERY_FIXTURES: dict[str, list[dict[str, Any]]] = {
    "openalex": [
        {
            "display_name": "Philosophy & Technology",
            "issn_l": "2210-5433",
            "issn": ["2210-5433", "2210-5441"],
            "publisher": "Springer Nature",
            "type": "journal",
            "topics": ["Philosophy of Technology", "Ethics of AI", "STS"],
            "works_count": 1250,
        },
        {
            "display_name": "Science, Technology, & Human Values",
            "issn_l": "0162-2439",
            "issn": ["0162-2439", "1552-8251"],
            "publisher": "SAGE Publications",
            "type": "journal",
            "topics": ["STS", "Sociology of Science", "Technology Studies"],
            "works_count": 2100,
        },
        {
            "display_name": "Ethics and Information Technology",
            "issn_l": "1388-1957",
            "issn": ["1388-1957", "1572-8439"],
            "publisher": "Springer Nature",
            "type": "journal",
            "topics": ["AI Ethics", "Information Ethics", "Philosophy of Technology"],
            "works_count": 980,
        },
        {
            "display_name": "Techné: Research in Philosophy and Technology",
            "issn_l": "1091-8264",
            "issn": ["1091-8264"],
            "publisher": "Society for Philosophy and Technology",
            "type": "journal",
            "topics": ["Philosophy of Technology", "Engineering Ethics"],
            "works_count": 420,
        },
        {
            "display_name": "Minerva",
            "issn_l": "0026-4695",
            "issn": ["0026-4695", "1573-1871"],
            "publisher": "Springer Nature",
            "type": "journal",
            "topics": ["Science Policy", "Higher Education", "Philosophy of Science"],
            "works_count": 1800,
        },
    ],
    "doaj": [
        {
            "display_name": "Philosophy & Technology",
            "issn_l": "2210-5433",
            "issn": ["2210-5433", "2210-5441"],
            "publisher": "Springer Nature",
            "oa_status": "hybrid",
            "doaj_seal": False,
            "subjects": ["Philosophy", "Technology"],
        },
        {
            "display_name": "Technology and Language",
            "issn_l": "2691-5596",
            "issn": ["2691-5596"],
            "publisher": "Springer Nature",
            "oa_status": "gold",
            "doaj_seal": False,
            "subjects": ["Philosophy of Technology", "Language Technology"],
        },
        {
            "display_name": "Open Philosophy",
            "issn_l": "2543-8875",
            "issn": ["2543-8875"],
            "publisher": "De Gruyter",
            "oa_status": "gold",
            "doaj_seal": False,
            "subjects": ["Philosophy"],
        },
    ],
    "crossref": [
        {
            "display_name": "Philosophy & Technology",
            "issn_l": "2210-5433",
            "issn": ["2210-5433", "2210-5441"],
            "publisher": "Springer Science and Business Media LLC",
            "doi_count": 980,
        },
        {
            "display_name": "Science, Technology, & Human Values",
            "issn_l": "0162-2439",
            "issn": ["0162-2439", "1552-8251"],
            "publisher": "SAGE Publications",
            "doi_count": 3200,
        },
    ],
}


def discover_venue_pool(
    *,
    semantic_profile: dict[str, Any] | None = None,
    pathways: list[dict[str, Any]] | None = None,
    scenario: dict[str, Any] | None = None,
    seed_venues: list[dict[str, Any]] | None = None,
    fixtures: dict[str, list[dict[str, Any]]] | None = None,
    live_enabled: bool = False,
    enabled_sources: list[str] | None = None,
    cache_dir: str | None = None,
) -> VenueCandidatePool:
    """Discover venue candidates from adapters and seed venues.

    Default behavior is offline (fixtures or stubs). Live requires
    explicit ``live_enabled=True``.
    """
    article_model_id = (semantic_profile or {}).get("article_model_id")
    scenario_id = (scenario or {}).get("submission_scenario_id")
    pathway_ids = [p.get("disciplinary_pathway_id", "") for p in (pathways or [])]

    queries = plan_venue_discovery(
        semantic_profile=semantic_profile,
        pathways=pathways,
        scenario=scenario,
    )

    all_fixtures = DISCOVERY_FIXTURES if fixtures is None else fixtures
    sources = enabled_sources or ["openalex", "doaj", "crossref"]
    constraints = _scenario_constraints(scenario)

    raw_candidates: list[dict[str, Any]] = []
    unknowns: list[str] = []

    for src in sources:
        try:
            src_candidates = _discover_from_source(
                src, queries, all_fixtures, constraints,
                live_enabled=live_enabled,
                cache_dir=cache_dir,
            )
            raw_candidates.extend(src_candidates)
        except Exception as exc:
            unknowns.append(f"Adapter {src} failed: {exc}")

    if seed_venues:
        seed_candidates = _candidates_from_seeds(seed_venues, pathways or [])
        raw_candidates.extend(seed_candidates)

    if not raw_candidates:
        unknowns.append("No candidates discovered from any source")

    candidates = [c for c in raw_candidates]

    return VenueCandidatePool(
        venue_candidate_pool_id=venue_candidate_pool_id(),
        article_model_id=article_model_id,
        scenario_id=scenario_id,
        pathway_ids=pathway_ids,
        queries=[q.to_dict() for q in queries],
        candidates=[_candidate_dict(c) for c in candidates],
        unknowns=unknowns,
    )


def _scenario_constraints(scenario: dict[str, Any] | None) -> dict[str, Any]:
    if not scenario:
        return {}
    c: dict[str, Any] = {}
    if scenario.get("language_constraint"):
        c["language"] = scenario["language_constraint"]
    if scenario.get("target_indexing"):
        c["indexing"] = scenario["target_indexing"]
    return c


def _discover_from_source(
    source: str,
    queries: list[VenueDiscoveryQuery],
    fixtures: dict[str, list[dict[str, Any]]],
    constraints: dict[str, Any],
    *,
    live_enabled: bool = False,
    cache_dir: str | None = None,
) -> list[dict[str, Any]]:
    if live_enabled and source in ("openalex", "doaj"):
        return _discover_live(source, queries, constraints, cache_dir=cache_dir)

    fixture_data = fixtures.get(source, [])
    if not fixture_data:
        return []

    candidates = []
    for item in fixture_data:
        reasons = _match_reasons(item, queries, constraints)
        if not reasons:
            continue

        issns = item.get("issn", [])
        candidate = {
            "canonical_name": item.get("display_name", ""),
            "issn": issns[0] if issns else None,
            "issn_l": item.get("issn_l"),
            "aliases": [],
            "urls": [],
            "sources": [source],
            "discovery_reasons": reasons,
            "status": VenueCandidateStatus.DISCOVERED.value,
            "confidence": "medium" if len(reasons) >= 2 else "low",
            "unknowns": [],
            "raw_adapter_data": {source: item},
        }
        candidates.append(candidate)

    return candidates


def _discover_live(
    source: str,
    queries: list[VenueDiscoveryQuery],
    constraints: dict[str, Any],
    *,
    cache_dir: str | None = None,
) -> list[dict[str, Any]]:
    """Call real adapters in LIVE_API mode for discovery search."""
    from ..adapters.venue.base import VenueAdapterMode

    adapter = _build_discovery_adapter(source, cache_dir=cache_dir)
    if adapter is None:
        return []

    seen_issns: set[str] = set()
    candidates: list[dict[str, Any]] = []

    for query in queries:
        search_terms = [t.strip() for t in query.query_text.split("|") if t.strip()]
        primary_term = search_terms[0] if search_terms else query.query_text

        try:
            results = adapter.search_venues(primary_term, per_page=10)
        except Exception as exc:
            logger.warning("Live search failed for %s/%s: %s", source, primary_term, exc)
            continue

        for result in results:
            if result.status != "success" or not result.claims:
                continue

            raw = result.raw_data or {}
            name = _claim_value(result, "canonical_name") or raw.get("display_name", "")
            issn = _claim_value(result, "issn") or raw.get("issn_l")

            if issn and issn in seen_issns:
                continue
            if issn:
                seen_issns.add(issn)

            reasons = _match_reasons_from_adapter(raw, search_terms, constraints)
            if not reasons:
                reasons = [VenueCandidateReason.KEYWORD_MATCH.value]

            authority = result.authority_assessment
            candidate = {
                "canonical_name": name,
                "issn": issn,
                "issn_l": raw.get("issn_l") or issn,
                "aliases": [],
                "urls": [raw.get("homepage_url")] if raw.get("homepage_url") else [],
                "sources": [source],
                "discovery_reasons": reasons,
                "authority_assessments": [authority] if authority else [],
                "adapter_result_refs": [result.adapter_id],
                "status": VenueCandidateStatus.DISCOVERED.value,
                "confidence": "medium" if authority else "low",
                "unknowns": result.unknowns,
                "raw_adapter_data": {source: raw},
            }
            candidates.append(candidate)

    return candidates


def _build_discovery_adapter(
    source: str,
    *,
    cache_dir: str | None = None,
) -> Any | None:
    from ..adapters.venue.base import VenueAdapterMode

    if source == "openalex":
        from ..adapters.venue.openalex import OpenAlexVenueAdapter
        return OpenAlexVenueAdapter(
            VenueAdapterMode.LIVE_API,
            cache_dir=cache_dir,
        )
    elif source == "doaj":
        from ..adapters.venue.doaj import DOAJVenueAdapter
        return DOAJVenueAdapter(
            VenueAdapterMode.LIVE_API,
            cache_dir=cache_dir,
        )
    return None


def _claim_value(result: Any, claim_path: str) -> Any | None:
    for claim in result.claims:
        if claim.claim_path == claim_path:
            return claim.claim_value
    return None


def _match_reasons_from_adapter(
    raw: dict[str, Any],
    search_terms: list[str],
    constraints: dict[str, Any],
) -> list[str]:
    """Derive discovery reasons from adapter raw data against search terms."""
    reasons: list[str] = []

    topics = []
    for t in raw.get("topics", []):
        if isinstance(t, str):
            topics.append(t.lower())
        elif isinstance(t, dict):
            topics.append(t.get("display_name", "").lower())
    subjects = [s.lower() for s in raw.get("subjects", [])]
    bib = raw.get("bibjson", {})
    if bib:
        for s in bib.get("subject", []):
            if s.get("term"):
                subjects.append(s["term"].lower())
    all_terms = topics + subjects

    for qt in search_terms:
        qt_lower = qt.lower()
        qt_words = qt_lower.split()
        for term in all_terms:
            if qt_lower in term or term in qt_lower:
                reasons.append(VenueCandidateReason.DISCIPLINE_MATCH.value)
                break
            if any(w in term for w in qt_words if len(w) > 3):
                reasons.append(VenueCandidateReason.KEYWORD_MATCH.value)
                break

    if raw.get("oa_status") and constraints.get("open_access"):
        reasons.append(VenueCandidateReason.OA_POLICY_MATCH.value)

    seen: set[str] = set()
    return [r for r in reasons if r not in seen and not seen.add(r)]  # type: ignore[func-returns-value]


def _match_reasons(
    item: dict[str, Any],
    queries: list[VenueDiscoveryQuery],
    constraints: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    topics = [t.lower() if isinstance(t, str) else t.get("display_name", "").lower()
              for t in item.get("topics", [])]
    subjects = [s.lower() for s in item.get("subjects", [])]
    all_terms = topics + subjects
    name_lower = item.get("display_name", "").lower()

    for q in queries:
        q_terms = [t.strip().lower() for t in q.query_text.split("|") if t.strip()]
        for qt in q_terms:
            qt_words = qt.split()
            for term in all_terms:
                if qt in term or term in qt:
                    reasons.append(VenueCandidateReason.DISCIPLINE_MATCH.value)
                    break
                if any(w in term for w in qt_words if len(w) > 3):
                    reasons.append(VenueCandidateReason.KEYWORD_MATCH.value)
                    break

    lang_constraint = constraints.get("language")
    if lang_constraint:
        langs = item.get("languages", [])
        if langs and lang_constraint.lower() not in [l.lower() for l in langs]:
            return []

    if item.get("oa_status") and constraints.get("open_access"):
        reasons.append(VenueCandidateReason.OA_POLICY_MATCH.value)

    seen: set[str] = set()
    deduped = []
    for r in reasons:
        if r not in seen:
            deduped.append(r)
            seen.add(r)
    return deduped


def _candidates_from_seeds(
    seed_venues: list[dict[str, Any]],
    pathways: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates = []
    for sv in seed_venues:
        name = sv.get("name") or sv.get("canonical_name", "")
        if not name:
            continue
        candidates.append({
            "canonical_name": name,
            "issn": sv.get("issn"),
            "issn_l": sv.get("issn_l"),
            "aliases": [],
            "urls": sv.get("official_urls", []),
            "sources": [VenueDiscoverySource.USER_SEED.value],
            "discovery_reasons": [VenueCandidateReason.USER_SEED.value],
            "status": VenueCandidateStatus.DISCOVERED.value,
            "confidence": "low",
            "unknowns": ["User seed — not yet verified by adapter evidence"],
            "raw_adapter_data": {"user_seed": sv},
        })
    return candidates


def _candidate_dict(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "venue_candidate_id": venue_candidate_id(),
        "canonical_name": c.get("canonical_name", ""),
        "aliases": c.get("aliases", []),
        "issn": c.get("issn"),
        "issn_l": c.get("issn_l"),
        "urls": c.get("urls", []),
        "sources": c.get("sources", []),
        "discovery_reasons": c.get("discovery_reasons", []),
        "authority_assessments": c.get("authority_assessments", []),
        "adapter_result_refs": c.get("adapter_result_refs", []),
        "evidence_refs": c.get("evidence_refs", []),
        "conflicts": c.get("conflicts", []),
        "status": c.get("status", VenueCandidateStatus.DISCOVERED.value),
        "confidence": c.get("confidence", "low"),
        "unknowns": c.get("unknowns", []),
        "raw_adapter_data": c.get("raw_adapter_data", {}),
    }
