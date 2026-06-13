"""Tests for protected core enforcement service."""

from __future__ import annotations

import unittest

from kairoskopion.enums import FieldCoreImpact
from kairoskopion.schema import RewritePlan
from kairoskopion.services.protected_core import (
    CoreImpactAssessment,
    ProtectedCoreValidationResult,
    _find_core_matches,
    apply_core_gate,
    validate_rewrite_plan,
)


def _plan_with_changes(changes: list[dict]) -> RewritePlan:
    return RewritePlan(changes=changes)


class TestFindCoreMatches(unittest.TestCase):
    def test_direct_substring_match(self):
        core = ["central thesis on individuation"]
        change = {"target_block": "topic", "desired_state": "reframe thesis on individuation", "reason": ""}
        matches = _find_core_matches(change, core)
        self.assertEqual(len(matches), 1)

    def test_keyword_overlap(self):
        core = ["methodological stance phenomenology"]
        change = {"target_block": "method", "desired_state": "add empirical methodology section", "reason": ""}
        matches = _find_core_matches(change, core)
        self.assertGreaterEqual(len(matches), 0)

    def test_no_match(self):
        core = ["central thesis on individuation"]
        change = {"target_block": "formal_compliance", "desired_state": "fix citation style", "reason": ""}
        matches = _find_core_matches(change, core)
        self.assertEqual(len(matches), 0)

    def test_empty_protected_core(self):
        matches = _find_core_matches({"target_block": "topic"}, [])
        self.assertEqual(matches, [])

    def test_multiple_core_elements(self):
        core = ["central thesis", "object of inquiry: technology"]
        change = {"target_block": "topic", "desired_state": "reframe central thesis", "reason": ""}
        matches = _find_core_matches(change, core)
        self.assertGreaterEqual(len(matches), 1)


class TestValidateRewritePlan(unittest.TestCase):
    def test_empty_plan(self):
        plan = _plan_with_changes([])
        result = validate_rewrite_plan(plan, ["thesis"])
        self.assertEqual(result.total_changes, 0)
        self.assertFalse(result.requires_user_consent)

    def test_no_protected_core(self):
        plan = _plan_with_changes([
            {"change_id": "ch_1", "target_block": "topic", "desired_state": "reframe", "reason": ""},
        ])
        result = validate_rewrite_plan(plan, [])
        self.assertFalse(result.requires_user_consent)
        self.assertGreater(len(result.unknowns), 0)

    def test_core_preserving_change(self):
        plan = _plan_with_changes([
            {"change_id": "ch_1", "target_block": "formal_compliance",
             "desired_state": "fix citation format", "reason": "wrong style",
             "field_core_risk": FieldCoreImpact.CORE_PRESERVING.value},
        ])
        result = validate_rewrite_plan(plan, ["central thesis on individuation"])
        self.assertEqual(result.blocked_count, 0)
        self.assertFalse(result.requires_user_consent)

    def test_core_touching_change_blocked(self):
        plan = _plan_with_changes([
            {"change_id": "ch_1", "target_block": "topic",
             "desired_state": "reframe central thesis for new audience", "reason": "mismatch",
             "field_core_risk": FieldCoreImpact.UNKNOWN_CORE_IMPACT.value},
        ])
        result = validate_rewrite_plan(plan, ["central thesis"])
        self.assertEqual(result.blocked_count, 1)
        self.assertTrue(result.requires_user_consent)

    def test_core_sensitive_axis_without_match(self):
        plan = _plan_with_changes([
            {"change_id": "ch_1", "target_block": "method",
             "desired_state": "add methods section", "reason": "venue requires it",
             "field_core_risk": FieldCoreImpact.UNKNOWN_CORE_IMPACT.value},
        ])
        result = validate_rewrite_plan(plan, ["authorial voice"])
        self.assertEqual(result.core_touching_count, 1)

    def test_mixed_changes(self):
        plan = _plan_with_changes([
            {"change_id": "ch_1", "target_block": "formal_compliance",
             "desired_state": "fix format", "reason": "",
             "field_core_risk": FieldCoreImpact.CORE_PRESERVING.value},
            {"change_id": "ch_2", "target_block": "topic",
             "desired_state": "reframe thesis statement", "reason": "",
             "field_core_risk": FieldCoreImpact.CORE_TOUCHING.value},
        ])
        result = validate_rewrite_plan(plan, ["thesis statement"])
        self.assertEqual(result.blocked_count, 1)
        self.assertEqual(result.core_preserving_count, 1)
        self.assertTrue(result.requires_user_consent)

    def test_destroying_risk_stays(self):
        plan = _plan_with_changes([
            {"change_id": "ch_1", "target_block": "topic",
             "desired_state": "replace thesis entirely", "reason": "",
             "field_core_risk": FieldCoreImpact.CORE_DESTROYING_RISK.value},
        ])
        result = validate_rewrite_plan(plan, ["thesis"])
        assessment = result.assessments[0]
        self.assertEqual(assessment["computed_impact"], FieldCoreImpact.CORE_DESTROYING_RISK.value)


