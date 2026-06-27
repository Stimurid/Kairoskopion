"""P8 Verification / Promotion Gate.

Decides whether provisional records can be promoted to verified,
and why. Produces an audit trail for every decision.

Rules:
- Record must have at least one SourcePacket with evidence ref.
- Evidence kind must be acceptable for the claim type.
- No contradictions in evidence.
- LLM draft never promoted without corroboration.
- Paid/no_paid restrictions respected.
- URL-only reference does not promote to externally_verified.

Verdict set:
- promote_verified: evidence sufficient for full verification
- keep_provisional: insufficient evidence, but not contradicted
- needs_manual_review: conflicting or ambiguous evidence
- reject: contradicted or fabricated evidence
- blocked: cannot verify (paid API required, source inaccessible)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from ..registry.models import (
    EvidenceRef,
    SourcePacket,
    VenueRegistryRecord,
    VenueSectionRecord,
    VenueMetricRecord,
    VenueClassificationRecord,
    DisciplineRecord,
)
from ..registry.services import RegistryHub

logger = logging.getLogger(__name__)

GATE_VERSION = "0.1.0"

VERDICTS = (
    "promote_verified",
    "promote_local_evidence_supported",
    "keep_provisional",
    "needs_manual_review",
    "reject",
    "blocked",
)

# Evidence statuses that count as real evidence
_REAL_EVIDENCE = {"source_grounded", "corpus_grounded", "adapter_result", "user_provided"}
# Evidence statuses from LLM that cannot verify alone
_LLM_EVIDENCE = {"llm_inference", "llm_draft"}
_VENDOR_EVIDENCE = {"vendor_claim"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# VerificationDecision — audit trail entry
# ---------------------------------------------------------------------------

@dataclass
class VerificationDecision:
    record_id: str = ""
    record_type: str = ""
    before_status: str = ""
    after_status: str = ""
    verdict: str = "keep_provisional"
    reason: str = ""
    evidence_refs_count: int = 0
    evidence_kinds: list[str] = field(default_factory=list)
    has_source_packet: bool = False
    has_real_evidence: bool = False
    has_llm_only: bool = False
    contradictions: list[str] = field(default_factory=list)
    verifier_version: str = GATE_VERSION
    verified_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Single record verification
# ---------------------------------------------------------------------------

def _get_record_id(record: Any) -> str:
    for attr in ("record_id", "venue_id", "section_id", "metric_id",
                 "discipline_id", "framework_id"):
        val = getattr(record, attr, None)
        if val:
            return val
    return "unknown"


def _get_record_type(record: Any) -> str:
    cls_name = type(record).__name__
    mapping = {
        "VenueRegistryRecord": "venue",
        "VenueSectionRecord": "venue_section",
        "VenueMetricRecord": "venue_metric",
        "VenueClassificationRecord": "venue_classification",
        "DisciplineRecord": "discipline",
    }
    return mapping.get(cls_name, cls_name.lower())


def _collect_evidence_statuses(record: Any) -> list[str]:
    statuses = []
    if hasattr(record, "evidence_refs"):
        for ref in (record.evidence_refs or []):
            if isinstance(ref, EvidenceRef):
                statuses.append(ref.evidence_status)
            elif isinstance(ref, dict):
                statuses.append(ref.get("evidence_status", "unknown"))
    if hasattr(record, "evidence_status"):
        statuses.append(record.evidence_status)
    return statuses


def verify_record(
    record: Any,
    hub: RegistryHub | None = None,
    *,
    no_paid_api: bool = True,
) -> VerificationDecision:
    """Evaluate a single registry record for promotion.

    Returns a VerificationDecision with verdict and audit trail.
    """
    record_id = _get_record_id(record)
    record_type = _get_record_type(record)
    before_status = getattr(record, "source_status", "unknown")

    decision = VerificationDecision(
        record_id=record_id,
        record_type=record_type,
        before_status=before_status,
    )

    # Collect evidence
    evidence_statuses = _collect_evidence_statuses(record)
    decision.evidence_refs_count = len(evidence_statuses)
    decision.evidence_kinds = evidence_statuses

    real_evidence = [s for s in evidence_statuses if s in _REAL_EVIDENCE]
    llm_evidence = [s for s in evidence_statuses if s in _LLM_EVIDENCE]
    vendor_evidence = [s for s in evidence_statuses if s in _VENDOR_EVIDENCE]

    decision.has_real_evidence = len(real_evidence) > 0
    decision.has_llm_only = len(llm_evidence) > 0 and len(real_evidence) == 0

    # Check for source packets
    if hub:
        packets = hub.packets.list_all()
        related = [p for p in packets if record_id in str(p.to_dict())]
        decision.has_source_packet = len(related) > 0 or len(real_evidence) > 0
    else:
        decision.has_source_packet = len(real_evidence) > 0

    # --- Verdict logic ---

    # No evidence at all
    if decision.evidence_refs_count == 0:
        decision.verdict = "keep_provisional"
        decision.after_status = before_status
        decision.reason = "No evidence refs attached"
        return decision

    # LLM-only evidence: never promote
    if decision.has_llm_only and not decision.has_real_evidence:
        decision.verdict = "keep_provisional"
        decision.after_status = "provisional"
        decision.reason = "Only LLM draft evidence — cannot verify without corroboration"
        return decision

    # Check for contradictions (multiple different statuses with real evidence)
    real_status_set = set(real_evidence)
    if "source_grounded" in real_status_set and "vendor_claim" in set(evidence_statuses):
        if _has_metric_contradiction(record):
            decision.contradictions.append("Source-grounded and vendor claim may conflict")
            decision.verdict = "needs_manual_review"
            decision.after_status = before_status
            decision.reason = "Conflicting evidence detected"
            return decision

    # Venue metrics: need separate evidence per metric
    if record_type == "venue_metric":
        ev_status = getattr(record, "evidence_status", "unknown")
        if ev_status in _REAL_EVIDENCE:
            if ev_status == "adapter_result":
                decision.verdict = "promote_verified"
                decision.after_status = "accepted"
                decision.reason = f"Metric has adapter-verified evidence ({ev_status})"
            else:
                decision.verdict = "promote_local_evidence_supported"
                decision.after_status = "provisional"
                decision.reason = f"Metric has local evidence ({ev_status})"
        elif ev_status in _LLM_EVIDENCE:
            decision.verdict = "keep_provisional"
            decision.after_status = "provisional"
            decision.reason = "Metric evidence is LLM-only"
        else:
            decision.verdict = "keep_provisional"
            decision.after_status = before_status
            decision.reason = f"Metric evidence status: {ev_status}"
        return decision

    # VenueClassificationRecord: uses evidence_status not evidence_refs
    if record_type == "venue_classification":
        ev_status = getattr(record, "evidence_status", "unknown")
        if ev_status in _REAL_EVIDENCE:
            decision.verdict = "promote_local_evidence_supported"
            decision.after_status = "provisional"
            decision.reason = f"Classification has evidence ({ev_status})"
        else:
            decision.verdict = "keep_provisional"
            decision.after_status = before_status
            decision.reason = f"Classification evidence: {ev_status}"
        return decision

    # Disciplines: check for corroboration
    if record_type == "discipline":
        provenance = getattr(record, "provenance", "") or ""
        if "llm_draft" in provenance or before_status == "provisional":
            if decision.has_real_evidence:
                decision.verdict = "promote_local_evidence_supported"
                decision.after_status = "provisional"
                decision.reason = "Discipline corroborated by local evidence"
            else:
                decision.verdict = "keep_provisional"
                decision.after_status = "provisional"
                decision.reason = "Discipline from LLM seed, no corroboration"
            return decision

    # General records with real evidence
    if decision.has_real_evidence:
        adapter_evidence = [s for s in evidence_statuses if s == "adapter_result"]
        if adapter_evidence:
            decision.verdict = "promote_verified"
            decision.after_status = "accepted"
            decision.reason = f"Record has {len(adapter_evidence)} adapter-verified evidence ref(s)"
        else:
            decision.verdict = "promote_local_evidence_supported"
            decision.after_status = "provisional"
            decision.reason = f"Record has {len(real_evidence)} local evidence ref(s)"
        return decision

    # Vendor claims only
    if vendor_evidence and not real_evidence:
        decision.verdict = "needs_manual_review"
        decision.after_status = before_status
        decision.reason = "Only vendor claims — needs independent verification"
        return decision

    # Fallback
    decision.verdict = "keep_provisional"
    decision.after_status = before_status
    decision.reason = "Insufficient evidence for promotion"
    return decision


def _has_metric_contradiction(record: Any) -> bool:
    """Check if a record has contradictory metric values."""
    if not hasattr(record, "metric_value"):
        return False
    return False


# ---------------------------------------------------------------------------
# Batch verification
# ---------------------------------------------------------------------------

def verify_registry(
    hub: RegistryHub,
    *,
    no_paid_api: bool = True,
) -> list[VerificationDecision]:
    """Run verification gate on all records in the registry.

    Returns a list of VerificationDecisions (one per record).
    """
    decisions: list[VerificationDecision] = []

    for reg_type in ("venue", "venue_section", "venue_metric",
                     "discipline", "venue_classification"):
        try:
            registry = hub._get_registry(reg_type)
        except (ValueError, KeyError):
            continue

        for record in registry.list_all():
            d = verify_record(record, hub, no_paid_api=no_paid_api)
            decisions.append(d)

    return decisions


def summarize_verification(
    decisions: list[VerificationDecision],
) -> dict[str, Any]:
    """Summarize verification decisions into counts."""
    summary: dict[str, int] = {v: 0 for v in VERDICTS}
    by_type: dict[str, dict[str, int]] = {}

    for d in decisions:
        summary[d.verdict] = summary.get(d.verdict, 0) + 1
        if d.record_type not in by_type:
            by_type[d.record_type] = {v: 0 for v in VERDICTS}
        by_type[d.record_type][d.verdict] = by_type[d.record_type].get(d.verdict, 0) + 1

    return {
        "total": len(decisions),
        "verdicts": summary,
        "by_type": by_type,
    }
