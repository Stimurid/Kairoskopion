"""URL hop adapter tests — fixture HTML only, no network."""

from __future__ import annotations

import re

from kairoskopion.adapters.venue.venue_url_hop import (
    CATEGORY_PATTERNS,
    _same_host,
    _strip_text,
    discover_urls_from_homepage,
)


FAKE_HOMEPAGE_HTML = """<!doctype html>
<html><head><title>J of Test</title></head><body>
  <nav>
    <a href="/about/aims-and-scope">Aims and Scope</a>
    <a href="/authors/instructions-for-authors">Instructions for Authors</a>
    <a href="https://otherdomain.example/foo">External link</a>
    <a href="/submit/manuscript">Submit Manuscript</a>
    <a href="/editorial-board">Editorial Board</a>
    <a href="/oa/open-access-policy">Open Access</a>
    <a href="#section">In-page anchor</a>
  </nav>
  <p>Some readable journal description content here at least 200 chars long
  to avoid the JS-only path. Lorem ipsum dolor sit amet, consectetur
  adipiscing elit. Sed do eiusmod tempor incididunt ut labore et
  dolore magna aliqua. Ut enim ad minim veniam, quis nostrud
  exercitation ullamco laboris.</p>
</body></html>"""


class TestUrlHopUnit:
    def test_strip_text_removes_scripts(self):
        html = "<p>hi</p><script>bad()</script><p>bye</p>"
        out = _strip_text(html)
        assert "hi" in out and "bye" in out
        assert "bad()" not in out

    def test_same_host_check(self):
        assert _same_host("https://www.example.org/x", "example.org")
        assert _same_host("https://example.org/", "example.org")
        assert not _same_host("https://other.com/x", "example.org")

    def test_category_patterns_cover_all_required(self):
        # The five required categories per task C
        for cat in (
            "guidelines", "submission_info", "editorial_board",
            "aims_scope", "policy_oa_apc",
        ):
            assert cat in CATEGORY_PATTERNS
            assert all(isinstance(p, re.Pattern) for p in CATEGORY_PATTERNS[cat])


class TestUrlHopFixtureExtraction:
    """Drive the discover function with pre-fetched HTML via monkeypatch."""

    def test_extracts_all_categories_from_fixture(self, monkeypatch):
        # Patch _fetch to return our fixture HTML
        from kairoskopion.adapters.venue import venue_url_hop as mod
        monkeypatch.setattr(
            mod, "_fetch",
            lambda url, timeout=15: (FAKE_HOMEPAGE_HTML, "opened"),
        )
        result = discover_urls_from_homepage("https://test.example.org/")
        assert result["homepage_access_status"] == "opened"
        d = result["discovered"]
        assert any("instructions-for-authors" in u for u in d["guidelines"])
        assert any("submit/manuscript" in u for u in d["submission_info"])
        assert any("editorial-board" in u for u in d["editorial_board"])
        assert any("aims-and-scope" in u for u in d["aims_scope"])
        assert any("open-access-policy" in u for u in d["policy_oa_apc"])

    def test_external_links_filtered_out(self, monkeypatch):
        from kairoskopion.adapters.venue import venue_url_hop as mod
        monkeypatch.setattr(
            mod, "_fetch",
            lambda url, timeout=15: (FAKE_HOMEPAGE_HTML, "opened"),
        )
        result = discover_urls_from_homepage("https://test.example.org/")
        # External link must not appear in any category
        for cat_urls in result["discovered"].values():
            for u in cat_urls:
                assert "otherdomain.example" not in u

    def test_no_homepage_returns_unknown(self):
        result = discover_urls_from_homepage("")
        assert result["homepage_access_status"] == "unknown"
        assert any("no homepage_url" in w for w in result["warnings"])

    def test_inaccessible_homepage_marks_status(self, monkeypatch):
        from kairoskopion.adapters.venue import venue_url_hop as mod
        monkeypatch.setattr(
            mod, "_fetch",
            lambda url, timeout=15: (None, "http_403"),
        )
        result = discover_urls_from_homepage("https://example.org/")
        assert result["homepage_access_status"] == "http_403"
        # All categories remain empty — UNKNOWN_NOT_FOUND semantically
        for v in result["discovered"].values():
            assert v == []

    def test_js_only_thin_page_detected(self, monkeypatch):
        from kairoskopion.adapters.venue import venue_url_hop as mod
        monkeypatch.setattr(
            mod, "_fetch",
            lambda url, timeout=15: ("<html><body><div id=root></div></body></html>",
                                       "opened"),
        )
        result = discover_urls_from_homepage("https://x.example.org/")
        assert result["homepage_access_status"] == "js_only"
