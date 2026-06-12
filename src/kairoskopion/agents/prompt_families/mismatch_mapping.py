"""Mismatch Mapping prompt family (spec §69.8).

Converts weak/bad fit axes into actionable mismatch descriptions
with severity, field-core impact, and adaptation cost estimates.
"""

from __future__ import annotations

FAMILY_ID = "mismatch_mapping_v1"
FAMILY_NAME = "Mismatch Mapping"
VERSION = "1.0.0"
PURPOSE = (
    "Convert weak or bad fit axes from FitAssessment into structured, "
    "actionable mismatch descriptions. Each mismatch gets severity, "
    "field-core impact assessment, estimated adaptation cost, and "
    "specific description of what's mismatched and why it matters."
)

INPUT_CONTRACT = {
    "fit_assessment": "FitAssessment dict with per-axis ratings",
    "article_model": "ArticleModel dict",
    "venue_model": "VenueModel dict",
}
OUTPUT_CONTRACT = {
    "mismatch_map": "MismatchMap dict with structured mismatches",
    "unknowns": "Mismatches that could not be fully assessed",
}

SYSTEM_PROMPT = """\
You are Mismatch Mapper — a specialized analytical role within \
Kairoskopion, an evidence-first publication-positioning system.

Your task: given a FitAssessment with per-axis ratings, an ArticleModel, \
and a VenueModel, produce a structured mismatch map. Each mismatch must \
describe WHAT is mismatched, WHY it matters for this venue, how SEVERE \
it is, and whether fixing it would TOUCH THE FIELD CORE.

## Mismatch dimensions

For each weak or bad axis in the FitAssessment:

1. **axis** — which fit axis (topic, discipline, genre, method, etc.)
2. **severity** — blocking, major, minor, informational
3. **description** — specific description of the gap
4. **venue_expectation** — what the venue wants/expects
5. **article_current** — what the article currently has
6. **field_core_impact** — core_preserving, core_touching, \
   core_transforming, core_destroying_risk, unknown_core_impact
7. **adaptation_cost** — none, light, medium, major, unknown
8. **adaptation_path** — brief description of what would need to change

## Severity rules

- **blocking** — submission will be desk-rejected without addressing this
- **major** — reviewers will raise this as a significant concern
- **minor** — worth fixing but not a rejection risk
- **informational** — nice to know, no action needed

## Field-core rules

- If fixing the mismatch requires changing the article's central \
  argument, theoretical framework, or core contribution: \
  core_touching or core_transforming
- If the article would lose its point after adaptation: \
  core_destroying_risk
- If only framing/packaging changes: core_preserving

## Rules

- Only create mismatches for weak or bad axes.
- Strong axes should NOT appear as mismatches.
- Medium axes may generate informational mismatches.
- Do NOT fabricate mismatches for axes rated unknown — flag them separately.
"""

USER_TEMPLATE = """\
Map mismatches between this article and venue.

## FitAssessment
```json
{fit_json}
```

## ArticleModel
```json
{article_json}
```

## VenueModel
```json
{venue_json}
```

Return a JSON object with structured mismatches.
"""

OUTPUT_SCHEMA: dict = {
    "title": "MismatchMappingResult",
    "type": "object",
    "properties": {
        "mismatches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "axis": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["blocking", "major", "minor", "informational"],
                    },
                    "description": {"type": "string"},
                    "venue_expectation": {"type": "string"},
                    "article_current": {"type": "string"},
                    "field_core_impact": {"type": "string"},
                    "adaptation_cost": {"type": "string"},
                    "adaptation_path": {"type": "string"},
                },
                "required": ["axis", "severity", "description"],
            },
        },
        "unknown_axes": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["mismatches", "unknowns", "confidence"],
    "additionalProperties": False,
}

FORBIDDEN_BEHAVIORS = [
    "Do not create mismatches for strong axes",
    "Do not fabricate mismatches for unknown axes",
    "Do not minimize field-core impact",
]

EVIDENCE_REQUIREMENTS = [
    "Each mismatch must reference the specific axis rating",
    "Field-core impact must be assessed against article's protected core",
]

UNKNOWN_HANDLING = "flag_unknown_axes_separately"
VALIDATION_NOTES = "Verify no mismatches for strong-rated axes"


def validate_mismatch_mapping(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("mismatches") and not data.get("unknown_axes"):
        warnings.append("No mismatches and no unknown axes — perfect fit is rare")
    return warnings


MISMATCH_MAPPING_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": "mismatch_mapper",
    "version": VERSION,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_mismatch_mapping,
}
