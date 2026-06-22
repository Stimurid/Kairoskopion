"""Locomotive pass: universal LLM attempt diagnostics.

Every semantic organ (RiskOfficer / RewritePlanner / CitationPlanner /
MismatchNarrator) should attach an ``attempt_diagnostics`` dict to its
output object so the operator can see WHY a section fell back to
needs_llm — without raw LLM output ever leaking.

Pure helper. No I/O. No imports beyond stdlib.

Doctrine:
  - Never include raw LLM output.
  - Never include stack traces.
  - Never include API keys, base URLs, or model parameters.
  - Only stable category codes + short redacted summaries.
"""

from __future__ import annotations

from typing import Any

# Provider status codes
PROVIDER_NOT_CONFIGURED = "not_configured"
PROVIDER_CALLED_OK = "called_ok"
PROVIDER_NETWORK_ERROR = "network_error"
PROVIDER_TIMEOUT = "timeout"
PROVIDER_EXCEPTION = "exception"

# Parse status codes (mirrors json_repair taxonomy)
PARSE_NOT_ATTEMPTED = "not_attempted"
PARSE_OK = "parsed_ok"
PARSE_REPAIRED_OK = "repaired_ok"
PARSE_INVALID_JSON = "invalid_json"
PARSE_REPAIR_FAILED = "repair_failed"
PARSE_SCHEMA_VALIDATION_FAILED = "schema_validation_failed"

# Schema error categories
SCHEMA_OK = "ok"
SCHEMA_MISSING_REQUIRED = "missing_required"
SCHEMA_WRONG_TOP_LEVEL = "wrong_top_level_shape"
SCHEMA_TYPE_MISMATCH = "type_mismatch"
SCHEMA_UNKNOWN = "unknown"

# Adapter status (after parse OK, agent-side mapping to dataclass)
ADAPTER_OK = "ok"
ADAPTER_DROPPED_INVALID_ITEMS = "dropped_invalid_items"
ADAPTER_EMPTY_AFTER_FILTER = "empty_after_filter"
ADAPTER_NOT_RUN = "not_run"

# Fallback reasons
FALLBACK_NONE = "none"
FALLBACK_PROVIDER_UNAVAILABLE = "provider_unavailable"
FALLBACK_PARSE_FAILED = "parse_failed"
FALLBACK_SCHEMA_FAILED = "schema_failed"
FALLBACK_ADAPTER_FAILED = "adapter_failed"
FALLBACK_EXCEPTION = "exception"
FALLBACK_NO_MISMATCH = "no_input_mismatch"

# Object-level semantic status (mirrors semantic_provenance.SEMANTIC_STATUS_*)
SEMANTIC_LLM_GROUNDED = "llm_grounded"
SEMANTIC_LLM_GROUNDED_PARTIAL = "llm_grounded_partial"
SEMANTIC_NEEDS_LLM = "needs_llm"
SEMANTIC_STRUCTURAL_ONLY = "structural_only"


def _redact_error(exc: BaseException | None, max_chars: int = 140) -> str | None:
    if exc is None:
        return None
    msg = str(exc)
    # Strip URLs, keys, paths
    import re
    msg = re.sub(r"https?://\S+", "<url>", msg)
    msg = re.sub(r"sk-[A-Za-z0-9_-]+", "<key>", msg)
    msg = re.sub(r"/[A-Za-z]:[\\/][^\s'\"]+", "<path>", msg)
    msg = re.sub(r"/(home|opt|var|etc|tmp|root)/\S+", "<path>", msg)
    # Truncate
    if len(msg) > max_chars:
        msg = msg[:max_chars] + "…"
    return f"{type(exc).__name__}: {msg}"


