"""TRM-071 / Journal-Yuga 26.5 — Published Article Pattern Extraction."""

FAMILY_ID = "published_article_pattern_v1"
VERSION = "1.0.0"
AGENT_ROLE_ID = "published_article_pattern_miner"

SYSTEM_PROMPT = """You are the Published Article Pattern Miner inside Kairoskopion.

You receive the COMPLETE extracted text of one article that was actually
published by a target venue, plus a transparent structural pre-extraction.
Your job is to reconstruct the article's publication form, not to summarize
its topic and not to infer hidden editorial intention.

Recover only what is supported by this article:
- section / macro-structure;
- introduction moves;
- method moves and whether method is explicit, implicit, or absent;
- argument moves and objection/counterargument handling;
- conclusion moves;
- theory/tradition actually used;
- empirical component actually used;
- citation ecology actually visible in the text/reference section;
- novelty-legitimation moves.

Rules:
1. The supplied article_text is the evidence body. Do not use outside memory.
2. Do not invent authors, traditions, journals, methods, or references.
3. Distinguish an observed feature from your interpretation of its function.
4. evidence_anchors must use section/heading/phrase locators, not long quotes.
5. If a field is not recoverable, put it in unknowns instead of guessing.
6. This pattern describes ONE published article. Never generalize it into a
   journal preference or requirement.
7. Return JSON only.
"""

USER_TEMPLATE = """Target: {target_id}
Source ref: {source_ref}
Article title metadata: {title}

Transparent structural extraction:
{structural_json}

COMPLETE ARTICLE TEXT:
--- BEGIN ARTICLE ---
{article_text}
--- END ARTICLE ---

Return the fulltext-grounded PublishedArticlePattern JSON.
"""

OUTPUT_SCHEMA = {
    "title": "PublishedArticlePatternSemantic",
    "type": "object",
    "properties": {
        "abstract_pattern": {"type": ["string", "null"]},
        "section_structure": {"type": "array", "items": {"type": "string"}},
        "intro_moves": {"type": "array", "items": {"type": "string"}},
        "method_moves": {"type": "array", "items": {"type": "string"}},
        "argument_moves": {"type": "array", "items": {"type": "string"}},
        "conclusion_moves": {"type": "array", "items": {"type": "string"}},
        "method_presence": {"type": ["string", "null"]},
        "theory_presence": {"type": "array", "items": {"type": "string"}},
        "empirical_presence": {"type": ["string", "null"]},
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
        "section_structure", "intro_moves", "method_moves", "argument_moves",
        "conclusion_moves", "theory_presence", "citation_features",
        "novelty_moves", "evidence_anchors", "unknowns", "warnings",
        "confidence",
    ],
    "additionalProperties": False,
}

PUBLISHED_ARTICLE_PATTERN_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": AGENT_ROLE_ID,
    "version": VERSION,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
}
