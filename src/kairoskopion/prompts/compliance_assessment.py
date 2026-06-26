"""Compliance Assessment prompt family — Organ #13.

Semantic compliance assessment: does the article's content satisfy
the venue's requirements? Not just field-present/absent.
"""

from __future__ import annotations

COMPLIANCE_ASSESSMENT_SYSTEM = """\
You are Compliance Assessor — a specialized role in Kairoskopion's \
fit-assessment pipeline.

Your input: a structural pre-check (field presence/absence from \
deterministic checklist), an article model, a venue model, and \
optionally a risk report and bibliography profile.

Your job: upgrade the structural checklist with semantic assessment. \
The structural pre-check tells you WHICH fields are present. You \
determine WHETHER the content of those fields SATISFIES the venue's \
requirements.

## Per-item assessment

For each structural checklist item:
1. **item_id** — echo from input.
2. **field** — which field (e.g. "abstract", "word_count", "ai_disclosure").
3. **structural_status** — echo from input ("present", "absent", "unknown").
4. **semantic_status** — your judgment:
   - "satisfied" — content meets venue requirement.
   - "partially_satisfied" — content exists but doesn't fully meet req.
   - "not_satisfied" — content present but fails to meet requirement.
   - "not_required" — venue does not require this.
   - "unknown_not_verified" — cannot determine from available data.
5. **reasoning** — why you judged this way.
6. **severity** — "blocking", "warning", "informational".

Also return:
- **overall_compliance** — "compliant", "conditionally_compliant", \
  "non_compliant", "insufficient_data".
- **summary**, **confidence**, **unknowns**.

## Rules

- NEVER upgrade "absent" structural items to "satisfied" semantically.
- If a field is structurally present but you cannot read its content, \
  use "unknown_not_verified".
- If the venue requirement is unknown, use "unknown_not_verified" — \
  do NOT assume "not_required".
- Structural items are NEVER downgraded by LLM failure — if LLM fails, \
  the structural status stands.
- Return JSON only.
"""

COMPLIANCE_ASSESSMENT_USER_TEMPLATE = """\
Assess compliance semantically for the following structural checklist.

Structural pre-check:
{structural_checklist_json}

Article model (compact):
{article_compact}

Venue model (compact):
{venue_compact}

Return a JSON object matching the schema.
"""

COMPLIANCE_ASSESSMENT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "field": {"type": "string"},
                    "structural_status": {"type": "string"},
                    "semantic_status": {
                        "type": "string",
                        "enum": [
                            "satisfied", "partially_satisfied",
                            "not_satisfied", "not_required",
                            "unknown_not_verified",
                        ],
                    },
                    "reasoning": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["blocking", "warning", "informational"],
                    },
                },
                "required": ["item_id", "field", "semantic_status",
                             "severity"],
                "additionalProperties": True,
            },
        },
        "overall_compliance": {
            "type": "string",
            "enum": ["compliant", "conditionally_compliant",
                     "non_compliant", "insufficient_data"],
        },
        "summary": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "unknowns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["items", "overall_compliance", "summary", "confidence",
                  "unknowns"],
    "additionalProperties": True,
}


def validate_compliance_assessment(data: dict) -> list[str]:
    warnings: list[str] = []
    items = data.get("items", [])
    if not items:
        warnings.append("no compliance items returned")
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            warnings.append(f"item[{i}] is not an object")
            continue
        if (item.get("structural_status") == "absent"
                and item.get("semantic_status") == "satisfied"):
            warnings.append(
                f"item[{i}] ({item.get('field', '?')}): structurally absent "
                f"but semantically 'satisfied' — impossible"
            )
    return warnings


COMPLIANCE_ASSESSMENT_FAMILY = {
    "family_id": "compliance_assessment_v1",
    "agent_role_id": "compliance_assessor",
    "version": "1.0.0",
    "system_prompt": COMPLIANCE_ASSESSMENT_SYSTEM,
    "user_prompt_template": COMPLIANCE_ASSESSMENT_USER_TEMPLATE,
    "output_schema": COMPLIANCE_ASSESSMENT_OUTPUT_SCHEMA,
    "validator": validate_compliance_assessment,
}
