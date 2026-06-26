"""Venue Matrix Assessment prompt family — Organ #4.

Produces per-candidate semantic assessment on fit axes.
"""

from __future__ import annotations

VENUE_MATRIX_SYSTEM = """\
You are Venue Matrix Assessor — a specialized role in Kairoskopion's \
venue-positioning pipeline.

Your input: a list of venue candidates (name, scope, subject areas, \
venue type) and an article context (discipline intent or article model).

Your job: for each candidate, produce a lightweight semantic assessment \
on key fit axes: topic_fit, discipline_fit, core_risk.

## Per-candidate output

For each candidate:
1. **venue_candidate_id** — echo the input ID.
2. **canonical_name** — echo the venue name.
3. **semantic_assessment**:
   - **topic_fit** — does the article's topic fit the venue's stated scope?
   - **discipline_fit** — does the article's discipline match?
   - **core_risk** — risk that publishing here would damage the article's \
     intellectual core (force rewrite of central claims/method).
   - **overall_impression** — 1-2 sentence summary.
   - **confidence** — how confident you are in this assessment.

Axis values: "strong", "medium", "weak", "bad", "unknown".

## Rules

- Base your assessment on the venue's scope_summary and subject_areas. \
  If those are empty, return "unknown" for all axes.
- Do NOT fabricate venue knowledge from training data alone. If the \
  venue model has insufficient scope info, say "unknown".
- This is a LIGHTWEIGHT assessment — not a full 12-axis fit. Save depth \
  for FitAssessorAgent.
- Return JSON only.
"""

VENUE_MATRIX_USER_TEMPLATE = """\
Assess the following venue candidates against the article context.

Article context:
{article_context}

Venue candidates:
{candidates_json}

Return a JSON object matching the schema.
"""

VENUE_MATRIX_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "venue_candidate_id": {"type": "string"},
                    "canonical_name": {"type": "string"},
                    "semantic_assessment": {
                        "type": "object",
                        "properties": {
                            "topic_fit": {
                                "type": "string",
                                "enum": ["strong", "medium", "weak",
                                         "bad", "unknown"],
                            },
                            "discipline_fit": {
                                "type": "string",
                                "enum": ["strong", "medium", "weak",
                                         "bad", "unknown"],
                            },
                            "core_risk": {
                                "type": "string",
                                "enum": ["strong", "medium", "weak",
                                         "bad", "unknown"],
                            },
                            "overall_impression": {"type": "string"},
                            "confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                            },
                        },
                        "required": ["topic_fit", "discipline_fit",
                                     "core_risk", "confidence"],
                        "additionalProperties": True,
                    },
                },
                "required": ["venue_candidate_id", "canonical_name",
                             "semantic_assessment"],
                "additionalProperties": True,
            },
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["assessments"],
    "additionalProperties": True,
}


def validate_venue_matrix(data: dict) -> list[str]:
    warnings: list[str] = []
    assessments = data.get("assessments", [])
    if not assessments:
        warnings.append("no assessments returned")
    for i, a in enumerate(assessments):
        if not isinstance(a, dict):
            warnings.append(f"assessment[{i}] is not an object")
            continue
        sa = a.get("semantic_assessment", {})
        if not isinstance(sa, dict):
            warnings.append(f"assessment[{i}] missing semantic_assessment")
    return warnings


VENUE_MATRIX_FAMILY = {
    "family_id": "venue_matrix_assessment_v1",
    "agent_role_id": "venue_matrix_assessor",
    "version": "1.0.0",
    "system_prompt": VENUE_MATRIX_SYSTEM,
    "user_prompt_template": VENUE_MATRIX_USER_TEMPLATE,
    "output_schema": VENUE_MATRIX_OUTPUT_SCHEMA,
    "validator": validate_venue_matrix,
}
