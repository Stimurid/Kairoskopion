"""Submission Scenario Service (spec §15.3).

Loads or creates SubmissionScenario from user input.
MVP: load from JSON dict, mark unknowns.
"""

from __future__ import annotations

from typing import Any

from ..enums import LifecycleStatus, RewriteDepth
from ..ids import submission_scenario_id
from ..schema import SubmissionScenario


def build_scenario_from_dict(
    data: dict[str, Any],
    *,
    article_model_id: str | None = None,
    venue_model_id: str | None = None,
) -> SubmissionScenario:
    """Build SubmissionScenario from a JSON-like dict (e.g. loaded from fixture)."""
    unknowns: list[str] = list(data.get("unknowns", []))

    rewrite = data.get("rewrite_depth_allowed", "unknown")
    if rewrite not in {e.value for e in RewriteDepth}:
        rewrite = RewriteDepth.UNKNOWN.value
        unknowns.append("rewrite_depth_allowed not recognized")

    if not data.get("goal"):
        unknowns.append("submission goal not specified")
    if not data.get("deadline"):
        unknowns.append("deadline not specified")

    return SubmissionScenario(
        submission_scenario_id=submission_scenario_id(),
        article_model_id=article_model_id,
        target_venue_ids=[venue_model_id] if venue_model_id else [],
        goal=data.get("goal"),
        target_indexing=data.get("target_indexing"),
        prestige_priority=data.get("prestige_priority"),
        speed_priority=data.get("speed_priority"),
        APC_constraints=data.get("APC_constraints"),
        language_constraints=data.get("language_constraints"),
        deadline=data.get("deadline"),
        rewrite_depth_allowed=rewrite,
        reframe_depth_allowed=data.get("reframe_depth_allowed"),
        risk_tolerance=data.get("risk_tolerance"),
        fallback_allowed=data.get("fallback_allowed", []),
        unknowns=unknowns,
        lifecycle_status=LifecycleStatus.CONFIRMED.value if data.get("goal") else LifecycleStatus.DRAFT.value,
    )
