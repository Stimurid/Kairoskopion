"""Depth Recommendation prompt family — Organ #5.

Recommends optimal depth mode given article complexity and venue state.
"""

from __future__ import annotations

DEPTH_RECOMMENDATION_SYSTEM = """\
You are Depth Recommendation Agent — a specialized role in \
Kairoskopion's venue-positioning pipeline.

Your input: article summary, venue summary, current depth mode, \
budget constraints, and investigation state.

Your job: recommend the optimal depth mode (quick / standard / deep / \
exhaustive) with reasoning about cost-quality tradeoffs.

## Depth modes

- **quick** — surface-level checks only (scope match, basic compliance). \
  Use when article-venue fit is obvious or budget is minimal.
- **standard** — full 12-axis fit assessment, mismatch mapping, basic \
  citation ecology. Default for most investigations.
- **deep** — standard + rewrite planning, compliance assessment, \
  bibliography gap analysis. Use for serious submission candidates.
- **exhaustive** — deep + full corpus analysis, editorial board \
  profiling, field-core risk assessment. Use when stakes are high.

## Rules

- Base your recommendation on the article's complexity (cross-disciplinary \
  articles need deeper analysis) and the venue's completeness (well-documented \
  venues need less depth).
- If article/venue data is insufficient to judge, return current mode with \
  confidence="low".
- Do NOT always recommend "exhaustive" — that wastes budget.
- Return JSON only.
"""

DEPTH_RECOMMENDATION_USER_TEMPLATE = """\
Recommend the optimal depth mode for this investigation.

Article summary:
{article_summary}

Venue summary:
{venue_summary}

Current depth mode: {current_depth}
Budget constraints: {budget_constraints}
Investigation state: {investigation_state}

Return a JSON object matching the schema.
"""

DEPTH_RECOMMENDATION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "recommended_depth": {
            "type": "string",
            "enum": ["quick", "standard", "deep", "exhaustive"],
        },
        "reasoning": {"type": "string"},
        "cost_tradeoff": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["recommended_depth", "reasoning", "confidence"],
    "additionalProperties": True,
}


def validate_depth_recommendation(data: dict) -> list[str]:
    warnings: list[str] = []
    if data.get("recommended_depth") not in (
        "quick", "standard", "deep", "exhaustive",
    ):
        warnings.append("invalid recommended_depth value")
    return warnings


DEPTH_RECOMMENDATION_FAMILY = {
    "family_id": "depth_recommendation_v1",
    "agent_role_id": "depth_recommendation",
    "version": "1.0.0",
    "system_prompt": DEPTH_RECOMMENDATION_SYSTEM,
    "user_prompt_template": DEPTH_RECOMMENDATION_USER_TEMPLATE,
    "output_schema": DEPTH_RECOMMENDATION_OUTPUT_SCHEMA,
    "validator": validate_depth_recommendation,
}
