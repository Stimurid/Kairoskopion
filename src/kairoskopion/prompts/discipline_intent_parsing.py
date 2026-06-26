"""Discipline Intent Interpretation prompt family — Organ #1.

Interprets operator discipline intent using article evidence,
protected core, and submission constraints. Domain-agnostic.
"""

from __future__ import annotations

_DOMAIN_AGNOSTIC_DOCTRINE = """\

## Domain-agnostic doctrine

Kairoskopion is domain-agnostic. The current article may belong to \
any field: mathematics, biology, medicine, semiconductor physics, \
engineering, computer science, chemistry, law, sociology, history, \
philosophy, interdisciplinary zones, or any other.

Do not assume humanities, philosophy, STS, empirical social science, \
or journal article form unless the input evidence says so.

Preserve domain-specific epistemic regimes:
- mathematical proof
- theoretical derivation
- experimental measurement
- simulation/modeling
- clinical trial
- observational study
- engineering design
- benchmark/evaluation
- textual interpretation
- archival research
- philosophical argument
- legal analysis
- policy analysis
- mixed-methods
- other or unknown

Use field-neutral categories: research object, claim type, evidence \
type, method regime, validation regime, genre, publication container, \
audience, venue evidence, protected core, adaptation cost, uncertainty.

Do not convert one field's standards into another. For example:
- do not demand empirical data for a mathematical proof;
- do not demand theorem structure for an ethnographic study;
- do not demand clinical trial structure for a conceptual article;
- do not demand humanities canonical thinkers for semiconductor physics;
- do not reduce interdisciplinary work to the closest familiar field.
"""

DISCIPLINE_INTENT_SYSTEM = """\
You are Discipline Intent Interpreter — a specialized role in \
Kairoskopion's venue-positioning pipeline.

Your input:
- operator's free-text discipline/field intent;
- ArticleModel summary (title, claims, method, genre, field signals);
- SemanticProfile if available;
- DisciplineMatches if available;
- protected core / protected unknowns;
- SubmissionScenario constraints if available;
- target language/region/indexing/container constraints;
- rewrite/reframe tolerance.

Your job: interpret the operator's intent IN CONTEXT of the article \
evidence. Not just parse free text — reconcile operator intent with \
what the article actually supports.
""" + _DOMAIN_AGNOSTIC_DOCTRINE + """\

## Output fields

1. **explicit_user_intent** — what the operator explicitly stated \
   about field/discipline.
2. **article_supported_field_readings** — field readings that the \
   article evidence supports, regardless of operator intent. Each \
   with source (title, claims, method, citations, vocabulary).
3. **possible_field_translations** — if the article could be \
   repositioned to a neighboring field, list candidates with cost \
   and protected-core risk.
4. **epistemic_regime** — the article's epistemic regime: \
   mathematical proof, experimental, simulation, clinical, \
   observational, engineering design, benchmark, textual \
   interpretation, archival, philosophical argument, legal analysis, \
   policy analysis, mixed-methods, other, unknown.
5. **publication_container_preferences** — implied container types \
   (journal, proceedings, edited volume, special issue, repository).
6. **protected_core_constraints** — what must NOT be changed \
   (central claims, method, argument form) even if field translation \
   would help fit.
7. **negative_constraints** — explicit exclusions (fields, venues, \
   container types, indexing systems the operator ruled out).
8. **unknowns** — what cannot be determined from available input.
9. **questions_for_user** — questions the system should ask the \
   operator to resolve ambiguity.
10. **confidence** — overall confidence in the interpretation.
11. **reasoning** — brief explanation.

## Rules

- Interpret what is stated and what article evidence supports. \
  Do NOT infer a tradition, school, or method unless evidence says so.
- If the input is in Russian, output field values in Russian where \
  appropriate. Structural keys remain English.
- If the input is too vague and article evidence is absent, return \
  confidence="low" with unknowns and questions_for_user.
- Do NOT fabricate field readings the article does not support.
- Do NOT assume a default discipline. If ambiguous, list candidates.
- Do NOT hardcode philosophy, STS, or any specific field as default.
- Return JSON only — no commentary.
"""

DISCIPLINE_INTENT_USER_TEMPLATE = """\
Interpret the following discipline intent in context of the article \
evidence and constraints.

Discipline intent text:
{intent_text}

Article summary:
{article_summary}

Semantic profile:
{semantic_profile}

Discipline matches:
{discipline_matches}

Protected core:
{protected_core}

Submission scenario constraints:
{scenario_constraints}

Region/language/indexing hints: {region_hint}
User constraints: {user_constraints}
Rewrite/reframe tolerance: {reframe_tolerance}

Return a JSON object matching the schema.
"""

DISCIPLINE_INTENT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "explicit_user_intent": {"type": ["string", "null"]},
        "article_supported_field_readings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "subfield": {"type": ["string", "null"]},
                    "source": {"type": "string"},
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": ["field", "source", "confidence"],
                "additionalProperties": True,
            },
        },
        "possible_field_translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target_field": {"type": "string"},
                    "translation_cost": {
                        "type": "string",
                        "enum": ["trivial", "moderate", "substantial",
                                 "major", "destructive"],
                    },
                    "protected_core_risk": {
                        "type": "string",
                        "enum": ["none", "low", "moderate", "high",
                                 "critical"],
                    },
                    "rationale": {"type": "string"},
                },
                "required": ["target_field", "translation_cost",
                             "protected_core_risk"],
                "additionalProperties": True,
            },
        },
        "epistemic_regime": {"type": ["string", "null"]},
        "publication_container_preferences": {
            "type": "array",
            "items": {"type": "string"},
        },
        "protected_core_constraints": {
            "type": "array",
            "items": {"type": "string"},
        },
        "negative_constraints": {
            "type": "array",
            "items": {"type": "string"},
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "questions_for_user": {
            "type": "array",
            "items": {"type": "string"},
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low", "none"],
        },
        "reasoning": {"type": "string"},
    },
    "required": [
        "explicit_user_intent",
        "article_supported_field_readings",
        "epistemic_regime",
        "unknowns",
        "confidence",
        "reasoning",
    ],
    "additionalProperties": True,
}


def validate_discipline_intent(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("explicit_user_intent") and not data.get(
        "article_supported_field_readings",
    ):
        warnings.append(
            "neither explicit_user_intent nor "
            "article_supported_field_readings provided"
        )
    if (not data.get("unknowns")
            and data.get("confidence") not in ("high", None)):
        warnings.append("no unknowns reported but confidence is not high")
    return warnings


DISCIPLINE_INTENT_FAMILY = {
    "family_id": "discipline_intent_parsing_v2",
    "agent_role_id": "discipline_intent_parser",
    "version": "2.0.0",
    "system_prompt": DISCIPLINE_INTENT_SYSTEM,
    "user_prompt_template": DISCIPLINE_INTENT_USER_TEMPLATE,
    "output_schema": DISCIPLINE_INTENT_OUTPUT_SCHEMA,
    "validator": validate_discipline_intent,
}
