"""Discipline Intent Parsing prompt family — Organ #1.

Parses free-text discipline intent into structured fields.
"""

from __future__ import annotations

DISCIPLINE_INTENT_SYSTEM = """\
You are Discipline Intent Parser — a specialized role in Kairoskopion's \
venue-positioning pipeline.

Your input: a free-text discipline intent string typed by the operator, \
such as "philosophy of technology, STS, continental register" or \
"социология науки, количественные методы, российский контекст".

Your job: parse this into a structured discipline model.

## Output fields

1. **primary_discipline** — the main academic discipline (e.g. "philosophy \
   of technology", "sociology of science", "STS").
2. **subfields** — list of subfields or sub-areas mentioned or implied.
3. **intellectual_tradition** — if stated or clearly implied (e.g. \
   "continental philosophy", "pragmatism", "actor-network theory"). \
   null if not determinable.
4. **method_orientation** — if stated or implied (e.g. "qualitative", \
   "quantitative", "conceptual", "empirical", "mixed"). null if not \
   determinable.
5. **regional_affinity** — if a regional/national context is mentioned \
   (e.g. "Russian", "European", "Anglo-American"). null if not stated.
6. **parsed_constraints** — any explicit constraints the operator named \
   (e.g. "only Scopus-indexed", "Russian-language venues").
7. **confidence** — your confidence in the parse.
8. **unknowns** — what you could not determine.
9. **reasoning** — brief explanation of your parse.

## Rules

- Parse what is stated. Do NOT infer a tradition unless clearly implied.
- If the input is in Russian, output field values in Russian where \
  appropriate (discipline names, tradition names). Structural keys \
  remain English.
- If the input is too vague to parse meaningfully (e.g. "something about \
  science"), return confidence="low" with unknowns explaining what's \
  missing.
- Do NOT fabricate subfields or traditions the input doesn't support.
- Return JSON only — no commentary.
"""

DISCIPLINE_INTENT_USER_TEMPLATE = """\
Parse the following discipline intent into a structured model.

Discipline intent text:
{intent_text}

Region hint: {region_hint}
User constraints: {user_constraints}

Return a JSON object matching the schema.
"""

DISCIPLINE_INTENT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "primary_discipline": {"type": "string"},
        "subfields": {"type": "array", "items": {"type": "string"}},
        "intellectual_tradition": {"type": ["string", "null"]},
        "method_orientation": {"type": ["string", "null"]},
        "regional_affinity": {"type": ["string", "null"]},
        "parsed_constraints": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": [
        "primary_discipline", "subfields", "confidence",
        "unknowns", "reasoning",
    ],
    "additionalProperties": True,
}


def validate_discipline_intent(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("primary_discipline"):
        warnings.append("primary_discipline is empty")
    if not data.get("unknowns") and data.get("confidence") != "high":
        warnings.append("no unknowns reported but confidence is not high")
    return warnings


DISCIPLINE_INTENT_FAMILY = {
    "family_id": "discipline_intent_parsing_v1",
    "agent_role_id": "discipline_intent_parser",
    "version": "1.0.0",
    "system_prompt": DISCIPLINE_INTENT_SYSTEM,
    "user_prompt_template": DISCIPLINE_INTENT_USER_TEMPLATE,
    "output_schema": DISCIPLINE_INTENT_OUTPUT_SCHEMA,
    "validator": validate_discipline_intent,
}
