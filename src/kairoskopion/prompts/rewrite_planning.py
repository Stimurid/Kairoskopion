"""Rewrite Planning prompt family — Organ #8.

Given MismatchMap, produces RewritePlan with semantic justification.
"""

from __future__ import annotations

REWRITE_PLANNING_SYSTEM = """\
You are Rewrite Planner — a specialized role in Kairoskopion's \
fit-assessment pipeline.

Your input: a MismatchMap (per-axis mismatches between article and venue), \
plus the ArticleModel and VenueModel.

Your job: for each mismatch, produce a concrete rewrite action with \
semantic justification.

## Per-change output

1. **change_id** — unique ID (rewrite_001, rewrite_002, ...).
2. **target_block** — which part of the article to modify (e.g. \
   "introduction", "method section", "bibliography", "abstract").
3. **change_type** — category: "reframe", "restructure", "add_section", \
   "remove_section", "rewrite_paragraph", "add_citations", \
   "change_terminology", "adjust_register", "format_fix".
4. **description** — what to do and why.
5. **desired_state** — what the section should look like after the change.
6. **difficulty** — "trivial", "moderate", "substantial", "major".
7. **field_core_risk** — risk that this change damages the article's \
   intellectual core: "none", "low", "moderate", "high", "critical".
8. **status** — "proposed" or "conditional" (conditional if depends on \
   uncertain venue expectations).
9. **mismatch_axis** — which fit axis this addresses.

Also return:
- **summary** — overall rewrite effort summary.
- **total_estimated_difficulty** — aggregate difficulty.
- **confidence**, **unknowns**.

## Rules

- Each action must be surgical — section-level or paragraph-level. \
  Do NOT recommend "rewrite the entire manuscript".
- If a mismatch axis has unknown venue expectations, the change must be \
  "conditional" with a note about what needs clarification.
- field_core_risk must be honest. Changing the core argument from \
  "conceptual" to "empirical" is field_core_risk="critical".
- Do NOT suggest fake citations.
- Return JSON only.
"""

REWRITE_PLANNING_USER_TEMPLATE = """\
Produce a rewrite plan for the following mismatches.

Article model (compact):
{article_compact}

Venue model (compact):
{venue_compact}

Mismatches:
{mismatches_json}

Return a JSON object matching the schema.
"""

REWRITE_PLANNING_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "change_id": {"type": "string"},
                    "target_block": {"type": "string"},
                    "change_type": {"type": "string"},
                    "description": {"type": "string"},
                    "desired_state": {"type": "string"},
                    "difficulty": {
                        "type": "string",
                        "enum": ["trivial", "moderate",
                                 "substantial", "major"],
                    },
                    "field_core_risk": {
                        "type": "string",
                        "enum": ["none", "low", "moderate",
                                 "high", "critical"],
                    },
                    "status": {
                        "type": "string",
                        "enum": ["proposed", "conditional"],
                    },
                    "mismatch_axis": {"type": "string"},
                },
                "required": ["change_id", "target_block", "change_type",
                             "description", "difficulty",
                             "field_core_risk", "status"],
                "additionalProperties": True,
            },
        },
        "summary": {"type": "string"},
        "total_estimated_difficulty": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "unknowns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["changes", "summary", "confidence"],
    "additionalProperties": True,
}


def validate_rewrite_plan(data: dict) -> list[str]:
    warnings: list[str] = []
    changes = data.get("changes", [])
    for i, c in enumerate(changes):
        if not isinstance(c, dict):
            warnings.append(f"change[{i}] is not an object")
            continue
        if c.get("field_core_risk") in ("high", "critical"):
            warnings.append(
                f"change[{i}] has {c['field_core_risk']} field_core_risk — "
                f"verify operator awareness"
            )
    return warnings


REWRITE_PLANNING_FAMILY = {
    "family_id": "rewrite_planning_v1",
    "agent_role_id": "rewrite_planner",
    "version": "1.0.0",
    "system_prompt": REWRITE_PLANNING_SYSTEM,
    "user_prompt_template": REWRITE_PLANNING_USER_TEMPLATE,
    "output_schema": REWRITE_PLANNING_OUTPUT_SCHEMA,
    "validator": validate_rewrite_plan,
}
