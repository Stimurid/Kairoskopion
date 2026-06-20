"""V2-D minimal CitationPlan builder.

Builds a CitationPlan from already-built chain artefacts (ArticleModel,
VenueModel, FitAssessment, MismatchMap, RiskReport, RewritePlan). Does
NOT generate concrete reference candidates, does NOT call external
APIs, does NOT invent DOIs/titles. Produces *gap categories*,
*verification tasks*, *search-task descriptions*, and explicit
unknowns when bibliography/venue corpus is absent.

Pure function. No I/O. No LLM. No dependency on BibliographyProfile —
when bibliography is absent the plan honestly says so and routes the
user to "parse bibliography first" before readiness can be assessed.
"""

from __future__ import annotations

from typing import Any

from ..schema import (
    ArticleModel,
    CitationPlan,
    FitAssessment,
    MismatchMap,
    RewritePlan,
    RiskReport,
    VenueModel,
)


# Allowed status values per V2-D brief.
STATUS_NOT_BUILT = "not_built"
STATUS_DRAFT = "draft"
STATUS_NEEDS_BIBLIOGRAPHY = "needs_bibliography"
STATUS_NEEDS_VENUE_CORPUS = "needs_venue_corpus"
STATUS_SEARCH_TASKS_READY = "search_tasks_ready"
STATUS_PARTIALLY_READY = "partially_ready"
STATUS_BLOCKED_MISSING_EVIDENCE = "blocked_missing_evidence"


def _bibliography_status(article: ArticleModel) -> str:
    """Determine whether parsed bibliography signal exists on the article.

    We do NOT have BibliographyProfile in the production fit chain
    today. Honest "unknown" is the right default; if the article
    self-reports references we mark "self_reported_only".
    """
    if (article.reference_count or 0) > 0:
        return "self_reported_only"
    if article.citation_ecology_current:
        return "ecology_text_only_not_parsed"
    return "absent_unknown"


def _axis_value(fit: FitAssessment, axis_name: str) -> str | None:
    for ax in fit.axes:
        if ax.get("axis") == axis_name:
            return ax.get("value")
    return None


def _venue_citation_expectation_status(venue: VenueModel) -> str:
    """Whether the venue text tells us anything about citation expectations.

    We must NOT invent venue-local citation expectations from scratch.
    """
    scope = (venue.scope_summary or "").lower()
    if not scope:
        return "venue_text_absent"
    # Signals the venue text mentions citation-related expectations
    markers = (
        "citation", "references", "bibliography", "corpus", "literature",
    )
    if any(m in scope for m in markers):
        return "scope_mentions_citation_expectations"
    return "scope_silent_on_citation_expectations"


