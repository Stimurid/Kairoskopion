"""Tests for reference verification service and agent."""

from __future__ import annotations

import json
import unittest

from kairoskopion.schema import BibliographyProfile, ReferenceItem
from kairoskopion.services.reference_verification import (
    ReferenceVerificationResult,
    _assess_padding_risk,
    _compute_aggregate_metrics,
    verify_references,
)
from kairoskopion.source_authority import CitationIntegrityCheck


class TestPaddingRiskHeuristic(unittest.TestCase):
    def test_no_doi_no_title_no_venue_is_high(self):
        ref = {"doi": None, "title_fragment": "", "venue_fragment": "", "source_kind": "unknown"}
        self.assertEqual(_assess_padding_risk(ref), "high")

    def test_unknown_kind_no_venue_no_doi_is_medium(self):
        ref = {"doi": None, "title_fragment": "Some title", "venue_fragment": "", "source_kind": "unknown"}
        self.assertEqual(_assess_padding_risk(ref), "medium")

    def test_web_source_short_raw_is_medium(self):
        ref = {"doi": None, "title_fragment": "t", "venue_fragment": "v", "source_kind": "web_source", "raw_text": "http://x.com"}
        self.assertEqual(_assess_padding_risk(ref), "medium")

    def test_normal_reference_is_low(self):
        ref = {"doi": "10.1234/test", "title_fragment": "A study", "venue_fragment": "Nature", "source_kind": "journal_article"}
        self.assertEqual(_assess_padding_risk(ref), "low")

    def test_no_doi_but_has_title_and_venue_is_low(self):
        ref = {"doi": None, "title_fragment": "A study of things", "venue_fragment": "Good Journal", "source_kind": "journal_article"}
        self.assertEqual(_assess_padding_risk(ref), "low")


class TestVerifyReferences(unittest.TestCase):
    def _make_profile(self, refs: list[dict]) -> BibliographyProfile:
        return BibliographyProfile(
            total_references=len(refs),
            references=refs,
        )

    def test_empty_references(self):
        profile = self._make_profile([])
        result = verify_references(profile)
        self.assertEqual(result.total_references, 0)
        self.assertEqual(len(result.checks), 0)
        self.assertIn("No references to verify", result.unknowns)

    def test_reference_with_doi_resolves_or_not(self):
        refs = [{"reference_item_id": "ref_001", "doi": "10.2307/2183914", "author_fragment": "Nagel"}]
        profile = self._make_profile(refs)
        result = verify_references(profile)
        self.assertEqual(result.total_references, 1)
        self.assertEqual(result.doi_present_count, 1)
        self.assertEqual(len(result.checks), 1)
        check = result.checks[0]
        self.assertIn(check["doi_resolution_status"], ("resolved", "not_found"))

    def test_reference_without_doi(self):
        refs = [{"reference_item_id": "ref_002", "doi": None, "author_fragment": "Smith"}]
        profile = self._make_profile(refs)
        result = verify_references(profile)
        self.assertEqual(result.doi_not_in_bibliography, 1)
        check = result.checks[0]
        self.assertEqual(check["doi_resolution_status"], "no_doi")
        self.assertEqual(check["status"], "no_doi")

    def test_retraction_stays_not_checked(self):
        refs = [{"reference_item_id": "ref_003", "doi": "10.1234/test"}]
        profile = self._make_profile(refs)
        result = verify_references(profile)
        check = result.checks[0]
        self.assertEqual(check["retraction_status"], "not_checked")

    def test_pubpeer_stays_not_checked(self):
        refs = [{"reference_item_id": "ref_004", "doi": "10.1234/test"}]
        profile = self._make_profile(refs)
        result = verify_references(profile)
        check = result.checks[0]
        self.assertEqual(check["pubpeer_signal"], "not_checked")

    def test_citation_supports_claim_stays_not_checked(self):
        refs = [{"reference_item_id": "ref_005", "doi": "10.1234/test"}]
        profile = self._make_profile(refs)
        result = verify_references(profile)
        check = result.checks[0]
        self.assertEqual(check["citation_supports_claim"], "not_checked")

    def test_padding_risk_counted(self):
        refs = [
            {"reference_item_id": "ref_010", "doi": None, "title_fragment": "", "venue_fragment": "", "source_kind": "unknown"},
            {"reference_item_id": "ref_011", "doi": "10.1234/x", "title_fragment": "Good", "venue_fragment": "Nature", "source_kind": "journal_article"},
        ]
        profile = self._make_profile(refs)
        result = verify_references(profile)
        self.assertEqual(result.padding_risk_count, 1)

    def test_multiple_references(self):
        refs = [
            {"reference_item_id": "ref_020", "doi": "10.2307/2183914", "author_fragment": "Nagel"},
            {"reference_item_id": "ref_021", "doi": None, "author_fragment": "Smith", "title_fragment": "A Study", "venue_fragment": "J. Phil", "source_kind": "journal_article"},
            {"reference_item_id": "ref_022", "doi": "10.9999/nonexist", "author_fragment": "Doe"},
        ]
        profile = self._make_profile(refs)
        result = verify_references(profile)
        self.assertEqual(result.total_references, 3)
        self.assertEqual(result.doi_present_count, 2)
        self.assertEqual(result.doi_not_in_bibliography, 1)
        self.assertEqual(len(result.checks), 3)


