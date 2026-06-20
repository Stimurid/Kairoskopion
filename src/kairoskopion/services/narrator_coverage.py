"""V2-B1: MismatchNarrator coverage classifier (pure, testable).

Given the MismatchNarrator agent's output_entity and the list of axis
names the chain *sent in*, compute a structured ``narrator_coverage``
dict that distinguishes the failure modes which were previously
collapsed into a single "0/N filled" number:

  - ``not_attempted``         LLM was not called (provider missing).
  - ``filled``                Every axis got a non-empty venue_side.
  - ``partial``               Some axes filled, some not.
  - ``empty_valid_unknown``   Narratives returned for every axis but
                              every venue_side was empty — model
                              honestly refused (likely valid unknowns
                              when venue text lacks expectations).
  - ``empty_llm_output``      ``narratives`` list was empty / absent.
  - ``missing_axes``          ``narratives`` returned, but none of the
                              input axes appeared in them.
  - ``axis_match_failure``    Narratives returned with axes that don't
                              exist in the input mismatch list (variant
                              spellings, hallucinated axes).
  - ``parse_failed``          ``parse_status`` indicates parser/schema
                              rejection. attempt metadata sourced.
  - ``provider_error``        Network / 5xx / timeout etc.
  - ``input_insufficient``    Input mismatch list was empty.
  - ``unknown``               None of the above patterns matched.

Also returns per-axis ``narrative_status`` strings which the chain
writes onto each mismatch dict so the dossier UI hint can stay
truthful per-row.

Pure function. No I/O. No raw LLM output retained. No model params.
"""

from __future__ import annotations

from typing import Any

STATUS_NOT_ATTEMPTED = "not_attempted"
STATUS_FILLED = "filled"
STATUS_PARTIAL = "partial"
STATUS_EMPTY_VALID_UNKNOWN = "empty_valid_unknown"
STATUS_EMPTY_LLM_OUTPUT = "empty_llm_output"
STATUS_MISSING_AXES = "missing_axes"
STATUS_AXIS_MATCH_FAILURE = "axis_match_failure"
STATUS_PARSE_FAILED = "parse_failed"
STATUS_PROVIDER_ERROR = "provider_error"
STATUS_INPUT_INSUFFICIENT = "input_insufficient"
STATUS_UNKNOWN = "unknown"

PER_AXIS_LLM_FILLED = "llm_filled"
PER_AXIS_NEEDS_LLM = "needs_llm"
PER_AXIS_UNKNOWN_DUE_TO_VENUE = "unknown_due_to_venue_evidence"
PER_AXIS_MISSING_FROM_LLM = "missing_from_llm_output"
PER_AXIS_UNMATCHED = "axis_unmatched"
PER_AXIS_PARSE_FAILED = "parse_failed"
PER_AXIS_PROVIDER_ERROR = "provider_error"


def _is_filled(narrative: dict[str, Any]) -> bool:
    """A narrative counts as filled iff venue_side is a non-empty string
    AFTER stripping. This matches ``enrich_mismatch_map_in_place``'s
    overwrite rule — we only count narratives that would actually flow
    into the mismatch.
    """
    if not isinstance(narrative, dict):
        return False
    return bool((narrative.get("venue_side") or "").strip())


