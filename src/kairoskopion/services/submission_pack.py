"""Submission Pack Builder (Sprint 6).

Assembles a structured SubmissionPack from pipeline artifacts:
  - Compliance checklist status
  - Required statements (data availability, AI disclosure, ethics)
  - Cover letter template
  - Missing items and blocking issues
  - Readiness assessment

No LLM — deterministic template generation.
"""

from __future__ import annotations

from typing import Any

from ..enums import SubmissionReadiness
from ..schema import (
    ArticleModel,
    ComplianceChecklist,
    FitAssessment,
    PublicationTrajectoryReport,
    RiskReport,
    SubmissionPack,
    SubmissionScenario,
    VenueModel,
)


def _generate_cover_letter(
    article: ArticleModel,
    venue: VenueModel,
    scenario: SubmissionScenario,
) -> str:
    """Generate a cover letter template (not final — needs author editing)."""
    title = article.title_current or "[TITLE]"
    journal = venue.canonical_name or "[JOURNAL NAME]"
    genre = article.genre_current or "research article"

    letter = f"""Dear Editor,

We are pleased to submit our {genre}, "{title}", for consideration
by {journal}.

[AUTHOR: Describe the key contribution and relevance to the journal scope.]

[AUTHOR: State that this manuscript has not been published elsewhere
and is not under consideration by another journal.]

[AUTHOR: Declare any conflicts of interest or funding sources.]

[AUTHOR: Confirm compliance with any venue-specific requirements.]

We look forward to your response.

Sincerely,
[AUTHOR NAME(S)]
[AFFILIATION(S)]
"""
    return letter.strip()


def _collect_required_statements(
    article: ArticleModel,
    venue: VenueModel,
) -> list[str]:
    """Determine which statements are required based on venue policies."""
    statements: list[str] = []

    if venue.data_policy:
        if getattr(article, "has_data_availability_statement", None):
            statements.append("Data availability statement: present in manuscript")
        else:
            statements.append("Data availability statement: REQUIRED — not detected in manuscript")

    if venue.ai_policy:
        if getattr(article, "has_ai_disclosure", None):
            statements.append("AI disclosure: present in manuscript")
        else:
            statements.append("AI disclosure: REQUIRED — not detected in manuscript")

    if venue.ethics_policy:
        statements.append("Ethics statement: check if applicable to this study")

    return statements


def _assess_readiness(
    compliance: ComplianceChecklist | None,
    risk: RiskReport | None,
    fit: FitAssessment | None,
    missing: list[str],
    blocking: list[str],
) -> str:
    """Determine submission readiness status."""
    if blocking:
        return SubmissionReadiness.NOT_READY.value

    if missing:
        return SubmissionReadiness.NEEDS_FILE_UPDATE.value

    if fit and fit.overall_label == "poor_fit":
        return SubmissionReadiness.NOT_READY.value

    if risk and risk.overall_risk_label == "high":
        return SubmissionReadiness.NEEDS_USER_INPUT.value

    if compliance and compliance.missing_items:
        return SubmissionReadiness.NEEDS_COMPLIANCE_CHECK.value

    if fit and fit.overall_label in ("strong_candidate", "possible"):
        return SubmissionReadiness.READY_FOR_MANUAL_SUBMISSION.value

    return SubmissionReadiness.NEEDS_USER_INPUT.value


def build_submission_pack(
    article: ArticleModel,
    venue: VenueModel,
    scenario: SubmissionScenario,
    fit: FitAssessment | None = None,
    risk: RiskReport | None = None,
    compliance: ComplianceChecklist | None = None,
    trajectory: PublicationTrajectoryReport | None = None,
) -> SubmissionPack:
    """Build a SubmissionPack from pipeline artifacts.

    Collects required files, statements, cover letter template,
    identifies missing items and blocking issues, and assesses readiness.
    """
    missing: list[str] = []
    blocking: list[str] = []
    warnings: list[str] = []
    files: list[str] = []
    metadata: dict[str, Any] = {}

    # --- Files ---
    files.append("manuscript")
    if not article.title_current:
        missing.append("Manuscript title not detected")

    # --- Statements ---
    statements = _collect_required_statements(article, venue)
    required_missing = [s for s in statements if "REQUIRED" in s]
    if required_missing:
        for s in required_missing:
            missing.append(s)

    # --- Cover letter ---
    cover_letter = _generate_cover_letter(article, venue, scenario)
    files.append("cover_letter_template")

    # --- Compliance ---
    if compliance:
        metadata["compliance_items"] = len(compliance.checklist_items)
        metadata["compliance_missing"] = len(compliance.missing_items)
        if compliance.missing_items:
            for item in compliance.missing_items:
                missing.append(f"Compliance: {item}")
    else:
        warnings.append("Compliance checklist not generated — run full pipeline first")

    # --- Fit blocking ---
    if fit:
        bad_axes = [a for a in fit.axes if a.get("value") == "bad"]
        for ax in bad_axes:
            blocking.append(
                f"Fit axis '{ax['axis']}' rated 'bad' — likely desk reject"
            )
        metadata["fit_label"] = fit.overall_label

    # --- Risk blocking ---
    if risk:
        for item in risk.risk_items:
            if item.get("severity") == "blocking":
                blocking.append(f"Risk: {item.get('description', 'unknown')}")
        metadata["risk_label"] = risk.overall_risk_label

    # --- Readiness ---
    readiness = _assess_readiness(compliance, risk, fit, missing, blocking)

    return SubmissionPack(
        article_model_id=article.article_model_id,
        manuscript_id=None,
        venue_model_id=venue.venue_model_id,
        submission_scenario_id=scenario.submission_scenario_id,
        compliance_checklist_id=(
            compliance.compliance_checklist_id if compliance else None
        ),
        files=files,
        metadata=metadata,
        statements=statements,
        cover_letter=cover_letter,
        missing_items=missing,
        blocking_issues=blocking,
        warnings=warnings,
        ready_status=readiness,
    )
