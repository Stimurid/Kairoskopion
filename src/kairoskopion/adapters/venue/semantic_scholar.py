"""Semantic Scholar venue adapter — citation graph and recommendation data."""

from __future__ import annotations

from typing import Any

from ...enums import SourceAccessMode
from .base import (
    VenueAdapter,
    VenueAdapterClaim,
    VenueAdapterMode,
    VenueAdapterResult,
    VenueAdapterStatus,
    _now_iso,
)


SEMANTIC_SCHOLAR_FIXTURE = {
    "venue_id": "synth_s2_001",
    "name": "Synthetic Philosophy of Technology Journal",
    "alternate_names": ["SPTJ", "Synth Phil Tech"],
    "issn": "2210-5433",
    "url": "https://example.com/sptj",
    "paper_count": 842,
    "citation_count": 14230,
    "h_index": 38,
    "highly_influential_citation_count": 1250,
    "fields_of_study": [
        "Philosophy", "Computer Science", "Engineering",
    ],
    "top_authors": [
        {"name": "A. Synthetic", "paper_count": 12, "citation_count": 450},
        {"name": "B. Heuristic", "paper_count": 8, "citation_count": 320},
    ],
    "recommended_venues": [
        {"name": "Philosophy & Technology", "similarity": 0.85},
        {"name": "Techné: Research in Philosophy and Technology", "similarity": 0.78},
        {"name": "Science, Technology, & Human Values", "similarity": 0.72},
    ],
}


class SemanticScholarVenueAdapter(VenueAdapter):
    adapter_id = "semantic_scholar_recommendations"
    source_role = "semantic_scholar_recommendations"
    source_access_mode = SourceAccessMode.CITATION_GRAPH.value

    def __init__(
        self,
        mode: VenueAdapterMode = VenueAdapterMode.OFFLINE_STUB,
        *,
        api_key: str | None = None,
        cache_dir: str | None = None,
        timeout: int = 30,
    ) -> None:
        super().__init__(mode)
        self._api_key = api_key
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
            return self._parse_response(SEMANTIC_SCHOLAR_FIXTURE, query)

        if self._mode == VenueAdapterMode.LIVE_API:
            return self.degrade_gracefully(
                query, "Live Semantic Scholar API not yet implemented"
            )

        if self._mode in (VenueAdapterMode.CACHED, VenueAdapterMode.CACHED_SNAPSHOT):
            return self.degrade_gracefully(
                query, "Cached Semantic Scholar lookup not yet implemented"
            )

        return self.degrade_gracefully(query, f"unsupported mode: {self._mode.value}")

    def _parse_response(
        self, data: dict[str, Any], query: dict[str, Any],
    ) -> VenueAdapterResult:
        claims: list[VenueAdapterClaim] = []
        es = "FACT_FROM_API_METADATA"

        if data.get("name"):
            claims.append(VenueAdapterClaim("canonical_name", data["name"], es, "medium"))

        if data.get("paper_count"):
            claims.append(VenueAdapterClaim("paper_count", data["paper_count"], es, "high"))

        if data.get("citation_count"):
            claims.append(VenueAdapterClaim("citation_count", data["citation_count"], es, "high"))

        if data.get("h_index"):
            claims.append(VenueAdapterClaim("h_index", data["h_index"], es, "high"))

        if data.get("highly_influential_citation_count"):
            claims.append(VenueAdapterClaim(
                "highly_influential_citation_count",
                data["highly_influential_citation_count"], es, "medium",
            ))

        fields = data.get("fields_of_study", [])
        if fields:
            claims.append(VenueAdapterClaim("fields_of_study", fields, es, "medium"))

        top_authors = data.get("top_authors", [])
        if top_authors:
            claims.append(VenueAdapterClaim(
                "top_authors",
                [a["name"] for a in top_authors if a.get("name")],
                es, "low",
            ))

        recommended = data.get("recommended_venues", [])
        if recommended:
            claims.append(VenueAdapterClaim(
                "recommended_venues",
                [{"name": r["name"], "similarity": r.get("similarity")} for r in recommended],
                es, "medium",
                "Similar venues by citation overlap",
            ))

        unknowns: list[str] = []
        if not data.get("paper_count"):
            unknowns.append("No paper count from Semantic Scholar")

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
