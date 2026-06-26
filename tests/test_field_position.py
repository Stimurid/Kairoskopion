"""Tests for FieldPositionModel and field_position_fit."""

from __future__ import annotations

import unittest

from kairoskopion.schema import FieldPositionModel
from kairoskopion.logic.field_position_fit import (
    compute_field_position_fit,
    _vector_distance_to_envelope,
    _scalar_distance,
    CONTAINED,
    ADJACENT,
    OUTSIDE,
    UNKNOWN,
)
from kairoskopion.prompts.field_positioning import (
    ARTICLE_FIELD_POSITION_FAMILY,
    VENUE_FIELD_POSITION_FAMILY,
    _validate_article_fpm,
    _validate_venue_fpm,
)


class TestFieldPositionModelDataclass(unittest.TestCase):
    def test_create_article_fpm(self):
        fpm = FieldPositionModel(
            entity_type="article",
            entity_id="art_test123",
            discipline_vector={"philosophy_of_technology": 0.7, "STS": 0.3},
            tradition_affiliation_vector={"Simondon": 0.9, "Stiegler": 0.3},
        )
        self.assertEqual(fpm.entity_type, "article")
        self.assertIn("philosophy_of_technology", fpm.discipline_vector)
        d = fpm.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["entity_type"], "article")

    def test_create_venue_fpm(self):
        fpm = FieldPositionModel(
            entity_type="venue",
            entity_id="ven_test456",
            discipline_vector={"philosophy_of_technology": 0.5},
            discipline_envelope={"philosophy_of_technology": [0.3, 1.0], "STS": [0.0, 0.4]},
            tradition_affiliation_vector={"continental_phenomenology": 0.6},
            tradition_envelope={"continental_phenomenology": [0.2, 0.9]},
        )
        self.assertEqual(fpm.entity_type, "venue")
        self.assertIsNotNone(fpm.discipline_envelope)

    def test_from_dict(self):
        d = {
            "entity_type": "article",
            "entity_id": "art_x",
            "discipline_vector": {"phil": 0.5},
            "unknowns": ["method unclear"],
        }
        fpm = FieldPositionModel.from_dict(d)
        self.assertEqual(fpm.entity_type, "article")
        self.assertEqual(fpm.discipline_vector, {"phil": 0.5})


class TestVectorDistanceToEnvelope(unittest.TestCase):
    def test_contained_in_envelope(self):
        point = {"a": 0.5, "b": 0.3}
        center = {"a": 0.5, "b": 0.3}
        envelope = {"a": [0.2, 0.8], "b": [0.1, 0.6]}
        status, dist, edge = _vector_distance_to_envelope(point, center, envelope)
        self.assertEqual(status, CONTAINED)
        self.assertEqual(dist, 0.0)

    def test_adjacent_to_envelope(self):
        point = {"a": 0.9}
        center = {"a": 0.5}
        envelope = {"a": [0.2, 0.8]}
        status, dist, edge = _vector_distance_to_envelope(point, center, envelope)
        self.assertEqual(status, ADJACENT)
        self.assertAlmostEqual(dist, 0.1, places=2)
        self.assertEqual(edge, "a")

    def test_outside_envelope(self):
        point = {"a": 1.0}
        center = {"a": 0.3}
        envelope = {"a": [0.0, 0.5]}
        status, dist, edge = _vector_distance_to_envelope(point, center, envelope)
        self.assertEqual(status, OUTSIDE)
        self.assertAlmostEqual(dist, 0.5, places=2)

    def test_no_envelope_uses_center_distance(self):
        point = {"a": 0.9}
        center = {"a": 0.1}
        status, dist, _ = _vector_distance_to_envelope(point, center, None)
        self.assertEqual(status, OUTSIDE)

    def test_empty_vectors(self):
        status, dist, _ = _vector_distance_to_envelope({}, {}, None)
        self.assertEqual(status, UNKNOWN)


