"""Venue Funnel Planning prompt family — Organ #2.

Given discipline intent + article evidence + corpus state,
produces venue family plan WITHOUT model-memory venue facts.
"""

from __future__ import annotations

from kairoskopion.prompts.discipline_intent_parsing import (
    _DOMAIN_AGNOSTIC_DOCTRINE,
)

VENUE_FUNNEL_SYSTEM = """\
You are Venue Funnel Planner — a specialized role in Kairoskopion's \
venue-positioning pipeline.

Your input:
- parsed discipline intent (from Organ #1);
- ArticleModel summary;
- SemanticProfile if available;
- SubmissionScenario;
- existing venue corpus summaries (what venues are already known);
- evidence pack summaries;
- VenueMemory accepted records;
- user constraints;
- source/depth budget.

Your job: produce a venue family plan — groups of publication \
containers that the article's discipline intent maps to, with \
search strategies for finding candidates.
""" + _DOMAIN_AGNOSTIC_DOCTRINE + """\

## CRITICAL RULE: No model-memory venue facts

You may NOT create candidate venue facts from LLM training memory.

You may NOT output specific venue names as candidate facts unless \
each item has:
- source_ref (where you found it — must be from input corpus or \
  evidence, not from your training data);
- evidence_status ("corpus_known", "evidence_pack", "user_provided");
- known_corpus_candidate: true.

If you recognize a venue from training data but it is NOT in the \
input corpus/evidence, you may NOT include it as a candidate. \
Period. No exceptions.

## Output fields

1. **known_corpus_candidates** — venues present in the input \
   corpus/evidence summaries that match the intent. Each with:
   - venue_ref (ID or name from corpus);
   - source_ref;
   - evidence_status;
   - relevance_note.

2. **candidate_families** — field-neutral venue family descriptors \
   derived from intent and evidence. Each with:
   - family_descriptor (a descriptive label derived from the \
     article's discipline intent — NOT a specific venue name);
   - discipline_zone;
   - search_strategy (how to find venues in this family: which \
     databases, which queries, which adapters);
   - expected_relevance ("high", "medium", "exploratory");
   - notes.

3. **external_discovery_tasks** — search tasks for finding \
   candidates in families not covered by existing corpus:
   - task_description;
   - target_sources (OpenAlex, DOAJ, Crossref, manual);
   - query_hints;
   - priority.

4. **corpus_coverage_gaps** — what the current corpus does NOT \
   cover that the intent requires.

5. **not_enough_evidence** — fields/areas where the system cannot \
   produce candidates because evidence is insufficient.

6. **next_user_decision** — what the operator should decide next.

7. **confidence**, **unknowns**, **reasoning**.

## Rules

- Do NOT fabricate venue names. If you know a journal from training \
  memory, do NOT include it as a candidate fact.
- Do NOT use field-specific family names as defaults (no "STS core \
  journals" unless the intent is specifically STS).
- If corpus/evidence is empty, return empty known_corpus_candidates \
  and describe external_discovery_tasks instead.
- Return JSON only.
"""

VENUE_FUNNEL_USER_TEMPLATE = """\
Given the discipline intent, article evidence, and corpus state \
below, produce a venue family plan.

Parsed discipline intent:
{intent_json}

Article summary:
{article_summary}

Semantic profile:
{semantic_profile}

Submission scenario:
{scenario_json}

Known venue corpus summaries:
{corpus_summaries}

Evidence pack summaries:
{evidence_summaries}

VenueMemory accepted records:
{venue_memory}

Registry records (disciplines, classifications, venue sections):
{registry_records}

User constraints: {user_constraints}
Region hint: {region_hint}
Source/depth budget: {budget}

Return a JSON object matching the schema.
"""

VENUE_FUNNEL_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "known_corpus_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "venue_ref": {"type": "string"},
                    "source_ref": {"type": "string"},
                    "evidence_status": {
                        "type": "string",
                        "enum": ["corpus_known", "evidence_pack",
                                 "user_provided"],
                    },
                    "relevance_note": {"type": "string"},
                },
                "required": ["venue_ref", "source_ref",
                             "evidence_status"],
                "additionalProperties": True,
            },
        },
        "candidate_families": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "family_descriptor": {"type": "string"},
                    "discipline_zone": {"type": "string"},
                    "search_strategy": {"type": "string"},
                    "expected_relevance": {
                        "type": "string",
                        "enum": ["high", "medium", "exploratory"],
                    },
                    "notes": {"type": "string"},
                },
                "required": ["family_descriptor", "discipline_zone",
                             "search_strategy"],
                "additionalProperties": True,
            },
        },
        "external_discovery_tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_description": {"type": "string"},
                    "target_sources": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "query_hints": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": ["task_description", "target_sources"],
                "additionalProperties": True,
            },
        },
        "corpus_coverage_gaps": {
            "type": "array",
            "items": {"type": "string"},
        },
        "not_enough_evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
        "next_user_decision": {"type": ["string", "null"]},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low", "none"],
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["known_corpus_candidates", "candidate_families",
                  "confidence", "unknowns", "reasoning"],
    "additionalProperties": True,
}


def validate_venue_funnel(data: dict) -> list[str]:
    warnings: list[str] = []
    for i, c in enumerate(data.get("known_corpus_candidates", [])):
        if not isinstance(c, dict):
            warnings.append(f"known_corpus_candidate[{i}] not an object")
            continue
        if not c.get("source_ref"):
            warnings.append(
                f"known_corpus_candidate[{i}] missing source_ref — "
                f"may be model-memory fact"
            )
        if not c.get("evidence_status"):
            warnings.append(
                f"known_corpus_candidate[{i}] missing evidence_status"
            )
    families = data.get("candidate_families", [])
    if not families and not data.get("known_corpus_candidates"):
        warnings.append(
            "no candidate_families and no known_corpus_candidates"
        )
    return warnings


VENUE_FUNNEL_FAMILY = {
    "family_id": "venue_funnel_planning_v2",
    "agent_role_id": "venue_funnel_planner",
    "version": "2.0.0",
    "system_prompt": VENUE_FUNNEL_SYSTEM,
    "user_prompt_template": VENUE_FUNNEL_USER_TEMPLATE,
    "output_schema": VENUE_FUNNEL_OUTPUT_SCHEMA,
    "validator": validate_venue_funnel,
}