class TestAggregateMetrics(unittest.TestCase):
    def test_zero_references(self):
        result = ReferenceVerificationResult(total_references=0)
        metrics = _compute_aggregate_metrics(result)
        self.assertEqual(metrics["doi_coverage"], 0.0)
        self.assertEqual(metrics["doi_resolution_rate"], 0.0)

    def test_all_resolved(self):
        result = ReferenceVerificationResult(
            total_references=10,
            doi_present_count=8,
            doi_resolved_count=8,
            doi_unresolved_count=0,
        )
        metrics = _compute_aggregate_metrics(result)
        self.assertEqual(metrics["doi_coverage"], 0.8)
        self.assertEqual(metrics["doi_resolution_rate"], 1.0)

    def test_partial_resolution(self):
        result = ReferenceVerificationResult(
            total_references=10,
            doi_present_count=6,
            doi_resolved_count=3,
            doi_unresolved_count=3,
        )
        metrics = _compute_aggregate_metrics(result)
        self.assertEqual(metrics["doi_coverage"], 0.6)
        self.assertEqual(metrics["doi_resolution_rate"], 0.5)

    def test_retraction_and_pubpeer_false(self):
        result = ReferenceVerificationResult(total_references=5)
        metrics = _compute_aggregate_metrics(result)
        self.assertFalse(metrics["retraction_checked"])
        self.assertFalse(metrics["pubpeer_checked"])


class TestResultSerialization(unittest.TestCase):
    def test_to_dict_round_trip(self):
        refs = [{"reference_item_id": "ref_030", "doi": "10.2307/2183914"}]
        profile = BibliographyProfile(total_references=1, references=refs)
        result = verify_references(profile)
        d = result.to_dict()
        self.assertIn("verification_id", d)
        self.assertIn("checks", d)
        self.assertIn("aggregate_metrics", d)
        text = json.dumps(d, default=str)
        self.assertIsInstance(json.loads(text), dict)

    def test_disclaimer_present(self):
        result = ReferenceVerificationResult()
        self.assertIn("Retraction", result.disclaimer)


class TestReferenceVerifierAgent(unittest.TestCase):
    def test_agent_with_raw_text(self):
        from kairoskopion.agents.registry import instantiate_agent
        from kairoskopion.agents.contract import AgentInput

        agent = instantiate_agent("reference_verifier")
        inp = AgentInput(
            operation_id="test_op",
            agent_role_id="reference_verifier",
            raw_text="References\n\nChalmers, D. (1996). The Conscious Mind. Oxford University Press.\n",
        )
        output = agent.execute_deterministic(inp)
        self.assertEqual(output.output_entity_type, "ReferenceVerificationResult")
        self.assertIn("total_references", output.output_entity)

    def test_agent_missing_input(self):
        from kairoskopion.agents.registry import instantiate_agent
        from kairoskopion.agents.contract import AgentInput

        agent = instantiate_agent("reference_verifier")
        inp = AgentInput(
            operation_id="test_op",
            agent_role_id="reference_verifier",
        )
        output = agent.execute_deterministic(inp)
        self.assertEqual(output.confidence, "none")

    def test_agent_with_bibliography_profile(self):
        from kairoskopion.agents.registry import instantiate_agent
        from kairoskopion.agents.contract import AgentInput

        bib = BibliographyProfile(
            total_references=1,
            references=[{"reference_item_id": "ref_040", "doi": "10.2307/2183914", "author_fragment": "Nagel"}],
        )
        agent = instantiate_agent("reference_verifier")
        inp = AgentInput(
            operation_id="test_op",
            agent_role_id="reference_verifier",
            entities={"bibliography_profile": bib.to_dict()},
        )
        output = agent.execute_deterministic(inp)
        self.assertEqual(output.output_entity_type, "ReferenceVerificationResult")
        self.assertGreater(output.output_entity.get("total_references", 0), 0)


class TestCLI(unittest.TestCase):
    def test_verify_references_runs(self):
        from kairoskopion.cli import main
        rc = main(["verify-references"])
        self.assertEqual(rc, 0)


class TestWorkflowIntegration(unittest.TestCase):
    def test_reference_verifier_in_uc1_workflow(self):
        from kairoskopion.agents.workflows import UC1_DRAFT_TO_VENUE_POOL_POSITIONING
        role_ids = [s["agent_role_id"] for s in UC1_DRAFT_TO_VENUE_POOL_POSITIONING.steps]
        self.assertIn("reference_verifier", role_ids)
        idx = role_ids.index("reference_verifier")
        self.assertGreater(idx, role_ids.index("citation_planner"))
        self.assertLess(idx, role_ids.index("risk_officer"))

    def test_discovery_mode_runs_reference_verifier(self):
        from kairoskopion.demo.uc1_runner import run_uc1_demo
        result = run_uc1_demo()
        step_agents = [s.get("agent_role_id") for s in result.step_results]
        self.assertIn("reference_verifier", step_agents)

    def test_selected_venue_mode_runs_reference_verifier(self):
        from kairoskopion.demo.uc1_runner import run_uc1_demo
        result = run_uc1_demo(select_candidate_index=0)
        step_agents = [s.get("agent_role_id") for s in result.step_results]
        self.assertIn("reference_verifier", step_agents)
        ref_step = next(s for s in result.step_results if s.get("agent_role_id") == "reference_verifier")
        self.assertEqual(ref_step["status"], "completed")


if __name__ == "__main__":
    unittest.main()
