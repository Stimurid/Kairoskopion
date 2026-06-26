"""Venue Family Context prompt family — Organ #3.

Given a concrete venue + corpus evidence, infers discipline family
context WITHOUT model-memory sibling suggestions.
"""

from __future__ import annotations

from kairoskopion.prompts.discipline_intent_parsing import (
    _DOMAIN_AGNOSTIC_DOCTRINE,
)

VENUE_FAMILY_CONTEXT_SYSTEM = """\
You are Venue Family Context Builder — a specialized role in \
Kairoskopion's venue-positioning pipeline.

Your input:
- a VenueModel or VenueProfilePackage (already extracted from \
  venue text) — canonical name, scope, subject areas, venue type;
- known corpus summaries (other venues the system already has \
  evidence for);
- accepted VenueMemory records;
- ArticleModel if available;
- DisciplineIntent if available.

Your job: infer the venue's discipline family context — what \
academic community this venue belongs to — using ONLY evidence \
from the input, not from LLM training memory.
""" + _DOMAIN_AGNOSTIC_DOCTRINE + """\

## CRITICAL RULE: No model-memory siblings

You may NOT suggest sibling/competitor venues from LLM training \
memory as facts.

Neighboring venues must come from the input corpus summaries or \
VenueMemory records ONLY. If the corpus does not contain \
neighbors, report that the family context is incomplete.

You may NOT label a venue as "flagship", "mid-tier", "emerging", \
or "niche" unless evidence from the input supports it. If evidence \
is absent, use "role_unknown".

## Output fields

1. **source_venue** — echo the venue's canonical name.

2. **families** — venue families the target belongs to (1-3). Each:
   - **family_descriptor** — descriptive name of the venue cluster.
   - **discipline_zone** — the discipline area.
   - **venue_role_in_family** — role of this venue: use \
     "role_unknown" if no evidence supports a role label.
   - **known_neighbors_from_corpus** — venues from the input \
     corpus that belong to the same family. Each with source_ref.
   - **evidence_basis** — what from the venue's scope/subject \
     areas supports this family assignment.

3. **corpus_coverage_warning** — if the corpus does not have enough \
   venues to establish family context, say so.

4. **recommended_next_action** — what the operator should do next \
   (e.g. "run discovery for this family zone", "add more venues \
   to corpus").

5. **families_status** — "assessed" if analysis succeeded, \
   "incomplete_corpus" if neighbors could not be established.

6. **confidence**, **unknowns**, **reasoning**.

## Rules

- Ground analysis in the venue's scope_summary and subject_areas.
- Do NOT fabricate sibling venue names from training data.
- If the venue is obscure and corpus is empty, return \
  confidence="low" with explicit unknowns and \
  corpus_coverage_warning.
- Return JSON only.
"""

VENUE_FAMILY_CONTEXT_USER_TEMPLATE = """\
Given the venue model and corpus state below, infer its discipline \
family context.

Venue model:
{venue_json}

Known corpus summaries:
{corpus_summaries}

VenueMemory accepted records:
{venue_memory}

Article model (if available):
{article_summary}

Discipline intent (if available):
{discipline_intent}

Return a JSON object matching the schema.
"""

VENUE_FAMILY_CONTEXT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "source_venue": {"type": "string"},
        "families": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "family_descriptor": {"type": "string"},
                    "discipline_zone": {"type": "string"},
                    "venue_role_in_family": {"type": "string"},
                    "known_neighbors_from_corpus": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "venue_ref": {"type": "string"},
                                "source_ref": {"type": "string"},
                            },
                            "required": ["venue_ref", "source_ref"],
                            "additionalProperties": True,
                        },
                    },
                    "evidence_basis": {"type": "string"},
                },
                "required": ["family_descriptor", "discipline_zone",
                             "venue_role_in_family"],
                "additionalProperties": True,
            },
        },
        "corpus_coverage_warning": {"type": ["string", "null"]},
        "recommended_next_action": {"type": ["string", "null"]},
        "families_status": {
            "type": "string",
            "enum": ["assessed", "incomplete_corpus",
                     "BLOCKED_NEEDS_LLM"],
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low", "none"],
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["source_venue", "families", "families_status",
                  "confidence", "unknowns", "reasoning"],
    "additionalProperties": True,
}


def validate_venue_family_context(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("families"):
        warnings.append("no families returned")
    if not data.get("source_venue"):
        warnings.append("source_venue is empty")
    for i, f in enumerate(data.get("families", [])):
        if not isinstance(f, dict):
            continue
        role = f.get("venue_role_in_family", "")
        if role in ("flagship", "mid-tier", "emerging", "niche"):
            basis = f.get("evidence_basis", "")
            if not basis or len(basis) < 10:
                warnings.append(
                    f"family[{i}] role '{role}' without evidence_basis"
                )
        neighbors = f.get("known_neighbors_from_corpus", [])
        for j, n in enumerate(neighbors):
            if isinstance(n, dict) and not n.get("source_ref"):
                warnings.append(
                    f"family[{i}] neighbor[{j}] missing source_ref — "
                    f"may be model-memory"
                )
    return warnings


VENUE_FAMILY_CONTEXT_FAMILY = {
    "family_id": "venue_family_context_v2",
    "agent_role_id": "venue_family_context_builder",
    "version": "2.0.0",
    "system_prompt": VENUE_FAMILY_CONTEXT_SYSTEM,
    "user_prompt_template": VENUE_FAMILY_CONTEXT_USER_TEMPLATE,
    "output_schema": VENUE_FAMILY_CONTEXT_OUTPUT_SCHEMA,
    "validator": validate_venue_family_context,
}