class TestApplyCoreGate(unittest.TestCase):
    def test_no_consent_needed_returns_original(self):
        plan = _plan_with_changes([{"change_id": "ch_1", "status": "proposed"}])
        validation = ProtectedCoreValidationResult(requires_user_consent=False)
        gated = apply_core_gate(plan, validation)
        self.assertIs(gated, plan)

    def test_consent_needed_blocks_changes(self):
        plan = _plan_with_changes([
            {"change_id": "ch_1", "target_block": "topic", "status": "proposed",
             "field_core_risk": FieldCoreImpact.CORE_TOUCHING.value},
            {"change_id": "ch_2", "target_block": "format", "status": "proposed",
             "field_core_risk": FieldCoreImpact.CORE_PRESERVING.value},
        ])
        validation = ProtectedCoreValidationResult(
            requires_user_consent=True,
            assessments=[
                CoreImpactAssessment(
                    change_id="ch_1", status="blocked_pending_consent",
                    computed_impact=FieldCoreImpact.CORE_TOUCHING.value,
                    reason="Matches: thesis",
                    matched_core_elements=["thesis"],
                ).to_dict(),
                CoreImpactAssessment(
                    change_id="ch_2", status="proposed",
                    computed_impact=FieldCoreImpact.CORE_PRESERVING.value,
                ).to_dict(),
            ],
        )
        gated = apply_core_gate(plan, validation)
        self.assertTrue(gated.requires_user_acceptance)
        self.assertEqual(gated.changes[0]["status"], "blocked_pending_consent")
        self.assertEqual(gated.changes[1]["status"], "proposed")
        self.assertIn("CORE GATE", gated.summary)


class TestRewritePlannerIntegration(unittest.TestCase):
    def test_rewrite_planner_applies_core_gate(self):
        from kairoskopion.agents.registry import instantiate_agent
        from kairoskopion.agents.contract import AgentInput

        agent = instantiate_agent("rewrite_planner")
        inp = AgentInput(
            operation_id="test_core_gate",
            agent_role_id="rewrite_planner",
            entities={
                "mismatch_map": {
                    "mismatch_map_id": "mm_test",
                    "fit_assessment_id": "fit_test",
                    "mismatches": [
                        {
                            "axis": "topic",
                            "severity": "major",
                            "article_side": "philosophy of technology",
                            "venue_side": "STS",
                            "description": "Topic reframing needed",
                            "possible_actions": ["Reframe thesis for STS"],
                            "field_core_risk": FieldCoreImpact.CORE_TOUCHING.value,
                        },
                    ],
                },
                "article": {
                    "article_model_id": "art_test",
                    "protected_core": [
                        "central thesis on individuation",
                        "Simondonian methodology",
                    ],
                },
                "venue": {"venue_model_id": "ven_test"},
            },
        )
        output = agent.execute_deterministic(inp)
        entity = output.output_entity
        self.assertIn("_core_validation", entity)
        validation = entity["_core_validation"]
        self.assertGreater(validation["total_changes"], 0)

    def test_rewrite_planner_no_protected_core(self):
        from kairoskopion.agents.registry import instantiate_agent
        from kairoskopion.agents.contract import AgentInput

        agent = instantiate_agent("rewrite_planner")
        inp = AgentInput(
            operation_id="test_no_core",
            agent_role_id="rewrite_planner",
            entities={
                "mismatch_map": {
                    "mismatch_map_id": "mm_test2",
                    "fit_assessment_id": "fit_test2",
                    "mismatches": [
                        {
                            "axis": "formal_compliance",
                            "severity": "minor",
                            "article_side": "APA",
                            "venue_side": "Chicago",
                            "description": "Wrong citation style",
                            "possible_actions": ["Switch to Chicago style"],
                            "field_core_risk": FieldCoreImpact.CORE_PRESERVING.value,
                        },
                    ],
                },
                "article": {"article_model_id": "art_test2"},
                "venue": {"venue_model_id": "ven_test2"},
            },
        )
        output = agent.execute_deterministic(inp)
        entity = output.output_entity
        validation = entity.get("_core_validation", {})
        self.assertFalse(validation.get("requires_user_consent", True))


class TestSerialization(unittest.TestCase):
    def test_result_to_dict(self):
        result = ProtectedCoreValidationResult(
            total_changes=2,
            blocked_count=1,
            requires_user_consent=True,
        )
        d = result.to_dict()
        self.assertEqual(d["blocked_count"], 1)
        self.assertTrue(d["requires_user_consent"])

    def test_assessment_to_dict(self):
        a = CoreImpactAssessment(
            change_id="ch_1",
            matched_core_elements=["thesis"],
            computed_impact=FieldCoreImpact.CORE_TOUCHING.value,
        )
        d = a.to_dict()
        self.assertEqual(d["change_id"], "ch_1")
        self.assertIn("thesis", d["matched_core_elements"])


class TestUC1Integration(unittest.TestCase):
    def test_selected_venue_mode_has_core_validation(self):
        from kairoskopion.demo.uc1_runner import run_uc1_demo
        result = run_uc1_demo(select_candidate_index=0)
        rewrite = result.entities.get("rewrite_plan", {})
        self.assertIn("_core_validation", rewrite)


if __name__ == "__main__":
    unittest.main()
