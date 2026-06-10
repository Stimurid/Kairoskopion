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

_CONDITIONAL_ACTIONS: dict[str, list[str]] = {
    "topic": ["Reframe introduction for target venue once scope is confirmed"],
    "discipline": ["Verify venue's disciplinary scope; add bridge section if needed"],
    "genre": ["Collect author guidelines to confirm accepted article types"],
    "argument_structure": [
        "Review venue's expected argument structure once guidelines obtained",
    ],
    "method": ["Confirm whether venue requires methods section or accepts conceptual work"],
    "citation_ecology": [
        "Conduct citation bridge search for venue-relevant references",
        "Add references from target venue's intellectual tradition",
    ],
    "novelty_positioning": ["Verify venue's novelty expectations from recent issues"],
    "language_register": [
        "Verify language policy — confirm whether submissions in this language are accepted",
        "Prepare translation/adaptation path if needed",
    ],
    "audience": ["Analyze recent issues to understand target audience expectations"],
    "formal_compliance": [
        "Collect official author guidelines",
        "Check word limit, citation style, abstract format, required sections",
    ],
    "author_eligibility": ["Verify author eligibility requirements"],
    "publication_regime": [
        "Verify submission route — open vs. thematic-issue-only",
        "Check whether unsolicited submissions are accepted",
    ],
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
    informational_mismatches: list[dict] = []

    for mm in mismatch_map.mismatches:
        severity = mm.get("severity", "informational")
        if severity == "informational":
            informational_mismatches.append(mm)
            continue

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

    if informational_mismatches:
        _add_conditional_changes(informational_mismatches, changes)

    overall_core_risk = (
        FieldCoreImpact.CORE_TOUCHING.value if has_core_risk
        else FieldCoreImpact.CORE_PRESERVING.value
    )

    effort = "major" if len(changes) >= 4 else "medium" if len(changes) >= 2 else "light"
    n_proposed = sum(1 for c in changes if c.get("status") == "proposed")
    n_conditional = sum(1 for c in changes if c.get("status") == "conditional")
    if n_conditional > 0 and n_proposed == 0:
        summary = (
            f"{n_conditional} conditional action(s) — venue evidence insufficient, "
            f"collect guidelines before rewriting"
        )
    elif n_conditional > 0:
        summary = (
            f"{n_proposed} proposed change(s) + {n_conditional} conditional "
            f"(venue evidence incomplete), estimated effort: {effort}"
        )
    else:
        summary = f"{len(changes)} proposed change(s), estimated effort: {effort}"

    return RewritePlan(
        rewrite_plan_id=rewrite_plan_id(),
        article_model_id=article_model_id,
        manuscript_id=manuscript_id,
        fit_assessment_id=mismatch_map.fit_assessment_id,
        target_venue_id=venue_model_id,
        changes=changes,
        summary=summary,
        estimated_effort=effort,
        field_core_risk=overall_core_risk,
        requires_user_acceptance=has_core_risk,
        lifecycle_status=LifecycleStatus.DRAFT.value,
    )


def _add_conditional_changes(
    informational_mismatches: list[dict],
    changes: list[dict],
) -> None:
    """Generate conditional trajectory actions for unassessed axes."""
    for mm in informational_mismatches:
        axis = mm.get("axis", "?")
        actions = _CONDITIONAL_ACTIONS.get(axis, [f"Collect evidence for {axis}"])
        change_type = _CHANGE_TYPE_MAP.get(axis, "evidence_collection")
        for action in actions:
            changes.append({
                "change_id": f"ch_{len(changes) + 1}",
                "target_block": axis,
                "change_type": change_type,
                "current_state": mm.get("article_side", ""),
                "desired_state": action,
                "reason": f"Axis '{axis}' not assessed — venue data missing",
                "evidence_refs": [],
                "related_mismatch_id": mm.get("mismatch_id", ""),
                "field_core_risk": FieldCoreImpact.UNKNOWN_CORE_IMPACT.value,
                "difficulty": "unknown",
                "status": "conditional",
            })
