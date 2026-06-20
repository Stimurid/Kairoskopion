"""Venue candidate screening service.

Screens candidates against ArticleSemanticProfile + DisciplinaryPathway +
SubmissionScenario. Produces VenueCandidateScreeningResult. When evidence
is missing, marks evidence gaps rather than inventing fit.
"""

from __future__ import annotations

from typing import Any

from ..enums import VenueCandidateStatus
from ..ids import candidate_evidence_matrix_id, venue_candidate_screening_id
from ..schema import CandidateEvidenceMatrix, VenueCandidateScreeningResult


def screen_candidates(
    *,
    candidates: list[dict[str, Any]],
    semantic_profile: dict[str, Any] | None = None,
    pathways: list[dict[str, Any]] | None = None,
    scenario: dict[str, Any] | None = None,
) -> list[VenueCandidateScreeningResult]:
    """Screen each candidate and return screening results."""
    results: list[VenueCandidateScreeningResult] = []
    profile = semantic_profile or {}
    scenario = scenario or {}

    for c in candidates:
        r = _screen_single(c, profile, pathways or [], scenario)
        results.append(r)

    return results


def _screen_single(
    candidate: dict[str, Any],
    profile: dict[str, Any],
    pathways: list[dict[str, Any]],
    scenario: dict[str, Any],
) -> VenueCandidateScreeningResult:
    fit_axes: dict[str, str] = {}
    blocking_gaps: list[str] = []
    evidence_gaps: list[str] = []
    authority_warnings: list[str] = []
    unknowns: list[str] = []
    next_actions: list[str] = []

    raw_data = candidate.get("raw_adapter_data", {})
    sources = candidate.get("sources", [])

    # Discipline/pathway fit
    fit_axes["discipline"] = _assess_discipline_fit(candidate, profile, pathways)

    # Article type fit
    fit_axes["article_type"] = _assess_article_type_fit(candidate, profile)

    # Language fit
    fit_axes["language"] = _assess_language_fit(candidate, scenario)

    # Publication regime fit
    fit_axes["publication_regime"] = _assess_regime_fit(candidate, raw_data)

    # Indexing/OA fit
    fit_axes["indexing"] = _assess_indexing_fit(candidate, scenario)

    # Corpus/profile evidence presence
    has_corpus = any("works_count" in (v if isinstance(v, dict) else {})
                     for v in raw_data.values())
    if has_corpus:
        fit_axes["corpus_evidence"] = "present"
    else:
        fit_axes["corpus_evidence"] = "missing"
        evidence_gaps.append("No corpus evidence available for this candidate")
        next_actions.append("Run venue evidence stack to at least L3 (corpus sample)")

    # Authority confidence
    assessments = candidate.get("authority_assessments", [])
    if assessments:
        fit_axes["authority_confidence"] = "supported"
    else:
        fit_axes["authority_confidence"] = "not_assessed"
        if "user_seed" not in sources:
            evidence_gaps.append("No authority assessment from any adapter")

    # Check for prohibited claims
    prohibited = candidate.get("prohibited_claims", [])
    if prohibited:
        authority_warnings.append(f"Prohibited authority claims: {', '.join(prohibited[:3])}")

    # Check conflicts
    conflicts = candidate.get("conflicts", [])
    for cf in conflicts:
        if cf.get("severity") == "blocking":
            blocking_gaps.append(f"Blocking conflict: {cf.get('type', 'unknown')}")

    # Compute overall fit
    axis_values = list(fit_axes.values())
    unknown_count = sum(1 for v in axis_values if v in ("unknown", "missing", "not_assessed"))
    positive_count = sum(1 for v in axis_values if v in ("match", "present", "supported", "likely"))
    negative_count = sum(1 for v in axis_values if v in ("mismatch", "rejected"))

    if negative_count > 0:
        preliminary_fit = "weak"
        if blocking_gaps:
            preliminary_fit = "rejected"
    elif unknown_count > positive_count:
        preliminary_fit = "insufficient_evidence"
    elif positive_count >= 3:
        preliminary_fit = "likely"
    else:
        preliminary_fit = "possible"

    if preliminary_fit == "rejected":
        status = VenueCandidateStatus.SCREENED_OUT.value
    elif preliminary_fit in ("likely", "possible") and not blocking_gaps:
        status = VenueCandidateStatus.SCREENED_IN.value
    elif preliminary_fit == "insufficient_evidence":
        status = VenueCandidateStatus.INSUFFICIENT_EVIDENCE.value
    else:
        status = VenueCandidateStatus.NEEDS_USER_SELECTION.value

    # Check minimum evidence for screened_in
    min_sources = 1
    if len(sources) < min_sources or (len(sources) == 1 and "user_seed" in sources):
        if status == VenueCandidateStatus.SCREENED_IN.value:
            status = VenueCandidateStatus.INSUFFICIENT_EVIDENCE.value
            evidence_gaps.append("Screened_in requires at least one adapter source beyond user seed")

    if not next_actions and evidence_gaps:
        next_actions.append("Acquire additional venue evidence via source adapters")

    pathway_id = None
    if pathways:
        pathway_id = pathways[0].get("disciplinary_pathway_id")

    return VenueCandidateScreeningResult(
        venue_candidate_screening_id=venue_candidate_screening_id(),
        candidate_id=candidate.get("venue_candidate_id", ""),
        article_model_id=profile.get("article_model_id"),
        semantic_profile_id=profile.get("article_semantic_profile_id"),
        pathway_id=pathway_id,
        preliminary_fit=preliminary_fit,
        fit_axes=fit_axes,
        blocking_gaps=blocking_gaps,
        evidence_gaps=evidence_gaps,
        authority_warnings=authority_warnings,
        recommended_next_actions=next_actions,
        status=status,
        unknowns=unknowns,
    )


