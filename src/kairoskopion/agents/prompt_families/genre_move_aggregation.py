"""TRM-071 / Journal-Yuga 26.6 — GenreMove Aggregation."""

FAMILY_ID = "genre_move_aggregation_v1"
VERSION = "1.0.0"
AGENT_ROLE_ID = "genre_move_aggregator"

SYSTEM_PROMPT = """You are the Genre / Move Aggregator inside Kairoskopion.

Input is a corpus of fulltext-grounded PublishedArticlePattern records from one
venue. Aggregate recurring publication forms without turning corpus frequency
into editorial intention.

Produce:
- observed move frequencies and dominant/rare/absent-in-sample patterns;
- 2-6 corpus archetypes when the sample supports them;
- countermodels: genuine minority/contrasting forms observed in the sample;
- implications for comparing a submitted article, stated as corpus
  observations/inferences, never as acceptance predictions.

Rules:
1. Every archetype must list its member_pattern_ids.
2. Never invent an archetype with zero observed members.
3. "Absent" means not observed in sampled corpus, never forbidden/rejected.
4. Preserve meaningful heterogeneity rather than forcing one average article.
5. Small/biased samples must reduce confidence and stay visible in unknowns.
6. Return JSON only.
"""

USER_TEMPLATE = """Target: {target_id}
Published corpus id: {published_corpus_id}
Selection strategy / bias context:
{corpus_context_json}

Fulltext-grounded article patterns ({sample_size}):
{patterns_json}

Aggregate the corpus into GenreMoveProfile + archetypes/countermodels.
"""

OUTPUT_SCHEMA = {
    "title": "GenreMoveAggregation",
    "type": "object",
    "properties": {
        "observed_moves": {"type": "object"},
        "dominant_moves": {"type": "array", "items": {"type": "string"}},
        "rare_moves": {"type": "array", "items": {"type": "string"}},
        "absent_in_sample_moves": {"type": "array", "items": {"type": "string"}},
        "archetypes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "archetype_id": {"type": "string"},
                    "label": {"type": "string"},
                    "member_pattern_ids": {
                        "type": "array", "items": {"type": "string"}
                    },
                    "defining_moves": {
                        "type": "array", "items": {"type": "string"}
                    },
                    "structure_signature": {
                        "type": "array", "items": {"type": "string"}
                    },
                    "method_signature": {"type": ["string", "null"]},
                    "theory_signature": {
                        "type": "array", "items": {"type": "string"}
                    },
                    "limitations": {
                        "type": "array", "items": {"type": "string"}
                    },
                },
                "required": [
                    "archetype_id", "label", "member_pattern_ids",
                    "defining_moves", "structure_signature",
                    "theory_signature", "limitations",
                ],
                "additionalProperties": False,
            },
        },
        "countermodels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "member_pattern_ids": {
                        "type": "array", "items": {"type": "string"}
                    },
                    "contrast": {"type": "string"},
                },
                "required": ["label", "member_pattern_ids", "contrast"],
                "additionalProperties": False,
            },
        },
        "article_comparison_dimensions": {
            "type": "array", "items": {"type": "string"}
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [
        "observed_moves", "dominant_moves", "rare_moves",
        "absent_in_sample_moves", "archetypes", "countermodels",
        "article_comparison_dimensions", "unknowns", "warnings", "confidence",
    ],
    "additionalProperties": False,
}

GENRE_MOVE_AGGREGATION_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": AGENT_ROLE_ID,
    "version": VERSION,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
}
