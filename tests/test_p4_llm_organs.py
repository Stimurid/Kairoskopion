"""Round III-P4: LLM Organ tests.

5 categories per organ:
  A = fixture success (mock LLM returns valid JSON)
  B = provider unavailable (execute_deterministic or provider raises)
  C = malformed response (LLM returns garbage)
  D = wrapper invoked (agent conforms to AgentRole contract)
  E = anti-zombie invariant (no deterministic semantic fallback)
"""

from __future__ import annotations

import json
import unittest
from typing import Any
from unittest.mock import MagicMock

from kairoskopion.agents.contract import AgentInput, AgentOutput, AgentRole
from kairoskopion.llm.response import LLMResponse


def _mock_provider(parsed: dict[str, Any] | None = None,
                   content: str = "",
                   raises: Exception | None = None) -> MagicMock:
    provider = MagicMock()
    if raises:
        provider.complete.side_effect = raises
    else:
        resp = LLMResponse(
            content=content or json.dumps(parsed or {}),
            parsed=parsed,
            model="test-model",
            input_tokens=100,
            output_tokens=200,
            latency_ms=50.0,
        )
        provider.complete.return_value = resp
    return provider


def _garbage_provider() -> MagicMock:
    """Provider that returns non-JSON garbage."""
    return _mock_provider(parsed=None, content="NOT JSON AT ALL {broken")


def _failing_provider() -> MagicMock:
    return _mock_provider(raises=RuntimeError("provider down"))


# ═══════════════════════════════════════════════════════════════════════
# Organ #1: DisciplineIntentParser
# ═══════════════════════════════════════════════════════════════════════

class TestDisciplineIntentParser(unittest.TestCase):
    def _agent(self):
        from kairoskopion.agents.discipline_intent_parser import (
            DisciplineIntentParserAgent,
        )
        return DisciplineIntentParserAgent()

    def _inp(self, text="philosophy of technology, STS"):
        return AgentInput(
            operation_id="t-1", agent_role_id="discipline_intent_parser",
            raw_text=text,
        )

    # A: fixture success
    def test_a_valid_llm_response(self):
        agent = self._agent()
        provider = _mock_provider(parsed={
            "primary_discipline": "philosophy of technology",
            "subfields": ["STS", "ethics of technology"],
            "intellectual_tradition": "continental",
            "method_orientation": "conceptual",
            "regional_affinity": None,
            "parsed_constraints": [],
            "confidence": "high",
            "unknowns": [],
            "reasoning": "Clear intent.",
        })
        out = agent.execute(self._inp(), provider)
        self.assertEqual(out.output_entity_type, "DisciplineIntentResult")
        self.assertEqual(
            out.output_entity["intent_parse_status"], "parsed",
        )
        self.assertIsNotNone(out.output_entity["parse_result"])

    # B: provider unavailable
    def test_b_provider_unavailable(self):
        agent = self._agent()
        out = agent.execute_deterministic(self._inp())
        self.assertEqual(
            out.output_entity["intent_parse_status"], "needs_llm",
        )
        self.assertIsNone(out.output_entity["parse_result"])

    # B2: provider raises
    def test_b2_provider_raises(self):
        agent = self._agent()
        out = agent.execute(self._inp(), _failing_provider())
        self.assertEqual(
            out.output_entity["intent_parse_status"], "needs_llm",
        )

    # C: malformed response
    def test_c_malformed_response(self):
        agent = self._agent()
        out = agent.execute(self._inp(), _garbage_provider())
        self.assertEqual(
            out.output_entity["intent_parse_status"], "needs_llm",
        )

    # D: wrapper invoked
    def test_d_is_agent_role(self):
        agent = self._agent()
        self.assertIsInstance(agent, AgentRole)
        self.assertEqual(agent.role_id, "discipline_intent_parser")

    # E: anti-zombie
    def test_e_no_deterministic_semantic_fallback(self):
        agent = self._agent()
        out = agent.execute_deterministic(self._inp())
        self.assertIsNone(out.output_entity["parse_result"])
        self.assertEqual(out.confidence, "none")


# ═══════════════════════════════════════════════════════════════════════
# Organ #2: VenueFunnelPlanner
# ═══════════════════════════════════════════════════════════════════════

