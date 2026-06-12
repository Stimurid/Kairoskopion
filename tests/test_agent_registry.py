"""Tests for agent registry."""

from __future__ import annotations

import unittest

from kairoskopion.agents.registry import (
    AGENT_SPEC_REGISTRY,
    get_agent_class,
    get_agent_spec,
    instantiate_agent,
    list_agent_ids,
    list_agent_specs,
)


class TestAgentRegistry(unittest.TestCase):
    def test_all_specs_have_role_id(self):
        for spec in list_agent_specs():
            self.assertTrue(spec.role_id, f"Empty role_id in spec: {spec}")

    def test_all_specs_have_layer(self):
        for spec in list_agent_specs():
            self.assertIn(
                spec.layer,
                {"control", "article", "venue", "fit", "submission", "review", "evidence"},
                f"Invalid layer for {spec.role_id}: {spec.layer}",
            )

    def test_all_specs_have_valid_implementation_status(self):
        valid = {"operational_now", "executable_stub", "prompt_only", "contract_only", "future"}
        for spec in list_agent_specs():
            self.assertIn(
                spec.implementation_status, valid,
                f"Invalid status for {spec.role_id}: {spec.implementation_status}",
            )

    def test_all_specs_have_valid_execution_mode(self):
        valid = {"deterministic", "llm_optional", "llm_required", "contract_only"}
        for spec in list_agent_specs():
            self.assertIn(
                spec.execution_mode, valid,
                f"Invalid mode for {spec.role_id}: {spec.execution_mode}",
            )

    def test_spec_count(self):
        ids = list_agent_ids()
        self.assertGreaterEqual(len(ids), 26)

    def test_registry_dict_matches_list(self):
        specs = list_agent_specs()
        self.assertEqual(len(specs), len(AGENT_SPEC_REGISTRY))
        for spec in specs:
            self.assertIn(spec.role_id, AGENT_SPEC_REGISTRY)

    def test_get_agent_spec_known(self):
        spec = get_agent_spec("article_modeler")
        self.assertEqual(spec.role_id, "article_modeler")
        self.assertEqual(spec.layer, "article")

    def test_get_agent_spec_unknown(self):
        with self.assertRaises(KeyError):
            get_agent_spec("nonexistent_agent")

    def test_get_agent_class_known(self):
        cls = get_agent_class("article_modeler")
        self.assertTrue(hasattr(cls, "role_id"))

    def test_get_agent_class_unknown(self):
        with self.assertRaises(KeyError):
            get_agent_class("nonexistent_agent")

    def test_instantiate_all_agents(self):
        for role_id in list_agent_ids():
            agent = instantiate_agent(role_id)
            self.assertEqual(agent.role_id, role_id)

    def test_no_duplicate_role_ids(self):
        ids = list_agent_ids()
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_spec_has_matching_class(self):
        for role_id in list_agent_ids():
            cls = get_agent_class(role_id)
            self.assertIsNotNone(cls)


class TestAgentLayers(unittest.TestCase):
    def test_control_layer(self):
        control = [s for s in list_agent_specs() if s.layer == "control"]
        ids = {s.role_id for s in control}
        self.assertIn("intent_classifier", ids)
        self.assertIn("scenario_prober", ids)
        self.assertIn("research_planner", ids)
        self.assertIn("status_job", ids)

    def test_review_layer_all_contract_only(self):
        review = [s for s in list_agent_specs() if s.layer == "review"]
        for s in review:
            self.assertEqual(
                s.implementation_status, "contract_only",
                f"{s.role_id} should be contract_only"
            )

    def test_evidence_layer(self):
        evidence = [s for s in list_agent_specs() if s.layer == "evidence"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].role_id, "evidence_auditor")


if __name__ == "__main__":
    unittest.main()
