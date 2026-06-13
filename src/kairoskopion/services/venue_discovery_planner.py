"""Venue discovery query planner.

Takes ArticleSemanticProfile + DisciplinaryPathways + SubmissionScenario
and creates adapter search plans. No network. No LLM. Deterministic.
"""

from __future__ import annotations

from typing import Any

from ..enums import VenueCandidateReason, VenueDiscoverySource
from ..ids import venue_discovery_query_id
from ..schema import VenueDiscoveryQuery


def plan_venue_discovery(
    *,
    semantic_profile: dict[str, Any] | None = None,
    pathways: list[dict[str, Any]] | None = None,
    scenario: dict[str, Any] | None = None,
) -> list[VenueDiscoveryQuery]:
    """Create discovery queries from article profile and pathways.

    Each pathway gets its own query plan. Scenario constraints
    narrow all queries.
    """
    queries: list[VenueDiscoveryQuery] = []
    profile = semantic_profile or {}
    scenario = scenario or {}
    pathways = pathways or []

    article_model_id = profile.get("article_model_id")
    profile_id = profile.get("article_semantic_profile_id")

    constraints = _extract_constraints(scenario)

    if not pathways:
        queries.append(_generic_query(profile, article_model_id, profile_id, constraints))
        return queries

    for pw in pathways:
        q = _pathway_query(pw, profile, article_model_id, profile_id, constraints)
        queries.append(q)

    return queries


def _extract_constraints(scenario: dict[str, Any]) -> dict[str, Any]:
    c: dict[str, Any] = {}
    if scenario.get("language_constraint"):
        c["language"] = scenario["language_constraint"]
    if scenario.get("target_indexing"):
        c["indexing"] = scenario["target_indexing"]
    if scenario.get("APC_constraints"):
        c["apc"] = scenario["APC_constraints"]
    if scenario.get("prestige_priority"):
        c["prestige"] = scenario["prestige_priority"]
    if scenario.get("risk_tolerance"):
        c["risk_tolerance"] = scenario["risk_tolerance"]
    oa_pref = scenario.get("oa_preference") or scenario.get("open_access")
    if oa_pref:
        c["open_access"] = oa_pref
    return c


def _pathway_query(
    pw: dict[str, Any],
    profile: dict[str, Any],
    article_model_id: str | None,
    profile_id: str | None,
    constraints: dict[str, Any],
) -> VenueDiscoveryQuery:
    discipline = pw.get("discipline_name", "")
    strength = pw.get("fit_strength", "unknown")
    schools = pw.get("schools_and_traditions", []) or profile.get("schools_and_traditions", [])
    venue_hints = pw.get("venue_type_hints", [])
    lang_options = pw.get("language_options", [])
    indexing_options = pw.get("indexing_options", [])

    terms = _build_search_terms(discipline, schools, profile)

    unknowns: list[str] = []
    if strength in ("weak", "unknown"):
        unknowns.append(f"Pathway '{discipline}' has {strength} fit — results may be off-target")
    if not terms:
        unknowns.append("No meaningful search terms could be derived")

    query_constraints = dict(constraints)
    if lang_options:
        query_constraints.setdefault("language_options", lang_options)
    if indexing_options:
        query_constraints.setdefault("indexing_options", indexing_options)
    if venue_hints:
        query_constraints["venue_type_hints"] = venue_hints

    return VenueDiscoveryQuery(
        venue_discovery_query_id=venue_discovery_query_id(),
        article_model_id=article_model_id,
        semantic_profile_id=profile_id,
        pathway_id=pw.get("disciplinary_pathway_id"),
        query_text=" | ".join(terms),
        source=VenueDiscoverySource.OPENALEX.value,
        constraints=query_constraints,
        expected_authority_scopes=["venue_identity", "indexing_status", "publication_regime"],
        unknowns=unknowns,
    )


def _generic_query(
    profile: dict[str, Any],
    article_model_id: str | None,
    profile_id: str | None,
    constraints: dict[str, Any],
) -> VenueDiscoveryQuery:
    disciplines = profile.get("disciplinary_registers", [])
    schools = profile.get("schools_and_traditions", [])
    terms = []
    for d in disciplines[:3]:
        terms.append(d)
    for s in schools[:2]:
        terms.append(s)

    return VenueDiscoveryQuery(
        venue_discovery_query_id=venue_discovery_query_id(),
        article_model_id=article_model_id,
        semantic_profile_id=profile_id,
        query_text=" | ".join(terms) if terms else "",
        source=VenueDiscoverySource.OPENALEX.value,
        constraints=constraints,
        expected_authority_scopes=["venue_identity"],
        unknowns=["No disciplinary pathways available — generic query only"],
    )


def _build_search_terms(
    discipline: str,
    schools: list[str],
    profile: dict[str, Any],
) -> list[str]:
    terms: list[str] = []
    if discipline:
        terms.append(discipline)
    for s in schools[:2]:
        if s and s.lower() != discipline.lower():
            terms.append(s)

    argument_type = profile.get("argument_move_type")
    if argument_type and argument_type not in ("unknown", "UNKNOWN"):
        terms.append(argument_type)

    return terms
