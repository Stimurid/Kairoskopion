"""Tests for the deterministic article-enrichment fallback after the
Phase B refactor (commit 3/5) that removed the Anglo-biased hardcoded
keyword tables and routes the fallback through the disciplinary
registry.

What changed:
- ``_detect_disciplines_via_registry(text)`` returns registry
  discipline_ids (e.g. ``intl-philosophy-of-technology``) instead of
  hardcoded buckets (e.g. ``philosophy_of_technology``).
- ``_detect_schools_via_registry(text)`` returns canonical author
  names found across registry ``key_authors`` instead of hardcoded
  school names like ``Heideggerian``.
- The high-level ``build_article_semantic_profile`` still returns an
  ``ArticleSemanticProfile`` with the same fields; only the
  vocabulary that fills ``disciplinary_registers`` /
  ``schools_and_traditions`` has changed.
"""

from __future__ import annotations

import unittest

from kairoskopion.schema import ArticleModel, ArticleSemanticProfile
from kairoskopion.services.article_enrichment import (
    _detect_argument_move,
    _detect_disciplines_via_registry,
    _detect_schools_via_registry,
    _extract_protected_core_candidates,
    build_article_semantic_profile,
)


class TestDetectDisciplinesViaRegistry(unittest.TestCase):
    def test_philosophy_of_technology_surfaces(self):
        text = "philosophy of technology and technical artifacts"
        result = _detect_disciplines_via_registry(text)
        # Either RU or international variant qualifies — the registry
        # has both. The point is the fallback now produces registry ids.
        self.assertTrue(
            any("philosophy-of-technology" in d for d in result),
            f"expected philosophy-of-technology hit; got {result}",
        )

    def test_sts_surfaces(self):
        text = "actor-network theory and laboratory ethnography"
        result = _detect_disciplines_via_registry(text)
        # ANT or STS should appear
        self.assertTrue(
            any("actor-network" in d or "sts" in d for d in result),
            f"expected ANT/STS hit; got {result}",
        )

    def test_no_match_returns_empty(self):
        result = _detect_disciplines_via_registry("recipe for borscht")
        self.assertEqual(result, [])

    def test_empty_input_safe(self):
        self.assertEqual(_detect_disciplines_via_registry(""), [])
        self.assertEqual(_detect_disciplines_via_registry("   "), [])


class TestDetectSchoolsViaRegistry(unittest.TestCase):
    def test_heidegger_surfaces(self):
        text = "Heidegger's concept of enframing"
        result = _detect_schools_via_registry(text)
        # Registry has Heidegger as boundary_setter in
        # intl-philosophy-of-technology; matcher finds him by last
        # name token.
        self.assertTrue(
            any("Heidegger" in name for name in result),
            f"expected Heidegger; got {result}",
        )

    def test_latour_surfaces(self):
        text = "we follow Latour's actor-network analysis"
        result = _detect_schools_via_registry(text)
        self.assertTrue(
            any("Latour" in name for name in result),
            f"expected Latour; got {result}",
        )

    def test_no_match_returns_empty(self):
        result = _detect_schools_via_registry("statistical population data")
        self.assertEqual(result, [])


class TestDetectArgumentMove(unittest.TestCase):
    def test_conceptual_analysis(self):
        text = "we offer a conceptual analysis of the notion of agency"
        self.assertEqual(_detect_argument_move(text), "conceptual_analysis")

    def test_critique(self):
        text = "this paper critiques the shortcoming of existing approaches"
        self.assertEqual(_detect_argument_move(text), "critique")

    def test_no_match(self):
        self.assertIsNone(_detect_argument_move("lorem ipsum dolor sit amet"))


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
    def test_basic_profile_uses_registry_ids(self):
        article = ArticleModel(
            title_current="Heidegger and the Philosophy of Technology",
            abstract_current="A conceptual analysis of technology and Heidegger's enframing.",
            object_of_inquiry="technology as such",
            core_claims=["enframing is the essence of modern technology"],
            theoretical_shoulders=["Heidegger 1954"],
            protected_core=["central thesis on enframing"],
            mutable_zones=["introduction framing"],
        )
        profile = build_article_semantic_profile(article)
        self.assertIsInstance(profile, ArticleSemanticProfile)
        # Disciplines are now registry ids
        self.assertTrue(
            any("philosophy-of-technology" in d for d in profile.disciplinary_registers),
            f"expected registry id; got {profile.disciplinary_registers}",
        )
        # Schools are now canonical author names
        self.assertTrue(
            any("Heidegger" in s for s in profile.schools_and_traditions),
            f"expected Heidegger; got {profile.schools_and_traditions}",
        )
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
        self.assertTrue(
            any("Heidegger" in s for s in profile.schools_and_traditions),
        )

    def test_serialization(self):
        article = ArticleModel(title_current="Test")
        profile = build_article_semantic_profile(article)
        d = profile.to_dict()
        self.assertIn("article_semantic_profile_id", d)
        self.assertIn("disciplinary_registers", d)


if __name__ == "__main__":
    unittest.main()
