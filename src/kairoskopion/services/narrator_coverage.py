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


# V2-B2: parse-failure category taxonomy. Stable strings safe to ship.
# Every value is mapped from already-redacted ``extraction_attempt``
# fields (parse_status / validation_errors_summary / repair_steps) —
# no raw LLM output is read or exposed.
PARSE_FAIL_INVALID_JSON = "invalid_json"
PARSE_FAIL_REPAIR_FAILED = "repair_failed"
PARSE_FAIL_SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
PARSE_FAIL_MISSING_REQUIRED = "missing_required"
PARSE_FAIL_TYPE_MISMATCH = "type_mismatch"
PARSE_FAIL_ENUM_MISMATCH = "enum_mismatch"
PARSE_FAIL_WRONG_TOP_LEVEL_SHAPE = "wrong_top_level_shape"
PARSE_FAIL_MISSING_NARRATIVES_KEY = "missing_narratives_key"
PARSE_FAIL_NARRATIVES_NOT_LIST = "narratives_not_list"
PARSE_FAIL_NARRATIVE_ITEM_NOT_OBJECT = "narrative_item_not_object"
PARSE_FAIL_AXIS_MISSING = "axis_missing"
PARSE_FAIL_AXIS_NOT_STRING = "axis_not_string"
PARSE_FAIL_EXTRA_PROPERTY = "extra_property"
PARSE_FAIL_EMPTY_AFTER_REPAIR = "empty_after_repair"
PARSE_FAIL_UNKNOWN = "unknown"


_MISSING_REQUIRED_PREFIX = "missing required field:"
_WRONG_TOP_LEVEL_MARKER = "top-level value is not an object"


def _extract_missing_path(err: str) -> str | None:
    """Pull the field name from a 'missing required field: X' message.

    Errors come from json_repair._schema_required_present which only
    ever emits this exact prefix — no raw model text is read.
    """
    if not err:
        return None
    low = err.lower().strip()
    if low.startswith(_MISSING_REQUIRED_PREFIX):
        return err[len(_MISSING_REQUIRED_PREFIX):].strip() or None
    return None