class TestVenueFunnelPlanner(unittest.TestCase):
    def _agent(self):
        from kairoskopion.agents.venue_funnel_planner import (
            VenueFunnelPlannerAgent,
        )
        return VenueFunnelPlannerAgent()

    def _inp(self):
        return AgentInput(
            operation_id="t-2", agent_role_id="venue_funnel_planner",
            entities={"discipline_intent": {
                "primary_discipline": "STS",
                "subfields": ["philosophy of technology"],
            }},
        )

    def test_a_valid_llm_response(self):
        agent = self._agent()
        provider = _mock_provider(parsed={
            "known_corpus_candidates": [],
            "candidate_families": [
                {"family_descriptor": "STS core",
                 "discipline_zone": "STS",
                 "search_strategy": "OpenAlex STS"},
            ],
            "external_discovery_tasks": [],
            "corpus_coverage_gaps": [],
            "confidence": "medium",
            "unknowns": [],
            "reasoning": "Standard STS mapping.",
        })
        out = agent.execute(self._inp(), provider)
        self.assertEqual(out.output_entity_type, "VenueFunnelPlan")
        self.assertEqual(
            out.output_entity["venue_families_status"], "planned",
        )
        self.assertTrue(
            len(out.output_entity["candidate_families"]) > 0,
        )

    def test_b_provider_unavailable(self):
        agent = self._agent()
        out = agent.execute_deterministic(self._inp())
        self.assertEqual(
            out.output_entity["venue_families_status"],
            "FUNNEL_BLOCKED_NEEDS_LLM",
        )
        self.assertEqual(
            out.output_entity.get("candidate_families",
                                  out.output_entity.get("known_corpus_candidates", [])),
            [],
        )

    def test_c_malformed_response(self):
        agent = self._agent()
        out = agent.execute(self._inp(), _garbage_provider())
        self.assertEqual(
            out.output_entity["venue_families_status"],
            "FUNNEL_BLOCKED_NEEDS_LLM",
        )

    def test_d_is_agent_role(self):
        self.assertIsInstance(self._agent(), AgentRole)

    def test_e_no_deterministic_families(self):
        agent = self._agent()
        out = agent.execute_deterministic(self._inp())
        self.assertEqual(
            out.output_entity["candidate_families"], [],
        )
        self.assertEqual(out.confidence, "none")


# ═══════════════════════════════════════════════════════════════════════
# Organ #3: VenueFamilyContextBuilder
# ═══════════════════════════════════════════════════════════════════════

class TestVenueFamilyContextBuilder(unittest.TestCase):
    def _agent(self):
        from kairoskopion.agents.venue_family_context_builder import (
            VenueFamilyContextBuilderAgent,
        )
        return VenueFamilyContextBuilderAgent()

    def _inp(self):
        return AgentInput(
            operation_id="t-3",
            agent_role_id="venue_family_context_builder",
            entities={"venue": {
                "canonical_name": "Social Studies of Science",
                "scope_summary": "STS journal",
            }},
        )

    def test_a_valid_llm_response(self):
        agent = self._agent()
        provider = _mock_provider(parsed={
            "source_venue": "Social Studies of Science",
            "families": [{"family_name": "STS core",
                          "discipline_zone": "STS",
                          "venue_role_in_family": "flagship",
                          "sibling_venues": ["Science, Technology & HV"]}],
            "families_status": "assessed",
            "confidence": "high",
            "unknowns": [],
            "reasoning": "Well-known STS journal.",
        })
        out = agent.execute(self._inp(), provider)
        self.assertEqual(out.output_entity["families_status"], "assessed")
        self.assertTrue(len(out.output_entity["families"]) > 0)

    def test_b_provider_unavailable(self):
        agent = self._agent()
        out = agent.execute_deterministic(self._inp())
        self.assertEqual(
            out.output_entity["families_status"], "BLOCKED_NEEDS_LLM",
        )

    def test_c_malformed(self):
        agent = self._agent()
        out = agent.execute(self._inp(), _garbage_provider())
        self.assertEqual(
            out.output_entity["families_status"], "BLOCKED_NEEDS_LLM",
        )

    def test_d_is_agent_role(self):
        self.assertIsInstance(self._agent(), AgentRole)

    def test_e_no_deterministic_families(self):
        out = self._agent().execute_deterministic(self._inp())
        self.assertEqual(out.output_entity["families"], [])


# ═══════════════════════════════════════════════════════════════════════
# Organ #4: VenueMatrixAssessor
# ═══════════════════════════════════════════════════════════════════════

