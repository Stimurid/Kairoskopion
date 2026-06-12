"""Publication Regime Classification prompt family (spec §69.4).

Classifies how publication works at a venue: review process, timeline,
special issue vs regular, open access model, regime type.
"""

from __future__ import annotations

FAMILY_ID = "publication_regime_v1"
FAMILY_NAME = "Publication Regime Classification"
VERSION = "1.0.0"
PURPOSE = (
    "Classify the publication regime of a venue from its guidelines, "
    "editorial policies, and submission instructions. Determines review "
    "type, timeline, open access model, and regime category."
)

INPUT_CONTRACT = {
    "venue_model": "VenueModel dict with basic venue info",
    "guidelines_text": "Raw venue guidelines / author instructions text",
}
OUTPUT_CONTRACT = {
    "publication_regime": "PublicationRegimeModel dict",
    "unknowns": "Aspects of the regime that could not be determined",
}

SYSTEM_PROMPT = """\
You are Publication Regime Classifier — a specialized analytical role \
within Kairoskopion, an evidence-first publication-positioning system.

Your task: given a VenueModel and raw venue guidelines text, classify \
the publication regime — how publication actually works at this venue.

## Regime dimensions to classify

1. **regime_type** — one of: classic_journal_article, \
   special_issue_article, research_topic_article, conference_proceedings, \
   mega_journal, reviewed_preprint, publish_then_review, \
   open_review_conference, humanities_special_issue, book_symposium, \
   focused_debate, edited_volume, non_focus_q3_or_local, \
   zine_or_nonstandard
2. **review_type** — single_blind, double_blind, open_review, \
   editorial_only, none, unknown
3. **typical_review_rounds** — integer or null
4. **typical_review_timeline_weeks** — integer range or null
5. **acceptance_rate** — percentage or null (mark source if vendor claim)
6. **open_access_model** — gold, green, hybrid, closed, unknown
7. **apc_required** — boolean or null
8. **apc_amount** — string or null
9. **page_limit** — integer or null
10. **word_limit** — integer or null
11. **reference_limit** — integer or null
12. **submission_window** — continuous, deadline_based, invitation_only, unknown

## Rules

- Extract from guidelines text. Do NOT guess regime type without evidence.
- If guidelines don't specify a field, mark it unknown.
- Distinguish between what the venue SAYS (vendor claim) and what you \
  can verify (fact from source).
- Do NOT conflate open access with quality.
- Do NOT assume all humanities journals are double-blind.
"""

USER_TEMPLATE = """\
Classify the publication regime for this venue.

## VenueModel
```json
{venue_json}
```

## Guidelines text (may be truncated)
{guidelines_text}

Return a JSON object with the full publication regime classification.
"""

OUTPUT_SCHEMA: dict = {
    "title": "PublicationRegimeResult",
    "type": "object",
    "properties": {
        "regime_type": {"type": "string"},
        "review_type": {
            "type": "string",
            "enum": ["single_blind", "double_blind", "open_review",
                     "editorial_only", "none", "unknown"],
        },
        "typical_review_rounds": {"type": ["integer", "null"]},
        "typical_review_timeline_weeks": {"type": ["string", "null"]},
        "acceptance_rate": {"type": ["string", "null"]},
        "open_access_model": {
            "type": "string",
            "enum": ["gold", "green", "hybrid", "closed", "unknown"],
        },
        "apc_required": {"type": ["boolean", "null"]},
        "apc_amount": {"type": ["string", "null"]},
        "page_limit": {"type": ["integer", "null"]},
        "word_limit": {"type": ["integer", "null"]},
        "reference_limit": {"type": ["integer", "null"]},
        "submission_window": {
            "type": "string",
            "enum": ["continuous", "deadline_based", "invitation_only", "unknown"],
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["regime_type", "unknowns", "confidence"],
    "additionalProperties": False,
}

FORBIDDEN_BEHAVIORS = [
    "Do not guess regime type without textual evidence",
    "Do not conflate open access with quality",
    "Do not assume review type without evidence",
]

EVIDENCE_REQUIREMENTS = [
    "regime_type must trace to guidelines text",
    "Acceptance rates must be marked as vendor_claim unless independently verified",
]

UNKNOWN_HANDLING = "mark_unknown"
VALIDATION_NOTES = "Verify regime_type is a valid enum value"


def validate_publication_regime(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("regime_type"):
        warnings.append("No regime type classified")
    if not data.get("unknowns"):
        warnings.append("No unknowns — unlikely from guidelines text alone")
    return warnings


PUBLICATION_REGIME_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": "publication_regime_classifier",
    "version": VERSION,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_publication_regime,
}
