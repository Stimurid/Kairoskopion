"""DOAJ venue adapter — journal inclusion and OA metadata."""

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


DOAJ_FIXTURE = {
    "id": "synth_doaj_001",
    "bibjson": {
        "title": "Synthetic Philosophy of Technology Journal",
        "alternative_title": "SPTJ",
        "pissn": "2210-5433",
        "eissn": "2210-5441",
        "publisher": {
            "name": "Synthetic Academic Press",
            "country": "NL",
        },
        "apc": {
            "has_apc": True,
            "max": [{"currency": "EUR", "price": 2990}],
        },
        "license": [
            {"type": "CC BY", "BY": True, "SA": False, "ND": False, "NC": False},
        ],
        "subject": [
            {"scheme": "LCC", "term": "Philosophy", "code": "B1-5802"},
        ],
        "ref": {
            "aims_scope": "https://example.com/aims",
            "author_instructions": "https://example.com/guidelines",
        },
        "editorial": {
            "review_process": ["Double blind peer review"],
            "review_url": "https://example.com/review-policy",
        },
        "oa_start": {"year": 2015},
    },
    "admin": {
        "in_doaj": True,
        "seal": False,
    },
}


class DOAJVenueAdapter(VenueAdapter):
    adapter_id = "doaj_venue"
    source_role = "doaj_record"
    source_access_mode = SourceAccessMode.INDEX_REGISTRY.value

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
            return self._parse_response(DOAJ_FIXTURE, query)

        if self._mode == VenueAdapterMode.LIVE_API:
            return self._live_lookup(query, issn=issn, name=name)

        if self._mode in (VenueAdapterMode.CACHED, VenueAdapterMode.CACHED_SNAPSHOT):
            return self._cached_lookup(query, issn=issn)

        return self.degrade_gracefully(query, f"unsupported mode: {self._mode.value}")

    def parse_response(self, data: dict[str, Any], query: dict[str, Any] | None = None) -> VenueAdapterResult:
        return self._parse_response(data, query or {})

    def _live_lookup(
        self, query: dict[str, Any], *, issn: str | None, name: str | None,
    ) -> VenueAdapterResult:
        from pathlib import Path

        if issn:
            api_url = f"https://doaj.org/api/search/journals/issn%3A{issn}"
        elif name:
            safe_name = name.replace(" ", "%20")
            api_url = f"https://doaj.org/api/search/journals/{safe_name}"
        else:
            return self.degrade_gracefully(query, "name or ISSN required for DOAJ lookup")

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
                unknowns=[f"DOAJ API error: {http_result.error}"],
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
                unknowns=["No results from DOAJ API"],
                provenance=self.adapter_id,
                fetched_at=_now_iso(),
            )

        result = self._parse_response(results_list[0], query)
        result.fetched_at = _now_iso()
        if http_result.from_cache:
            result.cached_at = result.fetched_at
        return result

    def search_venues(
        self,
        query_text: str,
        *,
        per_page: int = 10,
    ) -> list[VenueAdapterResult]:
        """Search DOAJ for multiple journals matching query_text.

        Returns up to per_page results. Only works in LIVE_API mode.
        """
        if self._mode in (VenueAdapterMode.OFFLINE_STUB, VenueAdapterMode.FIXTURE):
            return []

        if self._mode != VenueAdapterMode.LIVE_API:
            return []

        from pathlib import Path
        from urllib.parse import quote

        safe_q = quote(query_text, safe="")
        api_url = (
            f"https://doaj.org/api/search/journals/{safe_q}"
            f"?pageSize={per_page}"
        )
        cache_path = Path(self._cache_dir) if self._cache_dir else None

        http_result = fetch_json_safe(
            api_url, timeout=self._timeout, cache_dir=cache_path,
        )

        if not http_result.ok:
            return []

        body = http_result.body or {}
        results_list = body.get("results", [])
        out: list[VenueAdapterResult] = []
        for item in results_list:
            result = self._parse_response(item, {"search": query_text})
            result.fetched_at = _now_iso()
            if http_result.from_cache:
                result.cached_at = result.fetched_at
            out.append(result)
        return out

    def _cached_lookup(
        self, query: dict[str, Any], *, issn: str | None,
    ) -> VenueAdapterResult:
        from pathlib import Path
        from ..http_client import read_cache

        if not issn:
            return self.degrade_gracefully(query, "ISSN required for cached DOAJ lookup")

        api_url = f"https://doaj.org/api/search/journals/issn%3A{issn}"
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
                unknowns=["No cached DOAJ data available"],
                provenance=self.adapter_id,
            )

        results_list = cached.get("results", []) if isinstance(cached, dict) else []
        if not results_list:
            return self.degrade_gracefully(query, "Cached DOAJ data has no results")

        result = self._parse_response(results_list[0], query)
        result.cached_at = _now_iso()
        return result

    def _parse_response(self, data: dict[str, Any], query: dict[str, Any]) -> VenueAdapterResult:
        claims: list[VenueAdapterClaim] = []
        es = "FACT_FROM_API_METADATA"
        bib = data.get("bibjson", {})
        admin = data.get("admin", {})

        # DOAJ inclusion is the key claim from this source
        in_doaj = admin.get("in_doaj", False)
        claims.append(VenueAdapterClaim("doaj_inclusion", in_doaj, es, "high",
                                         "DOAJ inclusion status from DOAJ registry"))

        if admin.get("seal"):
            claims.append(VenueAdapterClaim("doaj_seal", True, es, "high"))

        if bib.get("title"):
            claims.append(VenueAdapterClaim("canonical_name", bib["title"], es, "medium"))
        if bib.get("pissn"):
            claims.append(VenueAdapterClaim("issn", bib["pissn"], es, "medium"))
        if bib.get("eissn"):
            claims.append(VenueAdapterClaim("eissn", bib["eissn"], es, "medium"))

        publisher = bib.get("publisher", {})
        if publisher.get("name"):
            claims.append(VenueAdapterClaim("publisher_or_owner", publisher["name"], es, "medium"))
        if publisher.get("country"):
            claims.append(VenueAdapterClaim("country", publisher["country"], es, "medium"))

        apc = bib.get("apc", {})
        if apc.get("has_apc") is not None:
            claims.append(VenueAdapterClaim("has_apc", apc["has_apc"], es, "high"))
        if apc.get("max"):
            claims.append(VenueAdapterClaim("apc_max", apc["max"], es, "medium"))

        licenses = bib.get("license", [])
        if licenses:
            license_types = [lic.get("type", "unknown") for lic in licenses]
            claims.append(VenueAdapterClaim("license", license_types, es, "medium"))

        subjects = bib.get("subject", [])
        if subjects:
            subj_terms = [s.get("term", "") for s in subjects if s.get("term")]
            claims.append(VenueAdapterClaim("subjects", subj_terms, es, "medium"))

        editorial = bib.get("editorial", {})
        if editorial.get("review_process"):
            claims.append(VenueAdapterClaim("review_process", editorial["review_process"], es, "medium"))

        oa_start = bib.get("oa_start")
        if isinstance(oa_start, dict) and oa_start.get("year"):
            claims.append(VenueAdapterClaim("oa_start_year", oa_start["year"], es, "medium"))
        elif isinstance(oa_start, (int, str)) and oa_start:
            claims.append(VenueAdapterClaim("oa_start_year", oa_start, es, "medium"))

        unknowns = []
        if not bib.get("title"):
            unknowns.append("journal title not found in DOAJ")
        if not in_doaj:
            unknowns.append("journal not currently in DOAJ")

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