class TestScalarDistance(unittest.TestCase):
    def test_contained(self):
        status, dist = _scalar_distance(0.5, 0.5)
        self.assertEqual(status, CONTAINED)

    def test_adjacent(self):
        status, dist = _scalar_distance(0.5, 0.3)
        self.assertEqual(status, ADJACENT)

    def test_outside(self):
        status, dist = _scalar_distance(0.0, 0.8)
        self.assertEqual(status, OUTSIDE)

    def test_unknown(self):
        status, _ = _scalar_distance(None, 0.5)
        self.assertEqual(status, UNKNOWN)


class TestComputeFieldPositionFit(unittest.TestCase):
    def _make_article(self):
        return {
            "discipline_vector": {"philosophy_of_technology": 0.7, "STS": 0.3},
            "tradition_affiliation_vector": {"Simondon": 0.8, "Stiegler": 0.2},
            "argument_move_vector": {"concept_reconstruction": 0.6, "genealogy": 0.4},
            "evidence_type_profile": {"theoretical_argument": 0.8, "textual_analysis": 0.2},
            "method_stance": {"explicit_method": False, "method_family": "philosophical_analysis"},
            "formalization_level": 0.3,
            "audience_level": {"accessibility_index": 0.3},
            "language_register": {"language": "en", "jargon_density": 0.7},
            "genre_position": {"genre_formality": 0.6},
            "geographic_affinity": {"language_of_publication": "en"},
        }

    def _make_venue_good_fit(self):
        return {
            "discipline_vector": {"philosophy_of_technology": 0.6, "STS": 0.3},
            "discipline_envelope": {
                "philosophy_of_technology": [0.3, 1.0],
                "STS": [0.0, 0.6],
            },
            "tradition_affiliation_vector": {"Simondon": 0.5, "continental_phenomenology": 0.3},
            "tradition_envelope": {
                "Simondon": [0.2, 0.9],
                "Stiegler": [0.0, 0.5],
                "continental_phenomenology": [0.1, 0.7],
            },
            "argument_move_vector": {"concept_reconstruction": 0.5, "genealogy": 0.3},
            "argument_move_envelope": {
                "concept_reconstruction": [0.2, 0.9],
                "genealogy": [0.0, 0.6],
            },
            "evidence_type_profile": {"theoretical_argument": 0.7, "textual_analysis": 0.3},
            "method_stance": {
                "requires_explicit_method": False,
                "accepted_method_families": ["philosophical_analysis", "hermeneutic"],
            },
            "formalization_level": 0.3,
            "audience_level": {"accessibility_index": 0.3},
            "language_register": {"language": "en", "jargon_density": 0.7},
            "genre_position": {"genre_formality": 0.6},
            "geographic_affinity": {"anglophone_hegemony_index": 0.7, "language_of_publication": "en"},
        }

    def test_good_fit(self):
        result = compute_field_position_fit(self._make_article(), self._make_venue_good_fit())
        self.assertIn("axes", result)
        self.assertIn("overall_label", result)
        self.assertIn(result["overall_label"], ("strong_candidate", "possible"))
        outside_axes = [a for a in result["axes"] if a["status"] == OUTSIDE]
        self.assertEqual(len(outside_axes), 0)

    def test_poor_fit(self):
        article = self._make_article()
        venue = self._make_venue_good_fit()
        venue["discipline_envelope"] = {"quantitative_economics": [0.5, 1.0]}
        venue["tradition_envelope"] = {"Chicago_school": [0.5, 1.0]}
        venue["argument_move_envelope"] = {"systematic_review": [0.5, 1.0]}
        venue["method_stance"]["requires_explicit_method"] = True
        venue["method_stance"]["accepted_method_families"] = ["econometrics"]
        venue["method_stance"]["rejected_method_families"] = ["philosophical_analysis"]
        venue["language_register"]["language"] = "de"
        result = compute_field_position_fit(article, venue)
        self.assertEqual(result["overall_label"], "poor_fit")

    def test_all_axes_present(self):
        result = compute_field_position_fit(self._make_article(), self._make_venue_good_fit())
        axis_names = {a["axis"] for a in result["axes"]}
        expected = {
            "discipline_fit", "school_fit", "argument_move_fit",
            "evidence_type_fit", "method_fit", "formalization_fit",
            "audience_fit", "jargon_fit", "language_match",
            "genre_formality_fit", "geographic_fit",
        }
        self.assertEqual(axis_names, expected)

    def test_summary_counts(self):
        result = compute_field_position_fit(self._make_article(), self._make_venue_good_fit())
        summary = result["summary"]
        self.assertEqual(
            summary["contained"] + summary["adjacent"] + summary["outside"] + summary["unknown"],
            summary["total"],
        )


