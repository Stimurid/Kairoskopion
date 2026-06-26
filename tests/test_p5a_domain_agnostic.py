"""P5A domain-agnostic prompt organ repair tests.

Tracks 13: verifies domain-agnostic doctrine, no-model-memory,
expanded matrix, canonical depth, citation roles, rewrite approval,
compliance freshness across math/biology/semiconductor/philosophy.
"""

from __future__ import annotations

import json
import unittest


# ═══════════════════════════════════════════════════════════════════════
# Shared doctrine constant
# ═══════════════════════════════════════════════════════════════════════

class TestDomainAgnosticDoctrine(unittest.TestCase):
    def test_doctrine_exists_and_has_regimes(self):
        from kairoskopion.prompts.discipline_intent_parsing import (
            _DOMAIN_AGNOSTIC_DOCTRINE,
        )
        self.assertIn("mathematical proof", _DOMAIN_AGNOSTIC_DOCTRINE)
        self.assertIn("experimental measurement", _DOMAIN_AGNOSTIC_DOCTRINE)
        self.assertIn("clinical trial", _DOMAIN_AGNOSTIC_DOCTRINE)
        self.assertIn("simulation", _DOMAIN_AGNOSTIC_DOCTRINE)
        self.assertIn("legal analysis", _DOMAIN_AGNOSTIC_DOCTRINE)

    def test_doctrine_no_philosophy_bias(self):
        from kairoskopion.prompts.discipline_intent_parsing import (
            _DOMAIN_AGNOSTIC_DOCTRINE,
        )
        lower = _DOMAIN_AGNOSTIC_DOCTRINE.lower()
        self.assertNotIn("postphenomenolog", lower)
        self.assertNotIn("ihde", lower)
        self.assertNotIn("verbeek", lower)
        self.assertNotIn("continental theory", lower)

    def test_doctrine_imported_by_all_prompt_families(self):
        from kairoskopion.prompts.discipline_intent_parsing import (
            _DOMAIN_AGNOSTIC_DOCTRINE,
        )
        from kairoskopion.prompts.venue_funnel_planning import (
            VENUE_FUNNEL_FAMILY,
        )
        from kairoskopion.prompts.venue_family_context import (
            VENUE_FAMILY_CONTEXT_FAMILY,
        )
        from kairoskopion.prompts.venue_matrix_assessment import (
            VENUE_MATRIX_FAMILY,
        )
        from kairoskopion.prompts.depth_recommendation import (
            DEPTH_RECOMMENDATION_FAMILY,
        )
        from kairoskopion.prompts.citation_ecology_analysis import (
            CITATION_ECOLOGY_FAMILY,
        )
        from kairoskopion.prompts.rewrite_planning import (
            REWRITE_PLANNING_FAMILY,
        )
        from kairoskopion.prompts.compliance_assessment import (
            COMPLIANCE_ASSESSMENT_FAMILY,
        )
        from kairoskopion.prompts.fit_assessment import (
            FIT_ASSESSMENT_FAMILY,
        )
        from kairoskopion.prompts.mismatch_narrative import (
            MISMATCH_NARRATIVE_FAMILY,
        )

        snippet = "mathematical proof"
        for name, fam in [
            ("venue_funnel", VENUE_FUNNEL_FAMILY),
            ("venue_family_context", VENUE_FAMILY_CONTEXT_FAMILY),
            ("venue_matrix", VENUE_MATRIX_FAMILY),
            ("depth_recommendation", DEPTH_RECOMMENDATION_FAMILY),
            ("citation_ecology", CITATION_ECOLOGY_FAMILY),
            ("rewrite_planning", REWRITE_PLANNING_FAMILY),
            ("compliance_assessment", COMPLIANCE_ASSESSMENT_FAMILY),
            ("fit_assessment", FIT_ASSESSMENT_FAMILY),
            ("mismatch_narrative", MISMATCH_NARRATIVE_FAMILY),
        ]:
            self.assertIn(
                snippet, fam["system_prompt"],
                f"{name} system_prompt missing domain-agnostic doctrine",
            )


# ═══════════════════════════════════════════════════════════════════════
# Venue funnel: no model-memory
# ═══════════════════════════════════════════════════════════════════════

