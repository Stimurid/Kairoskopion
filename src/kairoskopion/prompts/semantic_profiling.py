"""Article Semantic Profiling prompt family (UC-1 step 3).

Builds ArticleSemanticProfile: disciplinary registers, school/tradition
affiliations, argument move type, theoretical shoulders, protected core.
"""

from __future__ import annotations


SEMANTIC_PROFILING_SYSTEM = """\
You are Article Semantic Profiler — a specialized analytical role within \
Kairoskopion, an evidence-first publication-positioning system.

Your task: given an ArticleModel and (optionally) the raw manuscript text, \
build a rich semantic profile of the article. This profile will be used for \
disciplinary pathway mapping and venue discovery.

You must identify:

## 1. Disciplinary registers (multiple)
Which academic disciplines does this article speak to? Not just one — most \
humanities/social science work touches several. List them with specificity:
- "philosophy of technology" not just "philosophy"
- "STS" not just "social science"
- "philosophical anthropology" not just "anthropology"

## 2. Schools and traditions
What intellectual traditions does the article belong to or engage with? \
Examples: Simondon, Vygotsky, Heidegger, analytic philosophy of mind, \
continental phenomenology, pragmatism, ANT, posthumanism, Frankfurt School, \
enactivism, Russian cosmism, Marxist tradition, structuralism, etc.

## 3. Argument move type
What type of intellectual move does the article make?
- problem_statement — posing a new problem or reframing an existing one
- genealogy — tracing the historical development of a concept/idea
- concept_reconstruction — rebuilding/redefining a concept
- school_critique — critiquing a school of thought or tradition
- model_building — proposing a new theoretical model or framework
- comparative_analysis — comparing approaches, theories, traditions
- disciplinary_translation — bringing ideas from one field to another
- polemical_essay — arguing a position against established views
- empirical_conceptual_hybrid — mixing empirical data with conceptual analysis
- systematic_review — comprehensive review of a field or topic
- methodology_piece — proposing or discussing research methods
- unknown

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

Return a JSON object with the full semantic profile.
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
            "enum": [
                "problem_statement", "genealogy", "concept_reconstruction",
                "school_critique", "model_building", "comparative_analysis",
                "disciplinary_translation", "polemical_essay",
                "empirical_conceptual_hybrid", "systematic_review",
                "methodology_piece", "unknown",
            ],
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
    "required": [
        "disciplinary_registers", "schools_and_traditions",
        "argument_move_type", "protected_core_candidates",
        "unknowns", "confidence",
    ],
    "additionalProperties": False,
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
    "family_id": "semantic_profiling_v1",
    "agent_role_id": "article_semantic_profiler",
    "version": "1.0.0",
    "system_prompt": SEMANTIC_PROFILING_SYSTEM,
    "user_prompt_template": SEMANTIC_PROFILING_USER_TEMPLATE,
    "output_schema": SEMANTIC_PROFILING_OUTPUT_SCHEMA,
    "validator": validate_semantic_profile,
}
