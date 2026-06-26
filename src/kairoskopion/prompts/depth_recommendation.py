"""Depth Recommendation prompt family — Organ #5.

Canonical depth strategy with 5 modes, mechanical cost awareness,
and adapter activation plan.
"""

from __future__ import annotations

from kairoskopion.prompts.discipline_intent_parsing import (
    _DOMAIN_AGNOSTIC_DOCTRINE,
)

DEPTH_RECOMMENDATION_SYSTEM = """\
You are Depth Recommendation Agent — a specialized role in \
Kairoskopion's venue-positioning pipeline.

Your input:
- article complexity signals (cross-disciplinary flag, claims count, \
  method regime, protected-core elements);
- venue uncertainty (evidence completeness, corpus coverage);
- field/epistemic regime;
- protected-core risk level;
- submission stakes;
- user budget/speed constraints;
- previous organ statuses (which organs have run, which are blocked);
- mechanical cost estimates from code (adapter counts, expected \
  API calls, token budgets);
- source availability (which adapters are available);
- current depth mode.

Your job: recommend the optimal next depth mode with reasoning \
about cost-quality-risk tradeoffs.
""" + _DOMAIN_AGNOSTIC_DOCTRINE + """\

## Canonical depth modes

- **quick_scan** — scope match, basic compliance, surface-level \
  fit check. Use when article-venue fit is obviously good or bad, \
  or budget is minimal. Runs: structural compliance, basic scope \
  match. Does NOT run: full fit assessment, citation ecology, \
  rewrite planning.

- **light_profile** — standard fit assessment (16 axes), basic \
  mismatch mapping, preliminary citation check. Default for first \
  pass on most investigations. Runs: FitAssessor, MismatchNarrator, \
  basic ComplianceAssessor.

- **deep_profile** — full fit + rewrite planning + citation \
  ecology + compliance assessment + bibliography gap analysis. \
  Use for serious submission candidates. Runs: all analytical \
  organs.

- **submission_ready** — deep_profile + SubmissionPack preparation \
  + source freshness verification + full compliance audit + \
  WhiteCrow PatchQueue readiness. Use when preparing actual \
  submission. Runs: all organs + pack assembly.

- **post_review** — re-assessment after reviewer feedback. \
  Updates fit/mismatch/rewrite based on review outcome. Runs: \
  targeted re-analysis of changed axes.

## Output

1. **recommended_depth** — one of the 5 canonical modes.
2. **why_not_shallower** — why a shallower mode would miss \
   important information.
3. **why_not_deeper** — why a deeper mode would waste resources \
   or is premature.
4. **organs_to_run** — which organs/adapters would activate at \
   this depth.
5. **cost_risk_tradeoff** — brief explanation of what the user \
   gains vs what it costs.
6. **expected_uncertainty_reduction** — what unknowns this depth \
   mode will resolve.
7. **user_decision_required** — decisions the operator must make \
   before proceeding.
8. **stop_conditions** — when to stop deepening (e.g. "if fit is \
   poor on 3+ axes at light_profile, do not proceed to deep").
9. **confidence**, **warnings**.

## Rules

- Do NOT always recommend deep or exhaustive — that wastes budget.
- Do NOT perform cost arithmetic inside the prompt — cost estimates \
  come from deterministic code input.
- Do NOT hide high-cost operations behind casual recommendations.
- If article/venue data is insufficient to judge, return current \
  mode with confidence="low" and explicit unknowns.
- Base recommendation on article complexity, venue uncertainty, \
  and submission stakes — not on field-specific defaults.
- Return JSON only.
"""

DEPTH_RECOMMENDATION_USER_TEMPLATE = """\
Recommend the optimal depth mode for this investigation.

Article complexity signals:
{article_complexity}

Venue uncertainty:
{venue_uncertainty}

Field/epistemic regime: {epistemic_regime}
Protected-core risk: {protected_core_risk}
Submission stakes: {submission_stakes}

User budget/speed constraints: {budget_constraints}
Current depth mode: {current_depth}
Previous organ statuses: {organ_statuses}

Mechanical cost estimates:
{cost_estimates}

Source availability:
{source_availability}

Return a JSON object matching the schema.
"""

_CANONICAL_DEPTHS = [
    "quick_scan", "light_profile", "deep_profile",
    "submission_ready", "post_review",
]

DEPTH_RECOMMENDATION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "recommended_depth": {
            "type": "string",
            "enum": _CANONICAL_DEPTHS,
        },
        "why_not_shallower": {"type": "string"},
        "why_not_deeper": {"type": "string"},
        "organs_to_run": {
            "type": "array",
            "items": {"type": "string"},
        },
        "cost_risk_tradeoff": {"type": "string"},
        "expected_uncertainty_reduction": {
            "type": "array",
            "items": {"type": "string"},
        },
        "user_decision_required": {
            "type": "array",
            "items": {"type": "string"},
        },
        "stop_conditions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low", "none"],
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["recommended_depth", "why_not_shallower",
                  "why_not_deeper", "confidence"],
    "additionalProperties": True,
}


def validate_depth_recommendation(data: dict) -> list[str]:
    warnings: list[str] = []
    depth = data.get("recommended_depth")
    if depth not in _CANONICAL_DEPTHS:
        warnings.append(
            f"invalid recommended_depth '{depth}' — "
            f"must be one of {_CANONICAL_DEPTHS}"
        )
    return warnings


DEPTH_RECOMMENDATION_FAMILY = {
    "family_id": "depth_recommendation_v2",
    "agent_role_id": "depth_recommendation",
    "version": "2.0.0",
    "system_prompt": DEPTH_RECOMMENDATION_SYSTEM,
    "user_prompt_template": DEPTH_RECOMMENDATION_USER_TEMPLATE,
    "output_schema": DEPTH_RECOMMENDATION_OUTPUT_SCHEMA,
    "validator": validate_depth_recommendation,
}
