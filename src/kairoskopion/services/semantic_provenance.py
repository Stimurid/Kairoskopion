"""Semantic provenance taxonomy (Round II audit).

Stable origin codes that every meaning-bearing field on a dossier
object should be tagged with so the operator (and UI) can see, per
field, what produced the content.

Allowed values, ordered from most-grounded to least:
  - llm:                       LLM agent produced this string/value.
  - source_fact_direct:        Direct extraction from supplied raw
                               text (DOI regex, H1 line, an explicit
                               ISSN, etc.). The string is taken
                               verbatim from a source.
  - user_input:                Operator typed it (scenario fields).
  - structural_extraction:     Mechanical extraction from supplied
                               text by regex/parser without semantic
                               judgement (year, URL, reference count,
                               heading detection).
  - deterministic_aggregation: Pure rule-based derivation from
                               *already-tagged* upstream fields
                               (e.g. SubmissionPack.ready_status from
                               bibliography_profile.status + rewrite
                               effort + compliance missing_items).
                               No new semantic content introduced.
  - deterministic_heuristic:   Code-written semantic content from
                               heuristics. FORBIDDEN by the Round II
                               doctrine for citation ecology, mismatch
                               descriptions, mismatch actions, risk
                               semantics, rewrite suggestions,
                               compliance interpretation, submission
                               strategy. Marked here ONLY for
                               grandfathered fields that have not yet
                               been replaced by an LLM organ; UI must
                               surface them honestly.
  - needs_llm:                 Field is intentionally empty because
                               the LLM organ that should produce it
                               is not wired in this build. UI shows a
                               clear placeholder.
  - unknown:                   Origin not determinable.

Semantic status (object-level):
  - llm_grounded:               Semantic content present and LLM-produced.
  - structural_only:            Object carries only structural/factual
                                content (counts, statuses, IDs). No
                                semantic claim.
  - deterministic_heuristic_only: Object's semantic fields are all
                                deterministic_heuristic — UI MUST flag
                                this.
  - needs_llm:                  Object's semantic fields are all empty
                                with needs_llm origin; LLM organ not
                                wired.
  - mixed:                      Object combines LLM + structural; OK.
  - not_built:                  Object absent.

Pure module. No I/O. No imports beyond stdlib.
"""

from __future__ import annotations

# Origin codes
ORIGIN_LLM = "llm"
ORIGIN_SOURCE_FACT_DIRECT = "source_fact_direct"
ORIGIN_USER_INPUT = "user_input"
ORIGIN_STRUCTURAL_EXTRACTION = "structural_extraction"
ORIGIN_DETERMINISTIC_AGGREGATION = "deterministic_aggregation"
ORIGIN_DETERMINISTIC_HEURISTIC = "deterministic_heuristic"
ORIGIN_NEEDS_LLM = "needs_llm"
ORIGIN_UNKNOWN = "unknown"

ALLOWED_ORIGINS = frozenset({
    ORIGIN_LLM,
    ORIGIN_SOURCE_FACT_DIRECT,
    ORIGIN_USER_INPUT,
    ORIGIN_STRUCTURAL_EXTRACTION,
    ORIGIN_DETERMINISTIC_AGGREGATION,
    ORIGIN_DETERMINISTIC_HEURISTIC,
    ORIGIN_NEEDS_LLM,
    ORIGIN_UNKNOWN,
})

# Object-level semantic status
SEMANTIC_STATUS_LLM_GROUNDED = "llm_grounded"
SEMANTIC_STATUS_STRUCTURAL_ONLY = "structural_only"
SEMANTIC_STATUS_DETERMINISTIC_HEURISTIC_ONLY = "deterministic_heuristic_only"
SEMANTIC_STATUS_NEEDS_LLM = "needs_llm"
SEMANTIC_STATUS_MIXED = "mixed"
SEMANTIC_STATUS_NOT_BUILT = "not_built"

ALLOWED_SEMANTIC_STATUSES = frozenset({
    SEMANTIC_STATUS_LLM_GROUNDED,
    SEMANTIC_STATUS_STRUCTURAL_ONLY,
    SEMANTIC_STATUS_DETERMINISTIC_HEURISTIC_ONLY,
    SEMANTIC_STATUS_NEEDS_LLM,
    SEMANTIC_STATUS_MIXED,
    SEMANTIC_STATUS_NOT_BUILT,
})


def aggregate_semantic_status(field_origins: dict[str, str]) -> str:
    """Derive the object-level semantic_status from per-field origins.

    Pure function. Empty dict → not_built.
    """
    if not field_origins:
        return SEMANTIC_STATUS_NOT_BUILT
    origins = set(field_origins.values())
    if ORIGIN_LLM in origins and (origins - {ORIGIN_LLM, ORIGIN_STRUCTURAL_EXTRACTION,
                                              ORIGIN_DETERMINISTIC_AGGREGATION,
                                              ORIGIN_SOURCE_FACT_DIRECT,
                                              ORIGIN_USER_INPUT}):
        return SEMANTIC_STATUS_MIXED
    if origins == {ORIGIN_LLM} or origins <= {
        ORIGIN_LLM, ORIGIN_STRUCTURAL_EXTRACTION,
        ORIGIN_DETERMINISTIC_AGGREGATION, ORIGIN_SOURCE_FACT_DIRECT,
        ORIGIN_USER_INPUT,
    } and ORIGIN_LLM in origins:
        return SEMANTIC_STATUS_LLM_GROUNDED
    if origins <= {
        ORIGIN_STRUCTURAL_EXTRACTION, ORIGIN_DETERMINISTIC_AGGREGATION,
        ORIGIN_SOURCE_FACT_DIRECT, ORIGIN_USER_INPUT,
    }:
        return SEMANTIC_STATUS_STRUCTURAL_ONLY
    if ORIGIN_DETERMINISTIC_HEURISTIC in origins:
        return SEMANTIC_STATUS_DETERMINISTIC_HEURISTIC_ONLY
    if origins == {ORIGIN_NEEDS_LLM} or origins <= {
        ORIGIN_NEEDS_LLM, ORIGIN_STRUCTURAL_EXTRACTION,
        ORIGIN_DETERMINISTIC_AGGREGATION,
    } and ORIGIN_NEEDS_LLM in origins:
        return SEMANTIC_STATUS_NEEDS_LLM
    return SEMANTIC_STATUS_MIXED
