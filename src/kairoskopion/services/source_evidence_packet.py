"""Deterministic builder for SourceEvidencePacket (PIM v1 §2, Sprint α B1).

Aggregates per-case sources (manuscript text, file uploads, venue URL,
adapter results) into a single SourceEvidencePacket recording
provenance, access_status, extraction_status, and granularity class.

No external calls. No LLM. Pure restructuring of state already in the Case.
"""

from __future__ import annotations

from typing import Any

from ..enums import EvidenceGranularity, EvidenceStatus, SourceAccessStatus
from ..schema import SourceEvidencePacket, SourceEvidenceEntry


def _classify_provenance(source_type: str | None, extra: dict[str, Any] | None = None) -> str:
    """Map an input source kind to PIM provenance vocabulary."""
    if not source_type:
        return "user_statement"
    st = source_type.lower()
    if st in ("file", "uploaded_file", "manuscript_file"):
        return "uploaded_file"
    if st in ("drive_doc", "drive"):
        return "drive_doc"
    if st in ("url", "web", "web_source", "journal_url", "cfp"):
        return "web_source"
    if st in ("user_text", "user_brief", "abstract", "notes", "review_letter"):
        return "user_statement"
    if st in ("inferred", "adapter_inference"):
        return "inferred"
    return "user_statement"


def _classify_granularity(source_type: str | None, evidence_status: str | None) -> str:
    """Map (source_type, evidence_status) to v1.0 granularity vocabulary."""
    if evidence_status == EvidenceStatus.UNKNOWN.value:
        return EvidenceGranularity.UNKNOWN.value
    if evidence_status == EvidenceStatus.CONFLICTING_EVIDENCE.value:
        return EvidenceGranularity.CONFLICTING_EVIDENCE.value
    if evidence_status == EvidenceStatus.VENDOR_CLAIM.value:
        return EvidenceGranularity.VENDOR_CLAIM.value
    if evidence_status == EvidenceStatus.CORPUS_OBSERVATION.value:
        return EvidenceGranularity.CORPUS_OBSERVATION.value
    if evidence_status == EvidenceStatus.INFERENCE.value:
        return EvidenceGranularity.INFERRED_PATTERN.value
    if evidence_status in (
        EvidenceStatus.USER_NOTE.value,
        EvidenceStatus.TACIT_SIGNAL.value,
    ):
        return EvidenceGranularity.USER_TACIT_NOTE.value
    if evidence_status in (
        EvidenceStatus.FACT_FROM_SOURCE.value,
        EvidenceStatus.FACT_FROM_API_METADATA.value,
    ):
        return EvidenceGranularity.SOURCE_FACT.value
    st = (source_type or "").lower()
    if st in ("user_text", "user_brief", "abstract", "notes"):
        return EvidenceGranularity.USER_TACIT_NOTE.value
    if st in ("file", "manuscript_file", "uploaded_file"):
        return EvidenceGranularity.TEXT_EXTRACTED_CLAIM.value
    return EvidenceGranularity.UNKNOWN.value


def _classify_access(extraction_status: str | None) -> str:
    if not extraction_status:
        return SourceAccessStatus.UNKNOWN.value
    es = extraction_status.lower()
    if es in ("parsed", "extracted", "ok", "success"):
        return SourceAccessStatus.FULL.value
    if es in ("partially_parsed", "partially_extracted"):
        return SourceAccessStatus.PARTIAL.value
    if es in ("failed", "inaccessible", "encrypted_or_unreadable", "binary_not_extracted"):
        return SourceAccessStatus.INACCESSIBLE.value
    if es in ("stale",):
        return SourceAccessStatus.STALE.value
    return SourceAccessStatus.UNKNOWN.value


def build_packet_from_case(case: Any) -> SourceEvidencePacket:
    """Build a SourceEvidencePacket from a Case's recorded inputs.

    The Case object is treated by attribute lookup so this stays
    compatible with both the in-memory orchestrator and a snapshot dict.
    """
    packet = SourceEvidencePacket(case_id=getattr(case, "case_id", None))
    entries: list[SourceEvidenceEntry] = []

    input_text = getattr(case, "input_text", "") or ""
    input_type = getattr(case, "input_type", "") or ""
    if input_text:
        entries.append(SourceEvidenceEntry(
            source_id=f"case_input:{getattr(case, 'case_id', 'unknown')}",
            source_type=input_type or "user_text",
            provenance=_classify_provenance(input_type),
            access_status=SourceAccessStatus.FULL.value,
            extraction_status="parsed",
            granularity=_classify_granularity(input_type, None),
            note=f"length={len(input_text)}",
        ))

    investigated = getattr(case, "investigated_venue", None)
    if investigated is not None:
        urls = getattr(investigated, "official_urls", []) or []
        for url in urls:
            entries.append(SourceEvidenceEntry(
                source_id=str(url),
                source_type="journal_url",
                provenance="web_source",
                access_status=SourceAccessStatus.UNKNOWN.value,
                extraction_status="manual",
                granularity=EvidenceGranularity.VENDOR_CLAIM.value,
                note="venue URL extracted during investigation",
            ))

    selected = getattr(case, "selected_venue", None)
    if selected is not None:
        srs = getattr(selected, "source_refs", []) or []
        for ref in srs:
            entries.append(SourceEvidenceEntry(
                source_id=str(ref),
                source_type="venue_source_ref",
                provenance="web_source",
                access_status=SourceAccessStatus.UNKNOWN.value,
                extraction_status="manual",
                granularity=EvidenceGranularity.VENDOR_CLAIM.value,
            ))

    # Granularity summary
    summary: dict[str, int] = {}
    for e in entries:
        g = e.granularity or EvidenceGranularity.UNKNOWN.value
        summary[g] = summary.get(g, 0) + 1

    packet.input_sources = [e.to_dict() for e in entries]
    packet.granularity_summary = summary
    if not entries:
        packet.unknowns.append("No input sources recorded on this case yet")
    return packet
