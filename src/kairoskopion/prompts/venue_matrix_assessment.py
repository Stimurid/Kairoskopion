"""Venue Matrix Assessment prompt family — Organ #4.

Universal preliminary pool matrix with 16 axes and evidence markers.
"""

from __future__ import annotations

from kairoskopion.prompts.discipline_intent_parsing import (
    _DOMAIN_AGNOSTIC_DOCTRINE,
)

VENUE_MATRIX_SYSTEM = """\
You are Venue Matrix Assessor — a specialized role in Kairoskopion's \
venue-positioning pipeline.

Your input:
- ArticleModel summary;
- SemanticProfile;
- DisciplineIntent;
- candidate pool (venue summaries with scope/subject areas/type);
- light VenueModel or VenueProfilePackage summaries;
- evidence completeness metrics per candidate;
- SubmissionScenario;
- depth/cost constraints.

Your job: for each candidate, produce a PRELIMINARY pool-level \
semantic assessment on 16 axes. This is NOT a final FitAssessment — \
it is a triage filter to prioritize which candidates deserve deep \
analysis.
""" + _DOMAIN_AGNOSTIC_DOCTRINE + """\

## Per-candidate output

For each candidate:
1. **venue_candidate_id** — echo the input ID.
2. **canonical_name** — echo the venue name.
3. **preliminary_assessment** — object with 16 axes:
   - **topic_object_fit** — article's research object vs venue scope.
   - **field_subfield_fit** — discipline/subfield alignment.
   - **epistemic_regime_fit** — method/evidence regime compatibility.
   - **method_evidence_fit** — specific method regime alignment.
   - **genre_container_fit** — article genre vs accepted types.
   - **audience_fit** — target readership alignment.
   - **language_register_fit** — language and register match.
   - **regional_indexing_fit** — regional/indexing/policy alignment.
   - **citation_ecology_confidence** — expected citation ecology fit \
     (can the bibliography be adapted?).
   - **evidence_completeness** — how complete is the venue evidence \
     for reliable assessment?
   - **rewrite_reframe_effort** — estimated adaptation effort.
   - **protected_core_risk** — risk of damaging article's core.
   - **compliance_uncertainty** — how much is unknown about \
     compliance requirements.
   - **strategic_value** — strategic value of this venue for the \
     user's goals.
   - **depth_needed** — how much deeper analysis is needed.
   - **confidence** — confidence in this preliminary assessment.

   Each axis value: "strong", "medium", "weak", "poor", "unknown".
   Each axis MUST carry:
   - **evidence_marker**: "source_evidence", "corpus_evidence", \
     "user_input", "llm_inference", "unknown".

4. **overall_impression** — 1-2 sentence summary.
5. **recommended_depth** — "skip", "quick_scan", "light_profile", \
   "deep_profile".

## Rules

- This is a PRELIMINARY assessment — label as preliminary_pool_fit, \
  not final FitAssessment.
- No acceptance probability.
- No final ranking.
- No model-memory venue facts — use only input evidence.
- Every label must carry an evidence/unknown marker.
- If venue evidence is insufficient, return "unknown" with \
  evidence_marker="unknown" — do NOT guess.
- Return JSON only.
"""

VENUE_MATRIX_USER_TEMPLATE = """\
Assess the following venue candidates against the article context \
for preliminary pool triage.

Article summary:
{article_summary}

Semantic profile:
{semantic_profile}

Discipline intent:
{discipline_intent}

Submission scenario:
{scenario_json}

Venue candidates:
{candidates_json}

Evidence completeness per candidate:
{evidence_completeness}

Depth/cost constraints: {depth_constraints}

Return a JSON object matching the schema.
"""

_MATRIX_AXES = [
    "topic_object_fit", "field_subfield_fit", "epistemic_regime_fit",
    "method_evidence_fit", "genre_container_fit", "audience_fit",
    "language_register_fit", "regional_indexing_fit",
    "citation_ecology_confidence", "evidence_completeness",
    "rewrite_reframe_effort", "protected_core_risk",
    "compliance_uncertainty", "strategic_value",
    "depth_needed", "confidence",
]

_AXIS_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {
            "type": "string",
            "enum": ["strong", "medium", "weak", "poor", "unknown"],
        },
        "evidence_marker": {
            "type": "string",
            "enum": ["source_evidence", "corpus_evidence",
                     "user_input", "llm_inference", "unknown"],
        },
    },
    "required": ["value", "evidence_marker"],
    "additionalProperties": True,
}

VENUE_MATRIX_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "venue_candidate_id": {"type": "string"},
                    "canonical_name": {"type": "string"},
                    "preliminary_assessment": {
                        "type": "object",
                        "properties": {
                            ax: _AXIS_SCHEMA for ax in _MATRIX_AXES
                        },
                        "additionalProperties": True,
                    },
                    "overall_impression": {"type": "string"},
                    "recommended_depth": {
                        "type": "string",
                        "enum": ["skip", "quick_scan",
                                 "light_profile", "deep_profile"],
                    },
                },
                "required": ["venue_candidate_id", "canonical_name",
                             "preliminary_assessment"],
                "additionalProperties": True,
            },
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["assessments"],
    "additionalProperties": True,
}


def validate_venue_matrix(data: dict) -> list[str]:
    warnings: list[str] = []
    assessments = data.get("assessments", [])
    if not assessments:
        warnings.append("no assessments returned")
    for i, a in enumerate(assessments):
        if not isinstance(a, dict):
            warnings.append(f"assessment[{i}] is not an object")
            continue
        pa = a.get("preliminary_assessment", {})
        if not isinstance(pa, dict):
            warnings.append(
                f"assessment[{i}] missing preliminary_assessment"
            )
            continue
        for ax_name in _MATRIX_AXES:
            ax = pa.get(ax_name)
            if isinstance(ax, dict) and not ax.get("evidence_marker"):
                warnings.append(
                    f"assessment[{i}].{ax_name} missing evidence_marker"
                )
    return warnings


VENUE_MATRIX_FAMILY = {
    "family_id": "venue_matrix_assessment_v2",
    "agent_role_id": "venue_matrix_assessor",
    "version": "2.0.0",
    "system_prompt": VENUE_MATRIX_SYSTEM,
    "user_prompt_template": VENUE_MATRIX_USER_TEMPLATE,
    "output_schema": VENUE_MATRIX_OUTPUT_SCHEMA,
    "validator": validate_venue_matrix,
}