def _assess_discipline_fit(
    candidate: dict[str, Any],
    profile: dict[str, Any],
    pathways: list[dict[str, Any]],
) -> str:
    reasons = candidate.get("discovery_reasons", [])
    if "discipline_match" in reasons or "pathway_match" in reasons:
        return "match"

    topics = []
    for src_data in candidate.get("raw_adapter_data", {}).values():
        if isinstance(src_data, dict):
            topics.extend(src_data.get("topics", []))
            topics.extend(src_data.get("subjects", []))

    if not topics:
        return "unknown"

    topic_strs = [t.lower() if isinstance(t, str) else t.get("display_name", "").lower()
                  for t in topics]
    disciplines = [d.lower() for d in profile.get("disciplinary_registers", [])]

    # Track D fix: previous logic was ``d in t or t in d`` over raw
    # lowercased strings — substring match. Cockpit symptom: candidate
    # topic "cartography" matched discipline "art" (art ⊂ cartography),
    # producing false "discipline: match". Now require token-level
    # equality on whitespace-split tokens with min length 4.
    def _tokens(s: str) -> set[str]:
        return {tok for tok in s.replace("-", " ").split() if len(tok) >= 4}

    d_token_sets = [_tokens(d) for d in disciplines]
    for t in topic_strs:
        t_tokens = _tokens(t)
        for d_tokens in d_token_sets:
            if d_tokens & t_tokens:
                return "match"
    return "unknown"


def _assess_article_type_fit(
    candidate: dict[str, Any],
    profile: dict[str, Any],
) -> str:
    return "unknown"


def _assess_language_fit(
    candidate: dict[str, Any],
    scenario: dict[str, Any],
) -> str:
    lang = scenario.get("language_constraint")
    if not lang:
        return "match"

    raw = candidate.get("raw_adapter_data", {})
    for src_data in raw.values():
        if isinstance(src_data, dict):
            langs = src_data.get("languages", [])
            if langs and lang.lower() not in [l.lower() for l in langs]:
                return "mismatch"
            if langs and lang.lower() in [l.lower() for l in langs]:
                return "match"

    return "unknown"


def _assess_regime_fit(
    candidate: dict[str, Any],
    raw_data: dict[str, Any],
) -> str:
    """Track D fix: previous logic returned ``"likely"`` whenever a
    candidate had ANY works in any adapter — i.e. virtually every
    indexed venue. Cockpit symptom: every venue showed
    ``publication_regime: likely`` regardless of actual regime mismatch,
    masking real regime problems.

    Honest behaviour: only return ``"likely"`` when adapter-provided
    ``type`` field is the explicit string ``"journal"``. ``works_count``
    alone is not regime information. Otherwise ``"unknown"`` — real
    regime fit needs VenueProfilingAgent output.
    """
    for src_data in raw_data.values():
        if isinstance(src_data, dict):
            if src_data.get("type") == "journal":
                return "likely"
    return "unknown"


def _assess_indexing_fit(
    candidate: dict[str, Any],
    scenario: dict[str, Any],
) -> str:
    target = scenario.get("target_indexing")
    if not target:
        return "match"

    raw = candidate.get("raw_adapter_data", {})
    doaj_data = raw.get("doaj")
    if doaj_data and target.lower() == "doaj":
        return "match"

    return "unknown"


def build_candidate_evidence_matrix(
    *,
    pool: dict[str, Any],
    screening_results: list[VenueCandidateScreeningResult],
) -> CandidateEvidenceMatrix:
    """Build cross-candidate evidence/gap/conflict summary."""
    rows: list[dict[str, Any]] = []
    missing: dict[str, list[str]] = {}
    conflicts_by_cand: dict[str, list[dict[str, Any]]] = {}
    warnings_by_cand: dict[str, list[str]] = {}
    unknowns: list[str] = []

    candidates = pool.get("candidates", [])

    for sr in screening_results:
        cid = sr.candidate_id
        cand = next((c for c in candidates if c.get("venue_candidate_id") == cid), None)
        name = cand.get("canonical_name", cid) if cand else cid

        row = {
            "candidate_id": cid,
            "canonical_name": name,
            "preliminary_fit": sr.preliminary_fit,
            "status": sr.status,
            "fit_axes": sr.fit_axes,
            "sources": cand.get("sources", []) if cand else [],
            "evidence_gaps_count": len(sr.evidence_gaps),
            "blocking_gaps_count": len(sr.blocking_gaps),
        }
        rows.append(row)

        if sr.evidence_gaps:
            missing[cid] = sr.evidence_gaps
        if sr.authority_warnings:
            warnings_by_cand[cid] = sr.authority_warnings

        if cand:
            cand_conflicts = cand.get("conflicts", [])
            if cand_conflicts:
                conflicts_by_cand[cid] = cand_conflicts

    return CandidateEvidenceMatrix(
        candidate_evidence_matrix_id=candidate_evidence_matrix_id(),
        pool_id=pool.get("venue_candidate_pool_id", ""),
        rows=rows,
        missing_evidence_by_candidate=missing,
        conflicts_by_candidate=conflicts_by_cand,
        authority_warnings_by_candidate=warnings_by_cand,
        unknowns=unknowns,
    )