class TestVenueMatrixAssessor(unittest.TestCase):
    def _agent(self):
        from kairoskopion.agents.venue_matrix_assessor import (
            VenueMatrixAssessorAgent,
        )
        return VenueMatrixAssessorAgent()

    def _inp(self):
        return AgentInput(
            operation_id="t-4",
            agent_role_id="venue_matrix_assessor",
            entities={
                "candidates": [
                    {"venue_candidate_id": "vc1",
                     "canonical_name": "Test Journal"},
                ],
                "article_context": {"discipline": "STS"},
            },
        )

    def test_a_valid_llm_response(self):
        agent = self._agent()
        provider = _mock_provider(parsed={
            "assessments": [{
                "venue_candidate_id": "vc1",
                "canonical_name": "Test Journal",
                "preliminary_assessment": {
                    "topic_fit": "strong",
                    "discipline_fit": "medium",
                    "core_risk": "weak",
                    "overall_impression": "Partial fit.",
                    "confidence": "medium",
                },
            }],
            "unknowns": [],
        })
        out = agent.execute(self._inp(), provider)
        self.assertEqual(out.output_entity_type, "VenueMatrixAssessment")
        a = out.output_entity["assessments"][0]
        self.assertIsInstance(a["preliminary_assessment"], dict)

    def test_b_provider_unavailable(self):
        agent = self._agent()
        out = agent.execute_deterministic(self._inp())
        a = out.output_entity["assessments"][0]
        self.assertEqual(a["preliminary_assessment"], "NOT_ASSESSED_NEEDS_LLM")

    def test_c_malformed(self):
        agent = self._agent()
        out = agent.execute(self._inp(), _garbage_provider())
        a = out.output_entity["assessments"][0]
        self.assertEqual(a["preliminary_assessment"], "NOT_ASSESSED_NEEDS_LLM")

    def test_d_is_agent_role(self):
        self.assertIsInstance(self._agent(), AgentRole)

    def test_e_no_fake_confidence(self):
        out = self._agent().execute_deterministic(self._inp())
        self.assertEqual(out.confidence, "none")


# ═══════════════════════════════════════════════════════════════════════
# Organ #5: DepthRecommendationAgent
# ═══════════════════════════════════════════════════════════════════════

class TestDepthRecommendation(unittest.TestCase):
    def _agent(self):
        from kairoskopion.agents.depth_recommendation import (
            DepthRecommendationAgent,
        )
        return DepthRecommendationAgent()

    def _inp(self):
        return AgentInput(
            operation_id="t-5",
            agent_role_id="depth_recommendation",
            entities={
                "article_summary": "complex cross-disciplinary article",
                "venue_summary": "STS journal",
            },
            user_constraints={"current_depth": "standard"},
        )

    def test_a_valid_llm_response(self):
        agent = self._agent()
        provider = _mock_provider(parsed={
            "recommended_depth": "deep",
            "reasoning": "Cross-disciplinary needs deeper analysis.",
            "cost_tradeoff": "2x cost vs standard.",
            "confidence": "medium",
            "warnings": [],
        })
        out = agent.execute(self._inp(), provider)
        self.assertEqual(
            out.output_entity["recommended_depth"], "deep",
        )

    def test_b_provider_unavailable(self):
        out = self._agent().execute_deterministic(self._inp())
        self.assertEqual(
            out.output_entity["recommended_depth"], "standard",
        )

    def test_c_malformed(self):
        out = self._agent().execute(self._inp(), _garbage_provider())
        self.assertEqual(
            out.output_entity["recommended_depth"], "standard",
        )

    def test_d_is_agent_role(self):
        self.assertIsInstance(self._agent(), AgentRole)

    def test_e_cost_stays_deterministic(self):
        out = self._agent().execute_deterministic(self._inp())
        self.assertNotIn("cost_estimate", out.output_entity)


# ═══════════════════════════════════════════════════════════════════════
# Organ #6: FitAssessmentOrgan (modified fallback)
# ═══════════════════════════════════════════════════════════════════════

