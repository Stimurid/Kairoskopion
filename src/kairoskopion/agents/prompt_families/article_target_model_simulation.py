"""HS-016 - article x deep target-model comparison, no acceptance prediction."""

FAMILY_ID = "article_target_model_simulation_v1"
VERSION = "1.0.0"
AGENT_ROLE_ID = "article_target_model_simulator"

SYSTEM_PROMPT = """You compare one ArticleModel or Artikl projection with a
fulltext-grounded deep target model.

This is a comparison, not a reviewer prediction and not an acceptance
forecast. Identify which observed corpus archetypes the article is closest to,
where it is unlike all observed archetypes, which countermodels matter, and
what target-facing transformations would be needed.

Never recommend destroying protected core. Never claim the venue rejects an
unobserved form. Preserve unknowns and distinguish corpus evidence from
inference. Return JSON only.
"""

USER_TEMPLATE = """Article:
{article_json}

Deep target model:
{deep_target_model_json}

Return the article x model simulation.
"""

OUTPUT_SCHEMA = {
    "title": "ArticleTargetModelSimulation",
    "type": "object",
    "properties": {
        "closest_archetypes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "archetype_id": {"type": "string"},
                    "fit_observations": {"type": "array", "items": {"type": "string"}},
                    "mismatches": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["archetype_id", "fit_observations", "mismatches"],
                "additionalProperties": False,
            },
        },
        "unmodeled_dimensions": {"type": "array", "items": {"type": "string"}},
        "countermodel_risks": {"type": "array", "items": {"type": "string"}},
        "target_facing_operations": {"type": "array", "items": {"type": "string"}},
        "protected_core_risks": {"type": "array", "items": {"type": "string"}},
        "evidence_pattern_ids": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [
        "closest_archetypes", "unmodeled_dimensions", "countermodel_risks",
        "target_facing_operations", "protected_core_risks",
        "evidence_pattern_ids", "unknowns", "confidence"
    ],
    "additionalProperties": False,
}

ARTICLE_TARGET_MODEL_SIMULATION_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": AGENT_ROLE_ID,
    "version": VERSION,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
}
