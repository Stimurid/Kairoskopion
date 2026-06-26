"""Article Semantic Profiling prompt family (UC-1 step 3).

Builds ArticleSemanticProfile: disciplinary registers, school/tradition
affiliations, argument move type, theoretical shoulders, protected core.
"""

from __future__ import annotations

from .discipline_intent_parsing import _OPEN_FIELD_DOCTRINE


SEMANTIC_PROFILING_SYSTEM = """\
You are Article Semantic Profiler — a specialized analytical role within \
Kairoskopion, an evidence-first publication-positioning system.

Your task: given an ArticleModel and (optionally) the raw manuscript text, \
build a rich semantic profile of the article. This profile will be used for \
disciplinary pathway mapping and venue discovery.
""" + _OPEN_FIELD_DOCTRINE + """
You must identify:

## 1. Disciplinary registers (multiple)
Which academic disciplines does this article speak to? Not just one — most \
research touches several. List them with specificity: use the most precise \
sub-field label the text supports rather than a broad umbrella term.

## 2. Schools and traditions
Schools and traditions mentioned in the article text. Do not assume any \
default school. Report only what the article text explicitly references.

## 3. Argument move type
Describe the argument move type as observed in the text. Use a short \
descriptive label that captures the intellectual move the article makes. \
Common patterns include (but are not limited to):
- problem_statement — posing a new problem or reframing an existing one
- model_building — proposing a new theoretical model or framework
- comparative_analysis — comparing approaches, theories, traditions
- disciplinary_translation — bringing ideas from one field to another
- empirical_conceptual_hybrid — mixing empirical data with conceptual analysis
- systematic_review — comprehensive review of a field or topic
- methodology_piece — proposing or discussing research methods
- unknown
If none of these labels fit, supply a free-form label that does.

## 4. Theoretical shoulders
Whose work does this article build on? Not just bibliography — the key \
intellectual debts that structure the argument.

## 5. Protected core
What parts of the article's intellectual contribution must NOT be destroyed \
during adaptation for different venues? What would make the article lose \
its point if removed?

## 6. Citation ecology signals
What citation traditions need to be present? What bridges are needed for \
different disciplinary audiences?

## Forbidden behavior

- Do NOT assign a single discipline when multiple are evident.
- Do NOT guess schools/traditions — only report what is evident from the text.
- Do NOT conflate "the article cites X" with "the article belongs to X's tradition".
- Do NOT ignore the protected core.
- Mark anything uncertain as unknown.

## Output format (MANDATORY — read every word)

You MUST return ONLY a single JSON object. No other text before or after.

WRONG (will break the system):
- ```json { ... } ```  ← code fences
- <thinking>reasoning</thinking>{ ... }  ← XML tags
- Here is my analysis: { ... }  ← prose before JSON
- { ... } I hope this helps  ← prose after JSON

CORRECT (the ONLY accepted format):
{
  "disciplinary_registers": ["sub-field A", "sub-field B"],
  "primary_discipline": "sub-field A",
  "schools_and_traditions": ["tradition referenced in text"],
  "theoretical_shoulders": ["Author X", "Author Y"],
  "opponents_or_foils": [],
  "argument_move_type": "model_building",
  "argument_move_description": "...",
  "citation_bridges_needed": [],
  "citation_ecology_description": null,
  "protected_core_candidates": ["central distinction X"],
  "mutable_zones": ["introduction framing"],
  "field_core_nonnegotiables": [],
  "intended_audience": "specialists in sub-field A",
  "audience_expertise_level": "specialist",
  "unknowns": ["citation ecology not assessed"],
  "questions_for_user": [],
  "confidence": "medium"
}

Every field listed above MUST be present in your response. Use empty arrays \
[] for lists with no items. Use null for text fields you cannot determine.
"""

SEMANTIC_PROFILING_USER_TEMPLATE = """\
Build a semantic profile for this article.

## ArticleModel
```json
{article_json}
```

## Manuscript text (first 8000 chars, may be truncated)
{manuscript_text}

## Known disciplinary landscape (optional context)

These are disciplines the registry already knows about. If the article \
clearly belongs to one or more of them, prefer their canonical names \
in ``disciplinary_registers`` and ``primary_discipline`` so downstream \
matchers can find the venue space directly. If the article does NOT \
fit any of them, ignore this block — do not force-fit.

{known_disciplines_context}

IMPORTANT: respond with ONLY the JSON object. No markdown fences, no XML \
tags, no prose before or after. Every field from the schema must be present.
"""

SEMANTIC_PROFILING_OUTPUT_SCHEMA: dict = {
    "title": "ArticleSemanticProfileResult",
    "type": "object",
    "properties": {
        "disciplinary_registers": {
            "type": "array",
            "items": {"type": "string"},
        },
        "primary_discipline": {"type": ["string", "null"]},
        "schools_and_traditions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "theoretical_shoulders": {
            "type": "array",
            "items": {"type": "string"},
        },
        "opponents_or_foils": {
            "type": "array",
            "items": {"type": "string"},
        },
        "argument_move_type": {
            "type": "string",
            "description": "Free-form label describing the argument move type observed in the text.",
        },
        "argument_move_description": {"type": ["string", "null"]},
        "citation_bridges_needed": {
            "type": "array",
            "items": {"type": "string"},
        },
        "citation_ecology_description": {"type": ["string", "null"]},
        "protected_core_candidates": {
            "type": "array",
            "items": {"type": "string"},
        },
        "mutable_zones": {
            "type": "array",
            "items": {"type": "string"},
        },
        "field_core_nonnegotiables": {
            "type": "array",
            "items": {"type": "string"},
        },
        "intended_audience": {"type": ["string", "null"]},
        "audience_expertise_level": {"type": ["string", "null"]},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "questions_for_user": {"type": "array", "items": {"type": "string"}},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
    },
    "required": [],
    "additionalProperties": True,
}


def validate_semantic_profile(data: dict) -> list[str]:
    warnings: list[str] = []

    if not data.get("disciplinary_registers"):
        warnings.append("No disciplinary registers — every article has at least one")

    if not data.get("protected_core_candidates"):
        warnings.append("No protected core candidates — what would be lost in adaptation?")

    if not data.get("unknowns"):
        warnings.append("No unknowns — unlikely for semantic profiling")

    return warnings


SEMANTIC_PROFILING_FAMILY = {
    "family_id": "semantic_profiling_v2",
    "agent_role_id": "article_semantic_profiler",
    "version": "2.0.0",
    "system_prompt": SEMANTIC_PROFILING_SYSTEM,
    "user_prompt_template": SEMANTIC_PROFILING_USER_TEMPLATE,
    "output_schema": SEMANTIC_PROFILING_OUTPUT_SCHEMA,
    "validator": validate_semantic_profile,
}
