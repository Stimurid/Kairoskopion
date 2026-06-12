"""Disciplinary Pathway Mapping prompt family (UC-1 step 4).

Takes ArticleModel + optional ArticleSemanticProfile and produces
ranked disciplinary pathways — which academic worlds the article can enter.
"""

from __future__ import annotations


DISCIPLINARY_MAPPING_SYSTEM = """\
You are Disciplinary Pathway Mapper — a specialized analytical role within \
Kairoskopion, an evidence-first publication-positioning system.

Your task: given an ArticleModel (and optionally an ArticleSemanticProfile), \
determine which academic disciplinary worlds this article could realistically \
enter. For each pathway, assess fit strength, required adaptations, and risks.

## Core rules

1. **Multiple pathways are the norm.** A single intellectual work can have \
   several publication fates: philosophical, STS, AI-ethics, education, etc.
2. **Each pathway is a different publication trajectory**, not just a keyword. \
   Different pathways mean different venues, different audiences, different \
   citation ecologies, different norms for what counts as a contribution.
3. **Rank by fit strength**, not by prestige. The user decides prestige later.
4. **Identify required adaptations per pathway.** Moving from philosophy of \
   technology to STS may require adding empirical material. Moving from \
   history of ideas to AI ethics may require a contemporary framing.
5. **Flag field-core risk.** If adapting for a pathway would destroy the \
   article's intellectual core, say so explicitly.
6. **Include language as a pathway dimension.** Russian-language vs. \
   English-language vs. bilingual are distinct trajectories.
7. **Unknown is a valid strength.** If you cannot assess a pathway, say unknown.

## Disciplinary landscape (non-exhaustive reference)

- Philosophy of technology / philosophy of engineering
- Philosophical anthropology
- History of philosophy / intellectual history
- Science and Technology Studies (STS)
- AI ethics / ethics of technology / philosophy of AI
- Digital humanities
- Education / learning sciences / philosophy of education
- Media studies / communication studies
- Cognitive science / philosophy of mind
- Social theory / critical theory
- Management / innovation studies / technology management
- Psychology-adjacent (if empirical component present)
- Area studies (if geographically bounded)

## School/tradition awareness

Recognize theoretical affiliations: Simondon, Vygotsky, Heidegger, \
analytic philosophy of mind, continental tradition, pragmatism, ANT, \
posthumanism, Frankfurt School, phenomenology, enactivism, etc. \
These affiliations affect which venues are receptive.

## Forbidden behavior

- Do NOT assign only one pathway unless the article is genuinely single-discipline.
- Do NOT rank by prestige. Rank by fit strength.
- Do NOT ignore language as a pathway dimension.
- Do NOT claim "any philosophy journal" — name specific disciplinary niches.
- Do NOT hide risks to the intellectual core.
"""

DISCIPLINARY_MAPPING_USER_TEMPLATE = """\
Map disciplinary pathways for this article.

## ArticleModel
```json
{article_json}
```

## ArticleSemanticProfile (may be empty)
```json
{semantic_profile_json}
```

Return a JSON object with ranked disciplinary pathways. \
Each pathway should include discipline name, fit strength, reasoning, \
required adaptations, field core risk, venue type hints, and language options.
"""

DISCIPLINARY_MAPPING_OUTPUT_SCHEMA: dict = {
    "title": "DisciplinaryPathwaySet",
    "type": "object",
    "properties": {
        "pathways": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "discipline_name": {"type": "string"},
                    "fit_strength": {
                        "type": "string",
                        "enum": ["strong", "medium", "weak", "incompatible", "unknown"],
                    },
                    "reasoning": {"type": "string"},
                    "required_adaptations": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "field_core_risk": {
                        "type": ["string", "null"],
                        "enum": ["none", "low", "medium", "high", "destructive", None],
                    },
                    "venue_type_hints": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Generic venue type labels (e.g. 'philosophy journal', 'STS proceedings')",
                    },
                    "example_venue_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Only include if you are certain the venue exists and publishes in this area. Omit rather than guess.",
                    },
                    "language_options": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "indexing_options": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "rank": {"type": "integer"},
                    "strategic_value_notes": {"type": ["string", "null"]},
                    "unknowns": {"type": "array", "items": {"type": "string"}},
                    "confidence": {
                        "type": ["string", "null"],
                        "enum": ["high", "medium", "low", None],
                    },
                },
                "required": ["discipline_name", "fit_strength", "reasoning", "rank"],
                "additionalProperties": False,
            },
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "questions_for_user": {"type": "array", "items": {"type": "string"}},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
    },
    "required": ["pathways", "unknowns", "confidence"],
    "additionalProperties": False,
}


def validate_disciplinary_mapping(data: dict) -> list[str]:
    """Check structural issues in disciplinary mapping output."""
    warnings: list[str] = []

    pathways = data.get("pathways", [])
    if not pathways:
        warnings.append("No pathways returned — every article has at least one disciplinary home")

    if len(pathways) == 1:
        warnings.append("Only one pathway — consider whether cross-disciplinary options exist")

    strengths = [p.get("fit_strength") for p in pathways]
    if all(s == "strong" for s in strengths if s):
        warnings.append("All pathways strong — suspiciously optimistic")

    if not data.get("unknowns"):
        warnings.append("No unknowns — unlikely for disciplinary mapping")

    return warnings


DISCIPLINARY_MAPPING_FAMILY = {
    "family_id": "disciplinary_mapping_v1",
    "agent_role_id": "disciplinary_pathway_mapper",
    "version": "1.0.0",
    "system_prompt": DISCIPLINARY_MAPPING_SYSTEM,
    "user_prompt_template": DISCIPLINARY_MAPPING_USER_TEMPLATE,
    "output_schema": DISCIPLINARY_MAPPING_OUTPUT_SCHEMA,
    "validator": validate_disciplinary_mapping,
}
