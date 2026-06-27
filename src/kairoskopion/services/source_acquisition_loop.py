"""P7.4 Source Acquisition Execution Loop.

Takes harvest tasks / acquisition gaps from P7.3 and executes them:
- classify task mode
- attach evidence
- validate evidence
- produce SourcePackets
- update provisional records when evidence is sufficient
- preserve provenance

No fabrication. No paid API. LLM seed never becomes verified without evidence.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..registry.models import (
    EvidenceRef,
    SourcePacket,
    SourceAcquisitionTask,
)
from ..registry.services import RegistryHub

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _acq_id() -> str:
    from ..ids import generate_id
    return generate_id("acqloop")


# ---------------------------------------------------------------------------
# Acquisition statuses (strict lifecycle)
# ---------------------------------------------------------------------------

ACQUISITION_STATUSES = (
    "provisional_llm_seed",
    "local_evidence_supported",
    "externally_verified",
    "manual_review_required",
    "blocked_no_paid_api",
    "rejected_insufficient_evidence",
)

EVIDENCE_KINDS = (
    "local_evidence_pack",
    "manual_note_with_citation",
    "url_reference_only",
    "adapter_result",
    "corpus_grounded",
    "insufficient",
)

# Evidence kinds that can upgrade from provisional to local_evidence_supported
_UPGRADE_KINDS = {"local_evidence_pack", "adapter_result", "corpus_grounded"}
# Evidence kinds that can upgrade to externally_verified
_VERIFY_KINDS = {"adapter_result"}


# ---------------------------------------------------------------------------
# AcquisitionLoopResult
# ---------------------------------------------------------------------------

@dataclass
class AcquisitionLoopResult:
    loop_id: str = field(default_factory=_acq_id)
    total_tasks: int = 0
    closed_local: int = 0
    closed_adapter: int = 0
    blocked: int = 0
    manual_required: int = 0
    rejected: int = 0
    records_upgraded: int = 0
    records_unchanged: int = 0
    source_packets_created: int = 0
    task_details: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Task classification
# ---------------------------------------------------------------------------

def classify_task_mode(
    task: dict[str, Any],
    *,
    evidence_pack_dir: Path | None = None,
    no_paid_api: bool = True,
) -> str:
    """Classify a harvest task into an acquisition mode."""
    status = task.get("status", "planned")
    task_type = task.get("task_type", "")
    adapter = task.get("adapter_hint", "")
    local_ref = task.get("local_source_ref", "")

    if status == "completed":
        return "verified"

    if status == "blocked":
        return "blocked_no_paid_api"

    if task_type == "ingest_local_evidence_pack":
        if local_ref and evidence_pack_dir:
            ep_dir = Path(local_ref) if local_ref else evidence_pack_dir
            if ep_dir.exists():
                return "local_evidence_ready"
        return "blocked_missing_source"

    if task_type == "ingest_discipline_seed":
        if local_ref and Path(local_ref).exists():
            return "local_evidence_ready"
        return "blocked_missing_source"

    if adapter in ("scopus", "wos", "elibrary_ru", "semantic_scholar"):
        if no_paid_api:
            return "blocked_no_paid_api"

    if adapter in ("openalex", "crossref", "doaj", "unpaywall",
                    "opencitations", "cyberleninka"):
        return "ready_for_import"

    if task_type == "manual_web_lookup":
        return "manual_lookup_required"

    if status == "ready":
        return "ready_for_import"

    return "manual_lookup_required"


# ---------------------------------------------------------------------------
# Evidence validation
# ---------------------------------------------------------------------------

def validate_evidence(
    evidence_kind: str,
    evidence_path_or_url: str | None = None,
    evidence_content: str | None = None,
) -> tuple[bool, str]:
    """Validate supplied evidence. Returns (valid, reason)."""
    if evidence_kind not in EVIDENCE_KINDS:
        return False, f"Unknown evidence_kind: {evidence_kind}"

    if evidence_kind == "insufficient":
        return False, "Evidence explicitly marked as insufficient"

    if evidence_kind == "url_reference_only":
        if not evidence_path_or_url:
            return False, "URL reference requires a URL"
        return True, "URL reference accepted (does not upgrade to verified)"

    if evidence_kind == "local_evidence_pack":
        if evidence_path_or_url:
            p = Path(evidence_path_or_url)
            if p.exists() and p.stat().st_size > 0:
                return True, "Local evidence pack file exists and is non-empty"
            if not p.exists():
                return False, f"Evidence file not found: {evidence_path_or_url}"
            return False, "Evidence file is empty"
        if evidence_content and len(evidence_content) > 50:
            return True, "Evidence content provided inline"
        return False, "No evidence file or content provided"

    if evidence_kind == "manual_note_with_citation":
        if evidence_content and len(evidence_content) > 10:
            return True, "Manual note with citation accepted"
        return False, "Manual note too short or missing"

    if evidence_kind in ("adapter_result", "corpus_grounded"):
        if evidence_content or evidence_path_or_url:
            return True, f"{evidence_kind} evidence accepted"
        return False, f"{evidence_kind} requires content or path"

    return False, "Unhandled evidence kind"


def determine_record_status(
    current_status: str,
    evidence_kind: str,
    evidence_valid: bool,
) -> str:
    """Determine what status a record should have after evidence is supplied."""
    if not evidence_valid:
        if current_status in ("provisional", "provisional_llm_seed"):
            return current_status
        return "rejected_insufficient_evidence"

    if evidence_kind in _VERIFY_KINDS:
        return "externally_verified"

    if evidence_kind in _UPGRADE_KINDS:
        return "local_evidence_supported"

    if evidence_kind == "url_reference_only":
        return current_status

    if evidence_kind == "manual_note_with_citation":
        if current_status == "provisional_llm_seed":
            return "manual_review_required"
        return "local_evidence_supported"

    return current_status


# ---------------------------------------------------------------------------
# TSV import parser
# ---------------------------------------------------------------------------

TSV_COLUMNS = (
    "task_id", "authority_id", "target_kind", "target_name",
    "claim_type", "required_evidence", "supplied_evidence_path_or_url",
    "evidence_kind", "access_status", "reviewer_note", "decision",
)


def parse_acquisition_tsv(content: str) -> tuple[list[dict[str, str]], list[str]]:
    """Parse source acquisition import TSV.

    Returns (rows, errors). Each row is a dict with TSV_COLUMNS keys.
    """
    rows: list[dict[str, str]] = []
    errors: list[str] = []

    reader = csv.DictReader(io.StringIO(content), delimiter="\t")

    if reader.fieldnames is None:
        errors.append("Empty TSV or missing header")
        return rows, errors

    missing = set(TSV_COLUMNS) - set(reader.fieldnames)
    if missing:
        errors.append(f"Missing columns: {sorted(missing)}")
        return rows, errors

    for i, row in enumerate(reader, start=2):
        if not row.get("task_id", "").strip():
            errors.append(f"Row {i}: missing task_id")
            continue
        if not row.get("decision", "").strip():
            errors.append(f"Row {i}: missing decision")
            continue
        decision = row["decision"].strip().lower()
        if decision not in ("accept", "reject", "skip", "blocked"):
            errors.append(f"Row {i}: invalid decision '{decision}'")
            continue
        rows.append({k: row.get(k, "").strip() for k in TSV_COLUMNS})

    return rows, errors


def validate_acquisition_tsv(content: str) -> tuple[bool, list[str]]:
    """Validate TSV without processing. Returns (valid, errors)."""
    _, errors = parse_acquisition_tsv(content)
    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Core acquisition loop
# ---------------------------------------------------------------------------

def run_acquisition_loop(
    harvest_tasks: list[dict[str, Any]],
    hub: RegistryHub,
    *,
    evidence_pack_dir: Path | None = None,
    no_paid_api: bool = True,
) -> AcquisitionLoopResult:
    """Execute the acquisition loop over harvest tasks.

    For each task:
    1. Classify mode
    2. If local evidence available, attach and close
    3. If blocked, leave blocked
    4. If manual required, create acquisition task
    5. Create SourcePackets for closed tasks
    """
    result = AcquisitionLoopResult(total_tasks=len(harvest_tasks))

    for task_dict in harvest_tasks:
        mode = classify_task_mode(
            task_dict,
            evidence_pack_dir=evidence_pack_dir,
            no_paid_api=no_paid_api,
        )

        detail: dict[str, Any] = {
            "task_id": task_dict.get("task_id", "unknown"),
            "task_type": task_dict.get("task_type", "unknown"),
            "mode": mode,
            "original_status": task_dict.get("status", "unknown"),
        }

        if mode == "local_evidence_ready":
            local_ref = task_dict.get("local_source_ref", "")
            packet = SourcePacket(
                packet_type="acquisition_closure",
                source_type="local_file",
                source_id=local_ref,
                title=task_dict.get("query", ""),
                evidence_status="corpus_grounded",
                adapter_name="local_import",
            )
            hub.packets.add(packet)
            result.source_packets_created += 1
            result.closed_local += 1
            detail["closed"] = True
            detail["packet_id"] = packet.packet_id
            detail["new_status"] = "local_evidence_supported"

        elif mode == "blocked_no_paid_api":
            result.blocked += 1
            detail["closed"] = False
            detail["new_status"] = "blocked_no_paid_api"
            detail["reason"] = task_dict.get("blocked_reason", "Requires paid API")

        elif mode == "blocked_missing_source":
            result.blocked += 1
            detail["closed"] = False
            detail["new_status"] = "blocked_missing_source"

        elif mode == "ready_for_import":
            acq_task = SourceAcquisitionTask(
                task_type=task_dict.get("task_type", "venue_lookup"),
                query=task_dict.get("query", ""),
                reason=f"Free adapter {task_dict.get('adapter_hint', '')} available",
                target_sources=[task_dict.get("adapter_hint", "")],
                priority=task_dict.get("priority", "normal"),
                status="open",
            )
            hub.tasks.add(acq_task)
            result.manual_required += 1
            detail["closed"] = False
            detail["new_status"] = "ready_for_import"
            detail["acquisition_task_id"] = acq_task.task_id

        elif mode == "manual_lookup_required":
            acq_task = SourceAcquisitionTask(
                task_type="manual_lookup",
                query=task_dict.get("query", ""),
                reason="Requires manual web lookup",
                target_sources=[task_dict.get("adapter_hint", "manual")],
                priority=task_dict.get("priority", "normal"),
                status="open",
            )
            hub.tasks.add(acq_task)
            result.manual_required += 1
            detail["closed"] = False
            detail["new_status"] = "manual_lookup_required"
            detail["acquisition_task_id"] = acq_task.task_id

        elif mode == "verified":
            result.closed_local += 1
            detail["closed"] = True
            detail["new_status"] = "verified"

        else:
            result.warnings.append(f"Unhandled mode {mode} for task {task_dict.get('task_id')}")
            detail["closed"] = False
            detail["new_status"] = mode

        result.task_details.append(detail)

    return result


def create_acquisition_tasks_from_gaps(
    gaps: list[str],
    hub: RegistryHub,
) -> list[SourceAcquisitionTask]:
    """Convert gap descriptions into actionable acquisition tasks."""
    tasks = []
    for gap in gaps:
        task = SourceAcquisitionTask(
            task_type="gap_resolution",
            query=gap,
            reason=f"Gap identified during harvest: {gap}",
            target_sources=["manual", "local_evidence"],
            priority="normal",
            status="open",
        )
        hub.tasks.add(task)
        tasks.append(task)
    return tasks


def apply_tsv_decisions(
    tsv_content: str,
    hub: RegistryHub,
) -> tuple[int, int, int, list[str]]:
    """Apply decisions from a TSV import file.

    Returns (accepted, rejected, skipped, errors).
    """
    rows, errors = parse_acquisition_tsv(tsv_content)
    if errors:
        return 0, 0, 0, errors

    accepted = 0
    rejected = 0
    skipped = 0

    for row in rows:
        decision = row["decision"].lower()
        task_id = row["task_id"]

        if decision == "accept":
            evidence_kind = row.get("evidence_kind", "manual_note_with_citation")
            evidence_path = row.get("supplied_evidence_path_or_url", "")
            reviewer_note = row.get("reviewer_note", "")
            valid, reason = validate_evidence(
                evidence_kind, evidence_path,
                evidence_content=reviewer_note,
            )

            if valid:
                packet = SourcePacket(
                    packet_type="tsv_import",
                    source_type=evidence_kind,
                    source_id=evidence_path or task_id,
                    title=row.get("target_name", ""),
                    excerpt=row.get("reviewer_note", ""),
                    evidence_status="corpus_grounded" if evidence_kind in _UPGRADE_KINDS else "user_provided",
                    adapter_name="tsv_import",
                )
                hub.packets.add(packet)
                accepted += 1
            else:
                errors.append(f"Task {task_id}: evidence invalid — {reason}")

        elif decision == "reject":
            rejected += 1

        elif decision in ("skip", "blocked"):
            skipped += 1

    return accepted, rejected, skipped, errors