class TestVenueFunnelNoModelMemory(unittest.TestCase):
    def test_prompt_forbids_model_memory(self):
        from kairoskopion.prompts.venue_funnel_planning import (
            VENUE_FUNNEL_FAMILY,
        )
        sys = VENUE_FUNNEL_FAMILY["system_prompt"].lower()
        self.assertIn("not create candidate venue facts from llm training memory", sys)

    def test_schema_requires_source_ref(self):
        from kairoskopion.prompts.venue_funnel_planning import (
            VENUE_FUNNEL_FAMILY,
        )
        schema = VENUE_FUNNEL_FAMILY["output_schema"]
        schema_str = json.dumps(schema)
        self.assertIn("source_ref", schema_str)
        self.assertIn("evidence_status", schema_str)

    def test_validator_flags_missing_source_ref(self):
        from kairoskopion.prompts.venue_funnel_planning import (
            validate_venue_funnel,
        )
        parsed = {
            "known_corpus_candidates": [
                {"venue_ref": "Journal X", "evidence_status": "confirmed"},
            ],
        }
        warnings = validate_venue_funnel(parsed)
        has_source_warning = any("source_ref" in w for w in warnings)
        self.assertTrue(
            has_source_warning,
            f"Expected source_ref warning, got: {warnings}",
        )

    def test_venue_family_context_forbids_model_memory(self):
        from kairoskopion.prompts.venue_family_context import (
            VENUE_FAMILY_CONTEXT_FAMILY,
        )
        sys = VENUE_FAMILY_CONTEXT_FAMILY["system_prompt"].lower()
        self.assertIn(
            "not suggest sibling/competitor venues from llm training memory",
            sys,
        )


# ═══════════════════════════════════════════════════════════════════════
# Venue matrix: 16 axes + evidence markers
# ═══════════════════════════════════════════════════════════════════════

class TestExpandedVenueMatrix(unittest.TestCase):
    def test_schema_has_16_axes(self):
        from kairoskopion.prompts.venue_matrix_assessment import (
            VENUE_MATRIX_FAMILY,
        )
        schema_str = json.dumps(VENUE_MATRIX_FAMILY["output_schema"])
        expected_axes = [
            "topic_object_fit", "field_subfield_fit",
            "epistemic_regime_fit", "method_evidence_fit",
            "genre_container_fit", "audience_fit",
            "language_register_fit", "regional_indexing_fit",
            "citation_ecology_confidence", "evidence_completeness",
            "rewrite_reframe_effort", "protected_core_risk",
            "compliance_uncertainty", "strategic_value",
            "depth_needed", "confidence",
        ]
        for ax in expected_axes:
            self.assertIn(ax, schema_str, f"Missing axis: {ax}")

    def test_evidence_marker_enum(self):
        from kairoskopion.prompts.venue_matrix_assessment import (
            VENUE_MATRIX_FAMILY,
        )
        schema_str = json.dumps(VENUE_MATRIX_FAMILY["output_schema"])
        for marker in [
            "source_evidence", "corpus_evidence",
            "user_input", "llm_inference", "unknown",
        ]:
            self.assertIn(marker, schema_str)

    def test_preliminary_assessment_replaces_semantic(self):
        from kairoskopion.prompts.venue_matrix_assessment import (
            VENUE_MATRIX_FAMILY,
        )
        schema_str = json.dumps(VENUE_MATRIX_FAMILY["output_schema"])
        self.assertNotIn("semantic_assessment", schema_str)


# ═══════════════════════════════════════════════════════════════════════
# Canonical depth modes
# ═══════════════════════════════════════════════════════════════════════

