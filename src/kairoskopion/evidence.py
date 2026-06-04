"""Evidence layer helpers.

Thin wrappers around schema.EvidenceItem / SourceSnapshot for common
creation patterns.
"""

from __future__ import annotations

from .enums import EvidenceStatus
from .ids import evidence_item_id, source_snapshot_id
from .schema import EvidenceItem, SourceSnapshot


def create_evidence_item(
    *,
    source_id: str | None = None,
    claim: str,
    status: EvidenceStatus = EvidenceStatus.UNKNOWN,
    url_or_file_ref: str | None = None,
    excerpt: str | None = None,
    confidence: str | None = None,
    notes: str | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_item_id(),
        source_id=source_id,
        url_or_file_ref=url_or_file_ref,
        claim_supported=claim,
        evidence_status=status.value,
        excerpt_or_locator=excerpt,
        confidence=confidence,
        notes=notes,
    )


def create_source_snapshot(
    *,
    source_id: str | None = None,
    url: str | None = None,
    content_type: str | None = None,
    extraction_status: str = "pending",
) -> SourceSnapshot:
    return SourceSnapshot(
        snapshot_id=source_snapshot_id(),
        source_id=source_id,
        url=url,
        content_type=content_type,
        extraction_status=extraction_status,
    )


def validate_evidence_status(status: str) -> bool:
    """Check if a string is a valid EvidenceStatus value."""
    try:
        EvidenceStatus(status)
        return True
    except ValueError:
        return False
