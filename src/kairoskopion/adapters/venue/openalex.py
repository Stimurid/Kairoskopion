"""OpenAlex venue adapter — offline/live modes for venue identity and metadata."""

from __future__ import annotations

from typing import Any

from .base import VenueAdapter, VenueAdapterClaim, VenueAdapterMode, VenueAdapterResult


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

    def lookup_venue(
        self,
        *,
        name: str | None = None,
        issn: str | None = None,
        url: str | None = None,
    ) -> VenueAdapterResult:
        query = {"name": name, "issn": issn, "url": url}

        if self._mode == VenueAdapterMode.OFFLINE_STUB:
            return self._parse_fixture(OPENALEX_FIXTURE, query)

        if self._mode == VenueAdapterMode.LIVE_API:
            return self.degrade_gracefully(query, "live_api mode not yet implemented")

        return self.degrade_gracefully(query, f"unsupported mode: {self._mode.value}")

    def parse_response(self, data: dict[str, Any], query: dict[str, Any] | None = None) -> VenueAdapterResult:
        return self._parse_fixture(data, query or {})

    def _parse_fixture(self, data: dict[str, Any], query: dict[str, Any]) -> VenueAdapterResult:
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

        unknowns = []
        if not data.get("display_name"):
            unknowns.append("canonical_name not found in OpenAlex")
        if not data.get("issn_l"):
            unknowns.append("ISSN not found in OpenAlex")

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
