"""Citation Ecology prompt family (spec §69.6).

Builds CitationExpectationProfile and citation adaptation plan:
what citation traditions a venue expects, what bridges the article
needs, gap analysis between article bibliography and venue norms.
"""

from __future__ import annotations

FAMILY_ID = "citation_ecology_v1"
FAMILY_NAME = "Citation Ecology"
VERSION = "1.0.0"
PURPOSE = (
    "Analyze citation expectations of a venue and compare against the "
    "article's current bibliography. Identify gaps, needed bridges, "
    "tradition mismatches, and propose a citation adaptation plan."
)

INPUT_CONTRACT = {
    "article_model": "ArticleModel dict with bibliography info",
    "venue_model": "VenueModel dict with citation expectations",
    "bibliography_profile": "Optional BibliographyProfile dict",
    "citation_expectation_profile": "Optional CitationExpectationProfile dict",
}
OUTPUT_CONTRACT = {
    "citation_ecology_report": "CitationEcologyReport dict",
    "gaps": "List of citation gap descriptions",
    "bridge_references": "Suggested bridge references",
    "unknowns": "Unknown citation expectations",
}

SYSTEM_PROMPT = """\
You are Citation Ecologist — a specialized analytical role within \
Kairoskopion, an evidence-first publication-positioning system.

Your task: compare an article's citation profile against a venue's \
citation expectations and identify gaps, needed bridges, and \
tradition mismatches.

## Analysis dimensions

1. **tradition_match** — does the article cite from the traditions \
   the venue expects? (e.g., a philosophy of technology journal \
   expects Simondon/Heidegger/Stiegler; an STS journal expects \
   Latour/Callon/Law)
2. **canonical_coverage** — are the canonical/foundational works \
   for this venue's discipline cited?
3. **recency** — does the article cite recent work? Some venues \
   expect cutting-edge references; others value historical depth.
4. **reference_count** — is the bibliography size appropriate? \
   (e.g., 25-40 for a humanities journal, 40-80 for a review article)
5. **self_citation** — any self-citation concerns for blind review?
6. **bridge_references** — which references would the article need \
   to add to be legible to this venue's audience?
7. **tradition_gaps** — which citation traditions are expected but \
   absent?
8. **risk_items** — citation-related risks (too few refs, wrong \
   tradition, self-citation in blind review, outdated bibliography)

## Rules

- Base analysis on actual bibliography data when available.
- Do NOT fabricate reference suggestions — suggest categories/types \
  of references needed, not specific fake citations.
- If BibliographyProfile is unavailable, work from ArticleModel's \
  citation_ecology field and note the limitation.
- Mark all inferences explicitly.
"""

USER_TEMPLATE = """\
Analyze citation ecology fit between this article and venue.

## ArticleModel
```json
{article_json}
```

## VenueModel
```json
{venue_json}
```

## BibliographyProfile (may be empty)
```json
{bibliography_json}
```

{rubric_context}

Return a JSON object with citation ecology analysis.
"""

OUTPUT_SCHEMA: dict = {
    "title": "CitationEcologyResult",
    "type": "object",
    "properties": {
        "tradition_match": {
            "type": "string",
            "enum": ["strong", "medium", "weak", "unknown"],
        },
        "canonical_coverage": {
            "type": "string",
            "enum": ["adequate", "partial", "missing", "unknown"],
        },
        "recency_assessment": {"type": ["string", "null"]},
        "reference_count_assessment": {"type": ["string", "null"]},
        "self_citation_risk": {"type": ["string", "null"]},
        "bridge_references_needed": {
            "type": "array",
            "items": {"type": "string"},
        },
        "tradition_gaps": {
            "type": "array",
            "items": {"type": "string"},
        },
        "risk_items": {
            "type": "array",
            "items": {"type": "string"},
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [],
    "additionalProperties": True,
}

FORBIDDEN_BEHAVIORS = [
    "Do not fabricate specific reference suggestions with fake DOIs",
    "Do not claim citation traditions are present without evidence",
    "Do not reduce citation ecology to reference count alone",
]

EVIDENCE_REQUIREMENTS = [
    "Tradition assessments must reference specific citation data",
    "Bridge reference suggestions must be categories, not fabricated citations",
]

UNKNOWN_HANDLING = "mark_unknown"
VALIDATION_NOTES = "Verify tradition_match is not empty"


def validate_citation_ecology(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("unknowns"):
        warnings.append("No unknowns — citation ecology always has uncertainties")
    return warnings


CITATION_ECOLOGY_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": "citation_ecology_profiler",
    "version": VERSION,
    "purpose": PURPOSE,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_citation_ecology,
    "forbidden_behaviors": FORBIDDEN_BEHAVIORS,
    "evidence_requirements": EVIDENCE_REQUIREMENTS,
    "unknown_handling": UNKNOWN_HANDLING,
}
