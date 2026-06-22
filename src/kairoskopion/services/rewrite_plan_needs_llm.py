"""Round II-B: needs_llm RewritePlan placeholder.

Per Round II-B doctrine, deterministic code MUST NOT emit semantic
rewrite recommendations ("revise introduction", "strengthen literature
review", "clarify method", "adapt to venue", "change argument",
field_core_risk=core_touching unless source-backed). Legacy
``services/rewrite_planning.py::build_rewrite_plan`` remains available
for unit tests and as the LLM agent's deterministic fallback target,
but the production chain now routes through THIS builder instead.

When ``agents/fit/rewrite_planner.py`` is wired as the production LLM
organ, the chain will use its output instead.
"""

from __future__ import annotations

from ..enums import FieldCoreImpact
from ..schema import MismatchMap, RewritePlan
from .semantic_provenance import (
    ORIGIN_NEEDS_LLM,
    ORIGIN_STRUCTURAL_EXTRACTION,
    SEMANTIC_STATUS_NEEDS_LLM,
)


def build_needs_llm_rewrite_plan(
    mismatch_map: MismatchMap | None,
    article_model_id: str | None = None,
    venue_model_id: str | None = None,
) -> RewritePlan:
    """Return a structural-only RewritePlan marked needs_llm.

    Doctrine: no deterministic rewrite recommendations. Empty
    changes[]. estimated_effort=None. field_core_risk=unknown.
    """
    unknowns = [
        "Rewrite recommendations require LLM rewrite_planner organ "
        "(Round II-B). Agent class exists at "
        "agents/fit/rewrite_planner.py with protected-core gate, but "
        "is not wired in the production chain in this pass; concrete "
        "section/claim/citation edits and field-core-risk assessment "
        "must come from that organ."
    ]
    field_origins = {
        "changes": ORIGIN_NEEDS_LLM,
        "summary": ORIGIN_NEEDS_LLM,
        "estimated_effort": ORIGIN_NEEDS_LLM,
        "field_core_risk": ORIGIN_NEEDS_LLM,
        "unknowns": ORIGIN_STRUCTURAL_EXTRACTION,
    }
    return RewritePlan(
        article_model_id=article_model_id,
        target_venue_id=venue_model_id,
        fit_assessment_id=(
            mismatch_map.fit_assessment_id
            if mismatch_map is not None
            else None
        ),
        changes=[],
        summary=None,
        estimated_effort=None,
        field_core_risk=FieldCoreImpact.UNKNOWN_CORE_IMPACT.value,
        requires_user_acceptance=True,
        unknowns=unknowns,
        field_origins=field_origins,
        semantic_status=SEMANTIC_STATUS_NEEDS_LLM,
    )
