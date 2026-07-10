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
- A new_candidate must be a real academic discipline / sub-discipline, \
  not an article topic. Distinguish between a topic (narrow research \
  subject) and a discipline (community with shared methods, objects, \
  and publication norms).

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


# ---------------------------------------------------------------------------
# v2: open-field, registry-first, no field examples
# ---------------------------------------------------------------------------

from .discipline_intent_parsing import _OPEN_FIELD_DOCTRINE

DISCIPLINE_MATCHING_V2_SYSTEM = """\
You are Discipline Matcher — an agent in Kairoskopion's disciplinary \
landscape registry.
""" + _OPEN_FIELD_DOCTRINE + """

Your job: given a short summary of an article (or a manuscript opener) \
and a list of candidate disciplines from the registry, decide:

1. Which of these candidates the article would legitimately be read in.
2. Whether the registry is MISSING a discipline that should clearly \
   exist for this article. If yes, propose ONE ``new_candidate`` per \
   call, with a clear justification.

## Hard rules

- The candidates come from the registry. Each is summarized by its \
  legitimate_objects, canonical_questions, forms_of_evidence, and \
  what it does NOT admit. Read those.
- Do NOT match a discipline whose ``illegitimate_or_borderline_objects`` \
  exclude the article's object.
- Do NOT match more than 4 disciplines.
- A new_candidate must be evidently distinct from EVERY existing \
  candidate. If you can describe it as "a sub-area of X" or "an \
  application of Y", do not propose it.
- A new_candidate must be a real academic discipline / sub-discipline, \
  not an article topic. Distinguish between a topic (narrow research \
  subject) and a discipline (community with shared methods, objects, \
  and publication norms).
- Candidate disciplines come only from the registry candidate block. \
  If the registry is insufficient, return source_acquisition_needed \
  or new_candidate_provisional — do NOT produce canonical field facts \
  from model memory.

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
  - ``source_acquisition_needed`` — boolean, true if registry evidence \
    is insufficient to validate this candidate
- ``confidence`` ∈ ``high`` / ``medium`` / ``low``
- ``reasoning`` — one or two sentences in Russian, summary of decision

If there are NO viable matches AND no obvious missing discipline, \
return ``matched: []`` and ``new_candidate: null`` with a low \
confidence and a reasoning that says so. Do not invent a match to \
fill space.
"""

