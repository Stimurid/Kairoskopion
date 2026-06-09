"""Risk Reporting Service (spec §6.23, §15.7).

Generates RiskReport from article/venue/scenario + mismatch data.

Sprint 2: expanded risk taxonomy to 18 types:
  desk_reject_risk, scope_mismatch, methodology_mismatch, citation_gap,
  language_quality, ethical_concern, formatting_violation, predatory_venue,
  author_eligibility, duplicate_submission, copyright_conflict,
  data_availability, reviewer_pool_mismatch, timeline_risk, cost_risk,
  reputational_risk, ai_policy_risk, core_transformation_risk.
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


# Complete risk taxonomy (Sprint 2)
RISK_TYPES = (
    "desk_reject_risk",
    "scope_mismatch",
    "methodology_mismatch",
    "citation_gap",
    "language_quality",
    "ethical_concern",
    "formatting_violation",
    "predatory_venue",
    "author_eligibility",
    "duplicate_submission",
    "copyright_conflict",
    "data_availability",
    "reviewer_pool_mismatch",
    "timeline_risk",
    "cost_risk",
    "reputational_risk",
    "ai_policy_risk",
    "core_transformation_risk",
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

    def _axis_value(axis_name: str) -> str | None:
        for a in fit.axes:
            if a.get("axis") == axis_name:
                return a.get("value")
        return None

    # --- Desk reject risk (high-level) ---
    bad_axes = sum(1 for a in fit.axes if a.get("value") == "bad")
    weak_axes = sum(1 for a in fit.axes if a.get("value") == "weak")
    if bad_axes > 0:
        _add("desk_reject_risk",
             f"{bad_axes} axis(es) rated 'bad' -- high desk reject probability",
             "blocking", "high",
             "Address bad-rated axes or consider alternative venues",
             user_action=True)
    elif weak_axes >= 3:
        _add("desk_reject_risk",
             f"{weak_axes} axes rated 'weak' -- moderate desk reject risk",
             "major", "medium",
             "Strengthen weakest axes before submission")

    # --- Scope mismatch ---
    if _axis_value("topic") in ("weak", "bad"):
        _add("scope_mismatch",
             "Article topic may not match venue scope",
             "major", "high",
             "Reframe introduction to emphasize venue-relevant aspects")

    # --- Methodology mismatch ---
    if _axis_value("method") in ("weak", "bad"):
        _add("methodology_mismatch",
             "Venue appears to prefer empirical work; article is conceptual only",
             "major", "high",
             "Add empirical component or justify purely conceptual approach",
             user_action=True)

    # --- Citation gap ---
    if _axis_value("citation_ecology") == "unknown":
        _add("citation_gap",
             "Citation ecology not yet assessed -- risk of missing key venue references",
             "major", "medium",
             "Profile venue citation expectations and conduct bridge search")
        unknowns.append("citation ecology not profiled")

    # --- Language quality ---
    if _axis_value("language_register") in ("bad", "weak"):
        _add("language_quality",
             "Language mismatch with venue policy",
             "major", "high",
             "Check venue language requirements; consider translation/editing")

    # --- Ethical concern ---
    if getattr(article, 'has_data_availability_statement', None) is False:
        _add("ethical_concern",
             "No data availability statement detected",
             "minor", "medium",
             "Add data availability statement if venue requires it")

    # --- Formatting violation ---
    _add("formatting_violation",
         "Formal compliance not yet verified against author guidelines",
         "minor", "medium",
         "Run ComplianceChecklist against venue guidelines")
    unknowns.append("formal compliance not checked")

    # --- Predatory venue ---
    if not venue.source_refs and not venue.official_urls:
        _add("predatory_venue",
             "No verified source refs for venue -- predatory risk not assessed",
             "minor", "low",
             "Verify venue through official indexing databases")
        unknowns.append("venue legitimacy not verified")

    # --- Author eligibility ---
    if _axis_value("author_eligibility") == "unknown":
        _add("author_eligibility",
             "Author eligibility not assessed -- some venues restrict by affiliation/geography",
             "minor", "low",
             "Check venue author requirements")
        unknowns.append("author eligibility not verified")

    # --- AI disclosure / AI policy risk ---
    ai_policy = getattr(venue, 'ai_policy', None)
    if ai_policy:
        _add("ai_policy_risk",
             f"Venue has AI policy: {ai_policy[:100]}",
             "minor", "medium",
             "Ensure AI usage disclosure complies with venue policy",
             user_action=True)
    elif "AI disclosure policy" in " ".join(venue.unknowns):
        _add("ai_policy_risk",
             "Venue AI disclosure policy unknown -- may require author declaration",
             "minor", "medium",
             "Check venue policy page for AI writing tool disclosure requirements")
        unknowns.append("AI disclosure policy unknown")

    # --- Data availability ---
    data_policy = getattr(venue, 'data_policy', None)
    if data_policy and getattr(article, 'has_data_availability_statement', None) is None:
        _add("data_availability",
             "Venue has data policy but article data availability status unknown",
             "minor", "medium",
             "Check data availability requirements")

    # --- Core transformation risk ---
    core_mismatches = [
        m for m in mismatch_map.mismatches
        if m.get("field_core_risk") in ("core_touching", "core_transforming", "core_destroying_risk")
    ]
    if core_mismatches:
        _add("core_transformation_risk",
             f"{len(core_mismatches)} adaptation(s) touch protected core",
             "major", "high",
             "Review each core-touching change with user before proceeding",
             user_action=True)

    # --- Timeline risk ---
    if scenario.deadline:
        _add("timeline_risk",
             f"Submission deadline: {scenario.deadline} -- adaptation effort may impact timeline",
             "minor", "medium",
             "Estimate rewrite effort and check against deadline")

    # --- Cost risk ---
    apc = getattr(venue, 'apc_policy', None)
    if apc and "open access" in (apc or "").lower():
        _add("cost_risk",
             "Venue may charge APC for open access publication",
             "minor", "medium",
             "Check APC amount and funding availability")

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
