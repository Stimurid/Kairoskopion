"""V2-D minimal SubmissionPack readiness builder.

NOT a final submission automation. NOT a portal-specific package.
NOT a cover-letter generator (V2-D skips cover_letter; see brief
"do not generate cover letter unless an existing safe skeleton
already exists" — operator must draft).

Computes a readiness skeleton from the already-built chain:
ArticleModel, VenueModel, SubmissionScenario, FitAssessment,
RiskReport, RewritePlan, CitationPlan, ComplianceChecklist. Produces:

  - `ready_status` from the V2-D taxonomy
  - `missing_items` (concrete items the user must provide)
  - `blocking_issues` (things that prevent submission readiness)
  - `warnings`
  - `next_actions` (concrete ordered checklist)
  - `depends_on` (object types this readiness depends on)
  - `unknowns`

Will NOT mark ready_for_manual_submission while:
  - RewritePlan effort is major/core_touching/major-cost;
  - CitationPlan requires bibliography or venue corpus;
  - ComplianceChecklist has blocking/missing critical items;
  - any explicit blocking_issues remain.
"""

from __future__ import annotations

from ..schema import (
    ArticleModel,
    CitationPlan,
    ComplianceChecklist,
    FitAssessment,
    RewritePlan,
    RiskReport,
    SubmissionPack,
    SubmissionScenario,
    VenueModel,
)


# V2-D ready_status taxonomy
READY_NOT_READY = "not_ready"
READY_NEEDS_USER_INPUT = "needs_user_input"
READY_NEEDS_FILE_UPDATE = "needs_file_update"
READY_NEEDS_REFERENCE_VERIFICATION = "needs_reference_verification"
READY_NEEDS_COMPLIANCE_CHECK = "needs_compliance_check"
READY_FOR_MANUAL_SUBMISSION = "ready_for_manual_submission"
READY_BLOCKED_MISSING_EVIDENCE = "blocked_missing_evidence"

# Overall status (parallels other V2-D objects)
STATUS_NOT_BUILT = "not_built"
STATUS_DRAFT = "draft"
STATUS_PARTIAL = "partial"
STATUS_READY_SKELETON = "ready_skeleton"
STATUS_BLOCKED = "blocked"


