"""Bridge: convert adapter results to SourceSnapshot / EvidenceItem.

Mock adapter results create sources with evidence_status=VENDOR_CLAIM,
never FACT_FROM_SOURCE. References are never marked verified by mock data.
"""

from __future__ import annotations

from typing import Any

from ..enums import EvidenceStatus
from ..ids import evidence_item_id, source_snapshot_id
from ..schema import EvidenceItem, SourceSnapshot, _now
from .base import AdapterResult


def convert_adapter_result_to_source_snapshot(
    result: AdapterResult,
) -> SourceSnapshot:
    """Create a SourceSnapshot representing the adapter query result."""
    evidence_tag = "mock" if result.is_mock else "external_api"
    return SourceSnapshot(
        snapshot_id=source_snapshot_id(),
        source_id=f"adapter:{result.adapter_name}:{result.adapter_result_id}",
        url=None,
        retrieved_at=result.retrieved_at,
        content_type="application/json",
        parser_used=f"{result.adapter_name}_adapter_{evidence_tag}",
        text_ref=f"adapter query: {result.query}",
        extraction_status="extracted" if result.records else "no_results",
        extraction_errors=[e.get("message", "") for e in result.errors] if result.errors else [],
    )


def convert_adapter_record_to_evidence_item(
    record: dict[str, Any],
    *,
    adapter_name: str,
    is_mock: bool = True,
    source_id: str | None = None,
) -> EvidenceItem:
    """Create an EvidenceItem from a single adapter record.

    Mock records get VENDOR_CLAIM status with low confidence.
    Real adapter records would get VENDOR_CLAIM with medium confidence.
    Neither ever gets FACT_FROM_SOURCE — that requires user verification.
    """
    title = record.get("title", "")
    doi = record.get("doi", "")
    claim = f"Metadata for: {title}" if title else f"Record from {adapter_name}"

    if is_mock:
        status = EvidenceStatus.VENDOR_CLAIM
        confidence = "low"
        notes = f"Mock {adapter_name} data — not from real API"
    else:
        status = EvidenceStatus.VENDOR_CLAIM
        confidence = "medium"
        notes = f"Retrieved from {adapter_name} API"

    return EvidenceItem(
        evidence_id=evidence_item_id(),
        source_id=source_id,
        source_type=f"{adapter_name}_adapter",
        url_or_file_ref=f"doi:{doi}" if doi else None,
        claim_supported=claim,
        evidence_status=status.value,
        excerpt_or_locator=f"DOI: {doi}" if doi else record.get("record_id"),
        confidence=confidence,
        notes=notes,
    )


def link_adapter_records_to_reference_items(
    adapter_records: list[dict[str, Any]],
    reference_items: list[dict[str, Any]],
    *,
    adapter_name: str,
) -> list[dict[str, Any]]:
    """Match adapter records to bibliography references by DOI or title.

    Returns a list of match dicts with reference_item_id, adapter_record_id,
    match_type ('doi' or 'title_fragment'), and match_confidence.

    This is a stub: matches by DOI only. Title matching requires fuzzy
    comparison not implemented in MVP.
    """
    adapter_by_doi: dict[str, dict[str, Any]] = {}
    for rec in adapter_records:
        doi = rec.get("doi")
        if doi:
            adapter_by_doi[doi.lower()] = rec

    matches = []
    for ref in reference_items:
        ref_doi = ref.get("doi")
        if ref_doi and ref_doi.lower() in adapter_by_doi:
            adapter_rec = adapter_by_doi[ref_doi.lower()]
            matches.append({
                "reference_item_id": ref.get("reference_item_id", ""),
                "adapter_record_id": adapter_rec.get("record_id", ""),
                "adapter_name": adapter_name,
                "match_type": "doi",
                "match_confidence": "high" if not adapter_rec.get("is_mock", True) else "low",
                "is_mock": True,
                "verification_status": "not_verified",
            })

    return matches
