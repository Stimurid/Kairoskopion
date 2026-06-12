"""Tests for agent shell modules — deterministic execution paths."""

from __future__ import annotations

import unittest

from kairoskopion.agents.contract import AgentInput, AgentOutput
from kairoskopion.agents.registry import instantiate_agent


def _make_input(role_id: str, **kwargs) -> AgentInput:
    return AgentInput(
        operation_id="test_op",
        agent_role_id=role_id,
        **kwargs,
    )


class TestControlShells(unittest.TestCase):
    def test_intent_classifier(self):
        agent = instantiate_agent("intent_classifier")
        out = agent.execute_deterministic(
            _make_input("intent_classifier", raw_text="I have a paper about neural networks")
        )
        self.assertIsInstance(out, AgentOutput)
        self.assertIn(out.output_entity_type, ("Intent", "IntentClassification"))
        self.assertTrue("intent" in out.output_entity or "intent_type" in out.output_entity)

    def test_scenario_prober(self):
        agent = instantiate_agent("scenario_prober")
        out = agent.execute_deterministic(
            _make_input("scenario_prober", raw_text="Submit to Nature by March")
        )
        self.assertIsInstance(out, AgentOutput)

    def test_research_planner(self):
        agent = instantiate_agent("research_planner")
        out = agent.execute_deterministic(
            _make_input("research_planner", entities={"article": {"title": "test"}})
        )
        self.assertIsInstance(out, AgentOutput)

    def test_status_job(self):
        agent = instantiate_agent("status_job")
        out = agent.execute_deterministic(
            _make_input("status_job", entities={"article": {"title": "t"}, "venue": None})
        )
        self.assertIsInstance(out, AgentOutput)
        self.assertEqual(out.output_entity_type, "StatusReport")


class TestVenueShells(unittest.TestCase):
    def test_venue_identifier(self):
        agent = instantiate_agent("venue_identifier")
        out = agent.execute_deterministic(
            _make_input("venue_identifier", raw_text="Nature Communications")
        )
        self.assertIsInstance(out, AgentOutput)
        self.assertIn(out.output_entity_type, ("VenueModel", "VenueIdentification"))

    def test_venue_discovery(self):
        agent = instantiate_agent("venue_discovery")
        pathway = {
            "pathway_id": "dp_test",
            "discipline_name": "Computer Science",
            "subdisciplines": ["Machine Learning"],
            "confidence": "medium",
        }
        out = agent.execute_deterministic(
            _make_input("venue_discovery", entities={"pathways": [pathway]})
        )
        self.assertIsInstance(out, AgentOutput)

    def test_venue_discovery_missing_input(self):
        agent = instantiate_agent("venue_discovery")
        out = agent.execute_deterministic(
            _make_input("venue_discovery", entities={})
        )
        self.assertEqual(out.confidence, "none")

    def test_publication_regime_classifier(self):
        agent = instantiate_agent("publication_regime_classifier")
        venue = {"name": "Test Journal", "oa_status": "gold", "review_type": "double_blind"}
        out = agent.execute_deterministic(
            _make_input("publication_regime_classifier", entities={"venue": venue})
        )
        self.assertIsInstance(out, AgentOutput)

    def test_venue_publication_profile_builder(self):
        agent = instantiate_agent("venue_publication_profile_builder")
        venue = {"name": "Test Journal", "scope": "broad"}
        out = agent.execute_deterministic(
            _make_input("venue_publication_profile_builder", entities={"venue": venue})
        )
        self.assertIsInstance(out, AgentOutput)


class TestFitShells(unittest.TestCase):
    def test_mismatch_mapper_missing_input(self):
        agent = instantiate_agent("mismatch_mapper")
        out = agent.execute_deterministic(
            _make_input("mismatch_mapper", entities={})
        )
        self.assertEqual(out.confidence, "none")

    def test_rewrite_planner_missing_input(self):
        agent = instantiate_agent("rewrite_planner")
        out = agent.execute_deterministic(
            _make_input("rewrite_planner", entities={})
        )
        self.assertEqual(out.confidence, "none")

    def test_citation_planner_missing_input(self):
        agent = instantiate_agent("citation_planner")
        out = agent.execute_deterministic(
            _make_input("citation_planner", entities={})
        )
        self.assertEqual(out.confidence, "none")


class TestSubmissionShells(unittest.TestCase):
    def test_risk_officer_missing_input(self):
        agent = instantiate_agent("risk_officer")
        out = agent.execute_deterministic(
            _make_input("risk_officer", entities={})
        )
        self.assertEqual(out.confidence, "none")

    def test_compliance_auditor_missing_input(self):
        agent = instantiate_agent("compliance_auditor")
        out = agent.execute_deterministic(
            _make_input("compliance_auditor", entities={})
        )
        self.assertEqual(out.confidence, "none")

    def test_submission_pack_builder_missing_input(self):
        agent = instantiate_agent("submission_pack_builder")
        out = agent.execute_deterministic(
            _make_input("submission_pack_builder", entities={})
        )
        self.assertEqual(out.confidence, "none")


class TestReviewShells(unittest.TestCase):
    """Review layer: all contract-only stubs."""

    REVIEW_AGENTS = [
        "reviewer_simulation",
        "review_outcome_analyst",
        "revision_planner",
        "rebuttal_architect",
        "tacit_signal_structurer",
        "venue_memory_keeper",
    ]

    def test_all_contract_only(self):
        for role_id in self.REVIEW_AGENTS:
            agent = instantiate_agent(role_id)
            out = agent.execute_deterministic(
                _make_input(role_id, entities={})
            )
            self.assertEqual(out.confidence, "none", f"{role_id}")
            self.assertEqual(out.evidence_status, "INACCESSIBLE", f"{role_id}")
            self.assertTrue(
                out.output_entity.get("_contract_only"),
                f"{role_id} should be contract_only",
            )


class TestEvidenceShell(unittest.TestCase):
    def test_evidence_auditor_missing_input(self):
        agent = instantiate_agent("evidence_auditor")
        out = agent.execute_deterministic(
            _make_input("evidence_auditor", entities={})
        )
        self.assertEqual(out.confidence, "none")


if __name__ == "__main__":
    unittest.main()
