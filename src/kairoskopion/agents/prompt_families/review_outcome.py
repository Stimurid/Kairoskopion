"""Review Outcome / Revision / Rebuttal / Venue Memory prompt family (spec §69.13).

Processes actual review feedback, plans revisions, architects rebuttals,
and updates venue memory from outcomes.
"""

from __future__ import annotations

FAMILY_ID = "review_outcome_v1"
FAMILY_NAME = "Review Outcome"
VERSION = "1.0.0"
PURPOSE = (
    "Process actual peer review feedback: classify reviewer concerns, "
    "plan revisions, architect rebuttals, and extract venue learning "
    "signals for VenueMemory."
)

INPUT_CONTRACT = {
    "review_text": "Raw review text (one or multiple reviewers)",
    "article_model": "ArticleModel dict",
    "venue_model": "VenueModel dict",
    "original_fit_assessment": "Optional FitAssessment from pre-submission",
}
OUTPUT_CONTRACT = {
    "review_outcome": "ReviewOutcome dict with classified concerns",
    "revision_plan": "RevisionPlan dict with ordered actions",
    "rebuttal_points": "List of rebuttal arguments",
    "venue_signals": "Tacit signals learned about the venue",
}

SYSTEM_PROMPT = """\
You are Review Outcome Analyst — a specialized role within Kairoskopion.

Your task: process peer review feedback and extract actionable intelligence.

## Analysis steps

1. **Classify concerns** — for each reviewer concern:
   - Is it about substance (argument, evidence, theory)?
   - Is it about method (approach, data, analysis)?
   - Is it about framing (genre, register, audience)?
   - Is it about compliance (format, length, references)?
   - Is it a misunderstanding of the article?
   - Is it a legitimate criticism?
   - Is it a taste/preference issue?

2. **Plan revisions** — for each legitimate concern:
   - What change addresses it?
   - Does it touch the field core?
   - Is the change compatible with other reviewer requests?
   - What's the effort estimate?

3. **Architect rebuttal** — for each concern:
   - What's the appropriate response type? (accept, partially accept, \
     respectfully disagree, clarify misunderstanding)
   - What evidence supports the response?
   - What's the diplomatic framing?

4. **Extract venue signals** — what did this review reveal about:
   - The venue's actual (not stated) preferences
   - Reviewer community expectations
   - Gap between guidelines and practice
   - Tacit norms not documented elsewhere

## Rules

- Do NOT treat all reviewer requests as equally valid.
- Do NOT recommend changes that destroy the field core.
- Do NOT fabricate evidence for rebuttals.
- Distinguish between requests that must be addressed and those \
  that can be respectfully declined.
"""

USER_TEMPLATE = """\
Analyze this review feedback.

## Review text
{review_text}

## ArticleModel
```json
{article_json}
```

## VenueModel
```json
{venue_json}
```

Return a JSON object with classified concerns, revision plan, and rebuttal points.
"""

OUTPUT_SCHEMA: dict = {
    "title": "ReviewOutcomeResult",
    "type": "object",
    "properties": {
        "concerns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "concern_text": {"type": "string"},
                    "category": {"type": "string"},
                    "legitimacy": {"type": "string"},
                    "response_type": {"type": "string"},
                    "revision_needed": {"type": "boolean"},
                    "field_core_impact": {"type": ["string", "null"]},
                },
                "required": ["concern_text", "category"],
            },
        },
        "revision_actions": {"type": "array", "items": {"type": "object"}},
        "rebuttal_points": {"type": "array", "items": {"type": "object"}},
        "venue_signals": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["concerns", "unknowns", "confidence"],
    "additionalProperties": False,
}

FORBIDDEN_BEHAVIORS = [
    "Do not treat all reviewer requests as equally valid",
    "Do not fabricate evidence for rebuttals",
    "Do not recommend core-destroying changes",
]

EVIDENCE_REQUIREMENTS = [
    "Each concern must quote or paraphrase the review text",
    "Rebuttal evidence must be traceable",
]

UNKNOWN_HANDLING = "mark_unknown"
VALIDATION_NOTES = "Verify concerns list is non-empty"


def validate_review_outcome(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("concerns"):
        warnings.append("No concerns extracted from review — unusual")
    return warnings


REVIEW_OUTCOME_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": "review_outcome_analyst",
    "version": VERSION,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_review_outcome,
}
