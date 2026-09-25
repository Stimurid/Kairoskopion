"""Artikl D24/D25 bibliography/source-verification ledger.

This module materializes evidence state only. It never fabricates bibliographic
entities and never mutates manuscript or Field semantics.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
from .source_completeness import SourceCompletenessReport

ENTRY_STATUSES={"VERIFIED","PARTIAL","UNRESOLVED","REJECTED"}
CARRIER_KINDS={"MANUSCRIPT_BIBLIOGRAPHY","SOURCE_MAP","DONOR","INLINE_TRACE","FAMILY_INDEX","OTHER"}

@dataclass
class BibliographyEvidenceEntry:
    entry_id: str
    carrier_ref: str
    carrier_kind: str
    raw_ref: str
    source_ref_id: str | None = None
    locator_status: str = "UNAVAILABLE"
    verification_status: str = "UNRESOLVED"
    bound_manuscript_revision: str | None = None
    provenance: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    def __post_init__(self):
        if self.carrier_kind not in CARRIER_KINDS: raise ValueError("unsupported carrier_kind")
        if self.verification_status not in ENTRY_STATUSES: raise ValueError("unsupported verification_status")
    def to_dict(self)->dict[str,Any]: return asdict(self)

@dataclass
class BibliographyLedger:
    ledger_id: str
    article_id: str
    manuscript_revision: str
    entries: list[BibliographyEvidenceEntry] = field(default_factory=list)
    completeness_claim: str = "UNKNOWN"
    completeness_basis: list[str] = field(default_factory=list)
    source_needs: list[str] = field(default_factory=list)
    locator_needs: list[str] = field(default_factory=list)
    provenance: list[str] = field(default_factory=list)

def verify_bibliography_ledger(ledger: BibliographyLedger) -> SourceCompletenessReport:
    exact=[e for e in ledger.entries if e.verification_status=="VERIFIED" and e.source_ref_id]
    all_current=all(e.bound_manuscript_revision==ledger.manuscript_revision for e in exact)
    complete=ledger.completeness_claim=="VERIFIED_COMPLETE"
    no_open=not ledger.source_needs and not ledger.locator_needs
    if complete and all_current and no_open and len(exact)==len(ledger.entries):
        return SourceCompletenessReport(
            report_id=f"sc:{ledger.ledger_id}", article_id=ledger.article_id,
            manuscript_revision=ledger.manuscript_revision,
            bibliography_status="VERIFIED_COMPLETE", reference_count_status="VERIFIED",
            reference_count=len(exact), carriers=sorted({e.carrier_ref for e in ledger.entries}),
            provenance=ledger.provenance + ledger.completeness_basis,
            decision="PROJECT_REFERENCE_COUNT",
            rationale=["complete bibliography scope explicitly asserted and every entry verified against current manuscript revision"],
        )
    kinds={e.carrier_kind for e in ledger.entries}
    if "SOURCE_MAP" in kinds: status="SOURCE_MAP_ONLY"
    elif kinds & {"DONOR","INLINE_TRACE","FAMILY_INDEX"}: status="SOURCE_TRACES_ONLY"
    elif "MANUSCRIPT_BIBLIOGRAPHY" in kinds: status="PRESENT_UNVERIFIED"
    elif not ledger.entries: status="ABSENT"
    else: status="UNKNOWN"
    return SourceCompletenessReport(
        report_id=f"sc:{ledger.ledger_id}", article_id=ledger.article_id,
        manuscript_revision=ledger.manuscript_revision, bibliography_status=status,
        reference_count_status="UNAVAILABLE", reference_count=None,
        carriers=sorted({e.carrier_ref for e in ledger.entries}),
        source_map_refs=[e.carrier_ref for e in ledger.entries if e.carrier_kind=="SOURCE_MAP"],
        source_trace_refs=[e.carrier_ref for e in ledger.entries if e.carrier_kind in {"DONOR","INLINE_TRACE","FAMILY_INDEX"}],
        unresolved_source_needs=list(ledger.source_needs),
        unresolved_locator_needs=list(ledger.locator_needs),
        provenance=list(ledger.provenance), decision="KEEP_UNKNOWN",
        rationale=["bibliography completeness or current-revision entry verification is not closed"],
    )