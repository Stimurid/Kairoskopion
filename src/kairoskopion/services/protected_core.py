"""Protected core enforcement — validate changes against protected elements.

The protected core is a list of semantic elements that cannot be modified
without explicit user acceptance: central thesis, object of inquiry,
key distinctions, methodological stance, authorial voice, etc.

This service checks whether proposed changes (from RewritePlan) intersect
with protected core elements, and gates them accordingly.
"""

from __future__ import annotations

import dataclasses as dc
import re
from typing import Any

from ..enums import FieldCoreImpact
from ..ids import generate_id
from ..schema import RewritePlan, _DictMixin, _field, _list, _now


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------

@dc.dataclass
class CoreImpactAssessment(_DictMixin):
    change_id: str = ""
    target_block: str = ""
    matched_core_elements: list[str] = _list()
    computed_impact: str = FieldCoreImpact.UNKNOWN_CORE_IMPACT.value
    original_impact: str = FieldCoreImpact.UNKNOWN_CORE_IMPACT.value
    status: str = "proposed"
    reason: str = ""


@dc.dataclass
class ProtectedCoreValidationResult(_DictMixin):
    validation_id: str = dc.field(default_factory=lambda: generate_id("pcv"))
    rewrite_plan_id: str = ""
    total_changes: int = 0
    blocked_count: int = 0
    core_touching_count: int = 0
    core_preserving_count: int = 0
    assessments: list[dict[str, Any]] = _list()
    requires_user_consent: bool = False
    protected_core_elements: list[str] = _list()
    unknowns: list[str] = _list()
    disclaimer: str = (
        "Protected core validation uses keyword overlap heuristics. "
        "LLM-based semantic analysis would improve accuracy."
    )
    validated_at: str = dc.field(default_factory=_now)


# ---------------------------------------------------------------------------
# Core axis mapping — which rewrite target_blocks touch which core aspects
# ---------------------------------------------------------------------------

_CORE_SENSITIVE_AXES = {
    "topic", "discipline", "argument_structure", "method",
    "novelty_positioning", "genre",
}

_CORE_KEYWORDS = {
    "thesis": ["thesis", "central claim", "argument", "position", "claim"],
    "methodology": ["method", "methodology", "approach", "framework", "analysis"],
    "object": ["object of inquiry", "research object", "subject", "phenomenon"],
    "distinction": ["distinction", "dichotomy", "opposition", "contrast", "tension"],
    "voice": ["voice", "authorial", "perspective", "stance", "register"],
    "vocabulary": ["vocabulary", "terminology", "concept", "term", "notion"],
}


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _find_core_matches(
    change: dict[str, Any],
    protected_core: list[str],
) -> list[str]:
    """Find which protected core elements a change might affect."""
    if not protected_core:
        return []

    target = change.get("target_block", "")
    desired = change.get("desired_state", "")
    reason = change.get("reason", "")
    change_text = _normalize(f"{target} {desired} {reason}")

    matches = []
    for element in protected_core:
        element_norm = _normalize(element)
        if not element_norm:
            continue

        # Direct substring match
        if element_norm in change_text or change_text in element_norm:
            matches.append(element)
            continue

        # Keyword overlap
        element_words = set(element_norm.split())
        change_words = set(change_text.split())
        overlap = element_words & change_words
        significant_words = overlap - {
            "the", "a", "an", "of", "in", "to", "for", "and", "or", "is", "are",
            "be", "not", "with", "from", "at", "by", "on", "as", "this", "that",
        }
        if len(significant_words) >= 2:
            matches.append(element)

    return matches


def _compute_impact(
    change: dict[str, Any],
    matches: list[str],
    original_impact: str,
) -> str:
    """Compute the effective core impact given matches and original assessment."""
    target = change.get("target_block", "")

    if matches:
        if original_impact in (
            FieldCoreImpact.CORE_DESTROYING_RISK.value,
            FieldCoreImpact.CORE_TRANSFORMING.value,
        ):
            return original_impact
        return FieldCoreImpact.CORE_TOUCHING.value

    if target in _CORE_SENSITIVE_AXES:
        if original_impact == FieldCoreImpact.UNKNOWN_CORE_IMPACT.value:
            return FieldCoreImpact.CORE_TOUCHING.value
        return original_impact

    return original_impact if original_impact != FieldCoreImpact.UNKNOWN_CORE_IMPACT.value \
        else FieldCoreImpact.CORE_PRESERVING.value


