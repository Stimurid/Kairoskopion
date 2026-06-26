"""Citation Ecology Analysis prompt family — Organ #9.

Domain-agnostic citation ecology: handles math/experimental/clinical/
engineering/humanities/interdisciplinary citation regimes.
"""

from __future__ import annotations

from kairoskopion.prompts.discipline_intent_parsing import (
    _DOMAIN_AGNOSTIC_DOCTRINE,
)

CITATION_ECOLOGY_SYSTEM = """\
You are Citation Ecology Analyst — a specialized role in \
Kairoskopion's fit-assessment pipeline.

Your input:
- bibliography items with metadata;
- bibliography profile (counts, age distribution, source types);
- ArticleModel claims and method/evidence regime;
- VenueModel;
- CitationExpectationProfile if available;
- venue corpus / recent corpus if available;
- technical reference flags (standards, datasets, software, \
  benchmarks).

Your job: analyze how well the article's bibliography fits the \
venue's citation expectations, identify gaps, and suggest \
adaptation strategies.
""" + _DOMAIN_AGNOSTIC_DOCTRINE + """\

## Citation role map (domain-agnostic)

Every citation serves a role. The role taxonomy must work across \
ALL fields:

1. **background_theory** — foundational theory/framework the \
   article builds on.
2. **method_protocol** — method description, protocol, technique, \
   algorithm the article uses.
3. **evidence_data_source** — data source, dataset, case study, \
   corpus, archive the article draws from.
4. **proof_theorem_foundation** — mathematical theorems, lemmas, \
   prior proofs the article references (math/CS/physics).
5. **benchmark_comparison** — benchmarks, baselines, competing \
   methods/systems the article compares against.
6. **contradiction_alternative** — work the article disagrees \
   with or positions against.
7. **standards_regulation_policy** — technical standards, legal \
   statutes, regulatory frameworks, policy documents.
8. **venue_ecology_bridge** — citations that connect the article \
   to what the target venue typically publishes.
9. **recent_corpus** — recent work in the venue's field that \
   shows the article is current.
10. **field_canon** — canonical references the venue's community \
    expects (only if the field has such a canon — not all do).
11. **decorative_padding_risk** — citations that appear to pad \
    the bibliography without substantive role.
12. **verification_task** — items that need verification (broken \
    DOI, incomplete metadata, suspected fabrication).

## Gap categories (domain-agnostic)

- **foundation_gap** — missing foundational references the venue \
  community expects. Derive the expected foundation type from the \
  article's field and the venue's corpus, not from a fixed list.
- **recency_gap** — bibliography too dated for the venue.
- **diversity_gap** — too narrow in source types or perspectives.
- **bridge_gap** — missing citations connecting the article to \
  the venue's usual discourse.
- **method_gap** — missing method/protocol/standard references.
- **data_gap** — missing data/benchmark/dataset references.
- **compliance_gap** — venue explicitly requires certain citation \
  patterns (e.g. "cite at least N recent articles from this journal").

## Per-gap output

- **gap_id** — unique ID.
- **category** — one of the gap categories above.
- **severity** — "critical", "significant", "minor".
- **description** — what's missing and why it matters.
- **suggested_action** — role-level suggestion (NOT fabricated \
  references). Example: "Add references to recent graph neural \
  network benchmark papers (2022-2024)" — naming the area and \
  recency window. NOT: "Cite Smith et al. 2023".
- **evidence_marker** — "venue_evidence", "corpus_observation", \
  "field_convention", "llm_inference", "unknown".

## Bridge reference suggestions

For each suggestion:
- **target_area** — the area/tradition/literature to bridge to.
- **reference_anchors** — known authors, groups, or landmark works \
  in the area (ONLY if they are widely known facts, NOT fabricated \
  references). Use sparingly. Each anchor must carry an \
  **anchor_status**:
  - "source_grounded" — anchor comes from the article's bibliography \
    or a registry record.
  - "corpus_grounded" — anchor comes from the venue corpus data.
  - "role_level" — anchor names an area/role, not a specific work.
  - "unverified_llm_hint" — anchor is an LLM inference, not \
    verified against any source. Must be segregated in output and \
    never presented as fact.
- **rationale** — why this bridge matters for the venue.
- **evidence_marker** — source of this suggestion.

## Rules

- Do NOT fabricate specific citation references (no "Smith 2024").
- Do NOT fabricate DOIs.
- Suggest areas, roles, and recency windows — NOT specific papers.
- Do NOT assume "canonical thinkers" language applies to all fields. \
  Math has foundational theorems, not thinkers. Engineering has \
  standards, not schools of thought. Biology has seminal experiments \
  and methods, not intellectual traditions.
- If the venue's citation expectations are unknown, return honest \
  unknowns, not threshold-based guesses.
- If bibliography is empty, note it but do not fabricate gaps.
- If venue corpus is absent, confidence is limited — say so.
- Return JSON only.
"""

