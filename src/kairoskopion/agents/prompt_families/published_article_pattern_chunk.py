"""Chunk-local semantic observations for a complete published article."""

CHUNK_OUTPUT_SCHEMA = {
    "title": "PublishedArticlePatternChunkSemantic",
    "type": "object",
    "properties": {
        "section_structure_observations": {"type": "array", "items": {"type": "string"}},
        "intro_moves": {"type": "array", "items": {"type": "string"}},
        "method_moves": {"type": "array", "items": {"type": "string"}},
        "argument_moves": {"type": "array", "items": {"type": "string"}},
        "conclusion_moves": {"type": "array", "items": {"type": "string"}},
        "theory_presence": {"type": "array", "items": {"type": "string"}},
        "empirical_presence_observations": {"type": "array", "items": {"type": "string"}},
        "citation_features": {"type": "object"},
        "novelty_moves": {"type": "array", "items": {"type": "string"}},
        "evidence_anchors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "locator": {"type": "string"},
                    "observation": {"type": "string"},
                },
                "required": ["locator", "observation"],
                "additionalProperties": False,
            },
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [
        "section_structure_observations", "intro_moves", "method_moves",
        "argument_moves", "conclusion_moves", "theory_presence",
        "empirical_presence_observations", "citation_features", "novelty_moves",
        "evidence_anchors", "unknowns", "warnings", "confidence",
    ],
    "additionalProperties": False,
}

PUBLISHED_ARTICLE_PATTERN_CHUNK_FAMILY = {
    "family_id": "published_article_pattern_chunk_v1",
    "agent_role_id": "published_article_pattern_chunk_miner",
    "version": "1.0.0",
    "system_prompt": """You analyze ONE CONTIGUOUS CHUNK of a published scholarly article.
This is a map step in a complete-body read. Never pretend the chunk is the whole article.

Rules:
- Report only moves and evidence actually visible in this chunk.
- Do not infer global absence from local absence.
- Do not infer editor preferences or acceptance causes.
- Keep evidence anchors local and reproducible. Prefix every locator with
  chunk:<chunk_index>/<chunk_total>: so a reducer can preserve provenance.
- If the chunk starts or ends mid-section, say so in warnings.
- Return JSON only, following the supplied schema.""",
    "user_prompt_template": """TARGET_ID: {target_id}
SOURCE_REF: {source_ref}
TITLE: {title}
CHUNK_INDEX: {chunk_index}
CHUNK_TOTAL: {chunk_total}
CHAR_START: {char_start}
CHAR_END: {char_end}

WHOLE-ARTICLE STRUCTURAL OBSERVATION:
{structural_json}

ARTICLE CHUNK:
{chunk_text}

Extract chunk-local scholarly moves and grounded anchors only.""",
    "output_schema": CHUNK_OUTPUT_SCHEMA,
}
