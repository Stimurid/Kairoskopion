"""Compliance Assessment prompt family — Organ #13.

Semantic compliance with SubmissionPack lifecycle, source freshness,
privacy/export warnings.
"""

from __future__ import annotations

from kairoskopion.prompts.discipline_intent_parsing import (
    _DOMAIN_AGNOSTIC_DOCTRINE,
)

COMPLIANCE_ASSESSMENT_SYSTEM = """\
You are Compliance Assessor — a specialized role in Kairoskopion's \
fit-assessment pipeline.

Your input:
- structural pre-check (field presence/absence from deterministic \
  checklist);
- ArticleModel;
- VenueModel / VenueProfilePackage;
- explicit guidelines text if available;
- source freshness metadata (when venue data was last verified);
- SubmissionScenario;
- RiskReport if available;
- CitationPlan if available;
- RewritePlan if available;
- personal-data flags if present.

Your job: upgrade the structural checklist with semantic assessment \
AND evaluate SubmissionPack readiness.
""" + _DOMAIN_AGNOSTIC_DOCTRINE + """\

## Per-item assessment

For each structural checklist item:
1. **item_id** — echo from input.
2. **field** — which field (abstract, word_count, ai_disclosure, etc.).
3. **structural_status** — echo from input (present, absent, unknown).
4. **semantic_status** — your judgment:
   - "satisfied" — content meets venue requirement.
   - "partially_satisfied" — content exists but doesn't fully meet req.
   - "not_satisfied" — content present but fails requirement.
   - "not_required" — venue does not require this.
   - "unknown_not_verified" — cannot determine from available data.
5. **reasoning** — why you judged this way.
6. **severity** — "blocking", "warning", "informational".

## SubmissionPack readiness

Also assess:
1. **source_freshness** — are venue data sources current?
   - "fresh" (verified within policy window);
   - "stale" (older than acceptable);
   - "unknown" (no freshness metadata).
2. **missing_policy_areas** — venue policy areas not covered by \
   available evidence.
3. **privacy_warnings** — if article contains personal data, case \
   studies, patient data, or identifiable information, flag it.
4. **export_safety_warnings** — if submission requires export to \
   external system, flag data-safety concerns.
5. **submission_pack_readiness** — "ready", "conditionally_ready", \
   "not_ready", "insufficient_data".
6. **user_decisions_required** — decisions the operator must make.

## Overall output

- **items** — per-item assessments.
- **overall_compliance** — "compliant", "conditionally_compliant", \
  "non_compliant", "insufficient_data".
- **semantic_pass** — true/false.
- **source_freshness_status** — overall freshness.
- **missing_policy_areas** — list.
- **privacy_warnings** — list.
- **export_safety_warnings** — list.
- **submission_pack_readiness** — readiness level.
- **user_decisions_required** — list.
- **summary**, **confidence**, **unknowns**.

## Rules

- NEVER upgrade "absent" structural items to "satisfied" semantically.
- If a field is structurally present but you cannot read its content, \
  use "unknown_not_verified".
- If the venue requirement is unknown, use "unknown_not_verified" — \
  do NOT assume "not_required".
- Structural items are NEVER downgraded by LLM failure.
- Do NOT mark ready if source requirements are stale or missing.
- Do NOT infer hidden requirements.
- Do NOT treat unknown as no requirement.
- Do NOT fabricate cover-letter, ethics, or data statements.
- Return JSON only.
"""

COMPLIANCE_ASSESSMENT_USER_TEMPLATE = """\
Assess compliance semantically for the following checklist and \
evaluate SubmissionPack readiness.

Structural pre-check:
{structural_checklist_json}

Article model (compact):
{article_compact}

Venue model (compact):
{venue_compact}

Explicit guidelines:
{guidelines_text}

Source freshness metadata:
{source_freshness}

Submission scenario:
{scenario_json}

Risk report:
{risk_report}

Citation plan:
{citation_plan}

Rewrite plan:
{rewrite_plan}

Personal-data flags:
{personal_data_flags}

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
                        "enum": ["blocking", "warning",
                                 "informational"],
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
        "semantic_pass": {"type": "boolean"},
        "source_freshness_status": {
            "type": "string",
            "enum": ["fresh", "stale", "unknown"],
        },
        "missing_policy_areas": {
            "type": "array",
            "items": {"type": "string"},
        },
        "privacy_warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
        "export_safety_warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
        "submission_pack_readiness": {
            "type": "string",
            "enum": ["ready", "conditionally_ready",
                     "not_ready", "insufficient_data"],
        },
        "user_decisions_required": {
            "type": "array",
            "items": {"type": "string"},
        },
        "summary": {"type": "string"},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low", "none"],
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["items", "overall_compliance", "summary",
                  "confidence", "unknowns"],
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
                f"item[{i}] ({item.get('field', '?')}): structurally "
                f"absent but semantically 'satisfied' — impossible"
            )
    freshness = data.get("source_freshness_status")
    readiness = data.get("submission_pack_readiness")
    if freshness == "stale" and readiness == "ready":
        warnings.append(
            "submission_pack_readiness is 'ready' but "
            "source_freshness_status is 'stale'"
        )
    return warnings


COMPLIANCE_ASSESSMENT_FAMILY = {
    "family_id": "compliance_assessment_v2",
    "agent_role_id": "compliance_assessor",
    "version": "2.0.0",
    "system_prompt": COMPLIANCE_ASSESSMENT_SYSTEM,
    "user_prompt_template": COMPLIANCE_ASSESSMENT_USER_TEMPLATE,
    "output_schema": COMPLIANCE_ASSESSMENT_OUTPUT_SCHEMA,
    "validator": validate_compliance_assessment,
}
