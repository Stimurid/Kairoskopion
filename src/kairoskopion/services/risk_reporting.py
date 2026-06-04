"""Risk Reporting Service (spec §6.23, §15.7).

Generates RiskReport from article/venue/scenario + mismatch data.
"""

from __future__ import annotations

from ..enums import LifecycleStatus
from ..ids import risk_report_id
from ..schema import (
    ArticleModel,
    FitAssessment,
    MismatchMap,
    RiskReport,
    SubmissionScenario,
    VenueModel,
)


def build_risk_report(
    article: ArticleModel,
    venue: VenueModel,
    scenario: SubmissionScenario,
    fit: FitAssessment,
    mismatch_map: MismatchMap,
) -> RiskReport:
    """Generate RiskReport based on article, venue, scenario and mismatches."""
    items: list[dict] = []
    blocking: list[str] = []
    warnings: list[str] = []
    unknowns: list[str] = []
    idx = 0

    def _add(risk_type: str, desc: str, severity: str, likelihood: str,
             mitigation: str | None = None, user_action: bool = False) -> None:
        nonlocal idx
        idx += 1
        rid = f"risk_{idx}"
        items.append({
            "risk_id": rid,
            "risk_type": risk_type,
            "description": desc,
            "severity": severity,
            "likelihood": likelihood,
            "evidence_refs": [],
            "mitigation": mitigation,
            "requires_user_action": user_action,
        })
        if severity == "blocking":
            blocking.append(f"{rid}: {desc}")
        elif severity == "major":
            warnings.append(f"{rid}: {desc}")

    # --- Scope risk ---
    scope_axes = [a for a in fit.axes if a.get("axis") == "topic"]
    if scope_axes and scope_axes[0].get("value") in ("weak", "bad"):
        _add("scope_mismatch",
             "Article topic may not match venue scope",
             "major", "high",
             "Reframe introduction to emphasize venue-relevant aspects")

    # --- Method risk ---
    method_axes = [a for a in fit.axes if a.get("axis") == "method"]
    if method_axes and method_axes[0].get("value") in ("weak", "bad"):
        _add("method_weakness",
             "Venue appears to prefer empirical work; article is conceptual only",
             "major", "high",
             "Add empirical component or justify purely conceptual approach",
             user_action=True)

    # --- Citation risk ---
    cit_axes = [a for a in fit.axes if a.get("axis") == "citation_ecology"]
    if cit_axes and cit_axes[0].get("value") == "unknown":
        _add("citation_gap",
             "Citation ecology not yet assessed — risk of missing key venue references",
             "major", "medium",
             "Profile venue citation expectations and conduct bridge search")
        unknowns.append("citation ecology not profiled")

    # --- Field-core loss risk ---
    core_mismatches = [
        m for m in mismatch_map.mismatches
        if m.get("field_core_risk") in ("core_touching", "core_transforming", "core_destroying_risk")
    ]
    if core_mismatches:
        _add("field_core_loss",
             f"{len(core_mismatches)} adaptation(s) touch protected core",
             "major", "high",
             "Review each core-touching change with user before proceeding",
             user_action=True)

    # --- Formal noncompliance risk ---
    _add("formal_noncompliance",
         "Formal compliance not yet verified against author guidelines",
         "minor", "medium",
         "Run ComplianceChecklist against venue guidelines")
    unknowns.append("formal compliance not checked")

    # --- AI disclosure risk ---
    if "AI disclosure policy" in " ".join(venue.unknowns):
        _add("AI_disclosure",
             "Venue AI disclosure policy unknown — may require author declaration",
             "minor", "medium",
             "Check venue policy page for AI writing tool disclosure requirements")
        unknowns.append("AI disclosure policy unknown")

    # --- Timeline risk ---
    if scenario.deadline:
        _add("timeline",
             f"Submission deadline: {scenario.deadline} — adaptation effort may impact timeline",
             "minor", "medium",
             "Estimate rewrite effort and check against deadline")

    # --- Overall label ---
    if blocking:
        overall = "high"
    elif len(warnings) >= 3:
        overall = "high"
    elif warnings:
        overall = "medium"
    else:
        overall = "low"

    return RiskReport(
        risk_report_id=risk_report_id(),
        article_model_id=article.article_model_id,
        venue_model_id=venue.venue_model_id,
        submission_scenario_id=scenario.submission_scenario_id,
        risk_items=items,
        overall_risk_label=overall,
        blocking_risks=blocking,
        warnings=warnings,
        unknowns=unknowns,
        lifecycle_status=LifecycleStatus.DRAFT.value,
    )
