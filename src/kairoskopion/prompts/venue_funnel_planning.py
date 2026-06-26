"""Venue Funnel Planning prompt family — Organ #2.

Given parsed discipline intent, produces venue family plan.
"""

from __future__ import annotations

VENUE_FUNNEL_SYSTEM = """\
You are Venue Funnel Planner — a specialized role in Kairoskopion's \
venue-positioning pipeline.

Your input: a parsed discipline intent (primary discipline, subfields, \
tradition, method orientation) from Organ #1.

Your job: produce a venue family plan — groups of journals/venues that \
this discipline intent naturally maps to, with search strategies.

## Output fields

For each venue family:
1. **family_name** — human-readable name (e.g. "STS core journals", \
   "Continental philosophy of technology").
2. **discipline_zone** — the discipline area this family covers.
3. **representative_venues** — 2-5 well-known venues in this family. \
   These are LLM suggestions for the operator to verify, NOT confirmed \
   facts.
4. **search_strategy** — how to find more venues in this family (e.g. \
   "search OpenAlex for STS + technology + ethics", "check DOAJ for \
   open-access philosophy journals").
5. **expected_fit** — "high", "medium", or "exploratory".
6. **notes** — any caveats.

Also return:
- **search_priorities** — ordered list of search directions.
- **confidence**, **unknowns**, **reasoning**.

## Rules

- Do NOT fabricate venue names that don't exist. Use well-known venues \
  you are confident about. Mark them as LLM suggestions.
- If the discipline is niche or cross-disciplinary, return fewer \
  families with honest caveats.
- If the input discipline is in Russian, use Russian venue names where \
  appropriate (e.g. "Вопросы философии", not a translation).
- Return JSON only.
"""

VENUE_FUNNEL_USER_TEMPLATE = """\
Given the parsed discipline intent below, produce a venue family plan.

Parsed discipline intent:
{intent_json}

Region hint: {region_hint}
User constraints: {user_constraints}

Return a JSON object matching the schema.
"""

VENUE_FUNNEL_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "venue_families": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "family_name": {"type": "string"},
                    "discipline_zone": {"type": "string"},
                    "representative_venues": {
                        "type": "array", "items": {"type": "string"},
                    },
                    "search_strategy": {"type": "string"},
                    "expected_fit": {
                        "type": "string",
                        "enum": ["high", "medium", "exploratory"],
                    },
                    "notes": {"type": "string"},
                },
                "required": ["family_name", "discipline_zone"],
                "additionalProperties": True,
            },
        },
        "search_priorities": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["venue_families", "confidence", "unknowns", "reasoning"],
    "additionalProperties": True,
}


def validate_venue_funnel(data: dict) -> list[str]:
    warnings: list[str] = []
    families = data.get("venue_families", [])
    if not families:
        warnings.append("no venue families returned")
    for i, f in enumerate(families):
        if not isinstance(f, dict):
            warnings.append(f"family[{i}] is not an object")
            continue
        if not f.get("family_name"):
            warnings.append(f"family[{i}] missing family_name")
    return warnings


VENUE_FUNNEL_FAMILY = {
    "family_id": "venue_funnel_planning_v1",
    "agent_role_id": "venue_funnel_planner",
    "version": "1.0.0",
    "system_prompt": VENUE_FUNNEL_SYSTEM,
    "user_prompt_template": VENUE_FUNNEL_USER_TEMPLATE,
    "output_schema": VENUE_FUNNEL_OUTPUT_SCHEMA,
    "validator": validate_venue_funnel,
}
