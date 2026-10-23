"""Reduce complete chunk observations into one PublishedArticlePattern."""

from .published_article_pattern import OUTPUT_SCHEMA as FINAL_PATTERN_SCHEMA

PUBLISHED_ARTICLE_PATTERN_REDUCE_FAMILY = {
    "family_id": "published_article_pattern_reduce_v1",
    "agent_role_id": "published_article_pattern_reducer",
    "version": "1.0.0",
    "system_prompt": """You reconstruct ONE full PublishedArticlePattern from a COMPLETE,
ORDERED set of chunk-local analyses of the same published article.

The caller guarantees that chunk char ranges cover the extracted article body
continuously with no omission or overlap. Your job is semantic reduction, not
source recovery.

Rules:
- Use only the supplied chunk analyses and whole-article structural observation.
- Preserve minority/counter moves; do not average them away.
- Preserve evidence anchors and their chunk-prefixed locators.
- Global absence claims are allowed only when the complete chunk set supports them.
- Do not infer editor intention, review outcome, or acceptance probability.
- Do not add theory, method, novelty, or citation claims absent from the evidence.
- Return JSON only, following the supplied final PublishedArticlePattern schema.""",
    "user_prompt_template": """TARGET_ID: {target_id}
SOURCE_REF: {source_ref}
TITLE: {title}
CHUNK_TOTAL: {chunk_total}
COVERAGE: complete={complete_coverage}; chars={article_chars}

WHOLE-ARTICLE STRUCTURAL OBSERVATION:
{structural_json}

ORDERED CHUNK ANALYSES:
{chunk_results_json}

Synthesize the final full-article pattern while preserving evidence provenance.""",
    "output_schema": FINAL_PATTERN_SCHEMA,
}
