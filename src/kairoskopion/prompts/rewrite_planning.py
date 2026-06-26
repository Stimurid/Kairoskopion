"""Rewrite Planning prompt family — Organ #8.

Universal rewrite/reframe planning with protected-core approval,
PatchQueue readiness, and ArticleVariant awareness.
"""

from __future__ import annotations

from kairoskopion.prompts.discipline_intent_parsing import (
    _DOMAIN_AGNOSTIC_DOCTRINE,
)

REWRITE_PLANNING_SYSTEM = """\
You are Rewrite Planner — a specialized role in Kairoskopion's \
fit-assessment pipeline.

Your input:
- ArticleModel;
- protected core (claims, method, argument form that must not \
  be destroyed);
- FitAssessment (per-axis fit values);
- MismatchMap (per-axis mismatches);
- RiskReport if available;
- CitationPlan if available;
- ComplianceChecklist if available;
- VenueModel / VenueProfilePackage;
- SubmissionScenario.

Your job: produce concrete rewrite and reframe plans with \
protected-core awareness and user-approval requirements.
""" + _DOMAIN_AGNOSTIC_DOCTRINE + """\

## Output structure

1. **rewrite_plan** — form-level changes (within current field/genre):
   Each change:
   - change_id;
   - target_block (section, paragraph, bibliography, abstract, etc.);
   - change_type: "reframe", "restructure", "add_section", \
     "remove_section", "rewrite_paragraph", "add_citations", \
     "change_terminology", "adjust_register", "format_fix";
   - description;
   - desired_state;
   - difficulty: "trivial", "moderate", "substantial", "major";
   - field_core_risk: "none", "low", "moderate", "high", "critical";
   - requires_user_approval: true if field_core_risk >= "moderate" \
     or if the change alters argument, method, or claims;
   - status: "proposed", "conditional" (uncertain venue expectations);
   - mismatch_axis;
   - dependency (other change_ids this depends on).

2. **reframe_candidates** — field/object/genre/method changes \
   (cross-field repositioning):
   Each candidate:
   - reframe_id;
   - description;
   - target_field or target_genre;
   - protected_core_impact: what would be lost;
   - feasibility: "feasible", "risky", "destructive";
   - requires_user_approval: always true;
   - rationale.

3. **variant_suggestions** — if the article could be split or \
   adapted into ArticleVariants for different venues:
   Each suggestion:
   - variant_id;
   - description;
   - target_venue_type;
   - relationship_to_original: "subset", "reframe", "extension";
   - requires_user_approval: always true.

4. **patch_queue_readiness** — is the plan ready for WhiteCrow \
   PatchQueue export?
   - ready: true/false;
   - blocking_issues;
   - user_decisions_needed.

5. **no_op_recommendations** — cases where adaptation would \
   destroy the article and the recommendation is NOT to adapt.

6. **dependency_graph** — change_ids and their dependencies.

7. **summary**, **total_estimated_difficulty**, **confidence**, \
   **unknowns**.

## Rules

- Each action must be surgical — section-level or paragraph-level. \
  Do NOT recommend "rewrite the entire manuscript".
- Do NOT recommend genre conversion without requires_user_approval.
- Do NOT suggest fake citations, methods, or data.
- Do NOT use field-specific rewrite defaults. A math paper's rewrite \
  plan looks nothing like a clinical study's.
- If a mismatch axis has unknown venue expectations, the change must \
  be "conditional".
- field_core_risk must be honest.
- Changes with field_core_risk >= "moderate" MUST have \
  requires_user_approval = true.
- If adaptation would destroy the article's core argument, recommend \
  no_op instead.
- Return JSON only.
"""

REWRITE_PLANNING_USER_TEMPLATE = """\
Produce a rewrite/reframe plan for the following article × venue \
pairing.

Article model (compact):
{article_compact}

Protected core:
{protected_core}

Venue model (compact):
{venue_compact}

FitAssessment:
{fit_assessment}

Mismatches:
{mismatches_json}

Risk report:
{risk_report}

Citation plan:
{citation_plan}

Compliance checklist:
{compliance_checklist}

Submission scenario:
{scenario_json}

Return a JSON object matching the schema.
"""