class TestCanonicalDepthModes(unittest.TestCase):
    def test_five_canonical_modes(self):
        from kairoskopion.prompts.depth_recommendation import (
            DEPTH_RECOMMENDATION_FAMILY,
        )
        schema_str = json.dumps(DEPTH_RECOMMENDATION_FAMILY["output_schema"])
        for mode in [
            "quick_scan", "light_profile", "deep_profile",
            "submission_ready", "post_review",
        ]:
            self.assertIn(mode, schema_str)

    def test_no_old_generic_modes(self):
        from kairoskopion.prompts.depth_recommendation import (
            DEPTH_RECOMMENDATION_FAMILY,
        )
        sys = DEPTH_RECOMMENDATION_FAMILY["system_prompt"]
        schema_str = json.dumps(DEPTH_RECOMMENDATION_FAMILY["output_schema"])
        combined = sys + schema_str
        for old_mode in ["exhaustive"]:
            if old_mode in combined:
                context = combined[combined.index(old_mode) - 30:combined.index(old_mode) + 30]
                self.assertNotIn(
                    f'"{old_mode}"', context,
                    f"Old mode '{old_mode}' still used as enum value",
                )

    def test_agent_default_is_light_profile(self):
        from kairoskopion.agents.depth_recommendation import (
            DepthRecommendationAgent,
        )
        from kairoskopion.agents.contract import AgentInput
        agent = DepthRecommendationAgent()
        out = agent.execute_deterministic(AgentInput(
            operation_id="t-depth",
            agent_role_id="depth_recommendation",
            entities={},
        ))
        self.assertEqual(
            out.output_entity["recommended_depth"], "light_profile",
        )


# ═══════════════════════════════════════════════════════════════════════
# Citation role map (12 domain-agnostic roles)
# ═══════════════════════════════════════════════════════════════════════

class TestCitationRoleMap(unittest.TestCase):
    def test_12_roles_in_prompt(self):
        from kairoskopion.prompts.citation_ecology_analysis import (
            CITATION_ECOLOGY_FAMILY,
        )
        sys_prompt = CITATION_ECOLOGY_FAMILY["system_prompt"]
        roles = [
            "background_theory", "method_protocol",
            "evidence_data_source", "proof_theorem_foundation",
            "benchmark_comparison", "contradiction_alternative",
            "standards_regulation_policy", "venue_ecology_bridge",
            "recent_corpus", "field_canon",
            "decorative_padding_risk", "verification_task",
        ]
        for role in roles:
            self.assertIn(role, sys_prompt, f"Missing role: {role}")

    def test_7_gap_categories(self):
        from kairoskopion.prompts.citation_ecology_analysis import (
            CITATION_ECOLOGY_FAMILY,
        )
        schema_str = json.dumps(CITATION_ECOLOGY_FAMILY["output_schema"])
        gaps = [
            "foundation_gap", "recency_gap", "diversity_gap",
            "bridge_gap", "method_gap", "data_gap", "compliance_gap",
        ]
        for gap in gaps:
            self.assertIn(gap, schema_str, f"Missing gap: {gap}")

    def test_no_key_thinkers(self):
        from kairoskopion.prompts.citation_ecology_analysis import (
            CITATION_ECOLOGY_FAMILY,
        )
        schema_str = json.dumps(CITATION_ECOLOGY_FAMILY["output_schema"])
        self.assertNotIn("key_thinkers", schema_str)

    def test_agent_output_has_role_map(self):
        from kairoskopion.agents.citation_ecology import (
            CitationEcologyAgent,
        )
        from kairoskopion.agents.contract import AgentInput
        agent = CitationEcologyAgent()
        out = agent.execute_deterministic(AgentInput(
            operation_id="t-ce",
            agent_role_id="citation_ecology",
            entities={"article": {}, "venue": {}, "bibliography": {}},
        ))
        self.assertIn("citation_role_map", out.output_entity)
        self.assertIn("venue_alignment_assessment", out.output_entity)
        self.assertNotIn("venue_canon_alignment", out.output_entity)


# ═══════════════════════════════════════════════════════════════════════
# Rewrite planner: user approval invariant
# ═══════════════════════════════════════════════════════════════════════

