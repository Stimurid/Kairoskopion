"""Citation Ecology Analysis prompt family — Organ #9.

Analyzes bibliography × venue context for semantic gaps and strategies.
"""

from __future__ import annotations

CITATION_ECOLOGY_SYSTEM = """\
You are Citation Ecology Analyst — a specialized role in Kairoskopion's \
fit-assessment pipeline.

Your input: a bibliography profile (reference list with metadata), an \
article model, a venue model, and venue guidelines text.

Your job: analyze the citation ecology — how well the article's \
bibliography fits the venue's expectations, and what gaps exist.

## Analysis areas

1. **gaps** — specific citation gaps with severity and category:
   - "canon_gap" — missing foundational references the venue expects.
   - "recency_gap" — bibliography is too dated for the venue.
   - "diversity_gap" — too few source types or traditions.
   - "bridge_gap" — missing citations that connect the article to the \
     venue's usual discourse.
   - "methodological_gap" — missing method references the venue expects.

2. **bridge_references** — suggested citation strategies (NOT fabricated \
   references). Example: "Add references to the postphenomenological \
   tradition (Verbeek, Ihde)" — naming the tradition, not fake papers.

3. **ecology_health** — overall assessment: "healthy", "adequate", \
   "needs_work", "critical".

4. **venue_canon_alignment** — how well the bibliography matches what \
   the venue typically publishes.

## Per-gap output

- **gap_id** — unique ID.
- **category** — one of the gap types above.
- **severity** — "critical", "significant", "minor".
- **description** — what's missing and why it matters.
- **suggested_action** — what to add (tradition/area, NOT fabricated refs).

## Rules

- Do NOT fabricate specific citation references (no "Smith 2024").
- Suggest traditions, schools, key thinkers — NOT specific papers.
- If the venue's citation expectations are unknown, return honest \
  unknowns, not threshold-based guesses.
- If the bibliography is empty, note it but do not fabricate gaps.
- Return JSON only.
"""

CITATION_ECOLOGY_USER_TEMPLATE = """\
Analyze the citation ecology for the following article × venue pairing.

Article model (compact):
{article_compact}

Bibliography profile:
{bibliography_json}

Venue model (compact):
{venue_compact}

Venue guidelines text (excerpt):
{venue_guidelines}

Return a JSON object matching the schema.
"""

CITATION_ECOLOGY_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "gap_id": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["canon_gap", "recency_gap",
                                 "diversity_gap", "bridge_gap",
                                 "methodological_gap"],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "significant", "minor"],
                    },
                    "description": {"type": "string"},
                    "suggested_action": {"type": "string"},
                },
                "required": ["gap_id", "category", "severity",
                             "description"],
                "additionalProperties": True,
            },
        },
        "bridge_references": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tradition_or_area": {"type": "string"},
                    "key_thinkers": {
                        "type": "array", "items": {"type": "string"},
                    },
                    "rationale": {"type": "string"},
                },
                "required": ["tradition_or_area", "rationale"],
                "additionalProperties": True,
            },
        },
        "ecology_health": {
            "type": "string",
            "enum": ["healthy", "adequate", "needs_work", "critical"],
        },
        "venue_canon_alignment": {"type": "string"},
        "summary": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "unknowns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["gaps", "ecology_health", "summary", "confidence",
                  "unknowns"],
    "additionalProperties": True,
}


def validate_citation_ecology(data: dict) -> list[str]:
    warnings: list[str] = []
    for i, g in enumerate(data.get("gaps", [])):
        if not isinstance(g, dict):
            warnings.append(f"gap[{i}] is not an object")
            continue
        action = g.get("suggested_action", "")
        if "202" in action and " " in action:
            warnings.append(
                f"gap[{i}] suggested_action may contain fabricated "
                f"citation reference"
            )
    for i, b in enumerate(data.get("bridge_references", [])):
        if not isinstance(b, dict):
            continue
        for t in b.get("key_thinkers", []):
            if "202" in str(t):
                warnings.append(
                    f"bridge_reference[{i}] may contain fabricated year"
                )
    return warnings


CITATION_ECOLOGY_FAMILY = {
    "family_id": "citation_ecology_analysis_v1",
    "agent_role_id": "citation_ecology",
    "version": "1.0.0",
    "system_prompt": CITATION_ECOLOGY_SYSTEM,
    "user_prompt_template": CITATION_ECOLOGY_USER_TEMPLATE,
    "output_schema": CITATION_ECOLOGY_OUTPUT_SCHEMA,
    "validator": validate_citation_ecology,
}