def classify_narrator_coverage(
    input_axes: list[str],
    narrator_output_entity: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute coverage summary from narrator agent output_entity.

    Args:
        input_axes: list of axis names from the deterministic mismatch
            map (the chain's source of truth).
        narrator_output_entity: ``output_entity`` dict returned by
            ``MismatchNarratorAgent.execute`` /
            ``execute_deterministic``. May be None when the narrator
            wasn't reached.

    Returns:
        Diagnostic dict with the keys documented at module top. Never
        contains raw LLM output, stack traces, or secrets.
    """
    total = len(input_axes)
    if narrator_output_entity is None:
        return {
            "narrator_attempted": False,
            "narrator_status": STATUS_NOT_ATTEMPTED,
            "filled_count": 0,
            "total_count": total,
            "missing_axes": list(input_axes),
            "unmatched_axes": [],
            "parse_status": None,
            "used_model": None,
            "latency_ms": None,
            "empty_reason": None,
        }

    attempt = narrator_output_entity.get("extraction_attempt") or {}
    narratives = narrator_output_entity.get("narratives") or []
    if not isinstance(narratives, list):
        narratives = []

    attempted = bool(attempt.get("llm_attempted"))
    parse_status = attempt.get("parse_status")
    fallback_reason = attempt.get("fallback_reason")
    used_model = attempt.get("llm_model")
    latency_ms = attempt.get("llm_latency_ms")

    input_set = set(input_axes)
    returned_axes = [
        n.get("axis", "") for n in narratives if isinstance(n, dict)
    ]
    by_axis: dict[str, dict[str, Any]] = {
        a: n
        for a, n in zip(returned_axes, narratives)
        if isinstance(n, dict) and a
    }
    matched_axes = [a for a in returned_axes if a in input_set]
    unmatched_axes = [a for a in returned_axes if a and a not in input_set]
    missing_axes = [a for a in input_axes if a not in by_axis]
    filled = sum(1 for n in narratives if _is_filled(n))
    matched_filled = sum(
        1 for a in matched_axes if _is_filled(by_axis.get(a, {}))
    )

    # Classification order matters: most-specific failure first.
    empty_reason: str | None = None
    if total == 0:
        status = STATUS_INPUT_INSUFFICIENT
    elif not attempted and fallback_reason == "llm_unavailable":
        status = STATUS_NOT_ATTEMPTED
    elif fallback_reason == "provider_error":
        status = STATUS_PROVIDER_ERROR
        empty_reason = "provider error during narrator call"
    elif fallback_reason == "schema_validation_failed" or parse_status in (
        "schema_validation_failed",
        "parse_failed",
    ):
        status = STATUS_PARSE_FAILED
        empty_reason = "narrator output failed schema validation"
    elif not narratives:
        status = STATUS_EMPTY_LLM_OUTPUT
        empty_reason = "narrator returned an empty narratives list"
    elif not matched_axes and unmatched_axes:
        status = STATUS_AXIS_MATCH_FAILURE
        empty_reason = (
            "narrator returned narratives but none of the axis names "
            "matched the input mismatch axes"
        )
    elif not matched_axes:
        status = STATUS_MISSING_AXES
        empty_reason = "narrator returned no narratives for any input axis"
    elif matched_filled == 0:
        # Narrator returned narratives for input axes but every
        # venue_side was empty/blank. Model honestly refused, so this
        # is most likely valid unknown — the venue text didn't support
        # any expectation.
        status = STATUS_EMPTY_VALID_UNKNOWN
        empty_reason = (
            "narrator returned narratives for the input axes but every "
            "venue_side was empty — likely valid unknown (venue text "
            "lacks explicit expectations on these axes)"
        )
    elif matched_filled == len(input_axes):
        status = STATUS_FILLED
    elif 0 < matched_filled < len(input_axes):
        status = STATUS_PARTIAL
    else:
        status = STATUS_UNKNOWN

    return {
        "narrator_attempted": attempted,
        "narrator_status": status,
        "filled_count": int(filled),
        "total_count": int(total),
        "missing_axes": missing_axes,
        "unmatched_axes": unmatched_axes,
        "parse_status": parse_status,
        "used_model": used_model,
        "latency_ms": latency_ms,
        "empty_reason": empty_reason,
    }


def per_axis_status(
    axis: str,
    input_axes: list[str],
    narrator_output_entity: dict[str, Any] | None,
    coverage_status: str,
) -> str:
    """Honest per-axis narrative status for the dossier UI hint."""
    if narrator_output_entity is None:
        return PER_AXIS_NEEDS_LLM
    narratives = narrator_output_entity.get("narratives") or []
    if not isinstance(narratives, list):
        return PER_AXIS_NEEDS_LLM
    by_axis = {
        n.get("axis"): n
        for n in narratives
        if isinstance(n, dict) and n.get("axis")
    }
    if coverage_status == STATUS_PROVIDER_ERROR:
        return PER_AXIS_PROVIDER_ERROR
    if coverage_status == STATUS_PARSE_FAILED:
        return PER_AXIS_PARSE_FAILED
    n = by_axis.get(axis)
    if n is None:
        if axis in input_axes:
            return PER_AXIS_MISSING_FROM_LLM
        return PER_AXIS_UNMATCHED
    if _is_filled(n):
        return PER_AXIS_LLM_FILLED
    # Narrative returned but venue_side empty.
    if coverage_status == STATUS_EMPTY_VALID_UNKNOWN:
        return PER_AXIS_UNKNOWN_DUE_TO_VENUE
    return PER_AXIS_NEEDS_LLM
