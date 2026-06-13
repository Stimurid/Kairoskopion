"""Sherpa RoMEO venue adapter — OA policy and self-archiving rights."""

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


SHERPA_FIXTURE = {
    "id": "synth_sherpa_001",
    "title": "Synthetic Philosophy of Technology Journal",
    "issn": "2210-5433",
    "publisher": {"name": "Synthetic Academic Press"},
    "publisher_policy": [
        {
            "id": "synth_policy_001",
            "permitted_oa": [
                {
                    "article_version": ["submitted", "accepted"],
                    "location": {
                        "location": ["authors_homepage", "institutional_repository"],
                    },
                    "conditions": ["Must link to publisher version"],
                    "embargo": {"amount": 12, "units": "months"},
                    "license": [{"license": "cc_by"}],
                },
                {
                    "article_version": ["published"],
                    "location": {"location": ["this_journal"]},
                    "conditions": ["APC paid"],
                    "license": [{"license": "cc_by"}],
                },
            ],
            "open_access_prohibited": False,
        },
    ],
    "system_metadata": {
        "date_modified": "2025-10-15",
    },
}


class SherpaVenueAdapter(VenueAdapter):
    adapter_id = "sherpa_policy"
    source_role = "sherpa_policy"
    source_access_mode = SourceAccessMode.INDEX_REGISTRY.value

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
            return self._parse_response(SHERPA_FIXTURE, query)

        if self._mode == VenueAdapterMode.LIVE_API:
            return self.degrade_gracefully(
                query, "Live Sherpa RoMEO API requires API key — not yet implemented"
            )

        if self._mode in (VenueAdapterMode.CACHED, VenueAdapterMode.CACHED_SNAPSHOT):
            return self.degrade_gracefully(query, "Cached Sherpa lookup not yet implemented")

        return self.degrade_gracefully(query, f"unsupported mode: {self._mode.value}")

    def _parse_response(
        self, data: dict[str, Any], query: dict[str, Any],
    ) -> VenueAdapterResult:
        claims: list[VenueAdapterClaim] = []
        es = "FACT_FROM_API_METADATA"

        if data.get("title"):
            claims.append(VenueAdapterClaim("canonical_name", data["title"], es, "medium"))

        publisher = data.get("publisher", {})
        if publisher.get("name"):
            claims.append(VenueAdapterClaim("publisher_or_owner", publisher["name"], es, "medium"))

        policies = data.get("publisher_policy", [])
        if policies:
            policy = policies[0]
            oa_prohibited = policy.get("open_access_prohibited", True)
            claims.append(VenueAdapterClaim("oa_prohibited", oa_prohibited, es, "high"))

            permitted = policy.get("permitted_oa", [])
            archiving_versions = set()
            embargo_months = None
            for perm in permitted:
                for v in perm.get("article_version", []):
                    archiving_versions.add(v)
                embargo = perm.get("embargo", {})
                if embargo.get("units") == "months" and embargo.get("amount"):
                    current = embargo["amount"]
                    if embargo_months is None or current > embargo_months:
                        embargo_months = current

            if archiving_versions:
                claims.append(VenueAdapterClaim(
                    "self_archiving_versions", sorted(archiving_versions), es, "high",
                ))
            if embargo_months is not None:
                claims.append(VenueAdapterClaim("embargo_months", embargo_months, es, "high"))

            locations = set()
            for perm in permitted:
                loc = perm.get("location", {})
                for l in loc.get("location", []):
                    locations.add(l)
            if locations:
                claims.append(VenueAdapterClaim(
                    "archiving_locations", sorted(locations), es, "medium",
                ))

        unknowns: list[str] = []
        if not policies:
            unknowns.append("No publisher policy found in Sherpa")

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
