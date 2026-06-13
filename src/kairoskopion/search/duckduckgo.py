"""DuckDuckGo search backend — zero external dependencies.

Uses DDG Instant Answer API (api.duckduckgo.com) for reliable results
without scraping. If ``duckduckgo-search`` package is installed, uses
it for richer full-text results.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .provider import SearchResult, WebSearchProvider

logger = logging.getLogger(__name__)

_DDG_API = "https://api.duckduckgo.com/"
_TIMEOUT = 15


class DuckDuckGoProvider(WebSearchProvider):
    """DuckDuckGo search — instant answer API + optional full-text."""

    @property
    def name(self) -> str:
        return "duckduckgo"

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        # Try duckduckgo-search package first (richer results)
        try:
            return self._search_via_package(query, max_results)
        except ImportError:
            pass
        except Exception as exc:
            logger.debug("duckduckgo-search package failed, falling back to API: %s", exc)

        # Fallback: DDG Instant Answer API (free, no deps)
        return self._search_via_api(query, max_results)

    def _search_via_package(self, query: str, max_results: int) -> list[SearchResult]:
        from duckduckgo_search import DDGS  # type: ignore[import-untyped]

        results: list[SearchResult] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    source="duckduckgo_text",
                ))
        return results

    def _search_via_api(self, query: str, max_results: int) -> list[SearchResult]:
        params = urllib.parse.urlencode({
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        })
        url = f"{_DDG_API}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Kairoskopion/1.0"})

        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            logger.warning("DDG API request failed: %s", exc)
            return []

        results: list[SearchResult] = []

        # Abstract (main instant answer)
        abstract = data.get("Abstract", "")
        if abstract:
            results.append(SearchResult(
                title=data.get("Heading", query),
                url=data.get("AbstractURL", ""),
                snippet=abstract,
                source="duckduckgo_instant",
            ))

        # Related topics
        for topic in data.get("RelatedTopics", []):
            if len(results) >= max_results:
                break
            if isinstance(topic, dict) and "Text" in topic:
                results.append(SearchResult(
                    title=topic.get("Text", "")[:120],
                    url=topic.get("FirstURL", ""),
                    snippet=topic.get("Text", ""),
                    source="duckduckgo_related",
                ))

        return results


def get_search_provider() -> WebSearchProvider:
    """Factory — returns the best available search provider."""
    return DuckDuckGoProvider()