class TestFitAssessmentOrgan(unittest.TestCase):
    def _agent(self):
        from kairoskopion.agents.fit_assessor import FitAssessorAgent
        return FitAssessorAgent()

    def _inp(self):
        return AgentInput(
            operation_id="t-6",
            agent_role_id="fit_assessor",
            entities={
                "article": {"article_model_id": "a1"},
                "venue": {"venue_model_id": "v1"},
                "scenario": {"submission_scenario_id": "s1"},
            },
        )

    def test_a_valid_llm_response(self):
        agent = self._agent()
        provider = _mock_provider(parsed={
            "overall_label": "possible",
            "axes": [
                {"axis": "topic_fit", "value": "strong",
                 "reasoning": "good match"},
            ],
            "unknowns": ["citation data incomplete"],
            "confidence": "medium",
        })
        out = agent.execute(self._inp(), provider)
        self.assertEqual(out.output_entity_type, "FitAssessment")
        self.assertIn("fit_assessment_id", out.output_entity)

    def test_b_provider_raises(self):
        out = self._agent().execute(self._inp(), _failing_provider())
        self.assertEqual(out.output_entity_type, "FitAssessment")
        fit = out.output_entity
        self.assertEqual(fit["overall_label"], "not_enough_data")

    def test_c_malformed(self):
        out = self._agent().execute(self._inp(), _garbage_provider())
        self.assertEqual(out.output_entity["overall_label"], "not_enough_data")

    def test_d_is_agent_role(self):
        self.assertIsInstance(self._agent(), AgentRole)

    def test_e_all_unknown_fallback(self):
        """Anti-zombie: deterministic fallback returns ALL unknown axes,
        not keyword-based semantic values."""
        out = self._agent().execute_deterministic(self._inp())
        axes = out.output_entity.get("axes", [])
        self.assertTrue(len(axes) > 0)
        for ax in axes:
            self.assertEqual(ax["value"], "unknown",
                             f"Axis {ax['axis']} should be 'unknown', "
                             f"got '{ax['value']}'")
        self.assertEqual(out.output_entity["overall_label"], "not_enough_data")
        self.assertEqual(out.confidence, "none")


# ═══════════════════════════════════════════════════════════════════════
# Organ #7: MismatchNarrativeOrgan (existing — verify fallback)
# ═══════════════════════════════════════════════════════════════════════

class TestMismatchNarrativeOrgan(unittest.TestCase):
    def _agent(self):
        from kairoskopion.agents.mismatch_narrator import (
            MismatchNarratorAgent,
        )
        return MismatchNarratorAgent()

    def _inp(self):
        return AgentInput(
            operation_id="t-7",
            agent_role_id="mismatch_narrator",
            entities={
                "article": {"title_current": "Test"},
                "venue": {"canonical_name": "Test Journal"},
                "mismatches": [
                    {"axis": "method", "severity": "weak",
                     "article_side": "conceptual"},
                ],
            },
        )

    def test_a_valid_llm_response(self):
        agent = self._agent()
        provider = _mock_provider(parsed={
            "narratives": [{
                "axis": "method",
                "venue_side": "Venue expects empirical research.",
                "description": "Method mismatch: conceptual vs empirical.",
                "possible_actions": ["Add empirical component."],
            }],
        })
        out = agent.execute(self._inp(), provider)
        narr = out.output_entity["narratives"]
        self.assertEqual(narr[0]["narrative_status"], "llm_filled")

    def test_b_provider_unavailable(self):
        out = self._agent().execute_deterministic(self._inp())
        narr = out.output_entity["narratives"]
        self.assertEqual(narr[0]["narrative_status"], "needs_llm")

    def test_c_malformed(self):
        out = self._agent().execute(self._inp(), _garbage_provider())
        narr = out.output_entity["narratives"]
        self.assertEqual(narr[0]["narrative_status"], "needs_llm")

    def test_d_is_agent_role(self):
        self.assertIsInstance(self._agent(), AgentRole)

    def test_e_no_hardcoded_venue_side(self):
        out = self._agent().execute_deterministic(self._inp())
        for n in out.output_entity["narratives"]:
            self.assertEqual(n["venue_side"], "")
            self.assertEqual(n["possible_actions"], [])


# ═══════════════════════════════════════════════════════════════════════
# Organ #8: RewritePlanOrgan
# ═══════════════════════════════════════════════════════════════════════

