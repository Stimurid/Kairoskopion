"""Venue snapshot crawler — stores provided HTML/text into vault.

No mass crawling. Accepts explicit URL or provided content only.
"""

from __future__ import annotations

from typing import Any

from ...enums import SourceAccessMode
from ..http_client import fetch_text_safe
from .base import (
    VenueAdapter,
    VenueAdapterClaim,
    VenueAdapterMode,
    VenueAdapterResult,
    VenueAdapterStatus,
    _now_iso,
)

SNAPSHOT_FIXTURE_HTML = """\
<html>
<head><title>Philosophy &amp; Technology - Author Guidelines</title></head>
<body>
<h1>Author Guidelines</h1>
<p>Philosophy &amp; Technology publishes original research articles in the
philosophy of technology, ethics of AI, and science and technology studies.</p>
<h2>Submission Guidelines</h2>
<ul>
  <li>Maximum word count: 10,000 words including references</li>
  <li>Abstract: 150-250 words</li>
  <li>Keywords: 4-6</li>
  <li>Reference style: APA 7th edition</li>
  <li>Review process: Double-blind peer review</li>
  <li>Language: English</li>
</ul>
<h2>Open Access</h2>
<p>Hybrid journal. APC for gold OA: EUR 2,990.</p>
<h2>Ethics</h2>
<p>Authors must disclose AI tool usage in a dedicated section.</p>
</body>
</html>
"""


class VenueSnapshotCrawler(VenueAdapter):
    adapter_id = "venue_snapshot_crawler"
    source_role = "official_homepage"
    source_access_mode = SourceAccessMode.OFFICIAL_WEBPAGE.value

    def __init__(
        self,
        mode: VenueAdapterMode = VenueAdapterMode.OFFLINE_STUB,
        vault: Any | None = None,
        *,
        is_official: bool = True,
        timeout: int = 30,
    ) -> None:
        super().__init__(mode)
        self._vault = vault
        self._is_official = is_official
        self._timeout = timeout
        if not is_official:
            self.source_access_mode = SourceAccessMode.MANUAL_NOTE.value

    def lookup_venue(
        self,
        *,
        name: str | None = None,
        issn: str | None = None,
        url: str | None = None,
    ) -> VenueAdapterResult:
        query = {"name": name, "issn": issn, "url": url}

        if self._mode in (VenueAdapterMode.OFFLINE_STUB, VenueAdapterMode.FIXTURE):
            return self.store_html(SNAPSHOT_FIXTURE_HTML, url=url or "https://example.com/guidelines", query=query)

        if self._mode == VenueAdapterMode.LIVE_API:
            if not url:
                return self.degrade_gracefully(query, "URL required for live snapshot crawl")
            return self._live_fetch(query, url)

        return self.degrade_gracefully(query, f"unsupported mode: {self._mode.value}")

    def _live_fetch(self, query: dict[str, Any], url: str) -> VenueAdapterResult:
        http_result = fetch_text_safe(url, timeout=self._timeout)

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
                unknowns=[f"Snapshot fetch failed: {http_result.error}"],
                provenance=self.adapter_id,
                fetched_at=_now_iso(),
            )

        result = self.store_html(http_result.text, url=url, query=query)
        result.fetched_at = _now_iso()
        return result

    def store_html(
        self,
        html: str,
        url: str = "https://example.com",
        query: dict[str, Any] | None = None,
    ) -> VenueAdapterResult:
        claims: list[VenueAdapterClaim] = []
        vault_ref = None
        es = "FACT_FROM_SOURCE" if self._is_official else "VENDOR_CLAIM"

        if self._vault is not None:
            from ...storage.vault_backend import VaultObjectKind
            safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_")[:60]
            vault_path = f"venue-snapshots/{safe_name}.html"
            ref = self._vault.write_text(
                vault_path, html, VaultObjectKind.HTML_SNAPSHOT.value,
                metadata={"source_url": url},
            )
            vault_ref = ref.vault_path

        import hashlib
        content_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]

        claims.append(VenueAdapterClaim("snapshot_stored", True, es, "high"))
        claims.append(VenueAdapterClaim("snapshot_url", url, es, "high"))
        claims.append(VenueAdapterClaim("snapshot_size_chars", len(html), es, "high"))
        claims.append(VenueAdapterClaim("content_hash", content_hash, es, "high"))

        result = VenueAdapterResult(
            adapter_id=self.adapter_id,
            mode=self._mode.value,
            query=query or {},
            status=VenueAdapterStatus.SUCCESS.value,
            source_access_mode=self.source_access_mode,
            evidence_status=es,
            source_role=self.source_role,
            claims=claims,
            vault_ref=vault_ref,
            unknowns=[],
            provenance=self.adapter_id,
        )
        return self._attach_authority(result)

    def store_provided_html(self, html: str, url: str) -> VenueAdapterResult:
        return self.store_html(html, url)
