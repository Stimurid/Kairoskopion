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

## Output format (MANDATORY — read every word)

You MUST return ONLY a single JSON object. Nothing else.
No markdown. No code fences (```). No prose before or after the JSON.
No XML tags. No explanations outside the JSON. JUST the raw JSON object.

The JSON object MUST have a top-level key "risk_items" — an array of
risk objects. Each risk object MUST have these keys:
  "risk_type": one of the 18 enum values listed above,
  "severity": one of "critical" / "high" / "medium" / "low" / "informational",
  "description": string explaining the risk,
  "evidence": string citing the data that triggered this risk,
  "mitigation": string with recommended action, or null.

Optional top-level keys: "overall_risk_level", "unknowns", "confidence".

If you have no risks to report, return exactly:
{"risk_items": [], "unknowns": ["No risks identified — justification here"]}

Examples of WRONG output (causes system failure):
  Here is my analysis: {"risk_items": [...]}
  ```json\n{"risk_items": [...]}\n```
  I'll analyze the risks...\n{"risk_items": [...]}

Example of CORRECT output:
  {"risk_items": [{"risk_type": "scope_mismatch", "severity": "high", "description": "...", "evidence": "...", "mitigation": "..."}], "unknowns": [], "confidence": "medium"}

## Voice

If the ArticleModel language is Russian or its content is
predominantly Cyrillic, write the "description", "evidence" and
"mitigation" fields in Russian. Otherwise in English.
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

{rubric_context}

IMPORTANT: respond with ONLY the JSON object. No other text.
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
                    "risk_type": {
                        "type": "string",
                        "enum": [
                            "desk_rejection", "scope_mismatch", "method_gap",
                            "genre_mismatch", "language_barrier", "citation_gap",
                            "novelty_concern", "compliance_gap", "timing_risk",
                            "author_eligibility", "field_core_destruction",
                            "ethical_concern", "career_risk", "indexing_risk",
                            "cost_risk", "review_hostility", "regime_instability",
                            "evidence_insufficiency",
                        ],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low", "informational"],
                    },
                    "description": {"type": "string"},
                    "evidence": {"type": "string"},
                    "mitigation": {"type": ["string", "null"]},
                },
                "required": ["risk_type", "severity", "description", "evidence"],
            },
        },
        "overall_risk_level": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low"],
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [],
    "additionalProperties": True,
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
    "purpose": PURPOSE,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_risk_report,
    "forbidden_behaviors": FORBIDDEN_BEHAVIORS,
    "evidence_requirements": EVIDENCE_REQUIREMENTS,
    "unknown_handling": UNKNOWN_HANDLING,
}
