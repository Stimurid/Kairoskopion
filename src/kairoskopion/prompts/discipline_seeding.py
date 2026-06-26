"""Discipline Seeder prompt family (Phase B2, P5C rewrite).

Consumes source packets from adapters/searches and produces a draft
DisciplineRecord card. The card is a working tool for downstream agents,
NOT an encyclopedia entry.

Key P5C invariants:
- key_authors ONLY from packet excerpts, never from LLM memory
- No examples of specific disciplines/thinkers in prompt text
- source_status ships as "provisional" (was "llm_draft")
- evidence_refs mirror input packets only — no new sources invented
"""

from __future__ import annotations

from .discipline_intent_parsing import _OPEN_FIELD_DOCTRINE

DISCIPLINE_SEEDING_SYSTEM = """\
You are Discipline Seeder — Phase B agent for Kairoskopion's \
disciplinary landscape registry.

Your job: given source packets describing a discipline, produce a \
DisciplineCard that downstream agents can use as a working tool.
""" + _OPEN_FIELD_DOCTRINE + """\

## Core principle: working tool, not encyclopedia

The card answers questions like:
- Which objects does this discipline legitimately study?
- Which objects does it NOT study (borderline cases)?
- Which forms of evidence does it accept?
- Which questions does it know how to formulate?
- Which argument styles count as proper here?
- Which publication genres does it use?

It does NOT need a comprehensive history, complete author list, or \
balanced encyclopedia-style description. Pick the few specifics that \
let an agent decide "this article fits / doesn't fit / borderline".

## Anti-rules

- Do NOT invent classification codes or identifiers. If a packet \
  doesn't provide them, leave evidence_refs[].source_id null.
- Do NOT fill every field. Leave fields that the packets don't justify \
  as null (for strings) or empty list (for arrays). Mark missing items \
  in ``unknowns``.
- Do NOT collapse discipline-specifics into generic phrases like \
  "various methods" or "many objects". If you can't be specific, \
  leave the field empty and put the name in ``unknowns``.
- Do NOT invent key_authors. Only include authors actually mentioned \
  in the source packet excerpts. Do NOT recall authors from LLM \
  training memory. If no authors are mentioned in packets, leave \
  key_authors empty.
- Do NOT propagate language assumption: a discipline may have \
  English-language theoretical core but Russian-language venue \
  practice — fill ``russian_specificity`` if relevant, otherwise null.

## Output

Return a JSON object matching DisciplineCard schema. ``source_status`` \
MUST be ``"provisional"``. ``evidence_refs`` MUST mirror the input \
packets (no new sources invented).

For fields you cannot fill, leave null / empty AND record the field \
name in ``unknowns``.
"""

DISCIPLINE_SEEDING_USER_TEMPLATE = """\
Produce a DisciplineCard draft from the following authoritative \
source packets.

Discipline target: {discipline_name}
Region: {region}
Packets (JSON):
{packets_json}

Apply the rules from your system prompt. Return the JSON object.
"""

DISCIPLINE_SEEDING_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "discipline_id": {"type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9.]+)*$"},
        "display_names": {
            "type": "object",
            "properties": {
                "ru": {"type": "string"},
                "en": {"type": "string"},
            },
            "additionalProperties": {"type": "string"},
        },
        "region": {
            "type": "string",
            "enum": ["ru", "international", "eu-fr", "eu-de", "en-us", "en-uk", "other"],
        },
        "source_status": {"type": "string", "enum": ["provisional"]},
        "aliases": {"type": "array", "items": {"type": "string"}},
        "paradigm": {"type": ["string", "null"]},
        "epistemic_regime": {"type": ["string", "null"]},
        "forms_of_evidence": {"type": "array", "items": {"type": "string"}},
        "canonical_questions": {"type": "array", "items": {"type": "string"}},
        "typical_problem_forms": {"type": "array", "items": {"type": "string"}},
        "legitimate_objects": {"type": "array", "items": {"type": "string"}},
        "illegitimate_or_borderline_objects": {"type": "array", "items": {"type": "string"}},
        "argument_styles": {"type": "array", "items": {"type": "string"}},
        "publication_genres": {"type": "array", "items": {"type": "string"}},
        "institutional_forms": {"type": "array", "items": {"type": "string"}},
        "russian_specificity": {"type": ["string", "null"]},
        "international_mapping": {"type": "array", "items": {"type": "string"}},
        "methods": {"type": "array", "items": {"type": "string"}},
        "instruments": {"type": "array", "items": {"type": "string"}},
        "ontologies": {"type": "array", "items": {"type": "string"}},
        "key_authors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string", "enum": ["founder", "classic", "contemporary", "boundary_setter", "critic"]},
                    "era": {"type": ["string", "null"]},
                    "discipline_relevance": {"type": ["string", "null"]},
                },
                "required": ["name", "role"],
                "additionalProperties": False,
            },
        },
        "history": {"type": ["string", "null"]},
        "boundaries": {"type": ["string", "null"]},
        "adjacent": {"type": "array", "items": {"type": "string"}},
        "evidence_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_type": {"type": "string"},
                    "source_id": {"type": ["string", "null"]},
                    "source_url": {"type": ["string", "null"]},
                    "excerpt": {"type": ["string", "null"]},
                },
                "required": ["source_type"],
                "additionalProperties": False,
            },
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "discipline_id", "display_names", "region", "source_status",
        "evidence_refs",
    ],
    "additionalProperties": True,
}


def validate_seeding(data: dict) -> list[str]:
    warnings: list[str] = []
    if data.get("source_status") != "provisional":
        warnings.append("seeder output must ship as source_status=provisional")
    if not data.get("evidence_refs"):
        warnings.append("seeder output must have at least one evidence_ref (from input packets)")
    # Working-tool fields should not all be empty
    working = ("legitimate_objects", "canonical_questions", "forms_of_evidence")
    empty = [k for k in working if not data.get(k)]
    if len(empty) == len(working):
        warnings.append(
            "All working-tool fields empty — card is encyclopedia-only and won't help agents"
        )
    return warnings


DISCIPLINE_SEEDING_FAMILY = {
    "family_id": "discipline_seeding_v2",
    "agent_role_id": "discipline_seeder",
    "version": "2.0.0",
    "system_prompt": DISCIPLINE_SEEDING_SYSTEM,
    "user_prompt_template": DISCIPLINE_SEEDING_USER_TEMPLATE,
    "output_schema": DISCIPLINE_SEEDING_OUTPUT_SCHEMA,
    "validator": validate_seeding,
}
