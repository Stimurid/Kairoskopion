"""Unpaywall adapter — article-level OA access lookup by DOI."""

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


UNPAYWALL_FIXTURE = {
    "doi": "10.1007/s13347-023-00001-x",
    "is_oa": True,
    "best_oa_location": {
        "url": "https://link.springer.com/article/10.1007/s13347-023-00001-x",
        "url_for_pdf": "https://link.springer.com/content/pdf/10.1007/s13347-023-00001-x.pdf",
        "host_type": "publisher",
        "license": "cc-by",
        "version": "publishedVersion",
    },
    "oa_status": "gold",
    "journal_is_oa": False,
    "journal_issns": "2210-5433,2210-5441",
    "journal_name": "Philosophy & Technology",
    "publisher": "Springer Nature",
    "title": "Synthetic article on technology mediation and AI ethics",
}


class UnpaywallAdapter(VenueAdapter):
    adapter_id = "unpaywall"
    source_role = "unpaywall_oa"
    source_access_mode = SourceAccessMode.METADATA_API.value

    def __init__(
        self,
        mode: VenueAdapterMode = VenueAdapterMode.OFFLINE_STUB,
        *,
        email: str = "kairoskopion@proton.me",
        cache_dir: str | None = None,
        timeout: int = 30,
    ) -> None:
        super().__init__(mode)
        self._email = email
        self._cache_dir = cache_dir
        self._timeout = timeout

    def lookup_venue(
        self,
        *,
        name: str | None = None,
        issn: str | None = None,
        url: str | None = None,
    ) -> VenueAdapterResult:
        # Unpaywall works by DOI, not venue lookup
        # This method exists for interface compatibility but returns limited data
        query = {"name": name, "issn": issn, "url": url}
        return self.degrade_gracefully(query, "Unpaywall requires DOI; use lookup_by_doi()")

    def lookup_by_doi(self, doi: str) -> VenueAdapterResult:
        query = {"doi": doi}

        if self._mode in (VenueAdapterMode.OFFLINE_STUB, VenueAdapterMode.FIXTURE):
            return self._parse_response(UNPAYWALL_FIXTURE, query)

        if self._mode == VenueAdapterMode.LIVE_API:
            return self._live_lookup(query, doi=doi)

        if self._mode in (VenueAdapterMode.CACHED, VenueAdapterMode.CACHED_SNAPSHOT):
            return self._cached_lookup(query, doi=doi)

        return self.degrade_gracefully(query, f"unsupported mode: {self._mode.value}")

    def parse_response(self, data: dict[str, Any], query: dict[str, Any] | None = None) -> VenueAdapterResult:
        return self._parse_response(data, query or {})

    def _live_lookup(self, query: dict[str, Any], *, doi: str) -> VenueAdapterResult:
        from pathlib import Path

        api_url = f"https://api.unpaywall.org/v2/{doi}?email={self._email}"
        cache_path = Path(self._cache_dir) if self._cache_dir else None

        http_result = fetch_json_safe(api_url, timeout=self._timeout, cache_dir=cache_path)

        if not http_result.ok:
            return VenueAdapterResult(
                adapter_id=self.adapter_id,
                mode=self._mode.value,
                query=query,
                status=VenueAdapterStatus.ERROR.value if http_result.error != "not_found" else VenueAdapterStatus.NO_RESULTS.value,
                source_access_mode=self.source_access_mode,
                evidence_status="UNKNOWN",
                source_role=self.source_role,
                error=http_result.error,
                unknowns=[f"Unpaywall API error: {http_result.error}"],
                provenance=self.adapter_id,
                fetched_at=_now_iso(),
            )

        result = self._parse_response(http_result.body or {}, query)
        result.fetched_at = _now_iso()
        if http_result.from_cache:
            result.cached_at = result.fetched_at
        return result

    def _cached_lookup(self, query: dict[str, Any], *, doi: str) -> VenueAdapterResult:
        from pathlib import Path
        from ..http_client import read_cache

        api_url = f"https://api.unpaywall.org/v2/{doi}?email={self._email}"
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
                unknowns=["No cached Unpaywall data available"],
                provenance=self.adapter_id,
            )

        result = self._parse_response(cached, query)
        result.cached_at = _now_iso()
        return result

    def _parse_response(self, data: dict[str, Any], query: dict[str, Any]) -> VenueAdapterResult:
        claims: list[VenueAdapterClaim] = []
        es = "FACT_FROM_API_METADATA"

        if "is_oa" in data:
            claims.append(VenueAdapterClaim("is_oa", data["is_oa"], es, "high"))
        if data.get("oa_status"):
            claims.append(VenueAdapterClaim("oa_status", data["oa_status"], es, "high"))

        best_loc = data.get("best_oa_location", {})
        if best_loc:
            if best_loc.get("url"):
                claims.append(VenueAdapterClaim("best_oa_url", best_loc["url"], es, "high"))
            if best_loc.get("host_type"):
                claims.append(VenueAdapterClaim("host_type", best_loc["host_type"], es, "medium"))
            if best_loc.get("license"):
                claims.append(VenueAdapterClaim("oa_license", best_loc["license"], es, "medium"))
            if best_loc.get("version"):
                claims.append(VenueAdapterClaim("oa_version", best_loc["version"], es, "medium"))

        if "journal_is_oa" in data:
            claims.append(VenueAdapterClaim("journal_is_oa", data["journal_is_oa"], es, "medium"))
        if data.get("journal_name"):
            claims.append(VenueAdapterClaim("journal_name", data["journal_name"], es, "medium"))
        if data.get("publisher"):
            claims.append(VenueAdapterClaim("publisher", data["publisher"], es, "medium"))

        unknowns = []
        if "is_oa" not in data:
            unknowns.append("OA status unknown from Unpaywall")
        if not best_loc:
            unknowns.append("no OA location found")

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
