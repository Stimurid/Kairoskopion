"""OpenCitations venue adapter — citation ecology for venue articles."""

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


OPENCITATIONS_FIXTURE = {
    "venue_issn": "2210-5433",
    "sample_dois": [
        "10.1007/s13347-023-00001-x",
        "10.1007/s13347-023-00002-w",
    ],
    "citation_stats": {
        "median_citations_per_article": 8,
        "median_references_per_article": 42,
        "self_citation_rate": 0.05,
    },
    "top_cited_works": [
        {"doi": "10.1007/s13347-020-00400-7", "citations": 85, "title": "AI and moral agency"},
        {"doi": "10.1007/s13347-019-00375-w", "citations": 62, "title": "Technology mediation"},
    ],
}


class OpenCitationsVenueAdapter(VenueAdapter):
    adapter_id = "opencitations_venue"
    source_role = "opencitations_graph"
    source_access_mode = SourceAccessMode.CITATION_GRAPH.value

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
            return self._parse_response(OPENCITATIONS_FIXTURE, query)

        if self._mode == VenueAdapterMode.LIVE_API:
            return self._live_lookup(query, issn=issn)

        if self._mode in (VenueAdapterMode.CACHED, VenueAdapterMode.CACHED_SNAPSHOT):
            return self.degrade_gracefully(query, "cached mode not implemented for OpenCitations")

        return self.degrade_gracefully(query, f"unsupported mode: {self._mode.value}")

    def parse_response(self, data: dict[str, Any], query: dict[str, Any] | None = None) -> VenueAdapterResult:
        return self._parse_response(data, query or {})

    def _live_lookup(
        self, query: dict[str, Any], *, issn: str | None,
    ) -> VenueAdapterResult:
        if not issn:
            return self.degrade_gracefully(query, "ISSN or DOI required for OpenCitations lookup")

        # OpenCitations COCI API uses DOIs, not ISSNs directly
        # For venue-level citation ecology, we'd need to aggregate article DOIs
        return self.degrade_gracefully(
            query, "live_api: venue-level citation ecology requires article DOI aggregation (future)",
        )

    def _parse_response(self, data: dict[str, Any], query: dict[str, Any]) -> VenueAdapterResult:
        claims: list[VenueAdapterClaim] = []
        es = "FACT_FROM_API_METADATA"

        stats = data.get("citation_stats", {})
        if stats.get("median_citations_per_article") is not None:
            claims.append(VenueAdapterClaim(
                "median_citations_per_article",
                stats["median_citations_per_article"],
                es, "medium",
            ))
        if stats.get("median_references_per_article") is not None:
            claims.append(VenueAdapterClaim(
                "median_references_per_article",
                stats["median_references_per_article"],
                es, "medium",
            ))
        if stats.get("self_citation_rate") is not None:
            claims.append(VenueAdapterClaim(
                "self_citation_rate",
                stats["self_citation_rate"],
                es, "medium",
            ))

        top_cited = data.get("top_cited_works", [])
        if top_cited:
            claims.append(VenueAdapterClaim(
                "top_cited_works",
                [{"doi": w.get("doi"), "citations": w.get("citations"), "title": w.get("title")} for w in top_cited],
                es, "medium",
            ))

        unknowns = []
        if not stats:
            unknowns.append("citation statistics unavailable from OpenCitations")

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