class TestRewritePlanOrgan(unittest.TestCase):
    def _agent(self):
        from kairoskopion.agents.rewrite_planner import RewritePlannerAgent
        return RewritePlannerAgent()

    def _inp(self):
        return AgentInput(
            operation_id="t-8",
            agent_role_id="rewrite_planner",
            entities={
                "article": {"title_current": "Test"},
                "venue": {"canonical_name": "Test Journal"},
                "mismatches": [
                    {"axis": "method", "severity": "weak"},
                ],
            },
        )

    def test_a_valid_llm_response(self):
        agent = self._agent()
        provider = _mock_provider(parsed={
            "changes": [{
                "change_id": "rewrite_001",
                "target_block": "method section",
                "change_type": "restructure",
                "description": "Add empirical component.",
                "desired_state": "Mixed-method section.",
                "difficulty": "substantial",
                "field_core_risk": "moderate",
                "status": "proposed",
                "mismatch_axis": "method",
            }],
            "summary": "Method section needs work.",
            "total_estimated_difficulty": "substantial",
            "confidence": "medium",
            "unknowns": [],
        })
        out = agent.execute(self._inp(), provider)
        self.assertEqual(out.output_entity_type, "RewritePlan")
        self.assertTrue(len(out.output_entity["changes"]) > 0)

    def test_b_provider_unavailable(self):
        out = self._agent().execute_deterministic(self._inp())
        self.assertEqual(out.output_entity["changes"], [])
        self.assertEqual(out.output_entity["summary"],
                         "needs_llm_rewrite_planner")

    def test_c_malformed(self):
        out = self._agent().execute(self._inp(), _garbage_provider())
        self.assertEqual(out.output_entity["summary"],
                         "needs_llm_rewrite_planner")

    def test_d_is_agent_role(self):
        self.assertIsInstance(self._agent(), AgentRole)

    def test_e_no_deterministic_changes(self):
        out = self._agent().execute_deterministic(self._inp())
        self.assertEqual(out.output_entity["changes"], [])
        self.assertEqual(out.confidence, "none")


# ═══════════════════════════════════════════════════════════════════════
# Organ #9: CitationEcologyOrgan
# ═══════════════════════════════════════════════════════════════════════

class TestCitationEcologyOrgan(unittest.TestCase):
    def _agent(self):
        from kairoskopion.agents.citation_ecology import (
            CitationEcologyAgent,
        )
        return CitationEcologyAgent()

    def _inp(self):
        return AgentInput(
            operation_id="t-9",
            agent_role_id="citation_ecology",
            entities={
                "article": {"title_current": "Test", "core_claims": []},
                "venue": {"canonical_name": "Test Journal"},
                "bibliography": {"references": []},
                "venue_guidelines": "Submit up to 50 references.",
            },
        )

    def test_a_valid_llm_response(self):
        agent = self._agent()
        provider = _mock_provider(parsed={
            "gaps": [{"gap_id": "g1", "category": "canon_gap",
                      "severity": "significant",
                      "description": "Missing foundational STS refs."}],
            "bridge_references": [],
            "ecology_health": "needs_work",
            "venue_alignment_assessment": "partial",
            "summary": "Bibliography needs STS canon.",
            "confidence": "medium",
            "unknowns": [],
        })
        out = agent.execute(self._inp(), provider)
        self.assertEqual(out.output_entity_type, "CitationEcologyReport")
        self.assertTrue(len(out.output_entity["gaps"]) > 0)

    def test_b_provider_unavailable(self):
        out = self._agent().execute_deterministic(self._inp())
        self.assertEqual(out.output_entity["summary"], "needs_llm")
        self.assertEqual(out.output_entity["gaps"], [])

    def test_c_malformed(self):
        out = self._agent().execute(self._inp(), _garbage_provider())
        self.assertEqual(out.output_entity["summary"], "needs_llm")

    def test_d_is_agent_role(self):
        self.assertIsInstance(self._agent(), AgentRole)

    def test_e_no_fabricated_citations(self):
        out = self._agent().execute_deterministic(self._inp())
        self.assertEqual(out.output_entity["bridge_references"], [])


# ═══════════════════════════════════════════════════════════════════════
# Organ #10: MavrinskySemantic (VPKG 16-axis)
# ═══════════════════════════════════════════════════════════════════════