DISCIPLINE_MATCHING_V2_OUTPUT_SCHEMA = {
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
                        "source_acquisition_needed": {
                            "type": "boolean",
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

DISCIPLINE_MATCHING_V2_FAMILY = {
    "family_id": "discipline_matching_v2",
    "agent_role_id": "discipline_matcher",
    "version": "2.0.0",
    "system_prompt": DISCIPLINE_MATCHING_V2_SYSTEM,
    "user_prompt_template": DISCIPLINE_MATCHING_USER_TEMPLATE,
    "output_schema": DISCIPLINE_MATCHING_V2_OUTPUT_SCHEMA,
    "validator": validate_discipline_match,
}


# ---------------------------------------------------------------------------
# v3: 10-candidate ranked analysis with detailed rationale
# ---------------------------------------------------------------------------

DISCIPLINE_MATCHING_V3_SYSTEM = """\
You are Discipline Matcher — an agent in Kairoskopion's disciplinary \
landscape registry.
""" + _OPEN_FIELD_DOCTRINE + """

Your job: given a short summary of an article and a list of candidate \
disciplines from the registry, produce a RANKED LIST of exactly 10 \
discipline candidates, ordered from most to least relevant.

## Hard rules

- The candidates come from the registry. Each is summarized by its \
  legitimate_objects, canonical_questions, forms_of_evidence, and \
  what it does NOT admit. Read those carefully.
- Do NOT match a discipline whose ``illegitimate_or_borderline_objects`` \
  exclude the article's object.
- You MUST return exactly 10 candidates. If the registry has fewer \
  than 10, return all available candidates.
- Each candidate MUST have a detailed rationale of 7-10 complete \
  Russian sentences explaining WHY this discipline fits or does not \
  fit, what specific textual evidence supports the match, and what \
  contradicts it.
- Rank candidates by decreasing relevance. The first candidate is the \
  best disciplinary home for this article.
- A new_candidate must be evidently distinct from EVERY existing \
  candidate and must be a real academic discipline, not an article topic.

## Output rules

Return JSON with:
- ``matched`` — list of exactly 10 objects, each with:
  - ``discipline_id`` (from the candidates list, verbatim)
  - ``display_name`` — Russian display name of the discipline
  - ``strength`` ∈ ``primary`` / ``strong_adjacent`` / ``partial`` / ``tangential``
  - ``confidence`` ∈ ``high`` / ``medium`` / ``low``
  - ``relation_type_ru`` — one of: "основное дисциплинарное поле", \
    "сильное смежное соответствие", "частичное соответствие", \
    "слабое боковое соответствие"
  - ``why`` — 7-10 complete sentences in Russian. Explain: what makes \
    this discipline relevant, what specific textual features match, \
    what the article's object/method/vocabulary share with this \
    discipline's legitimate objects and canonical questions, and what \
    limits or contradicts the match.
  - ``supporting_evidence`` — list of 2-5 specific textual features \
    that support this match (terms, methods, objects, traditions)
  - ``contradicting_evidence`` — list of 0-3 features that weaken or \
    contradict this match
  - ``position_rationale`` — one sentence explaining why this candidate \
    is ranked above or below its neighbors
- ``new_candidate`` (or null) — same as v2
- ``confidence`` ∈ ``high`` / ``medium`` / ``low``
- ``reasoning`` — 3-5 sentences in Russian, summary of the overall \
  disciplinary positioning decision

If the registry has fewer than 10 candidates, return all available.
"""

DISCIPLINE_MATCHING_V3_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "matched": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "discipline_id": {"type": "string"},
                    "display_name": {"type": "string"},
                    "strength": {
                        "type": "string",
                        "enum": ["primary", "strong_adjacent", "partial", "tangential"],
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "relation_type_ru": {"type": "string"},
                    "why": {"type": "string"},
                    "supporting_evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "contradicting_evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "position_rationale": {"type": "string"},
                },
                "required": [
                    "discipline_id", "display_name", "strength",
                    "confidence", "relation_type_ru", "why",
                    "supporting_evidence", "contradicting_evidence",
                    "position_rationale",
                ],
            },
            "minItems": 1,
            "maxItems": 10,
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
                        "source_acquisition_needed": {
                            "type": "boolean",
                        },
                    },
                    "required": [
                        "proposed_name_ru",
                        "proposed_name_en",
                        "why_existing_insufficient",
                        "proposed_legitimate_objects",
                    ],
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
}


def validate_discipline_match_v3(data: dict) -> list[str]:
    warnings: list[str] = []
    matched = data.get("matched") or []
    if len(matched) < 1:
        warnings.append("matched is empty — expected up to 10 candidates")
    seen_ids: set[str] = set()
    for m in matched:
        did = m.get("discipline_id")
        if did in seen_ids:
            warnings.append(f"duplicate discipline_id: {did}")
        seen_ids.add(did)
        why = m.get("why", "")
        sentences = [s.strip() for s in why.split(".") if s.strip()]
        if len(sentences) < 5:
            warnings.append(
                f"{did}: rationale has {len(sentences)} sentences, expected 7-10"
            )
    return warnings


DISCIPLINE_MATCHING_V3_FAMILY = {
    "family_id": "discipline_matching_v3",
    "agent_role_id": "discipline_matcher",
    "version": "3.0.0",
    "system_prompt": DISCIPLINE_MATCHING_V3_SYSTEM,
    "user_prompt_template": DISCIPLINE_MATCHING_USER_TEMPLATE,
    "output_schema": DISCIPLINE_MATCHING_V3_OUTPUT_SCHEMA,
    "validator": validate_discipline_match_v3,
}