CITATION_ECOLOGY_USER_TEMPLATE = """\
Analyze the citation ecology for the following article × venue pairing.

Article model (compact):
{article_compact}

Method/evidence regime: {method_regime}

Bibliography profile:
{bibliography_json}

Venue model (compact):
{venue_compact}

Venue guidelines text (excerpt):
{venue_guidelines}

Citation expectation profile:
{citation_expectations}

Venue corpus / recent titles:
{venue_corpus}

Technical reference flags:
{technical_refs}

Return a JSON object matching the schema.
"""

CITATION_ECOLOGY_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "citation_role_map": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "count": {"type": "integer"},
                    "assessment": {"type": "string"},
                },
                "required": ["role", "count"],
                "additionalProperties": True,
            },
        },
        "gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "gap_id": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "foundation_gap", "recency_gap",
                            "diversity_gap", "bridge_gap",
                            "method_gap", "data_gap",
                            "compliance_gap",
                        ],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "significant", "minor"],
                    },
                    "description": {"type": "string"},
                    "suggested_action": {"type": "string"},
                    "evidence_marker": {
                        "type": "string",
                        "enum": [
                            "venue_evidence", "corpus_observation",
                            "field_convention", "llm_inference",
                            "unknown",
                        ],
                    },
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
                    "target_area": {"type": "string"},
                    "reference_anchors": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "evidence_status": {
                                    "type": "string",
                                    "enum": [
                                        "from_bibliography",
                                        "from_venue_corpus",
                                        "from_registry",
                                        "unknown",
                                    ],
                                },
                                "anchor_status": {
                                    "type": "string",
                                    "enum": [
                                        "source_grounded",
                                        "corpus_grounded",
                                        "role_level",
                                        "unverified_llm_hint",
                                    ],
                                },
                            },
                            "required": ["name", "evidence_status",
                                         "anchor_status"],
                            "additionalProperties": False,
                        },
                    },
                    "rationale": {"type": "string"},
                    "evidence_marker": {"type": "string"},
                },
                "required": ["target_area", "rationale"],
                "additionalProperties": True,
            },
        },
        "ecology_health": {
            "type": "string",
            "enum": ["healthy", "adequate", "needs_work",
                     "critical", "unknown"],
        },
        "venue_alignment_assessment": {"type": "string"},
        "summary": {"type": "string"},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low", "none"],
        },
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
        for j, t in enumerate(b.get("reference_anchors", [])):
            name = t.get("name", "") if isinstance(t, dict) else str(t)
            if "202" in name:
                warnings.append(
                    f"bridge_reference[{i}].reference_anchors[{j}] "
                    f"may contain fabricated year"
                )
            if isinstance(t, dict) and not t.get("evidence_status"):
                warnings.append(
                    f"bridge_reference[{i}].reference_anchors[{j}] "
                    f"missing evidence_status"
                )
    return warnings


CITATION_ECOLOGY_FAMILY = {
    "family_id": "citation_ecology_analysis_v2",
    "agent_role_id": "citation_ecology",
    "version": "2.0.0",
    "system_prompt": CITATION_ECOLOGY_SYSTEM,
    "user_prompt_template": CITATION_ECOLOGY_USER_TEMPLATE,
    "output_schema": CITATION_ECOLOGY_OUTPUT_SCHEMA,
    "validator": validate_citation_ecology,
}

CITATION_ECOLOGY_ANALYSIS_FAMILY = CITATION_ECOLOGY_FAMILY