def build_diagnostics(
    agent_role: str,
    model_role: str | None,
    call_attempted: bool,
    call_completed: bool,
    parse_status: str | None,
    schema_error_category: str | None,
    repair_attempted: bool,
    repair_status: str | None,
    adapter_status: str,
    fallback_reason: str,
    semantic_status: str,
    exception: BaseException | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a redacted diagnostic dict for a semantic organ.

    Pure function. No I/O. Always returns a stable shape.
    """
    diag: dict[str, Any] = {
        "agent_role": agent_role,
        "model_role": model_role,
        "provider_status": (
            PROVIDER_CALLED_OK if call_completed
            else PROVIDER_EXCEPTION if exception is not None
            else PROVIDER_NETWORK_ERROR if call_attempted
            else PROVIDER_NOT_CONFIGURED
        ),
        "call_attempted": bool(call_attempted),
        "call_completed": bool(call_completed),
        "parse_status": parse_status or PARSE_NOT_ATTEMPTED,
        "schema_error_category": schema_error_category or SCHEMA_OK,
        "repair_attempted": bool(repair_attempted),
        "repair_status": repair_status,
        "adapter_status": adapter_status,
        "fallback_reason": fallback_reason,
        "semantic_status": semantic_status,
        "redacted_error_summary": _redact_error(exception),
    }
    if extra:
        # Only allow safe extra fields
        for k, v in extra.items():
            if k in diag:
                continue
            kl = k.lower()
            if any(x in kl for x in ("raw", "trace", "secret", "key", "token")):
                continue
            diag[k] = v
    return diag


def diagnostics_provider_unavailable(
    agent_role: str, model_role: str | None,
) -> dict[str, Any]:
    return build_diagnostics(
        agent_role=agent_role,
        model_role=model_role,
        call_attempted=False,
        call_completed=False,
        parse_status=PARSE_NOT_ATTEMPTED,
        schema_error_category=SCHEMA_OK,
        repair_attempted=False,
        repair_status=None,
        adapter_status=ADAPTER_NOT_RUN,
        fallback_reason=FALLBACK_PROVIDER_UNAVAILABLE,
        semantic_status=SEMANTIC_NEEDS_LLM,
    )


def diagnostics_exception(
    agent_role: str, model_role: str | None, exc: BaseException,
) -> dict[str, Any]:
    return build_diagnostics(
        agent_role=agent_role,
        model_role=model_role,
        call_attempted=True,
        call_completed=False,
        parse_status=PARSE_NOT_ATTEMPTED,
        schema_error_category=SCHEMA_OK,
        repair_attempted=False,
        repair_status=None,
        adapter_status=ADAPTER_NOT_RUN,
        fallback_reason=FALLBACK_EXCEPTION,
        semantic_status=SEMANTIC_NEEDS_LLM,
        exception=exc,
    )


def diagnostics_parse_or_schema_failed(
    agent_role: str, model_role: str | None,
    parse_status: str, repair_steps: list[str] | None,
) -> dict[str, Any]:
    schema_cat = SCHEMA_OK
    if parse_status == PARSE_SCHEMA_VALIDATION_FAILED:
        schema_cat = SCHEMA_UNKNOWN
    return build_diagnostics(
        agent_role=agent_role,
        model_role=model_role,
        call_attempted=True,
        call_completed=True,
        parse_status=parse_status,
        schema_error_category=schema_cat,
        repair_attempted=bool(repair_steps),
        repair_status=("failed" if repair_steps else None),
        adapter_status=ADAPTER_NOT_RUN,
        fallback_reason=(
            FALLBACK_SCHEMA_FAILED if parse_status == PARSE_SCHEMA_VALIDATION_FAILED
            else FALLBACK_PARSE_FAILED
        ),
        semantic_status=SEMANTIC_NEEDS_LLM,
    )


def diagnostics_ok(
    agent_role: str, model_role: str | None,
    semantic_status: str = SEMANTIC_LLM_GROUNDED,
    adapter_status: str = ADAPTER_OK,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_diagnostics(
        agent_role=agent_role,
        model_role=model_role,
        call_attempted=True,
        call_completed=True,
        parse_status=PARSE_OK,
        schema_error_category=SCHEMA_OK,
        repair_attempted=False,
        repair_status=None,
        adapter_status=adapter_status,
        fallback_reason=FALLBACK_NONE,
        semantic_status=semantic_status,
        extra=extra,
    )
