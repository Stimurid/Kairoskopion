"""Phase 3: Track A Funnel — discipline intent, venue families, venue matrix."""

from __future__ import annotations

import unittest

from kairoskopion.api.cases import Case, _case_to_snapshot, _case_from_snapshot


class TestSetDisciplineIntent(unittest.TestCase):
    def test_set_basic_intent(self):
        case = Case(case_id="test_di", user_id="u1")
        result = case.set_discipline_intent("philosophy of technology, STS")
        self.assertEqual(result["status"], "ok")
        self.assertIsNotNone(case.discipline_intent)
        self.assertIn("venue_families", result)

    def test_intent_with_region(self):
        case = Case(case_id="test_di2", user_id="u1")
        result = case.set_discipline_intent("sociology", region="ru")
        self.assertEqual(case.region_hint, "ru")
        families = result["venue_families"]
        self.assertTrue(len(families) > 0)

    def test_intent_with_constraints(self):
        case = Case(case_id="test_di3", user_id="u1")
        result = case.set_discipline_intent(
            "philosophy", constraints=["VAK preferred"],
        )
        self.assertEqual(case.discipline_intent["constraints"], ["VAK preferred"])

    def test_unknown_discipline(self):
        case = Case(case_id="test_di4", user_id="u1")
        result = case.set_discipline_intent("xyzzy unknown field")
        families = result["venue_families"]
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0]["discipline_zone"], "unknown")
        self.assertEqual(families[0]["confidence"], "low")


class TestVenueFamilyInference(unittest.TestCase):
    def test_philosophy_family(self):
        case = Case(case_id="test_vf", user_id="u1")
        families = case._infer_venue_families("philosophy of mind")
        self.assertTrue(any(f["discipline_zone"] == "philosophy" for f in families))

    def test_sts_family(self):
        case = Case(case_id="test_vf2", user_id="u1")
        families = case._infer_venue_families("STS actor-network")
        self.assertTrue(any(f["discipline_zone"] == "sts" for f in families))

    def test_region_filter_ru(self):
        case = Case(case_id="test_vf3", user_id="u1")
        families = case._infer_venue_families("philosophy", region="ru")
        for f in families:
            for v in f["expected_venues"]:
                self.assertNotIn("Synthese", v)

    def test_region_filter_intl(self):
        case = Case(case_id="test_vf4", user_id="u1")
        families = case._infer_venue_families("philosophy", region="international")
        for f in families:
            for v in f["expected_venues"]:
                self.assertNotIn("Вопросы философии", v)


class TestVenueFamilyFromVenue(unittest.TestCase):
    def test_venue_investigation_sets_family_context(self):
        case = Case(case_id="test_vfc", user_id="u1")
        text = "A journal about continental philosophy and STS. " * 20
        case.investigate_venue(text)
        self.assertIsNotNone(case.venue_family_context)
        self.assertIn("families", case.venue_family_context)

    def test_family_context_has_source_venue(self):
        case = Case(case_id="test_vfc2", user_id="u1")
        text = "A journal about philosophy and technology. " * 20
        case.investigate_venue(text)
        if case.venue_family_context:
            self.assertIn("source_venue", case.venue_family_context)


class TestVenueMatrix(unittest.TestCase):
    def test_empty_pool_returns_no_pool(self):
        case = Case(case_id="test_vm", user_id="u1")
        result = case.get_venue_matrix()
        self.assertEqual(result["status"], "no_pool")

    def test_matrix_from_pool(self):
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

    def test_venue_family_context_roundtrip(self):
        case = Case(case_id="test_p3_rt2", user_id="u1")
        text = "Continental philosophy journal. " * 20
        case.investigate_venue(text)
        snap = _case_to_snapshot(case)
        restored = _case_from_snapshot(snap)
        if case.venue_family_context:
            self.assertIsNotNone(restored.venue_family_context)


if __name__ == "__main__":
    unittest.main()
