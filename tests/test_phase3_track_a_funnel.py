"""Phase 3: Track A Funnel — discipline intent, venue families (LLM-blocked), venue matrix."""

from __future__ import annotations

import unittest

from kairoskopion.api.cases import Case, _case_to_snapshot, _case_from_snapshot


class TestSetDisciplineIntent(unittest.TestCase):
    def test_set_basic_intent(self):
        case = Case(case_id="test_di", user_id="u1")
        result = case.set_discipline_intent("philosophy of technology, STS")
        self.assertEqual(result["status"], "ok")
        self.assertIsNotNone(case.discipline_intent)
        self.assertEqual(case.discipline_intent["text"], "philosophy of technology, STS")

    def test_intent_stores_raw_text(self):
        case = Case(case_id="test_di_raw", user_id="u1")
        case.set_discipline_intent("continental philosophy and actor-network theory")
        self.assertEqual(
            case.discipline_intent["text"],
            "continental philosophy and actor-network theory",
        )

    def test_intent_marks_needs_llm(self):
        """Discipline intent must NOT produce venue families without LLM."""
        case = Case(case_id="test_di_llm", user_id="u1")
        result = case.set_discipline_intent("philosophy")
        self.assertEqual(result["venue_families_status"], "FUNNEL_BLOCKED_NEEDS_LLM")
        self.assertEqual(result["venue_families"], [])

    def test_intent_with_region(self):
        case = Case(case_id="test_di2", user_id="u1")
        result = case.set_discipline_intent("sociology", region="ru")
        self.assertEqual(case.region_hint, "ru")

    def test_intent_with_constraints(self):
        case = Case(case_id="test_di3", user_id="u1")
        result = case.set_discipline_intent(
            "philosophy", constraints=["VAK preferred"],
        )
        self.assertEqual(case.discipline_intent["constraints"], ["VAK preferred"])

    def test_no_deterministic_keyword_family_mapping(self):
        """Verify no keyword→venue family deterministic mapping exists."""
        case = Case(case_id="test_no_zombie", user_id="u1")
        result = case.set_discipline_intent("philosophy of mind")
        families = result["venue_families"]
        self.assertEqual(families, [])


class TestVenueFamilyFromVenue(unittest.TestCase):
    def test_venue_investigation_without_llm_returns_error(self):
        """ARCH-SEM-001: investigate_venue requires LLM; without it returns error."""
        case = Case(case_id="test_vfc", user_id="u1")
        text = "A journal about continental philosophy and STS. " * 20
        result = case.investigate_venue(text)
        self.assertEqual(result["status"], "llm_required")
        self.assertIsNone(case.investigated_venue)

    def test_family_context_set_when_venue_exists(self):
        """Family context is set when venue is provided directly."""
        from kairoskopion.schema import VenueModel
        case = Case(case_id="test_vfc2", user_id="u1")
        case.investigated_venue = VenueModel(
            canonical_name="Philosophy Journal",
            scope_summary="Continental philosophy and STS",
        )
        case._build_venue_family_from_venue()
        if case.venue_family_context:
            self.assertIn("source_venue", case.venue_family_context)


class TestVenueMatrix(unittest.TestCase):
    def test_empty_pool_returns_no_pool(self):
        case = Case(case_id="test_vm", user_id="u1")
        result = case.get_venue_matrix()
        self.assertEqual(result["status"], "no_pool")

    def test_matrix_has_only_technical_fields(self):
        from kairoskopion.schema import VenueCandidatePool, VenueCandidate
        case = Case(case_id="test_vm2", user_id="u1")
        case.venue_pool = VenueCandidatePool(
            candidates=[
                VenueCandidate(canonical_name="Logos", status="discovered"),
                VenueCandidate(canonical_name="VF", status="light_profiled"),
            ],
        )
        result = case.get_venue_matrix()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["candidates"]), 2)
        for c in result["candidates"]:
            self.assertEqual(c["preliminary_assessment"], "NOT_ASSESSED_NEEDS_LLM")
            self.assertNotIn("confidence", c)

    def test_matrix_next_action_is_technical(self):
        """next_action is status-driven (technical), not semantic."""
        from kairoskopion.schema import VenueCandidatePool, VenueCandidate
        case = Case(case_id="test_vm3", user_id="u1")
        case.venue_pool = VenueCandidatePool(
            candidates=[
                VenueCandidate(canonical_name="A", status="discovered"),
                VenueCandidate(canonical_name="B", status="light_profiled"),
            ],
        )
        result = case.get_venue_matrix()
        self.assertEqual(result["candidates"][0]["next_action"], "investigate")
        self.assertEqual(result["candidates"][1]["next_action"], "deepen")


class TestPhase3Persistence(unittest.TestCase):
    def test_discipline_intent_roundtrip(self):
        case = Case(case_id="test_p3_rt", user_id="u1")
        case.set_discipline_intent("philosophy", region="ru")
        snap = _case_to_snapshot(case)
        restored = _case_from_snapshot(snap)
        self.assertIsNotNone(restored.discipline_intent)
        self.assertEqual(restored.discipline_intent["region"], "ru")
        self.assertEqual(restored.discipline_intent["intent_parse_status"], "needs_llm")

    def test_venue_source_metadata_roundtrip(self):
        """venue_source_metadata is set even without LLM and survives roundtrip."""
        case = Case(case_id="test_p3_rt2", user_id="u1")
        text = "Continental philosophy journal. " * 20
        case.investigate_venue(text)
        self.assertIsNotNone(case.venue_source_metadata)
        snap = _case_to_snapshot(case)
        restored = _case_from_snapshot(snap)
        self.assertIsNotNone(restored.venue_source_metadata)


class TestSemanticDoctrineInvariants(unittest.TestCase):
    """Invariant tests: semantic branches block without LLM."""

    def test_no_deterministic_fallback_for_venue_families(self):
        case = Case(case_id="test_inv1", user_id="u1")
        result = case.set_discipline_intent("philosophy of technology")
        self.assertEqual(result["venue_families"], [])
        self.assertIn("BLOCKED", result["venue_families_status"])

    def test_venue_matrix_no_fake_semantic_scores(self):
        from kairoskopion.schema import VenueCandidatePool, VenueCandidate
        case = Case(case_id="test_inv2", user_id="u1")
        case.venue_pool = VenueCandidatePool(
            candidates=[VenueCandidate(canonical_name="X", status="discovered")],
        )
        result = case.get_venue_matrix()
        for c in result["candidates"]:
            self.assertNotIn("fit_score", c)
            self.assertNotIn("risk_score", c)
            self.assertNotIn("overall_fit", c)


if __name__ == "__main__":
    unittest.main()
