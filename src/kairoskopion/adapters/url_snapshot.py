"""URL snapshot adapter placeholder (spec §26.1).

Provides the contract for URL-based source acquisition.
In MVP, actual HTTP fetching is DISABLED by default.
The adapter creates a placeholder SourceSnapshot with INACCESSIBLE status,
ready for later replacement with real fetching.
"""

from __future__ import annotations

from ..enums import EvidenceStatus
from ..ids import evidence_item_id, source_snapshot_id
from ..schema import EvidenceItem, SourceSnapshot, _now
from .source_intake import SourceRole


def create_url_snapshot_placeholder(
    url: str,
    *,
    role: SourceRole = SourceRole.UNKNOWN,
    source_id: str | None = None,
    notes: str | None = None,
) -> SourceSnapshot:
    """Create a placeholder snapshot for a URL without fetching.

    This registers the URL as a known source with INACCESSIBLE extraction
    status, so downstream code knows the source exists but hasn't been
    fetched. When real web fetching is implemented, this function will
    be replaced by one that actually retrieves the page.
    """
    sid = source_id or f"url:{url}"
    return SourceSnapshot(
        snapshot_id=source_snapshot_id(),
        source_id=sid,
        url=url,
        retrieved_at=_now(),
        content_type="text/html",
        parser_used="url_placeholder",
        extraction_status="not_fetched",
        extraction_errors=[
            "URL not fetched — web access disabled in MVP",
            f"Role: {role.value}",
        ],
    )


def create_url_evidence_placeholder(
    snapshot: SourceSnapshot,
    *,
    expected_claim: str,
    notes: str | None = None,
) -> EvidenceItem:
    """Create a placeholder evidence item for an unfetched URL.

    The evidence status is INACCESSIBLE — not UNKNOWN (we know the URL
    exists, we just haven't read it).
    """
    return EvidenceItem(
        evidence_id=evidence_item_id(),
        source_id=snapshot.source_id,
        source_type="url_placeholder",
        url_or_file_ref=snapshot.url,
        claim_supported=expected_claim,
        evidence_status=EvidenceStatus.INACCESSIBLE.value,
        confidence=None,
        notes=notes or "Source registered but not yet fetched",
    )
