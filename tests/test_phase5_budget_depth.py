"""Phase 5: Depth mode & budget controls."""

from __future__ import annotations

import unittest

from kairoskopion.api.cases import Case, _case_to_snapshot, _case_from_snapshot


class TestDepthMode(unittest.TestCase):
    def test_default_is_standard(self):
        case = Case(case_id="test_dm", user_id="u1")
        self.assertEqual(case.depth_mode, "standard")

    def test_set_valid_mode(self):
        case = Case(case_id="test_dm2", user_id="u1")
        result = case.set_depth_mode("deep")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(case.depth_mode, "deep")

    def test_set_invalid_mode(self):
        case = Case(case_id="test_dm3", user_id="u1")
        result = case.set_depth_mode("turbo")
        self.assertEqual(result["status"], "invalid")
        self.assertIn("valid_modes", result)

    def test_all_modes_accepted(self):
        for mode in ("quick", "standard", "deep", "exhaustive"):
            case = Case(case_id=f"test_dm_{mode}", user_id="u1")
            result = case.set_depth_mode(mode)
            self.assertEqual(result["status"], "ok")


class TestBudgetConstraints(unittest.TestCase):
    def test_set_budget(self):
        case = Case(case_id="test_bc", user_id="u1")
        result = case.set_budget_constraints(max_api_calls=5, max_tokens=10000)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(case.budget_constraints["max_api_calls"], 5)

    def test_budget_partial(self):
        case = Case(case_id="test_bc2", user_id="u1")
        result = case.set_budget_constraints(max_api_calls=3)
        self.assertIsNone(result["budget_constraints"]["max_tokens"])


class TestCostEstimate(unittest.TestCase):
    def test_default_profile(self):
        case = Case(case_id="test_ce", user_id="u1")
        result = case.get_cost_estimate()
        self.assertEqual(result["depth_mode"], "standard")
        self.assertIn("profile", result)

    def test_quick_mode_no_external(self):
        case = Case(case_id="test_ce2", user_id="u1")
        case.set_depth_mode("quick")
        result = case.get_cost_estimate()
        self.assertEqual(result["profile"]["adapter_calls"], 0)
        self.assertEqual(result["profile"]["llm_calls"], 0)

    def test_budget_caps_adapter_calls(self):
        case = Case(case_id="test_ce3", user_id="u1")
        case.set_depth_mode("exhaustive")
        case.set_budget_constraints(max_api_calls=2)
        result = case.get_cost_estimate()
        self.assertLessEqual(result["profile"]["adapter_calls"], 2)

    def test_deep_mode_profile(self):
        case = Case(case_id="test_ce4", user_id="u1")
        case.set_depth_mode("deep")
        result = case.get_cost_estimate()
        self.assertGreater(result["profile"]["adapter_calls"], 0)
        self.assertGreater(result["profile"]["llm_calls"], 0)


class TestPhase5Persistence(unittest.TestCase):
    def test_depth_mode_roundtrip(self):
        case = Case(case_id="test_p5_rt", user_id="u1")
        case.set_depth_mode("deep")
        snap = _case_to_snapshot(case)
        restored = _case_from_snapshot(snap)
        self.assertEqual(restored.depth_mode, "deep")

    def test_budget_roundtrip(self):
        case = Case(case_id="test_p5_rt2", user_id="u1")
        case.set_budget_constraints(max_api_calls=10, max_tokens=50000)
        snap = _case_to_snapshot(case)
        restored = _case_from_snapshot(snap)
        self.assertIsNotNone(restored.budget_constraints)
        self.assertEqual(restored.budget_constraints["max_api_calls"], 10)

    def test_default_not_serialized(self):
        case = Case(case_id="test_p5_rt3", user_id="u1")
        snap = _case_to_snapshot(case)
        self.assertNotIn("depth_mode", snap)
        self.assertNotIn("budget_constraints", snap)


if __name__ == "__main__":
    unittest.main()
