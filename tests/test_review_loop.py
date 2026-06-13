"""Tests for review loop service."""

from __future__ import annotations

import unittest

from kairoskopion.enums import FieldCoreImpact
from kairoskopion.schema import RewritePlan
from kairoskopion.services.review_loop import (
    ReviewLoopIteration,
    ReviewLoopResult,
    UserDecision,
    apply_user_decisions,
    extract_blocked_changes,
    run_review_loop,
)


def _plan_with_blocked() -> RewritePlan:
    return RewritePlan(
        changes=[
            {
                "change_id": "ch_1",
                "target_block": "topic",
                "desired_state": "reframe thesis",
                "reason": "mismatch",
                "status": "blocked_pending_consent",
                "field_core_risk": FieldCoreImpact.CORE_TOUCHING.value,
                "_blocked_reason": "Matches: thesis",
                "_matched_core_elements": ["thesis"],
            },
            {
                "change_id": "ch_2",
                "target_block": "format",
                "desired_state": "fix citations",
                "reason": "style",
                "status": "proposed",
                "field_core_risk": FieldCoreImpact.CORE_PRESERVING.value,
            },
            {
                "change_id": "ch_3",
                "target_block": "method",
                "desired_state": "add methods section",
                "reason": "venue requires",
                "status": "blocked_pending_consent",
                "field_core_risk": FieldCoreImpact.CORE_TOUCHING.value,
                "_blocked_reason": "Sensitive axis",
                "_matched_core_elements": [],
            },
        ],
        requires_user_acceptance=True,
    )


class TestExtractBlockedChanges(unittest.TestCase):
    def test_extracts_blocked_only(self):
        plan = _plan_with_blocked()
        blocked = extract_blocked_changes(plan)
        self.assertEqual(len(blocked), 2)
        ids = [b["change_id"] for b in blocked]
        self.assertIn("ch_1", ids)
        self.assertIn("ch_3", ids)
        self.assertNotIn("ch_2", ids)

    def test_empty_plan(self):
        plan = RewritePlan(changes=[])
        blocked = extract_blocked_changes(plan)
        self.assertEqual(len(blocked), 0)

    def test_no_blocked(self):
        plan = RewritePlan(changes=[{"change_id": "ch_1", "status": "proposed"}])
        blocked = extract_blocked_changes(plan)
        self.assertEqual(len(blocked), 0)


class TestApplyUserDecisions(unittest.TestCase):
    def test_accept_unblocks(self):
        plan = _plan_with_blocked()
        decisions = [UserDecision("ch_1", "accept", "approved by author")]
        updated, iteration = apply_user_decisions(plan, decisions)
        ch1 = next(c for c in updated.changes if c["change_id"] == "ch_1")
        self.assertEqual(ch1["status"], "user_accepted")
        self.assertNotIn("_blocked_reason", ch1)
        self.assertIn("_user_accept_reason", ch1)
        self.assertEqual(iteration.changes_accepted, 1)

    def test_reject_marks_rejected(self):
        plan = _plan_with_blocked()
        decisions = [UserDecision("ch_1", "reject", "author declines")]
        updated, iteration = apply_user_decisions(plan, decisions)
        ch1 = next(c for c in updated.changes if c["change_id"] == "ch_1")
        self.assertEqual(ch1["status"], "user_rejected")
        self.assertEqual(iteration.changes_rejected, 1)

    def test_defer_keeps_blocked(self):
        plan = _plan_with_blocked()
        decisions = [UserDecision("ch_1", "defer")]
        updated, iteration = apply_user_decisions(plan, decisions)
        ch1 = next(c for c in updated.changes if c["change_id"] == "ch_1")
        self.assertEqual(ch1["status"], "blocked_pending_consent")
        self.assertEqual(iteration.changes_deferred, 1)

    def test_proposed_changes_untouched(self):
        plan = _plan_with_blocked()
        decisions = [UserDecision("ch_1", "accept")]
        updated, _ = apply_user_decisions(plan, decisions)
        ch2 = next(c for c in updated.changes if c["change_id"] == "ch_2")
        self.assertEqual(ch2["status"], "proposed")

    def test_all_resolved_clears_acceptance_flag(self):
        plan = _plan_with_blocked()
        decisions = [
            UserDecision("ch_1", "accept"),
            UserDecision("ch_3", "reject"),
        ]
        updated, iteration = apply_user_decisions(plan, decisions)
        self.assertEqual(iteration.remaining_blocked, 0)
        self.assertFalse(updated.requires_user_acceptance)

    def test_partial_resolution_keeps_acceptance(self):
        plan = _plan_with_blocked()
        decisions = [UserDecision("ch_1", "accept")]
        updated, iteration = apply_user_decisions(plan, decisions)
        self.assertEqual(iteration.remaining_blocked, 1)

    def test_with_protected_core_revalidation(self):
        plan = _plan_with_blocked()
        decisions = [
            UserDecision("ch_1", "accept"),
            UserDecision("ch_3", "accept"),
        ]
        updated, iteration = apply_user_decisions(
            plan, decisions, protected_core=["central thesis"],
        )
        self.assertIsNotNone(iteration.revalidation_result)

    def test_original_plan_not_mutated(self):
        plan = _plan_with_blocked()
        original_status = plan.changes[0]["status"]
        decisions = [UserDecision("ch_1", "accept")]
        apply_user_decisions(plan, decisions)
        self.assertEqual(plan.changes[0]["status"], original_status)


