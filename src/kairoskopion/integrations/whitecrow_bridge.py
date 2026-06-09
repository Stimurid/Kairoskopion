"""WhiteCrow Patch Queue Bridge (Sprint 8).

Generates PatchCandidate records from Kairoskopion pipeline artifacts:
  - MismatchMap mismatches → patches for manuscript sections
  - RewritePlan changes → patches with effort estimates
  - ComplianceChecklist missing items → compliance patches
  - RiskReport blocking risks → risk-mitigation patches

Output is a list of PatchCandidate dicts ready for JSONL serialization
or direct import into WhiteCrow's patch queue.

No LLM calls. No network. Pure deterministic mapping.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..ids import generate_id
from ..enums import FieldCoreImpact
from ..schema import (
    ComplianceChecklist,
    FitAssessment,
    MismatchMap,
    RewritePlan,
    RiskReport,
)


def _patch_id() -> str:
    return generate_id("patch")


# ---------------------------------------------------------------------------
# Patch generators
# ---------------------------------------------------------------------------


def patches_from_mismatches(
    mismatch_map: MismatchMap,
    *,
    target_document_ref: str | None = None,
) -> list[dict[str, Any]]:
    """Generate PatchCandidates from MismatchMap mismatches."""
    patches: list[dict[str, Any]] = []

    for mm in mismatch_map.mismatches:
        axis = mm.get("axis", "unknown")
        description = mm.get("description", "")
        severity = mm.get("severity", "minor")

        # Map severity to field core impact
        if severity == "blocking":
            impact = FieldCoreImpact.CORE_TRANSFORMING.value
        elif severity == "major":
            impact = FieldCoreImpact.CORE_TOUCHING.value
        else:
            impact = FieldCoreImpact.CORE_PRESERVING.value

        patches.append({
            "patch_id": _patch_id(),
            "source_plan_id": mismatch_map.mismatch_map_id,
            "target_document_ref": target_document_ref,
            "target_block_or_section": axis,
            "change_summary": f"Address mismatch on axis '{axis}': {description}",
            "change_type": "mismatch_fix",
            "reason": description or f"Mismatch detected on {axis}",
            "evidence_refs": [],
            "related_mismatch_id": mismatch_map.mismatch_map_id,
            "field_core_impact": impact,
            "estimated_effort": "unknown",
            "status": "proposed",
            "user_decision": None,
            "bridge_version": "kairoskopion-whitecrow-v1",
        })

    return patches


def patches_from_rewrite_plan(
    plan: RewritePlan,
    *,
    target_document_ref: str | None = None,
) -> list[dict[str, Any]]:
    """Generate PatchCandidates from RewritePlan changes."""
    patches: list[dict[str, Any]] = []

    for change in plan.changes:
        section = change.get("section", "unknown")
        description = change.get("description", "")
        change_type = change.get("type", "revision")
        effort = change.get("effort", plan.estimated_effort or "unknown")

        patches.append({
            "patch_id": _patch_id(),
            "source_plan_id": plan.rewrite_plan_id,
            "target_document_ref": target_document_ref,
            "target_block_or_section": section,
            "change_summary": description or f"Rewrite {section}",
            "change_type": change_type,
            "reason": change.get("reason", "From rewrite plan"),
            "evidence_refs": [],
            "related_mismatch_id": plan.fit_assessment_id,
            "field_core_impact": plan.field_core_risk,
            "estimated_effort": effort,
            "status": "proposed",
            "user_decision": None,
            "bridge_version": "kairoskopion-whitecrow-v1",
        })

    return patches


def patches_from_compliance(
    compliance: ComplianceChecklist,
    *,
    target_document_ref: str | None = None,
) -> list[dict[str, Any]]:
    """Generate PatchCandidates from ComplianceChecklist missing items."""
    patches: list[dict[str, Any]] = []

    for item in compliance.missing_items:
        patches.append({
            "patch_id": _patch_id(),
            "source_plan_id": compliance.compliance_checklist_id,
            "target_document_ref": target_document_ref,
            "target_block_or_section": "compliance",
            "change_summary": f"Add missing compliance item: {item}",
            "change_type": "compliance_fix",
            "reason": f"Required by venue guidelines: {item}",
            "evidence_refs": [],
            "related_mismatch_id": None,
            "field_core_impact": FieldCoreImpact.CORE_PRESERVING.value,
            "estimated_effort": "low",
            "status": "proposed",
            "user_decision": None,
            "bridge_version": "kairoskopion-whitecrow-v1",
        })

    for item in compliance.blocking_items:
        patches.append({
            "patch_id": _patch_id(),
            "source_plan_id": compliance.compliance_checklist_id,
            "target_document_ref": target_document_ref,
            "target_block_or_section": "compliance",
            "change_summary": f"[BLOCKING] Fix compliance issue: {item}",
            "change_type": "compliance_fix",
            "reason": f"Blocking compliance requirement: {item}",
            "evidence_refs": [],
            "related_mismatch_id": None,
            "field_core_impact": FieldCoreImpact.CORE_TOUCHING.value,
            "estimated_effort": "medium",
            "status": "proposed",
            "user_decision": None,
            "bridge_version": "kairoskopion-whitecrow-v1",
        })

    return patches


def patches_from_risk(
    risk: RiskReport,
    *,
    target_document_ref: str | None = None,
) -> list[dict[str, Any]]:
    """Generate PatchCandidates from RiskReport blocking/major risks."""
    patches: list[dict[str, Any]] = []

    for item in risk.risk_items:
        severity = item.get("severity", "minor")
        if severity not in ("blocking", "major"):
            continue  # Only generate patches for significant risks

        risk_type = item.get("risk_type", "unknown")
        description = item.get("description", "")
        mitigation = item.get("mitigation", "")

        impact = (
            FieldCoreImpact.CORE_TRANSFORMING.value if severity == "blocking"
            else FieldCoreImpact.CORE_TOUCHING.value
        )

        patches.append({
            "patch_id": _patch_id(),
            "source_plan_id": risk.risk_report_id,
            "target_document_ref": target_document_ref,
            "target_block_or_section": risk_type,
            "change_summary": (
                f"Mitigate {risk_type} risk: {description}"
                + (f" — {mitigation}" if mitigation else "")
            ),
            "change_type": "risk_mitigation",
            "reason": description,
            "evidence_refs": [],
            "related_mismatch_id": None,
            "field_core_impact": impact,
            "estimated_effort": "unknown",
            "status": "proposed",
            "user_decision": None,
            "bridge_version": "kairoskopion-whitecrow-v1",
        })

    return patches


# ---------------------------------------------------------------------------
# Full export
# ---------------------------------------------------------------------------


def build_whitecrow_patch_queue(
    *,
    mismatch_map: MismatchMap | None = None,
    rewrite_plan: RewritePlan | None = None,
    compliance: ComplianceChecklist | None = None,
    risk: RiskReport | None = None,
    target_document_ref: str | None = None,
) -> list[dict[str, Any]]:
    """Build a complete WhiteCrow patch queue from Kairoskopion artifacts.

    Returns a list of PatchCandidate dicts ready for JSONL serialization.
    """
    patches: list[dict[str, Any]] = []

    if mismatch_map:
        patches.extend(
            patches_from_mismatches(mismatch_map, target_document_ref=target_document_ref)
        )
    if rewrite_plan:
        patches.extend(
            patches_from_rewrite_plan(rewrite_plan, target_document_ref=target_document_ref)
        )
    if compliance:
        patches.extend(
            patches_from_compliance(compliance, target_document_ref=target_document_ref)
        )
    if risk:
        patches.extend(
            patches_from_risk(risk, target_document_ref=target_document_ref)
        )

    return patches


def write_whitecrow_patches(
    patches: list[dict[str, Any]],
    output_dir: Path,
    *,
    filename: str = "patch_queue.jsonl",
) -> Path:
    """Write WhiteCrow patch queue as a JSONL file.

    Returns path to the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename

    with open(path, "a", encoding="utf-8") as f:
        for patch in patches:
            f.write(json.dumps(patch, ensure_ascii=False, default=str) + "\n")

    return path
