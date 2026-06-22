"""Rewrite / Reframe Planning prompt family (spec §69.9).

Generates RewritePlan or ReframePlan from mismatches: ordered
adaptation actions with field-core impact and effort estimates.
"""

from __future__ import annotations

FAMILY_ID = "rewrite_planning_v1"
FAMILY_NAME = "Rewrite / Reframe Planning"
VERSION = "1.0.0"
PURPOSE = (
    "Generate an ordered action plan for adapting an article to a target "
    "venue. Each action addresses a specific mismatch with estimated "
    "effort, field-core impact, and dependencies. Distinguishes surface "
    "rewrites from deep reframes."
)

INPUT_CONTRACT = {
    "mismatch_map": "MismatchMap dict",
    "article_model": "ArticleModel dict",
    "venue_model": "VenueModel dict",
}
OUTPUT_CONTRACT = {
    "rewrite_plan": "RewritePlan dict with ordered actions",
    "rewrite_depth": "Overall depth: none / light / medium / major",
    "field_core_risk": "Summary of core impact",
}

SYSTEM_PROMPT = """\
You are Rewrite Planner — a specialized role within Kairoskopion.

Your task: given a MismatchMap, ArticleModel, and VenueModel, generate \
an ordered adaptation plan. Each action addresses one or more mismatches.

## Plan structure

Each action in the plan must specify:
1. **action_id** — sequential identifier
2. **target_mismatch** — which mismatch axis this addresses
3. **action_type** — reframe_argument, add_section, remove_section, \
   rewrite_section, add_citations, change_methodology_framing, \
   adjust_word_count, translate, add_empirical_material, other
4. **description** — what to do
5. **effort** — trivial, light, medium, heavy, research_required
6. **field_core_impact** — core_preserving, core_touching, \
   core_transforming, core_destroying_risk
7. **dependencies** — list of action_ids that must be done first
8. **notes** — additional context

## Planning rules

- Order actions by: blocking mismatches first, then dependency order, \
  then by effort (light before heavy).
- If fixing one mismatch makes another worse, flag the conflict.
- If the overall adaptation would destroy the field core, recommend \
  AGAINST this venue and explain why.
- Distinguish REWRITE (surface changes) from REFRAME (structural \
  argument changes).
- Never recommend removing the article's core contribution.

## Output shape (strict)

Return ONE JSON object with key "actions" — an array of action
objects. No markdown, no code fences, no prose around the JSON.
If you genuinely cannot propose actions because of insufficient
data, return {"actions": [], "overall_depth": "none", "unknowns":
["..."], "recommend_against_venue": false} and explain in unknowns.

## Voice

Russian for "description"/"notes" if the ArticleModel is Russian or
its content is predominantly Cyrillic. Otherwise English.
"""

USER_TEMPLATE = """\
Generate a rewrite/reframe plan for this article-venue pair.

## MismatchMap
```json
{mismatch_json}
```

## ArticleModel
```json
{article_json}
```

## VenueModel
```json
{venue_json}
```

{rubric_context}

Return a JSON object with the ordered adaptation plan.
"""

OUTPUT_SCHEMA: dict = {
    "title": "RewritePlanResult",
    "type": "object",
    "properties": {
        "overall_depth": {
            "type": "string",
            "enum": ["none", "light", "medium", "major"],
        },
        "recommend_against_venue": {"type": "boolean"},
        "recommend_against_reason": {"type": ["string", "null"]},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action_id": {"type": "integer"},
                    "target_mismatch": {"type": "string"},
                    "action_type": {"type": "string"},
                    "description": {"type": "string"},
                    "effort": {"type": "string"},
                    "field_core_impact": {"type": "string"},
                    "dependencies": {"type": "array", "items": {"type": "integer"}},
                    "notes": {"type": ["string", "null"]},
                },
                "required": ["action_id", "target_mismatch", "description"],
            },
        },
        "conflicts": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [],
    "additionalProperties": True,
}

FORBIDDEN_BEHAVIORS = [
    "Do not recommend removing the article's core contribution",
    "Do not hide field-core impact behind vague wording",
    "Do not order heavy rewrites before checking if venue is worth it",
]

EVIDENCE_REQUIREMENTS = [
    "Each action must reference the specific mismatch it addresses",
    "Field-core impact must be assessed per action",
]

UNKNOWN_HANDLING = "mark_unknown"
VALIDATION_NOTES = "Verify actions list is non-empty if mismatches exist"


def validate_rewrite_plan(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("actions") and data.get("overall_depth") != "none":
        warnings.append("No actions but depth is not 'none'")
    return warnings


REWRITE_PLANNING_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": "rewrite_planner",
    "version": VERSION,
    "purpose": PURPOSE,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_rewrite_plan,
    "forbidden_behaviors": FORBIDDEN_BEHAVIORS,
    "evidence_requirements": EVIDENCE_REQUIREMENTS,
    "unknown_handling": UNKNOWN_HANDLING,
}
