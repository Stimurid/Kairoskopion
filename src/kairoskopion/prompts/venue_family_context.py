"""Venue Family Context prompt family — Organ #3.

Given a concrete venue, infers its discipline family and sibling venues.
"""

from __future__ import annotations

VENUE_FAMILY_CONTEXT_SYSTEM = """\
You are Venue Family Context Builder — a specialized role in \
Kairoskopion's venue-positioning pipeline.

Your input: a VenueModel (already extracted from venue text) — \
canonical name, scope, subject areas, venue type.

Your job: infer the venue's discipline family context — what academic \
community this venue belongs to, sibling/competitor venues, its role \
within the venue cluster.

## Output fields

For each family the venue belongs to (a venue may span 1-3 families):
1. **family_name** — name of the venue cluster/family.
2. **discipline_zone** — the discipline area.
3. **venue_role_in_family** — role of this specific venue: "flagship", \
   "mid-tier", "emerging", "niche", "interdisciplinary bridge".
4. **sibling_venues** — 2-5 similar venues. These are LLM suggestions \
   for operator verification.

Also return:
- **families_status** — "assessed" if analysis succeeded.
- **confidence**, **unknowns**, **reasoning**.

## Rules

- Ground your analysis in the venue's scope_summary and subject_areas. \
  Do NOT rely on training data alone — if the venue model has scope info, \
  use it.
- Do NOT fabricate sibling venue names you are not confident about.
- If the venue is obscure or you cannot confidently place it, return \
  confidence="low" with explicit unknowns.
- Return JSON only.
"""

VENUE_FAMILY_CONTEXT_USER_TEMPLATE = """\
Given the venue model below, infer its discipline family context.

Venue model:
{venue_json}

Return a JSON object matching the schema.
"""

VENUE_FAMILY_CONTEXT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "source_venue": {"type": "string"},
        "families": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "family_name": {"type": "string"},
                    "discipline_zone": {"type": "string"},
                    "venue_role_in_family": {"type": "string"},
                    "sibling_venues": {
                        "type": "array", "items": {"type": "string"},
                    },
                },
                "required": ["family_name", "discipline_zone"],
                "additionalProperties": True,
            },
        },
        "families_status": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["source_venue", "families", "families_status",
                  "confidence", "unknowns", "reasoning"],
    "additionalProperties": True,
}


def validate_venue_family_context(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("families"):
        warnings.append("no families returned")
    if not data.get("source_venue"):
        warnings.append("source_venue is empty")
    return warnings


VENUE_FAMILY_CONTEXT_FAMILY = {
    "family_id": "venue_family_context_v1",
    "agent_role_id": "venue_family_context_builder",
    "version": "1.0.0",
    "system_prompt": VENUE_FAMILY_CONTEXT_SYSTEM,
    "user_prompt_template": VENUE_FAMILY_CONTEXT_USER_TEMPLATE,
    "output_schema": VENUE_FAMILY_CONTEXT_OUTPUT_SCHEMA,
    "validator": validate_venue_family_context,
}
