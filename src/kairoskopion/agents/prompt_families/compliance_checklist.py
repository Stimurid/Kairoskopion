"""Compliance Checklist prompt family (spec §69.11).

Verifies formal submission requirements: word count, format, sections,
cover letter, figures, supplementary materials, author information.
"""

from __future__ import annotations

FAMILY_ID = "compliance_checklist_v1"
FAMILY_NAME = "Compliance Checklist"
VERSION = "1.0.0"
PURPOSE = (
    "Check article against venue's formal submission requirements and "
    "produce a structured checklist of met/unmet/unknown items."
)

INPUT_CONTRACT = {
    "article_model": "ArticleModel dict",
    "venue_model": "VenueModel dict with formal requirements",
    "manuscript_model": "Optional ManuscriptModel for structural checks",
}
OUTPUT_CONTRACT = {
    "compliance_checklist": "ComplianceChecklist dict",
}

SYSTEM_PROMPT = """\
You are Compliance Auditor — a specialized role within Kairoskopion.

Your task: check an article against a venue's formal requirements and \
produce a compliance checklist.

## Checklist dimensions

1. Word/page count limits
2. Abstract length
3. Required sections (introduction, methodology, discussion, etc.)
4. Reference format (APA, Chicago, numbered, etc.)
5. Figure/table requirements
6. Supplementary material policy
7. Author information requirements
8. Cover letter requirements
9. Language/register requirements
10. File format requirements
11. Conflict of interest disclosure
12. Funding acknowledgment
13. Ethics statement (if empirical)
14. Data availability statement
15. ORCID/author identifiers

## Status per item

- **met** — requirement satisfied
- **unmet** — requirement not satisfied
- **unknown_requirement** — venue doesn't specify or unclear
- **unknown_article** — can't determine from article data
- **not_applicable** — requirement doesn't apply to this article type

## Rules

- Only flag requirements that the venue actually states.
- Do NOT invent requirements the venue doesn't have.
- If the venue guidelines are incomplete, flag what's unknown.
- Distinguish between hard requirements and recommendations.
"""

USER_TEMPLATE = """\
Check compliance for this article-venue pair.

## ArticleModel
```json
{article_json}
```

## VenueModel
```json
{venue_json}
```

## ManuscriptModel (may be empty)
```json
{manuscript_json}
```

## Venue Guidelines (may be empty)
{guidelines_text}

Return a JSON object with the compliance checklist.
"""

OUTPUT_SCHEMA: dict = {
    "title": "ComplianceChecklistResult",
    "type": "object",
    "properties": {
        "checklist_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "requirement": {"type": "string"},
                    "category": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["met", "unmet", "unknown_requirement",
                                 "unknown_article", "not_applicable"],
                    },
                    "details": {"type": ["string", "null"]},
                    "hard_requirement": {"type": "boolean"},
                },
                "required": ["requirement", "status"],
            },
        },
        "met_count": {"type": "integer"},
        "unmet_count": {"type": "integer"},
        "unknown_count": {"type": "integer"},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["checklist_items", "unknowns", "confidence"],
    "additionalProperties": False,
}

FORBIDDEN_BEHAVIORS = [
    "Do not invent requirements the venue does not state",
    "Do not assume compliance without evidence",
]

EVIDENCE_REQUIREMENTS = [
    "Each checklist item must reference venue guidelines",
]

UNKNOWN_HANDLING = "mark_unknown_requirement_or_article"
VALIDATION_NOTES = "Verify checklist is non-empty"


def validate_compliance(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("checklist_items"):
        warnings.append("Empty checklist — every venue has some requirements")
    return warnings


COMPLIANCE_CHECKLIST_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": "compliance_auditor",
    "version": VERSION,
    "purpose": PURPOSE,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_compliance,
    "forbidden_behaviors": FORBIDDEN_BEHAVIORS,
    "evidence_requirements": EVIDENCE_REQUIREMENTS,
    "unknown_handling": UNKNOWN_HANDLING,
}
