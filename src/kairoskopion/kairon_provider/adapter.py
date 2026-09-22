"""Normalization helpers from existing Kairoskopion diagnostics to Kairon pressure.

This module does not authorize manuscript changes. It translates existing fit
and mismatch diagnostics into evidence-bearing pressure items for Kairon.
"""

from __future__ import annotations

from typing import Any

from .models import TargetPressureItem, TargetPressurePack


_DEPTH_BY_SEVERITY = {
    "bad": "structural_or_deeper",
    "weak": "local_or_structural",
    "medium": "local",
    "strong": "none",
    "unknown": "evidence_needed",
    "critical": "identity_or_reseed_review",
    "major": "structural_or_deeper",
    "moderate": "local_or_structural",
    "minor": "local",
}


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    raise TypeError(f"Unsupported diagnostic object: {type(value)!r}")


def _norm_value(value: Any) -> str:
    if value is None:
        return "unknown"
    return str(value).strip().lower() or "unknown"


def pressure_pack_from_diagnostics(
    *,
    target_id: str,
    snapshot_id: str,
    fit: Any = None,
    mismatch_map: Any = None,
    evidence_refs: list[str] | None = None,
) -> TargetPressurePack:
    """Build a provider pressure pack without claiming Kairon authority.

    Weak/bad/unknown fit axes and explicit mismatches become pressure items.
    Strong axes are omitted because they do not currently require transduction.
    Existing evidence refs are preserved, and unknowns stay explicit.
    """
    fit_d = _as_dict(fit)
    mm_d = _as_dict(mismatch_map)
    shared_refs = list(evidence_refs or [])
    items: list[TargetPressureItem] = []
    unknowns: list[str] = []

    axes = fit_d.get("axes") or fit_d.get("fit_axes") or []
    if isinstance(axes, dict):
        axes = [
            {"axis": key, **(val if isinstance(val, dict) else {"value": val})}
            for key, val in axes.items()
        ]

    for idx, axis in enumerate(axes):
        if not isinstance(axis, dict):
            continue
        dimension = str(axis.get("axis") or axis.get("name") or axis.get("dimension") or f"axis_{idx}")
        value = _norm_value(axis.get("value") or axis.get("status") or axis.get("fit"))
        if value == "strong":
            continue
        refs = list(dict.fromkeys(shared_refs + list(axis.get("evidence_refs") or [])))
        observation = str(axis.get("notes") or axis.get("reason") or f"{dimension} fit is {value}")
        items.append(
            TargetPressureItem(
                pressure_id=f"fit:{dimension}:{idx}",
                dimension=dimension,
                observation=observation,
                evidence_refs=refs,
                evidence_status=str(axis.get("evidence_status") or "inference"),
                severity=value,
                transformation_depth_hint=_DEPTH_BY_SEVERITY.get(value, "unknown"),
                uncertainty=list(axis.get("unknowns") or []),
                source_kind="fit_axis",
            )
        )
        if value == "unknown":
            unknowns.append(f"fit:{dimension}")

    mismatches = mm_d.get("mismatches") or mm_d.get("items") or []
    for idx, mm in enumerate(mismatches):
        if not isinstance(mm, dict):
            continue
        dimension = str(mm.get("axis") or mm.get("dimension") or mm.get("type") or f"mismatch_{idx}")
        severity = _norm_value(mm.get("severity") or mm.get("value"))
        refs = list(dict.fromkeys(shared_refs + list(mm.get("evidence_refs") or [])))
        observation = str(
            mm.get("description")
            or mm.get("reason")
            or mm.get("current_state")
            or f"Mismatch on {dimension}"
        )
        depth = str(mm.get("transformation_depth_hint") or _DEPTH_BY_SEVERITY.get(severity, "unknown"))
        uncertainty = list(mm.get("unknowns") or [])
        if mm.get("field_core_risk") in ("core_touching", "core_transforming", "core_destroying_risk"):
            depth = "identity_or_reseed_review"
        items.append(
            TargetPressureItem(
                pressure_id=str(mm.get("mismatch_id") or f"mismatch:{dimension}:{idx}"),
                dimension=dimension,
                observation=observation,
                evidence_refs=refs,
                evidence_status=str(mm.get("evidence_status") or "inference"),
                severity=severity,
                transformation_depth_hint=depth,
                uncertainty=uncertainty,
                source_kind="mismatch",
            )
        )
        unknowns.extend(f"mismatch:{dimension}:{u}" for u in uncertainty)

    return TargetPressurePack(
        target_id=target_id,
        snapshot_id=snapshot_id,
        items=items,
        unknowns=list(dict.fromkeys(unknowns)),
    )
