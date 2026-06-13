"""OpenAlex venue adapter — offline/fixture/cached/live modes for venue metadata."""

from __future__ import annotations

from typing import Any

from ...enums import SourceAccessMode
from ..http_client import fetch_json_safe
from .base import (
    VenueAdapter,
    VenueAdapterClaim,
    VenueAdapterMode,
    VenueAdapterResult,
    VenueAdapterStatus,
    _now_iso,
)


OPENALEX_FIXTURE = {
    "id": "https://openalex.org/S4210169036",
    "display_name": "Philosophy & Technology",
    "issn_l": "2210-5433",
    "issn": ["2210-5433", "2210-5441"],
    "publisher": "Springer Nature",
    "type": "journal",
    "homepage_url": "https://www.springer.com/journal/13347",
    "works_count": 1250,
    "cited_by_count": 18500,
    "topics": [
        {"display_name": "Philosophy of Technology"},
        {"display_name": "Ethics of AI"},
        {"display_name": "Science and Technology Studies"},
    ],
    "x_concepts": [
        {"display_name": "Philosophy", "level": 0, "score": 0.85},
        {"display_name": "Computer Science", "level": 0, "score": 0.35},
    ],
}


class OpenAlexVenueAdapter(VenueAdapter):
    adapter_id = "openalex_venue"
    source_role = "openalex_source"
    source_access_mode = SourceAccessMode.METADATA_API.value

    def __init__(
        self,
        mode: VenueAdapterMode = VenueAdapterMode.OFFLINE_STUB,
        *,
        cache_dir: str | None = None,
        timeout: int = 30,
    ) -> None:
        super().__init__(mode)
        self._cache_dir = cache_dir
        self._timeout = timeout

    def lookup_venue(
        self,
        *,
        name: str | None = None,
        issn: str | None = None,
        url: str | None = None,
    ) -> VenueAdapterResult:
        query = {"name": name, "issn": issn, "url": url}

        if self._mode in (VenueAdapterMode.OFFLINE_STUB, VenueAdapterMode.FIXTURE):
            return self._parse_response(OPENALEX_FIXTURE, query)

        if self._mode == VenueAdapterMode.LIVE_API:
            return self._live_lookup(query, name=name, issn=issn)

        if self._mode in (VenueAdapterMode.CACHED, VenueAdapterMode.CACHED_SNAPSHOT):
            return self._cached_lookup(query, name=name, issn=issn)

        return self.degrade_gracefully(query, f"unsupported mode: {self._mode.value}")

    def parse_response(self, data: dict[str, Any], query: dict[str, Any] | None = None) -> VenueAdapterResult:
        return self._parse_response(data, query or {})

    def _live_lookup(
        self, query: dict[str, Any], *, name: str | None, issn: str | None,
    ) -> VenueAdapterResult:
        from pathlib import Path

        search_term = issn or name
        if not search_term:
            return self.degrade_gracefully(query, "name or ISSN required")

        api_url = f"https://api.openalex.org/sources?search={search_term}&per_page=1"
        cache_path = Path(self._cache_dir) if self._cache_dir else None

        http_result = fetch_json_safe(
            api_url, timeout=self._timeout, cache_dir=cache_path,
        )

        if not http_result.ok:
            return VenueAdapterResult(
                adapter_id=self.adapter_id,
                mode=self._mode.value,
                query=query,
                status=VenueAdapterStatus.ERROR.value,
                source_access_mode=self.source_access_mode,
                evidence_status="UNKNOWN",
                source_role=self.source_role,
                error=http_result.error,
                unknowns=[f"OpenAlex API error: {http_result.error}"],
                provenance=self.adapter_id,
                fetched_at=_now_iso(),
            )

        body = http_result.body or {}
        results_list = body.get("results", [])
        if not results_list:
            return VenueAdapterResult(
                adapter_id=self.adapter_id,
                mode=self._mode.value,
                query=query,
                status=VenueAdapterStatus.NO_RESULTS.value,
                source_access_mode=self.source_access_mode,
                evidence_status="UNKNOWN",
                source_role=self.source_role,
                unknowns=["No results from OpenAlex API"],
                provenance=self.adapter_id,
                fetched_at=_now_iso(),
            )

        result = self._parse_response(results_list[0], query)
        result.fetched_at = _now_iso()
        if http_result.from_cache:
            result.cached_at = result.fetched_at
        return result

    def _cached_lookup(
        self, query: dict[str, Any], *, name: str | None, issn: str | None,
    ) -> VenueAdapterResult:
        from pathlib import Path
        from ..http_client import read_cache

        search_term = issn or name
        if not search_term:
            return self.degrade_gracefully(query, "name or ISSN required")

        api_url = f"https://api.openalex.org/sources?search={search_term}&per_page=1"
        cache_path = Path(self._cache_dir) if self._cache_dir else None
        cached = read_cache(api_url, cache_dir=cache_path)

        if cached is None:
            return VenueAdapterResult(
                adapter_id=self.adapter_id,
                mode=self._mode.value,
                query=query,
                status=VenueAdapterStatus.UNAVAILABLE.value,
                source_access_mode=self.source_access_mode,
                evidence_status="UNKNOWN",
                source_role=self.source_role,
                error="no_cache_hit",
                unknowns=["No cached OpenAlex data available"],
                provenance=self.adapter_id,
            )

        results_list = cached.get("results", []) if isinstance(cached, dict) else []
        if not results_list:
            return VenueAdapterResult(
                adapter_id=self.adapter_id,
                mode=self._mode.value,
                query=query,
                status=VenueAdapterStatus.NO_RESULTS.value,
                source_access_mode=self.source_access_mode,
                evidence_status="UNKNOWN",
                source_role=self.source_role,
                unknowns=["Cached OpenAlex data has no results"],
                provenance=self.adapter_id,
            )

        result = self._parse_response(results_list[0], query)
        result.cached_at = _now_iso()
        return result

    def _parse_response(self, data: dict[str, Any], query: dict[str, Any]) -> VenueAdapterResult:
        claims: list[VenueAdapterClaim] = []
        es = "FACT_FROM_API_METADATA"

        if data.get("display_name"):
            claims.append(VenueAdapterClaim("canonical_name", data["display_name"], es, "high"))
        if data.get("issn_l"):
            claims.append(VenueAdapterClaim("issn", data["issn_l"], es, "high"))
        if data.get("issn"):
            for extra in data["issn"]:
                if extra != data.get("issn_l"):
                    claims.append(VenueAdapterClaim("eissn", extra, es, "high"))
        if data.get("publisher"):
            claims.append(VenueAdapterClaim("publisher_or_owner", data["publisher"], es, "high"))
        if data.get("type"):
            claims.append(VenueAdapterClaim("venue_type", data["type"], es, "high"))
        if data.get("homepage_url"):
            claims.append(VenueAdapterClaim("official_urls", data["homepage_url"], es, "medium"))
        if data.get("works_count"):
            claims.append(VenueAdapterClaim("works_count", data["works_count"], es, "high"))
        if data.get("cited_by_count"):
            claims.append(VenueAdapterClaim("cited_by_count", data["cited_by_count"], es, "high"))
        if data.get("topics"):
            topic_names = [t["display_name"] for t in data["topics"]]
            claims.append(VenueAdapterClaim("topics", topic_names, es, "medium"))
        if data.get("x_concepts"):
            concepts = [
                {"name": c["display_name"], "level": c.get("level"), "score": c.get("score")}
                for c in data["x_concepts"]
            ]
            claims.append(VenueAdapterClaim("concepts", concepts, es, "medium"))
        if data.get("id"):
            claims.append(VenueAdapterClaim("openalex_id", data["id"], es, "high"))
        if data.get("country_code"):
            claims.append(VenueAdapterClaim("country", data["country_code"], es, "medium"))

        unknowns = []
        if not data.get("display_name"):
            unknowns.append("canonical_name not found in OpenAlex")
        if not data.get("issn_l"):
            unknowns.append("ISSN not found in OpenAlex")

        result = VenueAdapterResult(
            adapter_id=self.adapter_id,
            mode=self._mode.value,
            query=query,
            status=VenueAdapterStatus.SUCCESS.value if claims else VenueAdapterStatus.NO_RESULTS.value,
            source_access_mode=self.source_access_mode,
            evidence_status=es,
            source_role=self.source_role,
            claims=claims,
            raw_data=data,
            unknowns=unknowns,
            provenance=self.adapter_id,
        )
        return self._attach_authority(result)
