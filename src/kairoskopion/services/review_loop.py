"""Review loop service — iterative plan refinement with protected core respect.

Handles user decisions on blocked rewrite plan changes:
- accept: unblock the change, mark as user_accepted
- reject: remove the change from the plan
- defer: keep blocked for future decision

Also re-validates the plan after mutations to ensure protected core
invariants are maintained.
"""

from __future__ import annotations

import dataclasses as dc
from typing import Any

from ..enums import FieldCoreImpact, LifecycleStatus
from ..ids import generate_id
from ..schema import RewritePlan, _DictMixin, _field, _list, _now
from .protected_core import validate_rewrite_plan, apply_core_gate


@dc.dataclass
class UserDecision:
    """A single user decision on a blocked change."""
    change_id: str
    action: str  # "accept" | "reject" | "defer"
    reason: str = ""


@dc.dataclass
class ReviewLoopIteration(_DictMixin):
    """Record of one review loop iteration."""
    iteration_id: str = dc.field(default_factory=lambda: generate_id("rli"))
    iteration_number: int = 0
    decisions_applied: int = 0
    changes_accepted: int = 0
    changes_rejected: int = 0
    changes_deferred: int = 0
    remaining_blocked: int = 0
    plan_status: str = ""
    revalidation_result: dict[str, Any] | None = None
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class ReviewLoopResult(_DictMixin):
    """Result of a complete review loop session."""
    review_loop_id: str = dc.field(default_factory=lambda: generate_id("rl"))
    rewrite_plan_id: str = ""
    iterations: list[dict[str, Any]] = _list()
    final_plan: dict[str, Any] | None = None
    total_accepted: int = 0
    total_rejected: int = 0
    total_deferred: int = 0
    is_complete: bool = False
    requires_further_review: bool = False
    unknowns: list[str] = _list()
    disclaimer: str = (
        "Review loop applies user decisions deterministically. "
        "Semantic analysis of change interactions requires LLM."
    )
    created_at: str = dc.field(default_factory=_now)


def apply_user_decisions(
    plan: RewritePlan,
    decisions: list[UserDecision],
    protected_core: list[str] | None = None,
) -> tuple[RewritePlan, ReviewLoopIteration]:
    """Apply user decisions to a rewrite plan and re-validate.

    For each decision:
    - accept: change status → "user_accepted", unblock
    - reject: change status → "user_rejected"
    - defer: change stays blocked

    After mutations, re-validates against protected core to catch
    any new issues from plan state changes.
    """
    decision_map = {d.change_id: d for d in decisions}
    new_changes: list[dict[str, Any]] = []
    accepted = 0
    rejected = 0
    deferred = 0

    for change in plan.changes:
        change_copy = dict(change)
        cid = change.get("change_id", "")
        decision = decision_map.get(cid)

        if decision:
            if decision.action == "accept":
                change_copy["status"] = "user_accepted"
                change_copy.pop("_blocked_reason", None)
                change_copy.pop("_matched_core_elements", None)
                if decision.reason:
                    change_copy["_user_accept_reason"] = decision.reason
                accepted += 1
            elif decision.action == "reject":
                change_copy["status"] = "user_rejected"
                if decision.reason:
                    change_copy["_user_reject_reason"] = decision.reason
                rejected += 1
            elif decision.action == "defer":
                deferred += 1
            # else: unknown action, leave as-is

        new_changes.append(change_copy)

    mutated_plan = RewritePlan(
        rewrite_plan_id=plan.rewrite_plan_id,
        article_model_id=plan.article_model_id,
        manuscript_id=plan.manuscript_id,
        fit_assessment_id=plan.fit_assessment_id,
        target_venue_id=plan.target_venue_id,
        changes=new_changes,
        summary=plan.summary,
        estimated_effort=plan.estimated_effort,
        field_core_risk=plan.field_core_risk,
        requires_user_acceptance=plan.requires_user_acceptance,
        lifecycle_status=plan.lifecycle_status,
    )

    # Re-validate against protected core
    core = protected_core or []
    revalidation = None
    remaining_blocked = 0

    if core:
        validation = validate_rewrite_plan(mutated_plan, core)
        revalidation = validation.to_dict()

        # Count still-blocked (excluding user_accepted and user_rejected)
        for ch in mutated_plan.changes:
            if ch.get("status") == "blocked_pending_consent":
                remaining_blocked += 1

        # Update plan acceptance flag
        if remaining_blocked == 0:
            mutated_plan = RewritePlan(
                rewrite_plan_id=mutated_plan.rewrite_plan_id,
                article_model_id=mutated_plan.article_model_id,
                manuscript_id=mutated_plan.manuscript_id,
                fit_assessment_id=mutated_plan.fit_assessment_id,
                target_venue_id=mutated_plan.target_venue_id,
                changes=mutated_plan.changes,
                summary=mutated_plan.summary,
                estimated_effort=mutated_plan.estimated_effort,
                field_core_risk=mutated_plan.field_core_risk,
                requires_user_acceptance=False,
                lifecycle_status=LifecycleStatus.ACCEPTED_BY_USER.value if not deferred else mutated_plan.lifecycle_status,
            )
    else:
        for ch in mutated_plan.changes:
            if ch.get("status") == "blocked_pending_consent":
                remaining_blocked += 1
        if remaining_blocked == 0 and mutated_plan.requires_user_acceptance:
            mutated_plan = RewritePlan(
                rewrite_plan_id=mutated_plan.rewrite_plan_id,
                article_model_id=mutated_plan.article_model_id,
                manuscript_id=mutated_plan.manuscript_id,
                fit_assessment_id=mutated_plan.fit_assessment_id,
                target_venue_id=mutated_plan.target_venue_id,
                changes=mutated_plan.changes,
                summary=mutated_plan.summary,
                estimated_effort=mutated_plan.estimated_effort,
                field_core_risk=mutated_plan.field_core_risk,
                requires_user_acceptance=False,
                lifecycle_status=LifecycleStatus.ACCEPTED_BY_USER.value if not deferred else mutated_plan.lifecycle_status,
            )

    iteration = ReviewLoopIteration(
        decisions_applied=len(decisions),
        changes_accepted=accepted,
        changes_rejected=rejected,
        changes_deferred=deferred,
        remaining_blocked=remaining_blocked,
        plan_status="all_resolved" if remaining_blocked == 0 else "pending_decisions",
        revalidation_result=revalidation,
    )

    return mutated_plan, iteration


