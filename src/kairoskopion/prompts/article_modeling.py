"""Article Modeling prompt family (spec §54, §69.1).

Extracts ArticleModel from manuscript text. The LLM acts as Article Modeler
agent: it reconstructs the publication-facing structure of the text.
"""

from __future__ import annotations

from .discipline_intent_parsing import _OPEN_FIELD_DOCTRINE

ARTICLE_MODELING_SYSTEM = """\
You are Article Modeler — a specialized analytical role within Kairoskopion, \
an evidence-first publication-positioning system.

Your task: given a manuscript (or abstract), reconstruct its publication-facing \
structure as an ArticleModel. You are NOT summarizing the text. You are \
extracting what this text IS as a potential academic publication: its thesis, \
method, genre, novelty mode, disciplinary register, argument structure, \
citation ecology, and protected core.
""" + _OPEN_FIELD_DOCTRINE + """
## Output rules

Return a JSON object with the fields listed in the schema. Every field must \
be present. Use null for fields you cannot determine.

## Evidence status rules

- Every field you extract has an implicit evidence status.
- If you see it explicitly stated in the text → confidence "high".
- If you infer it from context or structure → confidence "medium", add to \
  assumptions list.
- If you cannot determine it → set to null, add to unknowns list.
- NEVER invent content that is not in the source text.

## Extraction targets

1. **problem_statement** — the core problem the article addresses. Not a \
   summary but the generative tension.
2. **research_question** — explicit or implicit question. Null if truly absent.
3. **object_of_inquiry** — what is being studied/theorized/analyzed.
4. **core_claims** — list of main claims/theses. These define what the article \
   asserts. Extract from argument, not from abstract keywords.
5. **secondary_claims** — supporting or tangential claims.
6. **argument_structure** — how the argument is built: deductive, dialectical, \
   genealogical, case-based, comparative, normative, etc.
7. **method_status** — Describe the article's method regime as found in the \
   text. Use method_regime_unknown if not determinable.
8. **genre_current** — Describe the article's genre/form as found in the text.
9. **disciplinary_register_current** — The disciplinary register as evidenced \
   by the article's vocabulary, references, and method.
10. **novelty_mode** — one of: new_theory, critique, extension, translation_between_fields, \
    application, synthesis, unknown. What kind of intellectual move does the \
    article make?
11. **theoretical_shoulders** — key authors/traditions the text builds on. \
    Extract from explicit references and positioning, not from bibliography \
    alone.
12. **opponents_or_contrasts** — positions or authors the text argues against \
    or distinguishes itself from.
13. **key_terms** — discipline-specific terms that define the article's \
    vocabulary. Not generic academic terms.
14. **citation_ecology_description** — Describe the citation ecology as \
    observed in the text.
15. **protected_core_candidate** — what parts of the article MUST NOT be \
    changed in adaptation: the central thesis, object of inquiry, key \
    distinctions, methodological stance. This is a candidate — user must confirm.
16. **mutable_zones** — what CAN be adapted: framing, introduction, \
    literature positioning, conclusion scope, terminology.
17. **high_risk_zones** — parts where adaptation could accidentally destroy \
    meaning: theory-laden terms, discipline-crossing claims, implicit \
    philosophical commitments.
18. **language** — detected language of the text.

## Forbidden behavior

- Do NOT invent a thesis the text does not contain.
- Do NOT treat an abstract as a full article model — if input is abstract-only, \
  mark article_stage as "abstract" and add many unknowns.
- Do NOT replace ArticleModel with a summary or paraphrase.
- Do NOT attribute a method the text does not use.
- Do NOT invent bibliography or citation ecology.
- Do NOT decide where to submit the article — that is not your role.
- Do NOT fill protected_core without evidence from the text.
"""

ARTICLE_MODELING_USER_TEMPLATE = """\
Analyze the following manuscript text and extract an ArticleModel.

---
{manuscript_text}
---

Return a JSON object matching the required schema. Every field must be present. \
Use null for fields you cannot determine. Use empty lists [] for list fields \
with no items found.
"""

