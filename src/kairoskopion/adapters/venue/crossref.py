"""Crossref venue adapter — offline/live modes for DOI and journal metadata."""

from __future__ import annotations

from typing import Any

from .base import VenueAdapter, VenueAdapterClaim, VenueAdapterMode, VenueAdapterResult


CROSSREF_FIXTURE = {
    "ISSN": ["2210-5433", "2210-5441"],
    "title": "Philosophy & Technology",
    "publisher": "Springer Science and Business Media LLC",
    "subjects": [
        {"name": "Philosophy", "ASJC": 1211},
        {"name": "Computer Science (miscellaneous)", "ASJC": 1701},
    ],
    "counts": {"total-dois": 980, "current-dois": 120},
    "coverage": {
        "references-backfile": 0.92,
        "orcids-backfile": 0.45,
        "abstracts-backfile": 0.88,
    },
    "last-status-check-time": "2026-05-15",
    "flags": {"deposits-articles": True},
}


class CrossrefVenueAdapter(VenueAdapter):
    adapter_id = "crossref_venue"
    source_role = "crossref_journal"

    def lookup_venue(
        self,
        *,
        name: str | None = None,
        issn: str | None = None,
        url: str | None = None,
    ) -> VenueAdapterResult:
        query = {"name": name, "issn": issn, "url": url}

        if self._mode == VenueAdapterMode.OFFLINE_STUB:
            return self._parse_fixture(CROSSREF_FIXTURE, query)

        if self._mode == VenueAdapterMode.LIVE_API:
            return self.degrade_gracefully(query, "live_api mode not yet implemented")

        return self.degrade_gracefully(query, f"unsupported mode: {self._mode.value}")

    def parse_response(self, data: dict[str, Any], query: dict[str, Any] | None = None) -> VenueAdapterResult:
        return self._parse_fixture(data, query or {})

    def _parse_fixture(self, data: dict[str, Any], query: dict[str, Any]) -> VenueAdapterResult:
        claims: list[VenueAdapterClaim] = []
        es = "FACT_FROM_API_METADATA"

        if data.get("title"):
            claims.append(VenueAdapterClaim("canonical_name", data["title"], es, "high"))
        if data.get("ISSN"):
            for issn_val in data["ISSN"]:
                claims.append(VenueAdapterClaim("issn", issn_val, es, "high"))
        if data.get("publisher"):
            claims.append(VenueAdapterClaim("publisher_or_owner", data["publisher"], es, "high"))
        if data.get("subjects"):
            subj_names = [s["name"] for s in data["subjects"]]
            claims.append(VenueAdapterClaim("subjects", subj_names, es, "medium"))
        if data.get("counts"):
            claims.append(VenueAdapterClaim("doi_count", data["counts"].get("total-dois"), es, "high"))
        if data.get("coverage"):
            claims.append(VenueAdapterClaim("metadata_coverage", data["coverage"], es, "medium"))

        unknowns = []
        if not data.get("title"):
            unknowns.append("journal title not found in Crossref")
        if not data.get("ISSN"):
            unknowns.append("ISSN not found in Crossref")

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
