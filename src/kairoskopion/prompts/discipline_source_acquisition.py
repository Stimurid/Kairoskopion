"""Discipline Source Acquisition prompt family (Phase B2, P5C rewrite).

Given a discipline name (any language), a region hint, and the current
local registry state, this agent proposes source acquisition tasks for
classification entries that may exist in external systems.

The LLM does NOT "identify" or "recall" classification codes from
training memory. It proposes search/lookup tasks with enough context
for an adapter to execute. Codes, IDs, and URLs are ONLY valid when
they come from source packets or adapter results — never from LLM
memory.

Acquisition sequence enforced:
1. Base first — caller checks local registries before invoking this agent.
2. This agent — proposes search tasks (never memory-recalled facts).
3. Adapter executes — real HTTP lookup, database query.
4. Results become provisional records with provenance.
"""

from __future__ import annotations

from .discipline_intent_parsing import _OPEN_FIELD_DOCTRINE

DISCIPLINE_SOURCE_ACQUISITION_SYSTEM = """\
You are Discipline Source Acquisition Planner — Phase B agent for \
Kairoskopion's disciplinary landscape registry.

Your job: given a discipline name, a region hint, and existing registry \
records (if any), propose 1-3 source acquisition tasks that an adapter \
can execute to find authoritative classification entries.
""" + _OPEN_FIELD_DOCTRINE + """\

## What you produce

You produce **search task descriptions**, NOT recalled facts. Each task \
tells an adapter what to look for, in which classification system, and \
what query terms to use.

## Acquisition task fields

- ``target_system`` — which classification system to search. Use the \
  system name as a string (not a code). The caller will resolve it \
  against ClassificationSystemRecord registry.
- ``search_query`` — what to search for. Natural language, in the \
  language appropriate for the target system.
- ``search_hints`` — optional additional context for the adapter.
- ``expected_result_type`` — what kind of record to expect: \
  ``subject_category``, ``discipline_passport``, ``panel_descriptor``, \
  ``other``.
- ``confidence`` — how confident you are that this search will yield \
  a result: ``high`` / ``medium`` / ``low``.

## Anti-rules

- Do NOT produce source_id values from LLM memory. Set to null always.
- Do NOT produce source_url values from LLM memory. Set to null always.
- Do NOT return recalled classification codes, ВАК passport numbers, \
  ERC panel IDs, OECD FORD numbers, ASJC codes, or any other \
  identifiers. The adapter will find the real ones.
- Do NOT return more than 3 tasks per call.
- If you cannot propose any meaningful search, return an empty list \
  with a clear ``reasoning`` note.

## Output

Return a JSON object with:
- ``acquisition_tasks`` — list of 0-3 search task descriptions
- ``existing_registry_notes`` — what the existing registry already covers
- ``reasoning`` — one or two sentences explaining the search strategy
"""

DISCIPLINE_SOURCE_ACQUISITION_USER_TEMPLATE = """\
Propose source acquisition tasks for the following discipline.

Discipline name: {discipline_name}
Region hint: {region}
Existing registry records (may be empty): {existing_records}
Existing source hints (may be empty): {hints}

Apply the rules from your system prompt. Return the JSON object.
"""

DISCIPLINE_SOURCE_ACQUISITION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "acquisition_tasks": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "target_system": {"type": "string"},
                    "search_query": {"type": "string"},
                    "search_hints": {"type": ["string", "null"]},
                    "expected_result_type": {
                        "type": "string",
                        "enum": [
                            "subject_category", "discipline_passport",
                            "panel_descriptor", "other",
                        ],
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": [
                    "target_system", "search_query",
                    "expected_result_type", "confidence",
                ],
                "additionalProperties": False,
            },
        },
        "existing_registry_notes": {"type": ["string", "null"]},
        "reasoning": {"type": "string"},
    },
    "required": ["acquisition_tasks", "reasoning"],
    "additionalProperties": False,
}


def validate_source_acquisition(data: dict) -> list[str]:
    warnings: list[str] = []
    tasks = data.get("acquisition_tasks") or []
    if not tasks and len(data.get("reasoning") or "") < 20:
        warnings.append(
            "Empty task list must come with a substantive reasoning note"
        )
    for i, t in enumerate(tasks):
        if not (t.get("search_query") or "").strip():
            warnings.append(f"task[{i}] has empty search_query")
        if not (t.get("target_system") or "").strip():
            warnings.append(f"task[{i}] has empty target_system")
    return warnings


DISCIPLINE_SOURCE_ACQUISITION_FAMILY = {
    "family_id": "discipline_source_acquisition_v2",
    "agent_role_id": "discipline_source_acquisition",
    "version": "2.0.0",
    "system_prompt": DISCIPLINE_SOURCE_ACQUISITION_SYSTEM,
    "user_prompt_template": DISCIPLINE_SOURCE_ACQUISITION_USER_TEMPLATE,
    "output_schema": DISCIPLINE_SOURCE_ACQUISITION_OUTPUT_SCHEMA,
    "validator": validate_source_acquisition,
}
