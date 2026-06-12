"""OpenCitations venue adapter — citation ecology for venue articles."""

from __future__ import annotations

from typing import Any

from .base import VenueAdapter, VenueAdapterClaim, VenueAdapterMode, VenueAdapterResult


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

    def lookup_venue(
        self,
        *,
        name: str | None = None,
        issn: str | None = None,
        url: str | None = None,
    ) -> VenueAdapterResult:
        query = {"name": name, "issn": issn, "url": url}

        if self._mode == VenueAdapterMode.OFFLINE_STUB:
            return self._parse_fixture(OPENCITATIONS_FIXTURE, query)

        if self._mode == VenueAdapterMode.LIVE_API:
            return self.degrade_gracefully(query, "live_api mode not yet implemented")

        return self.degrade_gracefully(query, f"unsupported mode: {self._mode.value}")

    def parse_response(self, data: dict[str, Any], query: dict[str, Any] | None = None) -> VenueAdapterResult:
        return self._parse_fixture(data, query or {})

    def _parse_fixture(self, data: dict[str, Any], query: dict[str, Any]) -> VenueAdapterResult:
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

        return VenueAdapterResult(
            adapter_id=self.adapter_id,
            mode=self._mode.value,
            query=query,
            status="success" if claims else "no_results",
            evidence_status=es,
            source_role=self.source_role,
            claims=claims,
            raw_data=data,
            unknowns=unknowns,
        )