REWRITE_PLANNING_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "rewrite_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "change_id": {"type": "string"},
                    "target_block": {"type": "string"},
                    "change_type": {"type": "string"},
                    "description": {"type": "string"},
                    "desired_state": {"type": "string"},
                    "difficulty": {
                        "type": "string",
                        "enum": ["trivial", "moderate",
                                 "substantial", "major"],
                    },
                    "field_core_risk": {
                        "type": "string",
                        "enum": ["none", "low", "moderate",
                                 "high", "critical"],
                    },
                    "requires_user_approval": {"type": "boolean"},
                    "status": {
                        "type": "string",
                        "enum": ["proposed", "conditional"],
                    },
                    "mismatch_axis": {"type": "string"},
                    "dependency": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["change_id", "target_block", "change_type",
                             "description", "difficulty",
                             "field_core_risk",
                             "requires_user_approval", "status"],
                "additionalProperties": True,
            },
        },
        "reframe_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "reframe_id": {"type": "string"},
                    "description": {"type": "string"},
                    "target_field": {"type": ["string", "null"]},
                    "target_genre": {"type": ["string", "null"]},
                    "protected_core_impact": {"type": "string"},
                    "feasibility": {
                        "type": "string",
                        "enum": ["feasible", "risky", "destructive"],
                    },
                    "requires_user_approval": {"type": "boolean"},
                    "rationale": {"type": "string"},
                },
                "required": ["reframe_id", "description",
                             "feasibility", "requires_user_approval"],
                "additionalProperties": True,
            },
        },
        "variant_suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "variant_id": {"type": "string"},
                    "description": {"type": "string"},
                    "target_venue_type": {"type": "string"},
                    "relationship_to_original": {
                        "type": "string",
                        "enum": ["subset", "reframe", "extension"],
                    },
                    "requires_user_approval": {"type": "boolean"},
                },
                "required": ["variant_id", "description",
                             "requires_user_approval"],
                "additionalProperties": True,
            },
        },
        "patch_queue_readiness": {
            "type": "object",
            "properties": {
                "ready": {"type": "boolean"},
                "blocking_issues": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "user_decisions_needed": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["ready"],
            "additionalProperties": True,
        },
        "no_op_recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "axis": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["axis", "reason"],
                "additionalProperties": True,
            },
        },
        "summary": {"type": "string"},
        "total_estimated_difficulty": {"type": "string"},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low", "none"],
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["rewrite_plan", "summary", "confidence"],
    "additionalProperties": True,
}


def validate_rewrite_plan(data: dict) -> list[str]:
    warnings: list[str] = []
    for i, c in enumerate(data.get("rewrite_plan", [])):
        if not isinstance(c, dict):
            warnings.append(f"change[{i}] is not an object")
            continue
        risk = c.get("field_core_risk", "none")
        approval = c.get("requires_user_approval", False)
        if risk in ("moderate", "high", "critical") and not approval:
            warnings.append(
                f"change[{i}] has {risk} field_core_risk but "
                f"requires_user_approval is false"
            )
    for i, r in enumerate(data.get("reframe_candidates", [])):
        if isinstance(r, dict) and not r.get("requires_user_approval"):
            warnings.append(
                f"reframe_candidate[{i}] missing requires_user_approval"
            )
    return warnings


REWRITE_PLANNING_FAMILY = {
    "family_id": "rewrite_planning_v2",
    "agent_role_id": "rewrite_planner",
    "version": "2.0.0",
    "system_prompt": REWRITE_PLANNING_SYSTEM,
    "user_prompt_template": REWRITE_PLANNING_USER_TEMPLATE,
    "output_schema": REWRITE_PLANNING_OUTPUT_SCHEMA,
    "validator": validate_rewrite_plan,
}
