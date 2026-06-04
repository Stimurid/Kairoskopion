"""Rewrite Planning Service (spec §6.20, §15.5).

Generates RewritePlan from MismatchMap — action-list mode, no auto-rewrite.
"""

from __future__ import annotations

from ..enums import FieldCoreImpact, LifecycleStatus
from ..ids import rewrite_plan_id
from ..schema import MismatchMap, RewritePlan


_CHANGE_TYPE_MAP = {
    "topic": "intro_reframe",
    "discipline": "intro_reframe",
    "genre": "section_addition",
    "method": "method_disclosure",
    "citation_ecology": "citation_bridge",
    "language_register": "language_register_shift",
    "formal_compliance": "formatting_change",
}


def build_rewrite_plan(
    mismatch_map: MismatchMap,
    *,
    article_model_id: str | None = None,
    manuscript_id: str | None = None,
    venue_model_id: str | None = None,
) -> RewritePlan:
    """Generate action-list RewritePlan from mismatches."""
    changes: list[dict] = []
    has_core_risk = False

    for mm in mismatch_map.mismatches:
        severity = mm.get("severity", "informational")
        if severity == "informational":
            continue  # skip unassessed axes — no rewrite suggested

        axis = mm.get("axis", "?")
        actions = mm.get("possible_actions", [])
        core_impact = mm.get("field_core_risk", FieldCoreImpact.UNKNOWN_CORE_IMPACT.value)

        if core_impact in (FieldCoreImpact.CORE_TOUCHING.value,
                           FieldCoreImpact.CORE_TRANSFORMING.value,
                           FieldCoreImpact.CORE_DESTROYING_RISK.value):
            has_core_risk = True

        change_type = _CHANGE_TYPE_MAP.get(axis, "other")

        for action in actions:
            changes.append({
                "change_id": f"ch_{len(changes) + 1}",
                "target_block": axis,
                "change_type": change_type,
                "current_state": mm.get("article_side", ""),
                "desired_state": action,
                "reason": mm.get("description", ""),
                "evidence_refs": mm.get("evidence_refs", []),
                "related_mismatch_id": mm.get("mismatch_id", ""),
                "field_core_risk": core_impact,
                "difficulty": "medium" if severity == "major" else "high",
                "status": "proposed",
            })

    overall_core_risk = (
        FieldCoreImpact.CORE_TOUCHING.value if has_core_risk
        else FieldCoreImpact.CORE_PRESERVING.value
    )

    effort = "major" if len(changes) >= 4 else "medium" if len(changes) >= 2 else "light"

    return RewritePlan(
        rewrite_plan_id=rewrite_plan_id(),
        article_model_id=article_model_id,
        manuscript_id=manuscript_id,
        fit_assessment_id=mismatch_map.fit_assessment_id,
        target_venue_id=venue_model_id,
        changes=changes,
        summary=f"{len(changes)} proposed change(s), estimated effort: {effort}",
        estimated_effort=effort,
        field_core_risk=overall_core_risk,
        requires_user_acceptance=has_core_risk,
        lifecycle_status=LifecycleStatus.DRAFT.value,
    )