class TestRunReviewLoop(unittest.TestCase):
    def test_single_round_resolves(self):
        plan = _plan_with_blocked()
        rounds = [
            [UserDecision("ch_1", "accept"), UserDecision("ch_3", "reject")],
        ]
        result = run_review_loop(plan, rounds)
        self.assertTrue(result.is_complete)
        self.assertFalse(result.requires_further_review)
        self.assertEqual(result.total_accepted, 1)
        self.assertEqual(result.total_rejected, 1)
        self.assertEqual(len(result.iterations), 1)

    def test_two_rounds(self):
        plan = _plan_with_blocked()
        rounds = [
            [UserDecision("ch_1", "accept")],
            [UserDecision("ch_3", "accept")],
        ]
        result = run_review_loop(plan, rounds)
        self.assertTrue(result.is_complete)
        self.assertEqual(result.total_accepted, 2)
        self.assertEqual(len(result.iterations), 2)

    def test_incomplete_loop(self):
        plan = _plan_with_blocked()
        rounds = [
            [UserDecision("ch_1", "defer")],
        ]
        result = run_review_loop(plan, rounds)
        self.assertFalse(result.is_complete)
        self.assertTrue(result.requires_further_review)
        self.assertGreater(len(result.unknowns), 0)

    def test_empty_rounds(self):
        plan = _plan_with_blocked()
        rounds = [[]]
        result = run_review_loop(plan, rounds)
        self.assertFalse(result.is_complete)

    def test_final_plan_attached(self):
        plan = _plan_with_blocked()
        rounds = [
            [UserDecision("ch_1", "accept"), UserDecision("ch_3", "accept")],
        ]
        result = run_review_loop(plan, rounds)
        self.assertIsNotNone(result.final_plan)
        self.assertIn("changes", result.final_plan)


class TestSerialization(unittest.TestCase):
    def test_iteration_to_dict(self):
        it = ReviewLoopIteration(decisions_applied=2, changes_accepted=1)
        d = it.to_dict()
        self.assertEqual(d["decisions_applied"], 2)

    def test_result_to_dict(self):
        result = ReviewLoopResult(total_accepted=1, is_complete=True)
        d = result.to_dict()
        self.assertTrue(d["is_complete"])


class TestCLI(unittest.TestCase):
    def test_review_loop_demo_runs(self):
        from kairoskopion.cli import main
        rc = main(["review-loop-demo"])
        self.assertEqual(rc, 0)


class TestReviewLoopWithProtectedCore(unittest.TestCase):
    def test_end_to_end_with_uc1(self):
        from kairoskopion.demo.uc1_runner import run_uc1_demo
        from kairoskopion.schema import RewritePlan

        result = run_uc1_demo(select_candidate_index=0)
        rewrite_data = result.entities.get("rewrite_plan", {})
        plan = RewritePlan.from_dict(rewrite_data)

        blocked = extract_blocked_changes(plan)

        if blocked:
            decisions = [UserDecision(b["change_id"], "accept") for b in blocked]
            updated, iteration = apply_user_decisions(
                plan, decisions,
                protected_core=rewrite_data.get("_core_validation", {}).get(
                    "protected_core_elements", []
                ),
            )
            self.assertEqual(iteration.remaining_blocked, 0)


if __name__ == "__main__":
    unittest.main()