def build_minimal_submission_pack(
    article: ArticleModel,
    venue: VenueModel,
    scenario: SubmissionScenario | None,
    fit: FitAssessment | None,
    risk_report: RiskReport | None,
    rewrite_plan: RewritePlan | None,
    citation_plan: CitationPlan | None,
    compliance_checklist: ComplianceChecklist | None,
) -> SubmissionPack:
    missing: list[str] = []
    blocking: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []
    unknowns: list[str] = []
    depends_on: list[str] = []
    created_from: list[str] = ["article_model", "venue_model"]

    # ----- Manuscript files -----
    files: list[str] = ["manuscript"]
    if not (article.title_current or "").strip():
        missing.append("manuscript title")
        next_actions.append(
            "Add a clear manuscript title (article modeler did not extract one)."
        )
    if not (article.abstract_current or "").strip():
        missing.append("abstract")
        next_actions.append("Ensure the manuscript has an abstract section.")

    # ----- Statements (do not invent; only honest TODOs) -----
    statements: list[str] = []
    statements.append(
        "Cover letter: NOT auto-generated. Operator must draft using "
        "ArticleModel + VenueModel + SubmissionScenario as anchors."
    )
    statements.append(
        "Author/affiliation list, ORCID, contributor roles: operator-provided."
    )

    # ----- Fit gating -----
    if fit is not None:
        created_from.append("fit_assessment")
        bad_axes = [a for a in fit.axes if a.get("value") == "bad"]
        for ax in bad_axes:
            blocking.append(
                f"fit axis '{ax.get('axis', '?')}' = bad (likely desk-reject)"
            )
        if fit.overall_label == "poor_fit":
            blocking.append("FitAssessment.overall_label = poor_fit")
        elif fit.overall_label == "possible_but_costly":
            warnings.append(
                "FitAssessment overall = possible_but_costly — significant "
                "rewrite expected before submission"
            )

    # ----- Risk gating -----
    if risk_report is not None:
        created_from.append("risk_report")
        for r in risk_report.risk_items:
            if not isinstance(r, dict):
                continue
            severity = r.get("severity", "")
            if severity == "blocking":
                blocking.append(
                    f"risk: {r.get('risk_type', '?')} — "
                    f"{(r.get('description') or '')[:140]}"
                )

    # ----- Rewrite gating -----
    rewrite_major = False
    if rewrite_plan is not None:
        created_from.append("rewrite_plan")
        depends_on.append("rewrite_plan")
        effort = (rewrite_plan.estimated_effort or "").lower()
        field_core = (rewrite_plan.field_core_risk or "").lower()
        if effort in ("major", "high") or "core_touching" in field_core or "core_transforming" in field_core:
            rewrite_major = True
            warnings.append(
                f"RewritePlan effort = {effort or '?'}, field_core_risk = "
                f"{field_core or '?'} — apply changes before pack readiness"
            )
            next_actions.append(
                "Review RewritePlan changes and accept/revise before "
                "preparing the submission pack."
            )

    # ----- Citation plan gating -----
    if citation_plan is not None:
        created_from.append("citation_plan")
        depends_on.append("citation_plan")
        cp_status = (citation_plan.status or "").lower()
        if cp_status in (
            "needs_bibliography",
            "needs_venue_corpus",
            "blocked_missing_evidence",
        ):
            warnings.append(
                f"CitationPlan status = {cp_status} — bibliography or "
                "venue-corpus work required before submission"
            )
            next_actions.append(
                "Address CitationPlan verification_tasks "
                "(bibliography / venue corpus) before submission."
            )

    # ----- Compliance gating -----
    if compliance_checklist is not None:
        created_from.append("compliance_checklist")
        depends_on.append("compliance_checklist")
        cc_status = (compliance_checklist.status or "").lower()
        if compliance_checklist.blocking_items:
            for b in compliance_checklist.blocking_items:
                blocking.append(f"compliance: {b}")
        if compliance_checklist.missing_items:
            for m in compliance_checklist.missing_items:
                missing.append(f"compliance: {m}")
            next_actions.append(
                "Resolve ComplianceChecklist missing_items before submission."
            )
        if compliance_checklist.unknowns:
            unknowns.extend(
                [f"compliance: {u}" for u in compliance_checklist.unknowns]
            )
            next_actions.append(
                "Verify ComplianceChecklist unknowns directly with the "
                "venue's submission guidelines (AI policy, data policy, "
                "ethics, COI, funding)."
            )
        if cc_status == "blocked":
            warnings.append("ComplianceChecklist overall = blocked")

    if scenario is not None:
        created_from.append("submission_scenario")
        if getattr(scenario, "scenario_preliminary", False):
            warnings.append(
                "SubmissionScenario is preliminary — fit/risk verdict may "
                "shift once operator completes scenario (goal, deadline, "
                "APC max, risk tolerance)"
            )
            next_actions.append(
                "Complete SubmissionScenario to lock down the fit verdict."
            )

    # ----- Compute ready_status -----
    if blocking:
        ready_status = READY_NOT_READY
    elif rewrite_major:
        ready_status = READY_NEEDS_USER_INPUT
    elif compliance_checklist is not None and compliance_checklist.missing_items:
        ready_status = READY_NEEDS_COMPLIANCE_CHECK
    elif compliance_checklist is not None and compliance_checklist.unknowns:
        ready_status = READY_NEEDS_USER_INPUT
    elif citation_plan is not None and (citation_plan.status or "") in (
        "needs_bibliography", "needs_venue_corpus", "blocked_missing_evidence",
    ):
        ready_status = READY_NEEDS_REFERENCE_VERIFICATION
    elif missing:
        ready_status = READY_NEEDS_FILE_UPDATE
    elif not (compliance_checklist and citation_plan):
        ready_status = READY_NEEDS_USER_INPUT
    else:
        # All gates pass — but this is still a SKELETON, not final pack.
        ready_status = READY_FOR_MANUAL_SUBMISSION

    # Always include the boundary statement
    next_actions.append(
        "SubmissionPack is a readiness skeleton — final portal-specific "
        "fields, cover letter draft, and final declarations must be "
        "prepared manually."
    )

    # Overall status
    if blocking:
        status = STATUS_BLOCKED
    elif ready_status == READY_FOR_MANUAL_SUBMISSION:
        status = STATUS_READY_SKELETON
    elif missing or warnings:
        status = STATUS_PARTIAL
    else:
        status = STATUS_DRAFT

    metadata: dict = {
        "ready_status_taxonomy": "v2d_minimal",
        "is_final_submission_package": False,
        "automation_level": "manual_only",
    }

    def _uniq(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return SubmissionPack(
        article_model_id=article.article_model_id,
        venue_model_id=venue.venue_model_id,
        submission_scenario_id=(
            scenario.submission_scenario_id if scenario else None
        ),
        compliance_checklist_id=(
            compliance_checklist.compliance_checklist_id
            if compliance_checklist else None
        ),
        citation_plan_id=(
            citation_plan.citation_plan_id if citation_plan else None
        ),
        files=files,
        metadata=metadata,
        statements=statements,
        cover_letter=None,  # V2-D: operator must draft
        missing_items=_uniq(missing),
        blocking_issues=_uniq(blocking),
        warnings=_uniq(warnings),
        next_actions=_uniq(next_actions),
        depends_on=_uniq(depends_on),
        created_from=_uniq(created_from),
        unknowns=_uniq(unknowns),
        ready_status=ready_status,
        status=status,
    )