class TestRewriteUserApproval(unittest.TestCase):
    def test_prompt_requires_approval_for_core_risk(self):
        from kairoskopion.prompts.rewrite_planning import (
            REWRITE_PLANNING_FAMILY,
        )
        sys = REWRITE_PLANNING_FAMILY["system_prompt"].lower()
        self.assertIn("requires_user_approval", sys)

    def test_validator_catches_unapproved_core_risk(self):
        from kairoskopion.prompts.rewrite_planning import (
            validate_rewrite_plan,
        )
        parsed = {
            "rewrite_plan": [
                {
                    "change_id": "c1",
                    "field_core_risk": "high",
                    "requires_user_approval": False,
                },
            ],
        }
        warnings = validate_rewrite_plan(parsed)
        has_approval_warning = any("approval" in w.lower() for w in warnings)
        self.assertTrue(
            has_approval_warning,
            f"Expected approval warning for high-risk change, got: {warnings}",
        )

    def test_schema_has_reframe_candidates(self):
        from kairoskopion.prompts.rewrite_planning import (
            REWRITE_PLANNING_FAMILY,
        )
        schema_str = json.dumps(REWRITE_PLANNING_FAMILY["output_schema"])
        self.assertIn("reframe_candidates", schema_str)
        self.assertIn("patch_queue_readiness", schema_str)


# ═══════════════════════════════════════════════════════════════════════
# Compliance freshness & submission pack lifecycle
# ═══════════════════════════════════════════════════════════════════════

class TestComplianceFreshness(unittest.TestCase):
    def test_schema_has_lifecycle_fields(self):
        from kairoskopion.prompts.compliance_assessment import (
            COMPLIANCE_ASSESSMENT_FAMILY,
        )
        schema_str = json.dumps(
            COMPLIANCE_ASSESSMENT_FAMILY["output_schema"],
        )
        for field in [
            "source_freshness_status",
            "missing_policy_areas",
            "privacy_warnings",
            "export_safety_warnings",
            "submission_pack_readiness",
            "user_decisions_required",
        ]:
            self.assertIn(field, schema_str, f"Missing field: {field}")

    def test_validator_catches_stale_but_ready(self):
        from kairoskopion.prompts.compliance_assessment import (
            validate_compliance_assessment,
        )
        parsed = {
            "source_freshness_status": "stale",
            "submission_pack_readiness": "ready",
        }
        warnings = validate_compliance_assessment(parsed)
        has_stale_warning = any(
            "stale" in w.lower() or "freshness" in w.lower()
            for w in warnings
        )
        self.assertTrue(
            has_stale_warning,
            f"Expected stale+ready warning, got: {warnings}",
        )

    def test_agent_output_has_lifecycle(self):
        from kairoskopion.agents.compliance_assessor import (
            ComplianceAssessorAgent,
        )
        from kairoskopion.agents.contract import AgentInput
        agent = ComplianceAssessorAgent()
        out = agent.execute_deterministic(AgentInput(
            operation_id="t-comp",
            agent_role_id="compliance_assessor",
            entities={"article": {}, "venue": {},
                      "structural_checklist": {}},
        ))
        self.assertIn("semantic_pass", out.output_entity)
        self.assertEqual(out.output_entity["semantic_pass"], False)


# ═══════════════════════════════════════════════════════════════════════
# Multi-domain agent fallback tests
# ═══════════════════════════════════════════════════════════════════════

class TestMultiDomainAgentFallback(unittest.TestCase):
    """Verify agents work for math, bio, semiconductor, philosophy."""

    def _run_discipline_intent(self, intent_text: str):
        from kairoskopion.agents.discipline_intent_parser import (
            DisciplineIntentParserAgent,
        )
        from kairoskopion.agents.contract import AgentInput
        agent = DisciplineIntentParserAgent()
        return agent.execute_deterministic(AgentInput(
            operation_id="t-multi",
            agent_role_id="discipline_intent_parser",
            entities={},
            user_constraints={"intent_text": intent_text},
        ))

    def test_math_intent(self):
        out = self._run_discipline_intent(
            "Proof of ergodic theorem for random matrices",
        )
        self.assertEqual(out.confidence, "none")
        self.assertIn("needs_llm", str(out.output_entity))

    def test_biology_intent(self):
        out = self._run_discipline_intent(
            "CRISPR-Cas9 off-target effects in zebrafish embryos",
        )
        self.assertEqual(out.confidence, "none")

    def test_semiconductor_intent(self):
        out = self._run_discipline_intent(
            "GaN HEMT thermal management in 5G base stations",
        )
        self.assertEqual(out.confidence, "none")

    def test_philosophy_intent(self):
        out = self._run_discipline_intent(
            "Postphenomenological analysis of AI-mediated perception",
        )
        self.assertEqual(out.confidence, "none")


if __name__ == "__main__":
    unittest.main()