class TestMavrinskySemantic(unittest.TestCase):
    def _agent(self):
        from kairoskopion.agents.fit_assessor import FitAssessorAgent
        return FitAssessorAgent()

    def _inp(self):
        return AgentInput(
            operation_id="t-10",
            agent_role_id="fit_assessor",
            entities={
                "article": {"article_model_id": "a1"},
                "vpkg": {"venue_model_id": "v1"},
                "corpus_titles": ["Title 1", "Title 2"],
            },
        )

    def test_a_valid_vpkg_response(self):
        agent = self._agent()
        provider = _mock_provider(parsed={
            "overall_label": "possible",
            "axes": [
                {"axis": "topic_fit", "value": "strong",
                 "reasoning": "matches"},
                {"axis": "argument_form_fit", "value": "medium",
                 "reasoning": "acceptable"},
            ],
            "unknowns": [],
            "confidence": "medium",
        })
        out = agent.execute_vpkg(self._inp(), provider)
        self.assertEqual(out.output_entity_type, "FitAssessment")
        self.assertIn("VPKG 16-axis mode", out.trace_notes)

    def test_b_vpkg_provider_fails(self):
        out = self._agent().execute_vpkg(
            self._inp(), _failing_provider(),
        )
        self.assertEqual(out.output_entity["overall_label"], "not_enough_data")

    def test_c_vpkg_malformed(self):
        out = self._agent().execute_vpkg(
            self._inp(), _garbage_provider(),
        )
        self.assertEqual(out.output_entity["overall_label"], "not_enough_data")

    def test_d_execute_vpkg_exists(self):
        self.assertTrue(hasattr(self._agent(), "execute_vpkg"))

    def test_e_no_token_bag_counting(self):
        out = self._agent().execute_deterministic(self._inp())
        for ax in out.output_entity.get("axes", []):
            self.assertEqual(ax["value"], "unknown")


# ═══════════════════════════════════════════════════════════════════════
# Organ #11: VenueRegimeDetector (extended VenueProfiler prompt)
# ═══════════════════════════════════════════════════════════════════════

class TestVenueRegimeDetector(unittest.TestCase):
    def test_a_regime_type_in_schema(self):
        from kairoskopion.prompts.venue_fact_extraction import (
            VENUE_FACT_EXTRACTION_OUTPUT_SCHEMA,
        )
        props = VENUE_FACT_EXTRACTION_OUTPUT_SCHEMA["properties"]
        self.assertIn("regime_type", props)

    def test_b_regime_classification_in_prompt(self):
        from kairoskopion.prompts.venue_fact_extraction import (
            VENUE_FACT_EXTRACTION_SYSTEM,
        )
        self.assertIn("Regime classification", VENUE_FACT_EXTRACTION_SYSTEM)
        self.assertIn("classic_journal_article", VENUE_FACT_EXTRACTION_SYSTEM)

    def test_c_venue_profiler_agent_exists(self):
        from kairoskopion.agents.venue_profiler import VenueProfilerAgent
        self.assertIsInstance(VenueProfilerAgent(), AgentRole)

    def test_d_no_substring_regime_as_semantic(self):
        from kairoskopion.prompts.venue_fact_extraction import (
            VENUE_FACT_EXTRACTION_SYSTEM,
        )
        self.assertIn("Do NOT default to", VENUE_FACT_EXTRACTION_SYSTEM)

    def test_e_regime_enum_values(self):
        from kairoskopion.prompts.venue_fact_extraction import (
            VENUE_FACT_EXTRACTION_OUTPUT_SCHEMA,
        )
        regime_enum = VENUE_FACT_EXTRACTION_OUTPUT_SCHEMA[
            "properties"]["regime_type"]["enum"]
        self.assertIn("classic_journal_article", regime_enum)
        self.assertIn("mega_journal", regime_enum)
        self.assertIn(None, regime_enum)


# ═══════════════════════════════════════════════════════════════════════
# Organ #12: VenuePolicyExtractor (extended VenueProfiler prompt)
# ═══════════════════════════════════════════════════════════════════════

