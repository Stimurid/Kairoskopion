"""Tests for prompt family definitions and validators."""

from __future__ import annotations

import unittest

from kairoskopion.prompts.article_modeling import (
    ARTICLE_MODELING_FAMILY,
    validate_article_extraction,
)
from kairoskopion.prompts.venue_fact_extraction import (
    VENUE_FACT_EXTRACTION_FAMILY,
    validate_venue_extraction,
)
from kairoskopion.prompts.fit_assessment import (
    FIT_ASSESSMENT_FAMILY,
    validate_fit_assessment,
)


class TestArticleModelingFamily(unittest.TestCase):
    def test_has_required_keys(self):
        for key in ("family_id", "system_prompt", "user_prompt_template", "output_schema"):
            self.assertIn(key, ARTICLE_MODELING_FAMILY)

    def test_template_has_placeholder(self):
        self.assertIn("{manuscript_text}", ARTICLE_MODELING_FAMILY["user_prompt_template"])

    def test_schema_is_dict(self):
        self.assertIsInstance(ARTICLE_MODELING_FAMILY["output_schema"], dict)

    def test_validator_flags_abstract_only(self):
        data = {
            "article_stage": "abstract",
            "confidence": "high",
        }
        warnings = validate_article_extraction(data)
        self.assertTrue(any("abstract" in w.lower() for w in warnings))

    def test_validator_ok_on_valid(self):
        data = {
            "article_stage": "full_manuscript",
            "confidence": "medium",
            "genre_current": "research_article",
            "novelty_mode": "new_theory",
            "method_status": "empirical_method",
        }
        warnings = validate_article_extraction(data)
        self.assertEqual(len(warnings), 0)


class TestVenueExtractionFamily(unittest.TestCase):
    def test_has_required_keys(self):
        for key in ("family_id", "system_prompt", "user_prompt_template", "output_schema"):
            self.assertIn(key, VENUE_FACT_EXTRACTION_FAMILY)

    def test_template_has_placeholders(self):
        tpl = VENUE_FACT_EXTRACTION_FAMILY["user_prompt_template"]
        self.assertIn("{venue_text}", tpl)
        self.assertIn("{source_type}", tpl)

    def test_validator_catches_indexing_as_fact(self):
        data = {
            "indexing_claims": [
                {"database": "Scopus", "evidence_status": "fact_from_source"}
            ],
        }
        warnings = validate_venue_extraction(data)
        self.assertTrue(any("indexing" in w.lower() or "vendor" in w.lower() for w in warnings))

    def test_validator_ok_on_valid(self):
        data = {
            "indexing_claims": [
                {"database": "Scopus", "evidence_status": "vendor_claim"}
            ],
            "unknowns": ["review timeline unclear"],
        }
        warnings = validate_venue_extraction(data)
        self.assertEqual(len(warnings), 0)


class TestFitAssessmentFamily(unittest.TestCase):
    def test_has_required_keys(self):
        for key in ("family_id", "system_prompt", "user_prompt_template", "output_schema"):
            self.assertIn(key, FIT_ASSESSMENT_FAMILY)

    def test_template_has_placeholders(self):
        tpl = FIT_ASSESSMENT_FAMILY["user_prompt_template"]
        self.assertIn("{article_json}", tpl)
        self.assertIn("{venue_json}", tpl)
        self.assertIn("{scenario_json}", tpl)

    def test_validator_catches_missing_axes(self):
        data = {"axes": [{"axis": "topic_fit", "value": "strong"}], "unknowns": ["x"]}
        warnings = validate_fit_assessment(data)
        self.assertTrue(any("missing" in w.lower() for w in warnings))

    def test_validator_catches_all_strong(self):
        axes = [
            {"axis": f"axis_{i}", "value": "strong"} for i in range(16)
        ]
        data = {"axes": axes, "unknowns": ["x"]}
        warnings = validate_fit_assessment(data)
        self.assertTrue(any("optimistic" in w.lower() for w in warnings))

    def test_validator_catches_no_unknowns(self):
        axes = [{"axis": "topic_fit", "value": "moderate"}]
        data = {"axes": axes, "unknowns": []}
        warnings = validate_fit_assessment(data)
        self.assertTrue(any("unknown" in w.lower() for w in warnings))


if __name__ == "__main__":
    unittest.main()