def run_review_loop(
    plan: RewritePlan,
    decision_rounds: list[list[UserDecision]],
    protected_core: list[str] | None = None,
) -> ReviewLoopResult:
    """Run a complete review loop with multiple decision rounds.

    Each round applies a batch of user decisions. The loop continues
    until all blocked changes are resolved or all rounds are exhausted.
    """
    result = ReviewLoopResult(rewrite_plan_id=plan.rewrite_plan_id)
    current_plan = plan
    total_accepted = 0
    total_rejected = 0
    total_deferred = 0

    for i, decisions in enumerate(decision_rounds):
        if not decisions:
            continue

        current_plan, iteration = apply_user_decisions(
            current_plan, decisions, protected_core,
        )
        iteration.iteration_number = i + 1
        result.iterations.append(iteration.to_dict())

        total_accepted += iteration.changes_accepted
        total_rejected += iteration.changes_rejected
        total_deferred += iteration.changes_deferred

        if iteration.remaining_blocked == 0:
            break

    result.final_plan = current_plan.to_dict()
    result.total_accepted = total_accepted
    result.total_rejected = total_rejected
    result.total_deferred = total_deferred

    remaining = sum(
        1 for ch in current_plan.changes
        if ch.get("status") == "blocked_pending_consent"
    )
    result.is_complete = remaining == 0
    result.requires_further_review = remaining > 0

    if result.requires_further_review:
        result.unknowns.append(
            f"{remaining} change(s) still blocked — need user decisions"
        )

    return result


def extract_blocked_changes(plan: RewritePlan) -> list[dict[str, Any]]:
    """Extract all blocked changes from a plan for user review presentation."""
    blocked = []
    for change in plan.changes:
        if change.get("status") == "blocked_pending_consent":
            blocked.append({
                "change_id": change.get("change_id", ""),
                "target_block": change.get("target_block", ""),
                "desired_state": change.get("desired_state", ""),
                "reason": change.get("reason", ""),
                "field_core_risk": change.get("field_core_risk", ""),
                "blocked_reason": change.get("_blocked_reason", ""),
                "matched_core_elements": change.get("_matched_core_elements", []),
            })
    return blocked
