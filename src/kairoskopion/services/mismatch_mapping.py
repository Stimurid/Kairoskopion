"""Mismatch Mapping Service (spec §6.19).

Translates weak/bad FitAssessment axes into structured MismatchMap.
"""

from __future__ import annotations

from ..enums import FieldCoreImpact, MismatchSeverity
from ..ids import mismatch_map_id
from ..schema import FitAssessment, MismatchMap


# Axes that touch protected core when changed
_CORE_SENSITIVE_AXES = {"discipline", "genre", "method", "novelty_mode"}


def build_mismatch_map(fit: FitAssessment) -> MismatchMap:
    """Generate MismatchMap from axes with weak/bad/unknown values."""
    mismatches: list[dict] = []
    critical: list[str] = []
    unknowns: list[str] = []
    idx = 0

    for ax in fit.axes:
        value = ax.get("value", "unknown")
        if value in ("strong", "medium"):
            continue

        idx += 1
        axis_name = ax.get("axis", "?")
        notes = ax.get("notes", "")
        is_core_sensitive = axis_name in _CORE_SENSITIVE_AXES

        if value == "bad":
            severity = MismatchSeverity.BLOCKING.value
            critical.append(f"mm_{idx}: {axis_name} — blocking mismatch")
        elif value == "weak":
            severity = MismatchSeverity.MAJOR.value
        else:
            severity = MismatchSeverity.INFORMATIONAL.value
            unknowns.append(f"{axis_name}: not assessed — data missing")

        core_impact = (
            FieldCoreImpact.CORE_TOUCHING.value if is_core_sensitive and value in ("weak", "bad")
            else FieldCoreImpact.CORE_PRESERVING.value if not is_core_sensitive
            else FieldCoreImpact.UNKNOWN_CORE_IMPACT.value
        )

        # Track D fix: ``venue_side`` was previously hardcoded to the
        # literal string "Venue expectation on {axis_name}", which
        # rendered in the cockpit as if it were real data. The
        # deterministic mismatch mapper doesn't actually know what the
        # venue expects on a given axis — that requires reading the
        # venue text via an LLM (MismatchNarrativeAgent, backlog).
        # Emit empty string + an unknown so the UI can label it
        # "needs LLM narrative" instead of pretending.
        mismatches.append({
            "mismatch_id": f"mm_{idx}",
            "axis": axis_name,
            "article_side": notes,
            "venue_side": "",
            "description": notes,
            "severity": severity,
            "evidence_refs": ax.get("evidence_refs", []),
            "possible_actions": _suggest_actions(axis_name, value),
            "field_core_risk": core_impact,
            "requires_user_acceptance": is_core_sensitive and value in ("weak", "bad"),
        })
        unknowns.append(
            f"{axis_name}: venue-side description not available "
            "(needs LLM MismatchNarrativeAgent — see VENUE_FIT_BACKLOG.md)"
        )

    summary_parts: list[str] = []
    if critical:
        summary_parts.append(f"{len(critical)} blocking mismatch(es)")
    major = [m for m in mismatches if m["severity"] == MismatchSeverity.MAJOR.value]
    if major:
        summary_parts.append(f"{len(major)} major mismatch(es)")
    info = [m for m in mismatches if m["severity"] == MismatchSeverity.INFORMATIONAL.value]
    if info:
        summary_parts.append(f"{len(info)} unassessed axis/axes")

    return MismatchMap(
        mismatch_map_id=mismatch_map_id(),
        fit_assessment_id=fit.fit_assessment_id,
        mismatches=mismatches,
        summary="; ".join(summary_parts) if summary_parts else "No significant mismatches",
        critical_mismatches=critical,
        unknowns=unknowns,
    )


def _suggest_actions(axis: str, value: str) -> list[str]:
    if value == "unknown":
        return [f"Collect evidence for {axis}"]
    actions: dict[str, list[str]] = {
        "topic": ["Reframe introduction to emphasize venue-relevant aspects"],
        "discipline": ["Add disciplinary bridge section", "Consider alternative venue in home discipline"],
        "genre": ["Restructure as accepted article type", "Add empirical/case component"],
        "method": ["Add empirical section or case study", "Justify conceptual-only approach"],
        "citation_ecology": ["Conduct citation bridge search", "Add venue-relevant references"],
        "language_register": ["Revise register to match venue conventions"],
        "formal_compliance": ["Check author guidelines and adjust formatting"],
        "publication_regime": ["Verify submission route and requirements"],
    }
    return actions.get(axis, [f"Address {axis} mismatch"])