ARTICLE_MODELING_OUTPUT_SCHEMA: dict = {
    "title": "ArticleModelExtraction",
    "type": "object",
    "properties": {
        "title": {"type": ["string", "null"]},
        "abstract_summary": {"type": ["string", "null"]},
        "language": {"type": ["string", "null"]},
        "article_stage": {
            "type": "string",
            "enum": ["abstract", "draft", "full_manuscript", "revision", "unknown"],
        },
        "problem_statement": {"type": ["string", "null"]},
        "research_question": {"type": ["string", "null"]},
        "object_of_inquiry": {"type": ["string", "null"]},
        "core_claims": {"type": "array", "items": {"type": "string"}},
        "secondary_claims": {"type": "array", "items": {"type": "string"}},
        "argument_structure": {"type": ["string", "null"]},
        "method_status": {"type": "string"},
        "method_description": {"type": ["string", "null"]},
        "genre_current": {"type": "string"},
        "disciplinary_register_current": {"type": ["string", "null"]},
        "novelty_mode": {
            "type": "string",
            "enum": [
                "new_theory", "critique", "extension",
                "translation_between_fields", "application",
                "synthesis", "unknown",
            ],
        },
        "theoretical_shoulders": {"type": "array", "items": {"type": "string"}},
        "opponents_or_contrasts": {"type": "array", "items": {"type": "string"}},
        "key_terms": {"type": "array", "items": {"type": "string"}},
        "citation_ecology_description": {"type": ["string", "null"]},
        "protected_core_candidate": {"type": "array", "items": {"type": "string"}},
        "mutable_zones": {"type": "array", "items": {"type": "string"}},
        "high_risk_zones": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
        "questions_for_user": {"type": "array", "items": {"type": "string"}},
    },
    # Required fields = those without which downstream code (semantic
    # profiler, fit assessor, disciplinary mapper, human view) reads
    # missing/wrong data and produces meaningless results.
    #
    # Moved to OPTIONAL with safe defaults (filled by
    # _fill_optional_defaults in json_repair) — display/metadata only:
    #   - title: dataclass already nullable; downstream uses
    #     "(untitled manuscript)" fallback in litops_bridge / submission_pack;
    #   - confidence: pure observability metadata; agent reads via
    #     parsed.get("confidence", "medium");
    #   - questions_for_user: never persisted to ArticleModel, only
    #     flows into AgentOutput; empty list is semantically "model had
    #     no follow-up questions".
    # Loosening these three unblocks cheaper LLM routes
    # (claude-haiku-4-5-20251001, gpt-4o-mini) which return rich content
    # but consistently skip these three keys, without weakening any
    # downstream invariant or observability signal (extraction_attempt
    # remains the source of truth for parse success).
    "required": [
        "language", "article_stage", "problem_statement",
        "research_question", "object_of_inquiry", "core_claims",
        "argument_structure", "method_status", "genre_current",
        "disciplinary_register_current", "novelty_mode",
        "theoretical_shoulders", "key_terms", "protected_core_candidate",
        "mutable_zones", "high_risk_zones", "unknowns", "assumptions",
    ],
    "additionalProperties": False,
}


def validate_article_extraction(data: dict) -> list[str]:
    """Check forbidden claims and structural issues. Returns list of warnings."""
    warnings: list[str] = []

    if data.get("article_stage") == "abstract":
        if data.get("confidence") == "high":
            warnings.append("Abstract-only input cannot have high confidence")
        if not data.get("unknowns"):
            warnings.append("Abstract-only input should have unknowns")

    if data.get("method_status") is not None and not isinstance(
        data.get("method_status"), str
    ):
        warnings.append(f"method_status must be a string: {data.get('method_status')}")

    if data.get("genre_current") is not None and not isinstance(
        data.get("genre_current"), str
    ):
        warnings.append(f"genre_current must be a string: {data.get('genre_current')}")

    return warnings


ARTICLE_MODELING_FAMILY = {
    "family_id": "article_modeling_v2",
    "agent_role_id": "article_modeler",
    "version": "2.0.0",
    "system_prompt": ARTICLE_MODELING_SYSTEM,
    "user_prompt_template": ARTICLE_MODELING_USER_TEMPLATE,
    "output_schema": ARTICLE_MODELING_OUTPUT_SCHEMA,
    "validator": validate_article_extraction,
}