def build_minimal_citation_plan(
    article: ArticleModel,
    venue: VenueModel,
    fit: FitAssessment,
    mismatch_map: MismatchMap | None,
    risk_report: RiskReport | None,
    rewrite_plan: RewritePlan | None,
) -> CitationPlan:
    """Build a minimal-real CitationPlan from chain artefacts.

    Honest defaults:
      - no bibliography parsed → status=needs_bibliography, search
        tasks describe the work needed, no concrete references
        produced;
      - venue text silent on citation expectations → unknown surfaced;
      - dangerous-padding warning always included when expansion is
        recommended without verified references.
    """
    gap_categories: list[str] = []
    missing_bridges: list[str] = []
    search_tasks: list[str] = []
    verification_tasks: list[str] = []
    padding_warnings: list[str] = []
    risk_flags: list[str] = []
    unknowns: list[str] = []
    created_from: list[str] = [
        "article_model", "venue_model", "fit_assessment",
    ]

    bib_status = _bibliography_status(article)
    venue_exp_status = _venue_citation_expectation_status(venue)

    # ----- Fit-axis signals -----
    cit_axis = _axis_value(fit, "citation_ecology")
    disc_axis = _axis_value(fit, "discipline")
    novelty_axis = _axis_value(fit, "novelty_positioning")
    method_axis = _axis_value(fit, "method")

    if cit_axis in ("bad", "weak", "unknown"):
        gap_categories.append(
            f"citation ecology fit = {cit_axis or 'unknown'}"
        )
    if disc_axis in ("bad", "weak"):
        gap_categories.append(
            "disciplinary citation bridging may be insufficient"
        )
        missing_bridges.append(
            "disciplinary bridge references between article's "
            "disciplinary register and venue's primary discipline"
        )
    if novelty_axis in ("bad", "weak"):
        gap_categories.append(
            "novelty-positioning citation work may be needed"
        )
        missing_bridges.append(
            "recent-debate-marker references for the venue's "
            "current conversation on this topic"
        )
    if method_axis in ("bad", "weak"):
        gap_categories.append(
            "method-justification citation gap (theoretical method "
            "in a venue with empirical expectations)"
        )

    # ----- Mismatch-map signals -----
    if mismatch_map is not None:
        for m in mismatch_map.mismatches:
            axis = m.get("axis", "") if isinstance(m, dict) else getattr(m, "axis", "")
            if axis == "citation_ecology":
                gap_categories.append("citation mismatch flagged in MismatchMap")
                created_from.append("mismatch_map")

    # ----- Risk-report signals -----
    if risk_report is not None:
        created_from.append("risk_report")
        for r in risk_report.risk_items:
            rtype = (r.get("risk_type") if isinstance(r, dict) else "") or ""
            if rtype in ("citation_gap", "reference_validity",
                         "scope_mismatch"):
                risk_flags.append(rtype)

    # ----- Rewrite-plan signals -----
    if rewrite_plan is not None:
        for ch in rewrite_plan.changes:
            tgt = (ch.get("target_block") if isinstance(ch, dict) else "") or ""
            reason = (ch.get("reason") if isinstance(ch, dict) else "") or ""
            if any(
                k in tgt.lower() or k in reason.lower()
                for k in ("citation", "reference", "bibliography",
                          "literature")
            ):
                created_from.append("rewrite_plan")
                gap_categories.append(
                    "rewrite plan requests citation/literature work"
                )
                break

    # ----- Search tasks (no concrete references invented) -----
    if disc_axis in ("bad", "weak", "unknown"):
        search_tasks.append(
            "Identify 5-8 recent articles from the target venue that "
            "engage the article's disciplinary tradition; extract the "
            "theoretical anchors they recur to. Do not cite venue-local "
            "papers cosmetically — only add a citation when it supports "
            "a real argumentative bridge in your article."
        )
    if novelty_axis in ("bad", "weak"):
        search_tasks.append(
            "Identify the current debate markers in the venue's recent "
            "issues on this topic; position the article's novelty "
            "claim against the most recent counter-argument."
        )
    if cit_axis == "unknown":
        search_tasks.append(
            "Parse the manuscript's bibliography (count, recency, source "
            "kind distribution) before citation ecology can be assessed."
        )

    # ----- Verification tasks -----
    if bib_status == "absent_unknown":
        verification_tasks.append(
            "Provide the manuscript's bibliography (parsed or raw) — "
            "without it, no citation gap can be verified at the "
            "reference level."
        )
        unknowns.append(
            "Bibliography not parsed for this case — citation gaps are "
            "inferred only from FitAssessment / MismatchMap signals."
        )
    elif bib_status == "ecology_text_only_not_parsed":
        verification_tasks.append(
            "Article's citation_ecology_current field is text only; run "
            "bibliography parser to get per-reference counts and dates."
        )
        unknowns.append(
            "Bibliography text present but not structurally parsed."
        )
    elif bib_status == "self_reported_only":
        verification_tasks.append(
            "Article self-reports a reference count; verify per-reference "
            "metadata (DOI, year, venue) before submission readiness."
        )

    if venue_exp_status == "venue_text_absent":
        unknowns.append("Venue text absent — no venue-local citation "
                        "expectation can be inferred.")
    elif venue_exp_status == "scope_silent_on_citation_expectations":
        unknowns.append(
            "Venue scope text does not mention citation expectations — "
            "venue-local norms (typical reference count, recency, "
            "preferred bridges) are unknown."
        )

    # ----- Dangerous-padding warning (always present when expansion suggested) -----
    if missing_bridges or search_tasks:
        padding_warnings.append(
            "Do not add references only to imitate venue metrics. Every "
            "added reference must support an actual argumentative bridge "
            "in the article. Cosmetic citation padding is a desk-reject "
            "risk and an integrity risk."
        )

    # ----- Status -----
    blocked_signals = (
        bib_status == "absent_unknown"
        and venue_exp_status == "venue_text_absent"
    )
    if blocked_signals:
        status = STATUS_BLOCKED_MISSING_EVIDENCE
    elif bib_status == "absent_unknown":
        status = STATUS_NEEDS_BIBLIOGRAPHY
    elif venue_exp_status == "venue_text_absent":
        status = STATUS_NEEDS_VENUE_CORPUS
    elif search_tasks and missing_bridges:
        status = STATUS_SEARCH_TASKS_READY
    elif search_tasks or missing_bridges or gap_categories:
        status = STATUS_PARTIALLY_READY
    else:
        status = STATUS_DRAFT

    confidence = "low" if (
        bib_status == "absent_unknown"
        or venue_exp_status == "venue_text_absent"
    ) else "medium"

    # de-dup with order preservation
    def _uniq(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return CitationPlan(
        article_model_id=article.article_model_id,
        venue_model_id=venue.venue_model_id,
        fit_assessment_id=fit.fit_assessment_id,
        current_bibliography_status=bib_status,
        venue_citation_expectation_status=venue_exp_status,
        citation_gap_categories=_uniq(gap_categories),
        missing_bridge_categories=_uniq(missing_bridges),
        recommended_reference_search_tasks=_uniq(search_tasks),
        verification_tasks=_uniq(verification_tasks),
        dangerous_padding_warnings=padding_warnings,
        risk_flags=_uniq(risk_flags),
        unknowns=_uniq(unknowns),
        created_from=_uniq(created_from),
        confidence=confidence,
        status=status,
    )