class TestPromptFamilyValidators(unittest.TestCase):
    def test_valid_article_fpm(self):
        parsed = {
            "discipline_vector": {"a": 0.5, "b": 0.3},
            "tradition_affiliation_vector": {"x": 0.6, "y": 0.4},
            "argument_move_vector": {"p": 0.5, "q": 0.5},
            "evidence_type_profile": {"t": 0.7, "u": 0.3},
            "formalization_level": 0.4,
        }
        warnings = _validate_article_fpm(parsed)
        self.assertEqual(warnings, [])

    def test_missing_vector(self):
        parsed = {
            "discipline_vector": {},
            "tradition_affiliation_vector": {"x": 0.5, "y": 0.5},
            "argument_move_vector": {"p": 0.5, "q": 0.5},
            "evidence_type_profile": {"t": 0.5, "u": 0.5},
        }
        warnings = _validate_article_fpm(parsed)
        self.assertTrue(any("discipline_vector" in w for w in warnings))

    def test_out_of_range(self):
        parsed = {
            "discipline_vector": {"a": 1.5, "b": 0.3},
            "tradition_affiliation_vector": {"x": 0.5, "y": 0.5},
            "argument_move_vector": {"p": 0.5, "q": 0.5},
            "evidence_type_profile": {"t": 0.5, "u": 0.5},
        }
        warnings = _validate_article_fpm(parsed)
        self.assertTrue(any("out-of-range" in w for w in warnings))

    def test_valid_venue_fpm(self):
        parsed = {
            "discipline_vector": {"a": 0.5},
            "discipline_envelope": {"a": [0.2, 0.8]},
            "tradition_affiliation_vector": {"x": 0.5},
            "tradition_envelope": {"x": [0.1, 0.9]},
            "argument_move_vector": {"p": 0.5},
            "argument_move_envelope": {"p": [0.2, 0.8]},
        }
        warnings = _validate_venue_fpm(parsed)
        self.assertEqual(warnings, [])

    def test_inverted_envelope(self):
        parsed = {
            "discipline_vector": {"a": 0.5},
            "discipline_envelope": {"a": [0.8, 0.2]},
            "tradition_affiliation_vector": {"x": 0.5},
            "tradition_envelope": {"x": [0.1, 0.9]},
            "argument_move_vector": {"p": 0.5},
            "argument_move_envelope": {"p": [0.2, 0.8]},
        }
        warnings = _validate_venue_fpm(parsed)
        self.assertTrue(any("min > max" in w for w in warnings))


class TestPromptFamiliesExist(unittest.TestCase):
    def test_article_family_structure(self):
        f = ARTICLE_FIELD_POSITION_FAMILY
        self.assertIn("system_prompt", f)
        self.assertIn("user_prompt_template", f)
        self.assertIn("output_schema", f)
        self.assertIn("validator", f)
        self.assertTrue(callable(f["validator"]))

    def test_venue_family_structure(self):
        f = VENUE_FIELD_POSITION_FAMILY
        self.assertIn("system_prompt", f)
        self.assertIn("user_prompt_template", f)
        self.assertIn("output_schema", f)
        self.assertTrue(callable(f["validator"]))


if __name__ == "__main__":
    unittest.main()
