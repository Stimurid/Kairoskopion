"""Tests for article semantic profile enrichment service."""

from __future__ import annotations

import unittest

from kairoskopion.schema import ArticleModel, ArticleSemanticProfile
from kairoskopion.services.article_enrichment import (
    build_article_semantic_profile,
    _detect_disciplines,
    _detect_schools,
    _detect_argument_move,
    _extract_protected_core_candidates,
)


class TestDetectDisciplines(unittest.TestCase):
    def test_philosophy_of_technology(self):
        text = "this paper examines the philosophy of technology and its implications"
        result = _detect_disciplines(text)
        self.assertIn("philosophy_of_technology", result)

    def test_sts(self):
        text = "we adopt a science and technology studies perspective"
        result = _detect_disciplines(text)
        self.assertIn("STS", result)

    def test_multiple_disciplines(self):
        text = "this paper bridges ethics and philosophy of technology"
        result = _detect_disciplines(text)
        self.assertIn("ethics", result)
        self.assertIn("philosophy_of_technology", result)

    def test_no_match(self):
        text = "this is a completely unrelated text about cooking"
        result = _detect_disciplines(text)
        self.assertEqual(len(result), 0)

    def test_phenomenology(self):
        text = "a phenomenological investigation of lived experience"
        result = _detect_disciplines(text)
        self.assertIn("phenomenology", result)


class TestDetectSchools(unittest.TestCase):
    def test_simondon(self):
        text = "following simondon's theory of individuation"
        result = _detect_schools(text)
        self.assertIn("Simondonian", result)

    def test_heidegger(self):
        text = "heidegger's concept of dasein reveals"
        result = _detect_schools(text)
        self.assertIn("Heideggerian", result)

    def test_multiple_schools(self):
        text = "drawing on both latour's actor-network theory and deleuze's assemblage"
        result = _detect_schools(text)
        self.assertIn("Latourian", result)
        self.assertIn("Deleuzian", result)

    def test_no_match(self):
        text = "a statistical analysis of population data"
        result = _detect_schools(text)
        self.assertEqual(len(result), 0)


class TestDetectArgumentMove(unittest.TestCase):
    def test_conceptual_analysis(self):
        text = "we offer a conceptual analysis of the notion of agency"
        result = _detect_argument_move(text)
        self.assertEqual(result, "conceptual_analysis")

    def test_critique(self):
        text = "this paper critiques the shortcoming of existing approaches"
        result = _detect_argument_move(text)
        self.assertEqual(result, "critique")

    def test_no_match(self):
        text = "lorem ipsum dolor sit amet"
        result = _detect_argument_move(text)
        self.assertIsNone(result)


class TestExtractProtectedCoreCandidates(unittest.TestCase):
    def test_from_protected_core_field(self):
        article = ArticleModel(protected_core=["central thesis on X"])
        result = _extract_protected_core_candidates(article)
        self.assertIn("central thesis on X", result)

    def test_adds_object_of_inquiry(self):
        article = ArticleModel(object_of_inquiry="technology as process")
        result = _extract_protected_core_candidates(article)
        self.assertIn("object of inquiry: technology as process", result)

    def test_adds_core_claims(self):
        article = ArticleModel(core_claims=["individuation is primary"])
        result = _extract_protected_core_candidates(article)
        self.assertIn("individuation is primary", result)

    def test_no_duplicates(self):
        article = ArticleModel(
            protected_core=["central thesis"],
            core_claims=["central thesis"],
        )
        result = _extract_protected_core_candidates(article)
        self.assertEqual(result.count("central thesis"), 1)


class TestBuildArticleSemanticProfile(unittest.TestCase):
    def test_basic_profile(self):
        article = ArticleModel(
            title_current="Simondon and the Philosophy of Technology",
            abstract_current="This paper offers a conceptual analysis of individuation in technical objects.",
            object_of_inquiry="technical individuation",
            core_claims=["individuation is the key process"],
            theoretical_shoulders=["Simondon (1958)"],
            protected_core=["central thesis on individuation"],
            mutable_zones=["introduction framing"],
        )
        profile = build_article_semantic_profile(article)
        self.assertIsInstance(profile, ArticleSemanticProfile)
        self.assertIn("philosophy_of_technology", profile.disciplinary_registers)
        self.assertIn("Simondonian", profile.schools_and_traditions)
        self.assertIsNotNone(profile.argument_move_type)
        self.assertGreater(len(profile.protected_core_candidates), 0)
        self.assertEqual(profile.article_model_id, article.article_model_id)

    def test_empty_article(self):
        article = ArticleModel()
        profile = build_article_semantic_profile(article)
        self.assertGreater(len(profile.unknowns), 0)
        self.assertEqual(profile.confidence, "low")

    def test_with_manuscript_text(self):
        article = ArticleModel(title_current="A study")
        profile = build_article_semantic_profile(
            article,
            manuscript_text="Heidegger's analysis of technology as enframing reveals...",
        )
        self.assertIn("Heideggerian", profile.schools_and_traditions)

    def test_audience_inference(self):
        article = ArticleModel(
            title_current="Ethics of AI",
            abstract_current="An ethical framework for artificial intelligence",
        )
        profile = build_article_semantic_profile(article)
        self.assertIsNotNone(profile.intended_audience)

    def test_serialization(self):
        article = ArticleModel(title_current="Test")
        profile = build_article_semantic_profile(article)
        d = profile.to_dict()
        self.assertIn("article_semantic_profile_id", d)
        self.assertIn("disciplinary_registers", d)

    def test_interdisciplinary_audience(self):
        article = ArticleModel(
            title_current="Ethics, epistemology, and phenomenology of technology",
            abstract_current="This paper bridges ethics, epistemology, and phenomenological approaches",
        )
        profile = build_article_semantic_profile(article)
        if len(profile.disciplinary_registers) > 2:
            self.assertEqual(profile.intended_audience, "interdisciplinary")


if __name__ == "__main__":
    unittest.main()
