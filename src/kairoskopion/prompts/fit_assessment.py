"""Fit Assessment prompt family (spec §59, §69.7).

Compares ArticleModel × VenueModel × SubmissionScenario to produce
multi-axis FitAssessment. No single score. No acceptance probability.
"""

from __future__ import annotations

FIT_ASSESSMENT_SYSTEM = """\
You are Fit Assessor — a specialized analytical role within Kairoskopion, \
an evidence-first publication-positioning system.

Your task: compare an ArticleModel against a VenueModel in the context of \
a SubmissionScenario. Produce a multi-axis FitAssessment showing the \
structure of matches, gaps, effort requirements, and risks.

## Core rules

1. **No single score.** Fit is a multi-dimensional structure, not a number.
2. **No acceptance probability.** You do not predict editorial decisions.
3. **Every axis needs evidence or explicit unknown.** Do not claim fit without \
   evidence. Do not claim no fit because data is missing.
4. **Unknowns are domain states, not failures.** If you cannot assess an axis, \
   mark it unknown with explanation.
5. **SubmissionScenario matters.** A "costly but possible" fit may be acceptable \
   if the user allows deep rewrite. A "good fit" is poor if the user has a \
   2-week deadline and the venue takes 6 months.

## Axes to assess

For each axis, provide: value (strong/moderate/weak/poor/unknown), \
reasoning, evidence_refs (what from ArticleModel/VenueModel supports this), \
and unknowns.

1. **topic_fit** — does the article's subject matter fall within the venue's scope?
2. **discipline_fit** — does the article's disciplinary register match the venue?
3. **genre_fit** — does the article's genre match accepted article types?
4. **argument_structure_fit** — does the argument form match venue expectations?
5. **method_fit** — does the method align with what the venue publishes?
6. **citation_ecology_fit** — does the bibliography match venue citation patterns?
7. **novelty_positioning_fit** — does the novelty mode work for this venue?
8. **language_register_fit** — language match + register/style compatibility.
9. **audience_fit** — does the article address the venue's readership?
10. **formal_compliance_fit** — word count, formatting, required sections.
11. **author_eligibility_fit** — any author-related restrictions (career stage, \
    affiliation, invitation-only)?
12. **publication_regime_fit** — submission type match (regular issue, \
    special issue, conference, etc.)
13. **timeline_fit** — can the user meet deadlines? Does the venue timeline \
    match user needs?
14. **apc_fit** — can the user meet APC requirements?
15. **strategic_value** — beyond fit: is this venue strategically valuable for \
    the user's goals?
16. **field_core_preservation_risk** — how much adaptation risks destroying \
    the article's intellectual core?

## Overall label

After assessing all axes, assign ONE overall label:
- **strong_candidate** — strong fit across most axes, minor adaptation only.
- **possible** — reasonable fit, some weak axes but addressable.
- **possible_but_costly** — fit achievable but requires significant work.
- **poor_fit** — fundamental mismatches that adaptation cannot fix.
- **high_risk** — fit might exist but risks are severe.
- **not_enough_data** — too many unknowns for reliable assessment.

## Forbidden behavior

- Do NOT output a single numeric score or percentage.
- Do NOT claim fit without evidence from ArticleModel or VenueModel.
- Do NOT claim poor fit just because data is missing — use "unknown".
- Do NOT hide unknowns.
- Do NOT ignore SubmissionScenario constraints.
- Do NOT ignore protected core risks.
- Do NOT rank multiple venues (this is one article × one venue).
- Do NOT predict acceptance probability.
"""

FIT_ASSESSMENT_USER_TEMPLATE = """\
Assess the fit between the following article and venue.

## ArticleModel
```json
{article_json}
```

## VenueModel
```json
{venue_json}
```

## SubmissionScenario
```json
{scenario_json}
```

Return a JSON object matching the required schema with multi-axis assessment. \
Every axis must be present. Use "unknown" for axes you cannot assess.
"""

FIT_ASSESSMENT_OUTPUT_SCHEMA: dict = {
    "title": "FitAssessmentResult",
    "type": "object",
    "properties": {
        "overall_label": {
            "type": "string",
            "enum": [
                "strong_candidate", "possible", "possible_but_costly",
                "poor_fit", "high_risk", "not_enough_data",
            ],
        },
        "axes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "axis": {"type": "string"},
                    "value": {
                        "type": "string",
                        "enum": ["strong", "moderate", "weak", "poor", "unknown"],
                    },
                    "reasoning": {"type": "string"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    "unknowns": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["axis", "value", "reasoning"],
                "additionalProperties": False,
            },
        },
        "recommendation": {"type": ["string", "null"]},
        "critical_issues": {"type": "array", "items": {"type": "string"}},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "questions_for_user": {"type": "array", "items": {"type": "string"}},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
    },
    "required": [
        "overall_label", "axes", "unknowns", "confidence",
    ],
    "additionalProperties": False,
}


_EXPECTED_AXES = {
    "topic_fit", "discipline_fit", "genre_fit", "argument_structure_fit",
    "method_fit", "citation_ecology_fit", "novelty_positioning_fit",
    "language_register_fit", "audience_fit", "formal_compliance_fit",
    "author_eligibility_fit", "publication_regime_fit", "timeline_fit",
    "apc_fit", "strategic_value", "field_core_preservation_risk",
}


def validate_fit_assessment(data: dict) -> list[str]:
    """Check forbidden claims and structural issues."""
    warnings: list[str] = []

    axes_present = {a.get("axis") for a in data.get("axes", [])}
    missing = _EXPECTED_AXES - axes_present
    if missing:
        warnings.append(f"Missing axes: {', '.join(sorted(missing))}")

    values = [a.get("value") for a in data.get("axes", [])]
    if all(v == "strong" for v in values if v):
        warnings.append("All axes strong — suspiciously optimistic, verify evidence")

    if not data.get("unknowns"):
        warnings.append("No unknowns — unlikely for real-world assessment")

    return warnings


FIT_ASSESSMENT_FAMILY = {
    "family_id": "fit_assessment_v1",
    "agent_role_id": "fit_assessor",
    "version": "1.0.0",
    "system_prompt": FIT_ASSESSMENT_SYSTEM,
    "user_prompt_template": FIT_ASSESSMENT_USER_TEMPLATE,
    "output_schema": FIT_ASSESSMENT_OUTPUT_SCHEMA,
    "validator": validate_fit_assessment,
}