class TestVenuePolicyExtractor(unittest.TestCase):
    def test_a_policy_fields_in_schema(self):
        from kairoskopion.prompts.venue_fact_extraction import (
            VENUE_FACT_EXTRACTION_OUTPUT_SCHEMA,
        )
        props = VENUE_FACT_EXTRACTION_OUTPUT_SCHEMA["properties"]
        for field in ("ai_policy", "data_policy", "ethics_policy",
                      "anonymization_policy", "apc_policy",
                      "open_access_status", "language_policy"):
            self.assertIn(field, props, f"Missing policy field: {field}")

    def test_b_policy_extraction_in_prompt(self):
        from kairoskopion.prompts.venue_fact_extraction import (
            VENUE_FACT_EXTRACTION_SYSTEM,
        )
        self.assertIn("Policy extraction", VENUE_FACT_EXTRACTION_SYSTEM)

    def test_c_negation_handling(self):
        from kairoskopion.prompts.venue_fact_extraction import (
            VENUE_FACT_EXTRACTION_SYSTEM,
        )
        self.assertIn("Negation matters", VENUE_FACT_EXTRACTION_SYSTEM)

    def test_d_venue_profiler_has_all_policy_mapping(self):
        from kairoskopion.agents.venue_profiler import VenueProfilerAgent
        agent = VenueProfilerAgent()
        self.assertEqual(agent.role_id, "venue_profiler")

    def test_e_no_regex_as_semantic(self):
        from kairoskopion.prompts.venue_fact_extraction import (
            VENUE_FACT_EXTRACTION_SYSTEM,
        )
        self.assertIn("Do NOT infer", VENUE_FACT_EXTRACTION_SYSTEM)


# ═══════════════════════════════════════════════════════════════════════
# Organ #13: ComplianceSemanticOrgan
# ═══════════════════════════════════════════════════════════════════════

class TestComplianceSemanticOrgan(unittest.TestCase):
    def _agent(self):
        from kairoskopion.agents.compliance_assessor import (
            ComplianceAssessorAgent,
        )
        return ComplianceAssessorAgent()

    def _inp(self):
        return AgentInput(
            operation_id="t-13",
            agent_role_id="compliance_assessor",
            entities={
                "article": {"title_current": "Test", "language": "en"},
                "venue": {"canonical_name": "Test Journal",
                          "language_policy": "English"},
                "structural_checklist": {
                    "items": [
                        {"item_id": "c1", "field": "abstract",
                         "structural_status": "present"},
                        {"item_id": "c2", "field": "ai_disclosure",
                         "structural_status": "absent"},
                    ],
                },
            },
        )

    def test_a_valid_llm_response(self):
        agent = self._agent()
        provider = _mock_provider(parsed={
            "items": [
                {"item_id": "c1", "field": "abstract",
                 "structural_status": "present",
                 "semantic_status": "satisfied",
                 "reasoning": "Abstract present and meets length.",
                 "severity": "informational"},
                {"item_id": "c2", "field": "ai_disclosure",
                 "structural_status": "absent",
                 "semantic_status": "not_satisfied",
                 "reasoning": "Venue requires AI disclosure.",
                 "severity": "blocking"},
            ],
            "overall_compliance": "non_compliant",
            "summary": "Missing AI disclosure.",
            "confidence": "high",
            "unknowns": [],
        })
        out = agent.execute(self._inp(), provider)
        self.assertEqual(out.output_entity_type, "ComplianceChecklist")
        self.assertTrue(out.output_entity["semantic_pass"])
        self.assertEqual(
            out.output_entity["overall_compliance"], "non_compliant",
        )

    def test_b_provider_unavailable(self):
        out = self._agent().execute_deterministic(self._inp())
        self.assertFalse(out.output_entity["semantic_pass"])
        self.assertEqual(
            out.output_entity["overall_compliance"], "insufficient_data",
        )

    def test_c_malformed(self):
        out = self._agent().execute(self._inp(), _garbage_provider())
        self.assertFalse(out.output_entity["semantic_pass"])

    def test_d_is_agent_role(self):
        self.assertIsInstance(self._agent(), AgentRole)

    def test_e_structural_items_preserved_on_fallback(self):
        out = self._agent().execute_deterministic(self._inp())
        items = out.output_entity.get("items", [])
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["structural_status"], "present")

    def test_e2_absent_never_satisfied(self):
        """Validator catches impossible absent→satisfied."""
        from kairoskopion.prompts.compliance_assessment import (
            validate_compliance_assessment,
        )
        bad_data = {
            "items": [{
                "item_id": "c1", "field": "abstract",
                "structural_status": "absent",
                "semantic_status": "satisfied",
                "severity": "informational",
            }],
            "overall_compliance": "compliant",
            "summary": "ok",
            "confidence": "high",
            "unknowns": [],
        }
        warnings = validate_compliance_assessment(bad_data)
        self.assertTrue(
            any("impossible" in w for w in warnings),
        )


if __name__ == "__main__":
    unittest.main()
