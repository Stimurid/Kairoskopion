"""Submission Pack prompt family (spec §69.12).

Assembles and validates submission readiness: manuscript files,
cover letter, compliance, risk acknowledgment.
"""

from __future__ import annotations

FAMILY_ID = "submission_pack_v1"
FAMILY_NAME = "Submission Pack"
VERSION = "1.0.0"
PURPOSE = (
    "Assess submission readiness and generate a submission pack "
    "summary: what's ready, what's missing, what needs user action."
)

INPUT_CONTRACT = {
    "article_model": "ArticleModel dict",
    "venue_model": "VenueModel dict",
    "scenario": "SubmissionScenario dict",
    "compliance_checklist": "Optional ComplianceChecklist dict",
    "risk_report": "Optional RiskReport dict",
}
OUTPUT_CONTRACT = {
    "submission_pack": "SubmissionPack dict with readiness assessment",
}

SYSTEM_PROMPT = """\
You are Submission Pack Builder — a specialized role within Kairoskopion.

Your task: given compliance, risk, and rewrite data, assess submission \
readiness and produce a structured submission pack summary.

## Readiness levels

- **ready_for_manual_submission** — all requirements met, risks acknowledged
- **needs_file_update** — manuscript needs changes before submission
- **needs_reference_verification** — bibliography needs checking
- **needs_compliance_check** — formal requirements not verified
- **needs_user_input** — user decisions required
- **not_ready** — blocking issues remain

## Pack contents to assess

1. Manuscript file readiness
2. Cover letter status
3. Compliance checklist completion
4. Risk acknowledgment
5. Outstanding rewrite actions
6. Missing information items
7. User decisions needed

Do not submit anything. Do not automate submission.
"""

USER_TEMPLATE = """\
Assess submission readiness for this article-venue pair.

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

## ComplianceChecklist (may be empty)
```json
{compliance_json}
```

## RiskReport (may be empty)
```json
{risk_json}
```

Return a JSON object with readiness assessment.
"""

OUTPUT_SCHEMA: dict = {
    "title": "SubmissionPackResult",
    "type": "object",
    "properties": {
        "readiness": {
            "type": "string",
            "enum": ["ready_for_manual_submission", "needs_file_update",
                     "needs_reference_verification", "needs_compliance_check",
                     "needs_user_input", "not_ready"],
        },
        "blocking_items": {"type": "array", "items": {"type": "string"}},
        "action_items": {"type": "array", "items": {"type": "string"}},
        "user_decisions_needed": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["readiness", "unknowns", "confidence"],
    "additionalProperties": False,
}

FORBIDDEN_BEHAVIORS = [
    "Do not submit anything automatically",
    "Do not claim readiness without checking compliance",
]

EVIDENCE_REQUIREMENTS = [
    "Readiness must be based on compliance and risk data",
]

UNKNOWN_HANDLING = "mark_unknown"
VALIDATION_NOTES = "readiness should not be ready if blocking_items non-empty"


def validate_submission_pack(data: dict) -> list[str]:
    warnings: list[str] = []
    if data.get("readiness") == "ready_for_manual_submission" and data.get("blocking_items"):
        warnings.append("Readiness is 'ready' but blocking items exist")
    return warnings


SUBMISSION_PACK_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": "submission_pack_builder",
    "version": VERSION,
    "purpose": PURPOSE,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_submission_pack,
    "forbidden_behaviors": FORBIDDEN_BEHAVIORS,
    "evidence_requirements": EVIDENCE_REQUIREMENTS,
    "unknown_handling": UNKNOWN_HANDLING,
}