def validate_rewrite_plan(
    plan: RewritePlan,
    protected_core: list[str],
) -> ProtectedCoreValidationResult:
    """Validate a rewrite plan against the article's protected core elements.

    For each change in the plan:
    - Check if the change's target/content intersects protected core elements
    - Compute effective core impact (upgrade from unknown if matches found)
    - Mark core-touching/transforming/destroying changes as blocked_pending_consent

    Returns a validation result with per-change assessments.
    """
    result = ProtectedCoreValidationResult(
        rewrite_plan_id=plan.rewrite_plan_id,
        protected_core_elements=list(protected_core),
    )

    changes = plan.changes or []
    result.total_changes = len(changes)

    if not changes:
        return result

    if not protected_core:
        result.unknowns.append(
            "No protected core elements defined — cannot validate. "
            "All changes pass through without core enforcement."
        )
        for change in changes:
            result.assessments.append(CoreImpactAssessment(
                change_id=change.get("change_id", ""),
                target_block=change.get("target_block", ""),
                computed_impact=change.get("field_core_risk",
                                           FieldCoreImpact.UNKNOWN_CORE_IMPACT.value),
                original_impact=change.get("field_core_risk",
                                           FieldCoreImpact.UNKNOWN_CORE_IMPACT.value),
                status=change.get("status", "proposed"),
                reason="No protected core — pass-through",
            ).to_dict())
        result.core_preserving_count = len(changes)
        return result

    blocked = 0
    core_touching = 0
    core_preserving = 0

    for change in changes:
        original_impact = change.get(
            "field_core_risk", FieldCoreImpact.UNKNOWN_CORE_IMPACT.value
        )
        matches = _find_core_matches(change, protected_core)
        computed = _compute_impact(change, matches, original_impact)

        is_blocked = computed in (
            FieldCoreImpact.CORE_TOUCHING.value,
            FieldCoreImpact.CORE_TRANSFORMING.value,
            FieldCoreImpact.CORE_DESTROYING_RISK.value,
        )

        if is_blocked:
            status = "blocked_pending_consent"
            blocked += 1
            core_touching += 1
        else:
            status = change.get("status", "proposed")
            core_preserving += 1

        assessment = CoreImpactAssessment(
            change_id=change.get("change_id", ""),
            target_block=change.get("target_block", ""),
            matched_core_elements=matches,
            computed_impact=computed,
            original_impact=original_impact,
            status=status,
            reason=f"Matches: {', '.join(matches)}" if matches else "No core overlap",
        )
        result.assessments.append(assessment.to_dict())

    result.blocked_count = blocked
    result.core_touching_count = core_touching
    result.core_preserving_count = core_preserving
    result.requires_user_consent = blocked > 0

    return result


def apply_core_gate(
    plan: RewritePlan,
    validation: ProtectedCoreValidationResult,
) -> RewritePlan:
    """Apply core gate to a rewrite plan: block changes that touch protected core.

    Returns a new RewritePlan with blocked changes marked as blocked_pending_consent.
    The original plan is not modified.
    """
    if not validation.requires_user_consent:
        return plan

    gated_changes = []
    assessment_map = {
        a.get("change_id", ""): a for a in validation.assessments
    }

    for change in plan.changes:
        change_copy = dict(change)
        assessment = assessment_map.get(change.get("change_id", ""))
        if assessment and assessment.get("status") == "blocked_pending_consent":
            change_copy["status"] = "blocked_pending_consent"
            change_copy["field_core_risk"] = assessment.get("computed_impact",
                                                             change.get("field_core_risk"))
            change_copy["_blocked_reason"] = assessment.get("reason", "")
            change_copy["_matched_core_elements"] = assessment.get("matched_core_elements", [])
        gated_changes.append(change_copy)

    return RewritePlan(
        rewrite_plan_id=plan.rewrite_plan_id,
        article_model_id=plan.article_model_id,
        manuscript_id=plan.manuscript_id,
        fit_assessment_id=plan.fit_assessment_id,
        target_venue_id=plan.target_venue_id,
        changes=gated_changes,
        summary=(plan.summary or "") + " [CORE GATE: consent required]",
        estimated_effort=plan.estimated_effort,
        field_core_risk=plan.field_core_risk,
        requires_user_acceptance=True,
        lifecycle_status=plan.lifecycle_status,
    )
