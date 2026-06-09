"""Publication Trajectory Report (Sprint 5).

Synthesizes FitAssessment, RiskReport, and BibliographyProfile into
a structured recommendation report for the author. No LLM — all
heuristic text generation.
"""

from __future__ import annotations

from ..schema import (
    ArticleModel,
    BibliographyProfile,
    FitAssessment,
    PublicationTrajectoryReport,
    RiskReport,
    VenueModel,
)


def build_trajectory_report(
    article: ArticleModel,
    venue: VenueModel,
    fit: FitAssessment,
    risk: RiskReport,
    bib: BibliographyProfile | None = None,
) -> PublicationTrajectoryReport:
    """Build a PublicationTrajectoryReport from pipeline artifacts.

    Aggregates strengths, weaknesses, critical actions, and optional
    improvements into a structured report for the author.
    """
    strengths: list[str] = []
    weaknesses: list[str] = []
    critical_actions: list[str] = []
    optional_improvements: list[str] = []
    unknowns: list[str] = []

    # --- Fit analysis ---
    strong_axes = [a for a in fit.axes if a.get("value") == "strong"]
    weak_axes = [a for a in fit.axes if a.get("value") in ("weak", "bad")]
    unknown_axes = [a for a in fit.axes if a.get("value") == "unknown"]

    for ax in strong_axes:
        strengths.append(f"{ax['axis']}: {ax.get('notes', 'strong fit')}")

    for ax in weak_axes:
        weaknesses.append(f"{ax['axis']}: {ax.get('notes', 'weak fit')}")
        if ax.get("value") == "bad":
            critical_actions.append(
                f"Address {ax['axis']} — rated 'bad', likely desk reject trigger"
            )
        else:
            optional_improvements.append(
                f"Strengthen {ax['axis']} — currently rated 'weak'"
            )

    for ax in unknown_axes:
        unknowns.append(f"{ax['axis']}: {ax.get('notes', 'not assessed')}")

    fit_summary = (
        f"Fit assessment: {fit.overall_label}. "
        f"{len(strong_axes)} strong, {len(weak_axes)} weak/bad, "
        f"{len(unknown_axes)} unknown axes out of {len(fit.axes)}."
    )

    # --- Risk analysis ---
    blocking = [r for r in risk.risk_items if r.get("severity") == "blocking"]
    major = [r for r in risk.risk_items if r.get("severity") == "major"]

    for r in blocking:
        critical_actions.append(
            f"[BLOCKING] {r.get('risk_type', 'unknown')}: {r.get('description', '')}"
        )

    for r in major:
        weaknesses.append(
            f"Risk: {r.get('risk_type', 'unknown')} — {r.get('description', '')}"
        )
        if r.get("mitigation"):
            optional_improvements.append(r["mitigation"])

    risk_summary = (
        f"Risk level: {risk.overall_risk_label}. "
        f"{len(blocking)} blocking, {len(major)} major, "
        f"{len(risk.risk_items)} total risk items."
    )

    # --- Bibliography analysis ---
    bib_summary = None
    if bib:
        parts = [f"{bib.total_references} references"]
        if bib.recency_profile:
            parts.append(f"recency: {bib.recency_profile}")
        if bib.reference_style:
            parts.append(f"style: {bib.reference_style}")
        if bib.doi_count is not None:
            parts.append(f"{bib.doi_count} with DOI")
        bib_summary = "Bibliography: " + ", ".join(parts) + "."

        if bib.recency_profile == "historical":
            weaknesses.append(
                "Bibliography skews historical — may need recent citations"
            )
            optional_improvements.append(
                "Add recent (post-2020) references to demonstrate currency"
            )

        if bib.total_references < 10:
            weaknesses.append(
                f"Only {bib.total_references} references — thin bibliography"
            )
            optional_improvements.append(
                "Expand bibliography to at least 20–30 references"
            )

        if bib.doi_count == 0 and bib.total_references > 0:
            optional_improvements.append(
                "Add DOIs to references for verification and linking"
            )

        unknowns.extend(bib.unknowns)

    # --- Overall recommendation ---
    if fit.overall_label == "strong_candidate" and risk.overall_risk_label == "low":
        overall = (
            "Strong candidate for submission. Proceed with compliance check "
            "and submission pack preparation."
        )
        confidence = "medium"
    elif fit.overall_label == "poor_fit" or risk.overall_risk_label == "high":
        overall = (
            "Submission not recommended in current form. Consider alternative "
            "venues or significant revisions before proceeding."
        )
        confidence = "medium"
    elif fit.overall_label in ("possible", "possible_but_costly"):
        overall = (
            "Submission is possible but requires attention to weak areas. "
            "Address critical actions before submission."
        )
        confidence = "low"
    else:
        overall = (
            "Insufficient data for a confident recommendation. "
            "Gather more evidence before deciding."
        )
        confidence = "low"

    # Aggregate unknowns
    unknowns.extend(fit.unknowns)
    unknowns.extend(risk.unknowns)
    # Deduplicate
    unknowns = list(dict.fromkeys(unknowns))

    return PublicationTrajectoryReport(
        article_model_id=article.article_model_id,
        venue_model_id=venue.venue_model_id,
        fit_summary=fit_summary,
        risk_summary=risk_summary,
        bibliography_summary=bib_summary,
        strengths=strengths,
        weaknesses=weaknesses,
        critical_actions=critical_actions,
        optional_improvements=optional_improvements,
        overall_recommendation=overall,
        confidence=confidence,
        unknowns=unknowns,
    )
