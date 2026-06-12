"""Risk Reporting prompt family (spec §69.10).

Identifies publication risks: desk rejection, review concerns,
ethical issues, timing risks, career risks, field-core risks.
"""

from __future__ import annotations

FAMILY_ID = "risk_reporting_v1"
FAMILY_NAME = "Risk Reporting"
VERSION = "1.0.0"
PURPOSE = (
    "Identify and categorize publication risks for an article-venue "
    "pair. Covers desk rejection risk, reviewer concerns, ethical "
    "issues, timing, career implications, and field-core destruction."
)

INPUT_CONTRACT = {
    "article_model": "ArticleModel dict",
    "venue_model": "VenueModel dict",
    "fit_assessment": "FitAssessment dict",
    "mismatch_map": "Optional MismatchMap dict",
}
OUTPUT_CONTRACT = {
    "risk_report": "RiskReport dict with categorized risk items",
}

SYSTEM_PROMPT = """\
You are Risk Officer — a specialized role within Kairoskopion.

Your task: given an article-venue pair with fit assessment and optional \
mismatch map, identify all publication risks and categorize them.

## Risk categories (18 types from spec)

1. desk_rejection — will editor reject before review?
2. scope_mismatch — article outside venue's scope
3. method_gap — method doesn't meet venue expectations
4. genre_mismatch — wrong article type for venue
5. language_barrier — language/register problems
6. citation_gap — bibliography doesn't match venue norms
7. novelty_concern — novelty claim doesn't fit venue expectations
8. compliance_gap — formal requirements not met
9. timing_risk — submission window/deadline problems
10. author_eligibility — author doesn't meet venue requirements
11. field_core_destruction — adaptation would destroy the work
12. ethical_concern — plagiarism/duplicate/salami risks
13. career_risk — publication in this venue may harm career goals
14. indexing_risk — venue may not meet indexing expectations
15. cost_risk — publication fees beyond budget
16. review_hostility — known hostile reviewer communities
17. regime_instability — venue changing editors/scope/format
18. evidence_insufficiency — not enough data to assess risk

## Risk severity levels

- **critical** — should not submit without resolution
- **high** — significant concern, needs attention
- **medium** — worth noting, monitor
- **low** — minor concern
- **informational** — context, no action needed

## Rules

- Every risk must have a specific justification.
- Do NOT fabricate risks without evidence.
- Do NOT minimize field-core destruction risk.
- Flag evidence_insufficiency for any dimension where data is missing.
"""

USER_TEMPLATE = """\
Assess publication risks for this article-venue pair.

## ArticleModel
```json
{article_json}
```

## VenueModel
```json
{venue_json}
```

## FitAssessment
```json
{fit_json}
```

## MismatchMap (may be empty)
```json
{mismatch_json}
```

Return a JSON object with categorized risk items.
"""

OUTPUT_SCHEMA: dict = {
    "title": "RiskReportResult",
    "type": "object",
    "properties": {
        "risk_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "risk_type": {"type": "string"},
                    "severity": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": {"type": "string"},
                    "mitigation": {"type": ["string", "null"]},
                },
                "required": ["risk_type", "severity", "description"],
            },
        },
        "overall_risk_level": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low"],
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["risk_items", "overall_risk_level", "unknowns", "confidence"],
    "additionalProperties": False,
}

FORBIDDEN_BEHAVIORS = [
    "Do not fabricate risks",
    "Do not minimize field-core destruction",
    "Do not claim zero risk without evidence",
]

EVIDENCE_REQUIREMENTS = [
    "Every risk must cite the specific data that triggered it",
]

UNKNOWN_HANDLING = "generate_evidence_insufficiency_risk"
VALIDATION_NOTES = "Check that evidence_insufficiency risk present when data missing"


def validate_risk_report(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("risk_items"):
        warnings.append("No risks identified — zero-risk assessments need justification")
    return warnings


RISK_REPORTING_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": "risk_officer",
    "version": VERSION,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_risk_report,
}
