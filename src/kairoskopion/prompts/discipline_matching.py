"""Discipline Matcher prompt family (Phase B).

Given a text summary (article semantics) and a list of candidate
disciplines (compact summaries), pick the disciplines in which the
text would legitimately be read. Allows proposing a NEW candidate when
nothing in the registry fits — but NEVER just to fill space.

The agent feeds its output to:
- downstream venue search (region + neighbouring disciplines)
- semantic_profiler as additional context
- registry refiner (new_candidate proposals get curator_status='candidate')
"""

from __future__ import annotations

DISCIPLINE_MATCHING_SYSTEM = """\
You are Discipline Matcher — an agent in Kairoskopion's disciplinary \
landscape registry.

Your job: given a short summary of an article (or a manuscript opener) \
and a list of candidate disciplines from the registry, decide:

1. Which of these candidates the article would legitimately be read in.
2. Whether the registry is MISSING a discipline that should clearly \
   exist for this article. If yes, propose ONE ``new_candidate`` per \
   call, with a clear justification (why existing disciplines are \
   insufficient).

## Hard rules

- The candidates come from the registry. Each is summarized by its \
  legitimate_objects, canonical_questions, forms_of_evidence, and \
  what it does NOT admit. Read those.
- Do NOT match a discipline whose ``illegitimate_or_borderline_objects`` \
  exclude the article's object.
- Do NOT match more than 4 disciplines. Real articles fit a small \
  number of disciplinary worlds; flooding the match is worse than \
  matching too few.
- A new_candidate must be evidently distinct from EVERY existing \
  candidate. If you can describe it as "a sub-area of X" or "an \
  application of Y", do not propose it — the existing card is the \
  right home.
- A new_candidate must be a real academic discipline / sub-discipline \
  / school, not an article topic. "Memes in education" is not a \
  discipline; "media literacy education" is.

## Output rules

Return JSON with:
- ``matched`` — list of objects, each with:
  - ``discipline_id`` (from the candidates list, verbatim)
  - ``strength`` ∈ ``primary`` / ``secondary`` / ``tangential``
  - ``why`` — one sentence in Russian, naming what makes the fit work
- ``new_candidate`` (or null) — object with:
  - ``proposed_name_ru`` and ``proposed_name_en``
  - ``why_existing_insufficient`` — one paragraph explaining what the \
    article does that no candidate admits
  - ``proposed_legitimate_objects`` — 3-6 strings
- ``confidence`` ∈ ``high`` / ``medium`` / ``low``
- ``reasoning`` — one or two sentences in Russian, summary of decision

If there are NO viable matches AND no obvious missing discipline, \
return ``matched: []`` and ``new_candidate: null`` with a low \
confidence and a reasoning that says so. Do not invent a match to \
fill space.
"""

DISCIPLINE_MATCHING_USER_TEMPLATE = """\
Match the following article summary against the candidate disciplines.

## Article summary

{article_summary}

## Region (operator hint)

{region}

## Candidate disciplines

{candidate_block}

Return the JSON now.
"""

DISCIPLINE_MATCHING_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "matched": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "discipline_id": {"type": "string"},
                    "strength": {
                        "type": "string",
                        "enum": ["primary", "secondary", "tangential"],
                    },
                    "why": {"type": "string"},
                },
                "required": ["discipline_id", "strength", "why"],
                "additionalProperties": False,
            },
            "maxItems": 4,
        },
        "new_candidate": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "proposed_name_ru": {"type": "string"},
                        "proposed_name_en": {"type": "string"},
                        "why_existing_insufficient": {"type": "string"},
                        "proposed_legitimate_objects": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 8,
                        },
                    },
                    "required": [
                        "proposed_name_ru",
                        "proposed_name_en",
                        "why_existing_insufficient",
                        "proposed_legitimate_objects",
                    ],
                    "additionalProperties": False,
                },
            ]
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
        "reasoning": {"type": "string"},
    },
    "required": ["matched", "new_candidate", "confidence", "reasoning"],
    "additionalProperties": False,
}


def validate_discipline_match(data: dict) -> list[str]:
    warnings: list[str] = []
    matched = data.get("matched") or []
    if len(matched) > 4:
        warnings.append("matched has more than 4 disciplines (rule cap = 4)")
    seen_ids: set[str] = set()
    for m in matched:
        did = m.get("discipline_id")
        if did in seen_ids:
            warnings.append(f"duplicate discipline_id in matched: {did}")
        seen_ids.add(did)
    return warnings


DISCIPLINE_MATCHING_FAMILY = {
    "family_id": "discipline_matching_v1",
    "agent_role_id": "discipline_matcher",
    "version": "1.0.0",
    "system_prompt": DISCIPLINE_MATCHING_SYSTEM,
    "user_prompt_template": DISCIPLINE_MATCHING_USER_TEMPLATE,
    "output_schema": DISCIPLINE_MATCHING_OUTPUT_SCHEMA,
    "validator": validate_discipline_match,
}
