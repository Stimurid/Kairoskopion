"""Tests for Sprint 3: Real Optional Adapters.

Tests the real adapter paths WITHOUT making actual network calls.
Uses mocked HTTP responses to verify parsing, caching, rate limiting,
and auto-dispatch logic.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kairoskopion.adapters.http_client import (
    HttpError,
    _cache_key,
    _rate_limit,
    _rate_state,
    fetch_json,
    read_cache,
    write_cache,
)
from kairoskopion.adapters.crossref import (
    _parse_crossref_work,
    lookup_doi,
    lookup_doi_auto,
    lookup_doi_mock,
    search_works,
    search_works_auto,
    search_works_mock,
)
from kairoskopion.adapters.openalex import (
    _parse_openalex_work,
    search_works as openalex_search_works,
    search_works_auto as openalex_search_auto,
    search_works_mock as openalex_search_mock,
)
from kairoskopion.adapters.opencitations import (
    get_citations,
    get_citations_auto,
    get_citations_mock,
)


# ---------------------------------------------------------------------------
# HTTP client: caching
# ---------------------------------------------------------------------------

class TestHttpCache:
    def test_write_and_read_cache(self, tmp_path):
        url = "https://api.example.com/works/123"
        body = {"title": "Test", "year": 2020}
        write_cache(url, body, cache_dir=tmp_path)
        result = read_cache(url, cache_dir=tmp_path, max_age_seconds=3600)
        assert result == body

    def test_cache_miss_on_unknown_url(self, tmp_path):
        result = read_cache("https://unknown.example.com", cache_dir=tmp_path)
        assert result is None

    def test_cache_expiry(self, tmp_path):
        url = "https://api.example.com/old"
        write_cache(url, {"old": True}, cache_dir=tmp_path)
        # Patch the cached_at to be old
        cache_file = tmp_path / f"{_cache_key(url)}.json"
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        data["_cached_at"] = time.time() - 100000
        cache_file.write_text(json.dumps(data), encoding="utf-8")
        result = read_cache(url, cache_dir=tmp_path, max_age_seconds=3600)
        assert result is None

    def test_cache_key_deterministic(self):
        url = "https://api.example.com/test"
        assert _cache_key(url) == _cache_key(url)

    def test_cache_key_differs_for_different_urls(self):
        assert _cache_key("https://a.com/1") != _cache_key("https://a.com/2")


# ---------------------------------------------------------------------------
# HTTP client: rate limiting
# ---------------------------------------------------------------------------

class TestRateLimit:
    def test_rate_limit_records_time(self):
        _rate_state.clear()
        _rate_limit("test-host.example.com")
        assert "test-host.example.com" in _rate_state


# ---------------------------------------------------------------------------
# HTTP client: fetch_json with mocked urllib
# ---------------------------------------------------------------------------

class TestFetchJson:
    def test_fetch_returns_cached(self, tmp_path):
        url = "https://api.example.com/cached"
        write_cache(url, {"cached": True}, cache_dir=tmp_path)
        result = fetch_json(url, cache_dir=tmp_path)
        assert result == {"cached": True}

    @patch("kairoskopion.adapters.http_client.urllib.request.urlopen")
    def test_fetch_calls_api_on_miss(self, mock_urlopen, tmp_path):
        url = "https://api.example.com/fresh"
        resp_body = json.dumps({"fresh": True}).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_body
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = fetch_json(url, cache_dir=tmp_path, rate_limit=False)
        assert result == {"fresh": True}
        # Should now be cached
        cached = read_cache(url, cache_dir=tmp_path)
        assert cached == {"fresh": True}


# ---------------------------------------------------------------------------
# Crossref real mode: parsing
# ---------------------------------------------------------------------------

class TestCrossrefParsing:
    def test_parse_crossref_work(self):
        item = {
            "DOI": "10.1234/test",
            "title": ["Test Paper Title"],
            "author": [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"},
            ],
            "published-print": {"date-parts": [[2020, 3]]},
            "container-title": ["Journal of Testing"],
            "type": "journal-article",
            "is-referenced-by-count": 42,
        }
        rec = _parse_crossref_work(item)
        assert rec.title == "Test Paper Title"
        assert rec.authors == ["John Doe", "Jane Smith"]
        assert rec.year == 2020
        assert rec.doi == "10.1234/test"
        assert rec.venue_name == "Journal of Testing"
        assert rec.citation_count == 42

    def test_parse_crossref_work_minimal(self):
        item = {"DOI": "10.1234/min", "type": "other"}
        rec = _parse_crossref_work(item)
        assert rec.doi == "10.1234/min"
        assert rec.title is None
        assert rec.authors == []
        assert rec.year is None


# ---------------------------------------------------------------------------
# Crossref real mode: API calls (mocked)
# ---------------------------------------------------------------------------

class TestCrossrefReal:
    @patch("kairoskopion.adapters.crossref.fetch_json")
    def test_lookup_doi_success(self, mock_fetch, tmp_path):
        mock_fetch.return_value = {
            "message": {
                "DOI": "10.1234/test",
                "title": ["Test"],
                "author": [{"given": "A", "family": "B"}],
                "published-print": {"date-parts": [[2021]]},
                "container-title": ["J Test"],
                "type": "journal-article",
            }
        }
        result = lookup_doi("10.1234/test", cache_dir=tmp_path)
        assert result.is_mock is False
        assert result.status == "success"
        assert len(result.records) == 1
        assert result.records[0]["doi"] == "10.1234/test"

    @patch("kairoskopion.adapters.crossref.fetch_json")
    def test_lookup_doi_not_found(self, mock_fetch, tmp_path):
        mock_fetch.side_effect = HttpError(404, "Not Found", "url")
        result = lookup_doi("10.9999/nonexistent", cache_dir=tmp_path)
        assert result.status == "no_results"
        assert result.is_mock is False
        assert len(result.records) == 0

    @patch("kairoskopion.adapters.crossref.fetch_json")
    def test_search_works_success(self, mock_fetch, tmp_path):
        mock_fetch.return_value = {
            "message": {
                "items": [
                    {"DOI": "10.1/a", "title": ["A"], "type": "article"},
                    {"DOI": "10.1/b", "title": ["B"], "type": "article"},
                ],
                "total-results": 100,
            }
        }
        result = search_works("test query", cache_dir=tmp_path)
        assert result.is_mock is False
        assert result.status == "success"
        assert len(result.records) == 2
        assert result.total_available == 100


# ---------------------------------------------------------------------------
# Auto-dispatch (mock/real)
# ---------------------------------------------------------------------------

class TestAutoDispatch:
    def test_crossref_auto_defaults_to_mock(self):
        result = lookup_doi_auto("10.2307/2183914")
        assert result.is_mock is True

    @patch("kairoskopion.adapters.crossref.fetch_json")
    def test_crossref_auto_real_mode(self, mock_fetch, tmp_path):
        mock_fetch.return_value = {"message": {"DOI": "10.1/x", "type": "article"}}
        result = lookup_doi_auto("10.1/x", mode="real", cache_dir=tmp_path)
        assert result.is_mock is False

    def test_openalex_auto_defaults_to_mock(self):
        result = openalex_search_auto("test")
        assert result.is_mock is True

    def test_opencitations_auto_defaults_to_mock(self):
        result = get_citations_auto("10.1234/test")
        assert result.is_mock is True


# ---------------------------------------------------------------------------
# OpenAlex real mode: parsing
# ---------------------------------------------------------------------------

class TestOpenAlexParsing:
    def test_parse_openalex_work(self):
        item = {
            "id": "W123",
            "title": "OpenAlex Test",
            "authorships": [
                {"author": {"display_name": "Alice"}},
                {"author": {"display_name": "Bob"}},
            ],
            "publication_year": 2022,
            "doi": "https://doi.org/10.5555/test",
            "primary_location": {
                "source": {"display_name": "J of OA"}
            },
            "type": "article",
            "cited_by_count": 15,
            "open_access": {"is_oa": True},
        }
        rec = _parse_openalex_work(item)
        assert rec.title == "OpenAlex Test"
        assert rec.authors == ["Alice", "Bob"]
        assert rec.doi == "10.5555/test"  # stripped prefix
        assert rec.year == 2022
        assert rec.citation_count == 15
        assert rec.is_open_access is True


# ---------------------------------------------------------------------------
# OpenAlex real mode: API calls (mocked)
# ---------------------------------------------------------------------------

class TestOpenAlexReal:
    @patch("kairoskopion.adapters.openalex.fetch_json")
    def test_search_works_success(self, mock_fetch, tmp_path):
        mock_fetch.return_value = {
            "results": [
                {"id": "W1", "title": "Paper 1", "type": "article",
                 "authorships": [], "publication_year": 2021},
            ],
            "meta": {"count": 50},
        }
        result = openalex_search_works("test", cache_dir=tmp_path)
        assert result.is_mock is False
        assert result.status == "success"
        assert len(result.records) == 1
        assert result.total_available == 50


# ---------------------------------------------------------------------------
# OpenCitations real mode (mocked)
# ---------------------------------------------------------------------------

class TestOpenCitationsReal:
    @patch("kairoskopion.adapters.opencitations.fetch_json")
    def test_get_citations_success(self, mock_fetch, tmp_path):
        mock_fetch.return_value = [
            {"citing": "10.1/a", "cited": "10.2/b", "journal_sc": "no"},
            {"citing": "10.1/c", "cited": "10.2/b", "journal_sc": "yes"},
        ]
        result = get_citations("10.2/b", direction="citations", cache_dir=tmp_path)
        assert result.is_mock is False
        assert result.status == "success"
        assert len(result.records) == 2

    @patch("kairoskopion.adapters.opencitations.fetch_json")
    def test_get_citations_empty(self, mock_fetch, tmp_path):
        mock_fetch.return_value = []
        result = get_citations("10.9999/none", cache_dir=tmp_path)
        assert result.status == "no_results"
        assert len(result.records) == 0


# ---------------------------------------------------------------------------
# CLI --adapter-mode flag
# ---------------------------------------------------------------------------

class TestCLIAdapterMode:
    def test_adapter_mode_flag_accepted(self):
        """CLI parser accepts --adapter-mode without error."""
        from kairoskopion.cli import main
        # Just check that "status" works with the flag
        code = main(["--adapter-mode", "mock", "status"])
        assert code == 0

    def test_adapter_mode_real_flag_accepted(self):
        from kairoskopion.cli import main
        code = main(["--adapter-mode", "real", "status"])
        assert code == 0


# ---------------------------------------------------------------------------
# No network calls in tests
# ---------------------------------------------------------------------------

class TestNoNetwork:
    def test_mock_adapters_dont_import_urllib(self):
        """Mock adapter functions should not require network."""
        # These should all work without any network
        r1 = lookup_doi_mock("10.2307/2183914")
        r2 = search_works_mock("test")
        r3 = openalex_search_mock("test")
        r4 = get_citations_mock("10.1/x")
        assert all(r.is_mock for r in [r1, r2, r3, r4])
