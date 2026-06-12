"""Tests for workflow specs and orchestrator."""

from __future__ import annotations

import unittest

from kairoskopion.agents.orchestrator import run_workflow
from kairoskopion.agents.workflows import (
    DIRECT_MANUSCRIPT_VENUE_FIT,
    REVIEW_LOOP,
    UC1_DRAFT_TO_VENUE_POOL_POSITIONING,
    VENUE_DEEP_PROFILE,
    WORKFLOW_REGISTRY,
    get_workflow_spec,
    list_workflow_ids,
    list_workflow_specs,
)


class TestWorkflowRegistry(unittest.TestCase):
    def test_four_workflows(self):
        self.assertEqual(len(list_workflow_ids()), 4)

    def test_ids(self):
        ids = set(list_workflow_ids())
        self.assertIn("direct_manuscript_venue_fit", ids)
        self.assertIn("uc1_draft_to_venue_pool_positioning", ids)
        self.assertIn("venue_deep_profile", ids)
        self.assertIn("review_loop", ids)

    def test_get_known(self):
        wf = get_workflow_spec("venue_deep_profile")
        self.assertEqual(wf.workflow_id, "venue_deep_profile")
        self.assertEqual(len(wf.steps), 3)

    def test_get_unknown(self):
        with self.assertRaises(KeyError):
            get_workflow_spec("nonexistent")

    def test_all_steps_reference_known_agents(self):
        from kairoskopion.agents.registry import list_agent_ids
        known = set(list_agent_ids())
        for wf in list_workflow_specs():
            for step_dict in wf.steps:
                role_id = step_dict["agent_role_id"]
                self.assertIn(role_id, known, f"{wf.workflow_id} step refs unknown agent {role_id}")

    def test_uc1_step_count(self):
        wf = UC1_DRAFT_TO_VENUE_POOL_POSITIONING
        self.assertEqual(len(wf.steps), 12)

    def test_review_loop_skeleton(self):
        self.assertEqual(REVIEW_LOOP.implementation_status, "skeleton")

    def test_direct_fit_executable(self):
        self.assertEqual(DIRECT_MANUSCRIPT_VENUE_FIT.implementation_status, "executable")


class TestOrchestratorVenueDeepProfile(unittest.TestCase):
    def test_run_with_minimal_venue(self):
        venue = {"name": "Test Journal", "scope": "broad"}
        result = run_workflow(
            VENUE_DEEP_PROFILE,
            initial_entities={"venue": venue},
        )
        self.assertIn(result.status, ("completed", "partial"))
        self.assertIsInstance(result.step_results, list)
        self.assertTrue(len(result.step_results) > 0)


class TestOrchestratorReviewLoop(unittest.TestCase):
    def test_review_loop_all_contract_only(self):
        result = run_workflow(
            REVIEW_LOOP,
            initial_entities={"article": {}, "venue": {}},
            stop_on_failure=False,
        )
        for sr in result.step_results:
            self.assertIn(sr["status"], ("completed", "skipped"))


if __name__ == "__main__":
    unittest.main()
