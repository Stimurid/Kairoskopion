"""Tests for web enrichment pipeline."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from kairoskopion.search.provider import SearchDepth, SearchResult, WebSearchProvider
from kairoskopion.search.duckduckgo import DuckDuckGoProvider


class TestSearchDepthEnum(unittest.TestCase):
    def test_values(self):
        self.assertEqual(SearchDepth.NONE.value, "none")
        self.assertEqual(SearchDepth.LIGHT.value, "light")
        self.assertEqual(SearchDepth.DEEP.value, "deep")

    def test_from_string(self):
        self.assertEqual(SearchDepth("none"), SearchDepth.NONE)
        self.assertEqual(SearchDepth("light"), SearchDepth.LIGHT)
        self.assertEqual(SearchDepth("deep"), SearchDepth.DEEP)

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            SearchDepth("turbo")


class TestSearchResult(unittest.TestCase):
    def test_fields(self):
        r = SearchResult(title="Test", url="https://x.com", snippet="A snippet")
        self.assertEqual(r.title, "Test")
        self.assertEqual(r.source, "")


class TestDuckDuckGoProvider(unittest.TestCase):
    def test_name(self):
        p = DuckDuckGoProvider()
        self.assertEqual(p.name, "duckduckgo")

    @patch("urllib.request.urlopen")
    def test_api_fallback_returns_results(self, mock_urlopen):
        import json
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({
            "Abstract": "Gilbert Simondon was a French philosopher.",
            "Heading": "Gilbert Simondon",
            "AbstractURL": "https://en.wikipedia.org/wiki/Gilbert_Simondon",
            "RelatedTopics": [
                {"Text": "Individuation philosophy", "FirstURL": "https://x.com/ind"},
            ],
        }).encode()
        mock_urlopen.return_value = mock_resp

        p = DuckDuckGoProvider()
        results = p._search_via_api("Gilbert Simondon", max_results=5)
        self.assertGreater(len(results), 0)
        self.assertIn("Simondon", results[0].snippet)
        self.assertEqual(results[0].source, "duckduckgo_instant")


class TestEnrichArticleModel(unittest.TestCase):
    def test_none_depth_is_noop(self):
        from kairoskopion.services.web_enrichment import enrich_article_model

        article = {"title_current": "Test", "unknowns": ["x"]}
        result = enrich_article_model(article, MagicMock(), MagicMock(), SearchDepth.NONE)
        self.assertEqual(result, article)

    def test_light_with_no_gaps(self):
        from kairoskopion.services.web_enrichment import enrich_article_model

        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.parsed = {"gaps": []}
        mock_resp.content = '{"gaps": []}'
        mock_llm.complete.return_value = mock_resp

        article = {"title_current": "Test", "unknowns": []}
        result = enrich_article_model(article, MagicMock(), mock_llm, SearchDepth.LIGHT)
        self.assertIn("_enrichment", result)
        self.assertEqual(result["_enrichment"]["status"], "no_gaps")


class TestCaseIntakeSearchDepth(unittest.TestCase):
    def test_intake_accepts_search_depth(self):
        import tempfile
        from kairoskopion.api.cases import Case

        case = Case(title="Test")
        result = case.intake_text(
            "This paper examines individuation in technical objects "
            "through a Simondonian lens.",
            input_type="article",
            search_depth="none",
        )
        self.assertIn("input_type", result)
        self.assertEqual(result["stage"], "article_model")


if __name__ == "__main__":
    unittest.main()