def classify_parse_failure(
    attempt: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify narrator parse/repair/schema failure from already-safe
    ``extraction_attempt`` metadata into the V2-B2 taxonomy.

    Returns a dict with keys:
      - ``parse_failure_category``: stable string from PARSE_FAIL_*
      - ``parse_failure_reason``: short human-readable reason (no raw
        LLM output)
      - ``schema_failure_path``: field path when known (e.g.
        "narratives"), else None
      - ``schema_failure_rule``: rule name when knowable, else None
      - ``repair_failure_stage``: last repair step name attempted, else
        None
      - ``repair_steps_attempted``: passthrough of repair_steps (already
        safe stable names from json_repair, never raw text)

    Returns all-None / empty values when attempt is None or parse
    succeeded. Pure function. No I/O.
    """
    blank = {
        "parse_failure_category": None,
        "parse_failure_reason": None,
        "schema_failure_path": None,
        "schema_failure_rule": None,
        "repair_failure_stage": None,
        "repair_steps_attempted": [],
    }
    if not isinstance(attempt, dict):
        return blank

    parse_status = attempt.get("parse_status") or ""
    fallback_reason = attempt.get("fallback_reason") or ""
    repair_steps = list(attempt.get("repair_steps") or [])
    errors = list(attempt.get("validation_errors_summary") or [])

    # No failure to classify.
    if parse_status in ("parsed_ok", "repaired_ok", "not_attempted"):
        return blank
    if not parse_status and fallback_reason in (
        "", "not_applicable", "llm_unavailable",
    ):
        return blank

    repair_stage = repair_steps[-1] if repair_steps else None

    # 1) Schema-validation failure: extract path/rule when we can.
    if parse_status == "schema_validation_failed" or (
        fallback_reason == "schema_validation_failed"
    ):
        # Top-level shape error has a specific marker
        for e in errors:
            if _WRONG_TOP_LEVEL_MARKER in (e or "").lower():
                return {
                    **blank,
                    "parse_failure_category": PARSE_FAIL_WRONG_TOP_LEVEL_SHAPE,
                    "parse_failure_reason": (
                        "narrator returned a non-object at the top level "
                        "(schema requires an object with 'narratives')"
                    ),
                    "schema_failure_rule": "type",
                    "repair_failure_stage": repair_stage,
                    "repair_steps_attempted": repair_steps,
                }
        # Missing-required cases
        for e in errors:
            path = _extract_missing_path(e or "")
            if path is None:
                continue
            if path == "narratives":
                return {
                    **blank,
                    "parse_failure_category": PARSE_FAIL_MISSING_NARRATIVES_KEY,
                    "parse_failure_reason": (
                        "narrator output object lacked the required "
                        "'narratives' key"
                    ),
                    "schema_failure_path": "narratives",
                    "schema_failure_rule": "required",
                    "repair_failure_stage": repair_stage,
                    "repair_steps_attempted": repair_steps,
                }
            return {
                **blank,
                "parse_failure_category": PARSE_FAIL_MISSING_REQUIRED,
                "parse_failure_reason": (
                    f"narrator output missing required field '{path}'"
                ),
                "schema_failure_path": path,
                "schema_failure_rule": "required",
                "repair_failure_stage": repair_stage,
                "repair_steps_attempted": repair_steps,
            }
        # Generic schema failure with no path info
        return {
            **blank,
            "parse_failure_category": PARSE_FAIL_SCHEMA_VALIDATION_FAILED,
            "parse_failure_reason": (
                "narrator output failed JSON schema validation"
            ),
            "repair_failure_stage": repair_stage,
            "repair_steps_attempted": repair_steps,
        }

    # 2) Repair failed: parser tried bounded repairs and none parsed.
    if parse_status == "repair_failed" or fallback_reason == "repair_failed":
        if not repair_steps:
            # Parser saw nothing it could even attempt to repair.
            return {
                **blank,
                "parse_failure_category": PARSE_FAIL_EMPTY_AFTER_REPAIR,
                "parse_failure_reason": (
                    "narrator output could not be parsed and no repair "
                    "steps applied (likely empty or non-JSON content)"
                ),
                "repair_failure_stage": None,
                "repair_steps_attempted": [],
            }
        return {
            **blank,
            "parse_failure_category": PARSE_FAIL_REPAIR_FAILED,
            "parse_failure_reason": (
                "narrator output failed JSON parsing and all bounded "
                "repair attempts were rejected"
            ),
            "repair_failure_stage": repair_stage,
            "repair_steps_attempted": repair_steps,
        }

    # 3) Invalid JSON without repair attempted
    if parse_status == "invalid_json" or fallback_reason == "invalid_json":
        return {
            **blank,
            "parse_failure_category": PARSE_FAIL_INVALID_JSON,
            "parse_failure_reason": (
                "narrator output was not valid JSON and no repair was "
                "attempted"
            ),
            "repair_failure_stage": repair_stage,
            "repair_steps_attempted": repair_steps,
        }

    # 4) Provider error / timeout / unknown — narrator coverage classifier
    # already reports these at the chain level. Don't double-classify here.
    if fallback_reason in (
        "provider_error", "llm_timeout", "llm_unavailable",
    ):
        return blank

    return {
        **blank,
        "parse_failure_category": PARSE_FAIL_UNKNOWN,
        "parse_failure_reason": (
            f"narrator parse failed with parse_status='{parse_status}' "
            f"fallback_reason='{fallback_reason}'"
        ),
        "repair_failure_stage": repair_stage,
        "repair_steps_attempted": repair_steps,
    }


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
            # V2-B2 redacted parse-failure detail (always absent here)
            "parse_failure_category": None,
            "parse_failure_reason": None,
            "schema_failure_path": None,
            "schema_failure_rule": None,
            "repair_failure_stage": None,
            "repair_steps_attempted": [],
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
    elif fallback_reason in (
        "schema_validation_failed", "repair_failed", "invalid_json",
    ) or parse_status in (
        "schema_validation_failed", "parse_failed",
        "repair_failed", "invalid_json",
    ):
        status = STATUS_PARSE_FAILED
        empty_reason = "narrator output failed parsing or schema validation"
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

    parse_failure = classify_parse_failure(attempt)
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
        # V2-B2: redacted parse-failure detail. All fields derived from
        # already-safe extraction_attempt metadata — no raw LLM output.
        "parse_failure_category": parse_failure["parse_failure_category"],
        "parse_failure_reason": parse_failure["parse_failure_reason"],
        "schema_failure_path": parse_failure["schema_failure_path"],
        "schema_failure_rule": parse_failure["schema_failure_rule"],
        "repair_failure_stage": parse_failure["repair_failure_stage"],
        "repair_steps_attempted": parse_failure["repair_steps_attempted"],
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
