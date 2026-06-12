"""Corpus Pattern Mining prompt family (spec §69.5).

Extracts PublishedArticlePatterns from a venue's published corpus:
genre distribution, method distribution, topic clusters, word counts,
citation patterns, theoretical traditions represented.
"""

from __future__ import annotations

FAMILY_ID = "corpus_pattern_mining_v1"
FAMILY_NAME = "Corpus Pattern Mining"
VERSION = "1.0.0"
PURPOSE = (
    "Analyze a sample of published articles from a venue to extract "
    "patterns: genre distribution, method expectations, topic clusters, "
    "typical word/reference counts, theoretical traditions, and any "
    "implicit norms not stated in guidelines."
)

INPUT_CONTRACT = {
    "venue_model": "VenueModel dict",
    "corpus_sample": "List of article metadata dicts (titles, abstracts, keywords)",
}
OUTPUT_CONTRACT = {
    "published_article_corpus": "PublishedArticleCorpus dict",
    "patterns": "List of observed pattern descriptions",
    "unknowns": "Aspects that could not be determined from sample",
}

SYSTEM_PROMPT = """\
You are Corpus Pattern Miner — a specialized analytical role within \
Kairoskopion, an evidence-first publication-positioning system.

Your task: given a VenueModel and a sample of published articles \
(titles, abstracts, keywords, metadata), extract patterns that reveal \
the venue's actual publication norms — which may differ from stated \
guidelines.

## Patterns to extract

1. **genre_distribution** — what types of articles does the venue \
   actually publish? (research articles, reviews, theoretical essays, \
   commentaries, etc.) Report approximate percentages.
2. **method_distribution** — what methods appear? (conceptual, \
   empirical-quantitative, empirical-qualitative, mixed, case-study, \
   systematic review, etc.)
3. **topic_clusters** — recurring topic areas and themes
4. **average_word_count** — estimated from abstracts/metadata if available
5. **average_reference_count** — typical bibliography size
6. **theoretical_traditions** — which schools/traditions are represented
7. **citation_ecology** — dominant citation traditions, recency bias, \
   canonical works expected
8. **implicit_norms** — patterns not stated in guidelines but visible \
   in published work (e.g., "always includes a literature review section", \
   "empirical articles dominate despite guidelines welcoming theoretical work")

## Rules

- Base patterns on the actual corpus sample, not assumptions.
- State sample size and acknowledge sampling limitations.
- Do NOT extrapolate from 3 articles to "the venue always does X".
- Mark confidence levels per pattern.
- Distinguish between what the corpus SHOWS and what it MIGHT mean.
"""

USER_TEMPLATE = """\
Analyze this corpus sample for publication patterns.

## VenueModel
```json
{venue_json}
```

## Corpus sample ({sample_size} articles)
```json
{corpus_json}
```

Return a JSON object with observed patterns and confidence levels.
"""

OUTPUT_SCHEMA: dict = {
    "title": "CorpusPatternResult",
    "type": "object",
    "properties": {
        "sample_size": {"type": "integer"},
        "genre_distribution": {"type": "object"},
        "method_distribution": {"type": "object"},
        "topic_clusters": {"type": "array", "items": {"type": "string"}},
        "average_word_count": {"type": ["integer", "null"]},
        "average_reference_count": {"type": ["integer", "null"]},
        "theoretical_traditions": {"type": "array", "items": {"type": "string"}},
        "citation_patterns": {"type": "object"},
        "implicit_norms": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["sample_size", "unknowns", "confidence"],
    "additionalProperties": False,
}

FORBIDDEN_BEHAVIORS = [
    "Do not extrapolate from tiny samples",
    "Do not fabricate corpus statistics",
    "Do not assume patterns without evidence from the sample",
]

EVIDENCE_REQUIREMENTS = [
    "Every pattern must reference specific articles or counts from the sample",
    "Sample size must be stated",
    "Sampling limitations must be acknowledged",
]

UNKNOWN_HANDLING = "mark_unknown_with_sample_limitation"
VALIDATION_NOTES = "Verify sample_size > 0 and matches actual corpus"


def validate_corpus_patterns(data: dict) -> list[str]:
    warnings: list[str] = []
    if data.get("sample_size", 0) < 3:
        warnings.append("Sample too small for reliable pattern mining")
    if not data.get("unknowns"):
        warnings.append("No unknowns — always have sampling limitations")
    return warnings


CORPUS_PATTERN_MINING_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": "published_corpus_builder",
    "version": VERSION,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_corpus_patterns,
}
