"""Base agent shell — shared utilities for all agent shells.

Provides helpers for wrapping existing deterministic services as
agent-compatible shells with consistent error handling, unknown
propagation, and contract-only stub generation.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .contract import AgentInput, AgentOutput

logger = logging.getLogger(__name__)


@dataclass
class LLMAttemptOutcome:
    """Round III-F: structured envelope returned by try_llm_call_with_outcome.

    Replaces bare ``None`` so adapters can see WHY the call did not yield
    a strict-parsed dict and can attempt a safe alternative-key rescue.
    NEVER stores raw LLM content. Only structural fingerprints
    (length / sha256 hash prefix / top-level type & keys).
    """

    ok: bool = False
    parsed: Any | None = None
    loose_parsed: Any | None = None
    content_present: bool = False
    content_length: int = 0
    content_hash_prefix: str = ""
    redacted_top_level_type: str | None = None
    redacted_top_level_keys: list[str] = field(default_factory=list)
    provider_status: str = "not_called"
    parse_status: str = "not_attempted"
    parse_failure_category: str | None = None
    schema_error_category: str | None = None
    repair_attempted: bool = False
    repair_status: str | None = None
    fallback_reason: str | None = None
    model_role: str | None = None
    agent_role: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "content_present": self.content_present,
            "content_length": self.content_length,
            "content_hash_prefix": self.content_hash_prefix,
            "redacted_top_level_type": self.redacted_top_level_type,
            "redacted_top_level_keys": list(self.redacted_top_level_keys),
            "provider_status": self.provider_status,
            "parse_status": self.parse_status,
            "parse_failure_category": self.parse_failure_category,
            "schema_error_category": self.schema_error_category,
            "repair_attempted": self.repair_attempted,
            "repair_status": self.repair_status,
            "fallback_reason": self.fallback_reason,
            "model_role": self.model_role,
            "agent_role": self.agent_role,
        }


def _redacted_content_fingerprint(content: str | None) -> tuple[int, str]:
    if not content:
        return 0, ""
    h = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
    return len(content), h[:16]


def _redacted_shape(parsed: Any) -> tuple[str | None, list[str]]:
    if parsed is None:
        return None, []
    if isinstance(parsed, list):
        return "list", []
    if isinstance(parsed, dict):
        return "object", list(parsed.keys())[:12]
    return type(parsed).__name__, []


def service_output(
    entity_type: str,
    entity: dict[str, Any] | None,
    *,
    evidence_refs: list[str] | None = None,
    unknowns: list[str] | None = None,
    warnings: list[str] | None = None,
    confidence: str = "medium",
    evidence_status: str = "INFERENCE",
    trace_notes: list[str] | None = None,
) -> AgentOutput:
    """Build AgentOutput from a deterministic service result."""
    return AgentOutput(
        output_entity_type=entity_type,
        output_entity=entity or {},
        evidence_refs=evidence_refs or [],
        unknowns=unknowns or [],
        confidence=confidence,
        warnings=warnings or [],
        evidence_status=evidence_status,
        trace_notes=trace_notes or ["deterministic service call"],
    )


def contract_only_output(
    entity_type: str,
    reason: str,
    *,
    unknowns: list[str] | None = None,
) -> AgentOutput:
    """Build AgentOutput for a contract-only stub that cannot produce real data."""
    return AgentOutput(
        output_entity_type=entity_type,
        output_entity={
            "_contract_only": True,
            "_reason": reason,
        },
        unknowns=unknowns or [reason],
        confidence="none",
        warnings=[f"Contract-only stub: {reason}"],
        evidence_status="INACCESSIBLE",
        trace_notes=[f"contract_only: {reason}"],
    )


def missing_input_output(
    entity_type: str,
    missing_field: str,
) -> AgentOutput:
    """Build AgentOutput for missing required input."""
    return AgentOutput(
        output_entity_type=entity_type,
        output_entity={},
        unknowns=[f"Missing required input: {missing_field}"],
        confidence="none",
        warnings=[f"Agent failed: missing required input '{missing_field}'"],
        quality_gate_status="failed",
        trace_notes=[f"missing_input: {missing_field}"],
    )


def try_llm_call(
    provider: Any,
    family: dict[str, Any],
    template_vars: dict[str, str],
    *,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Try an LLM call using a prompt family. Returns (parsed, meta) or None."""
    from ..llm.provider import LLMProvider

    if not isinstance(provider, LLMProvider):
        return None

    user_prompt = family["user_prompt_template"].format(**template_vars)
    messages = [
        {"role": "system", "content": family["system_prompt"]},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = provider.complete(
            messages,
            response_schema=family.get("output_schema"),
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        logger.warning("LLM call failed for %s: %s", family.get("agent_role_id", "?"), exc)
        return None

    parsed = response.parsed
    if not parsed:
        try:
            parsed = json.loads(response.content)
        except (json.JSONDecodeError, TypeError):
            logger.warning("LLM returned non-JSON for %s, falling back", family.get("agent_role_id", "?"))
            return None

    meta = {
        "model": response.model,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "latency_ms": response.latency_ms,
    }
    return parsed, meta


def try_llm_call_with_outcome(
    provider: Any,
    family: dict[str, Any],
    template_vars: dict[str, str],
    *,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    strict_schema: bool = False,
    agent_role: str | None = None,
    model_role: str | None = None,
) -> LLMAttemptOutcome:
    """Round III-F: outcome-envelope variant. Never returns bare None.

    On any failure path, returns ``LLMAttemptOutcome`` with structural
    diagnostics and (when possible) a loose-parsed candidate the adapter
    can apply contract normalization to. NEVER stores raw content —
    only length + sha256 prefix + top-level shape.

    ``strict_schema=False`` (default) tells the provider NOT to enforce
    the schema strictly at the upstream layer (we do local validation
    in the adapter instead). This avoids the upstream cutting valid
    JSON because of an extra/missing field.
    """
    from ..llm.provider import LLMProvider

    outcome = LLMAttemptOutcome(
        agent_role=agent_role or family.get("agent_role_id"),
        model_role=model_role,
    )

    if not isinstance(provider, LLMProvider):
        outcome.provider_status = "not_configured"
        outcome.fallback_reason = "provider_unavailable"
        return outcome

    try:
        user_prompt = family["user_prompt_template"].format(**template_vars)
    except KeyError as exc:
        outcome.provider_status = "not_called"
        outcome.parse_failure_category = "prompt_template_var_missing"
        outcome.fallback_reason = f"missing_template_var:{exc.args[0]}"
        return outcome

    messages = [
        {"role": "system", "content": family["system_prompt"]},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = provider.complete(
            messages,
            response_schema=(family.get("output_schema") if strict_schema else None),
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001
        outcome.provider_status = "exception"
        outcome.fallback_reason = "provider_exception"
        outcome.parse_failure_category = type(exc).__name__
        logger.warning(
            "LLM call exception for %s: %s",
            family.get("agent_role_id", "?"), exc,
        )
        return outcome

    outcome.provider_status = "called_ok"
    content = getattr(response, "content", "") or ""
    outcome.content_present = bool(content)
    outcome.content_length, outcome.content_hash_prefix = (
        _redacted_content_fingerprint(content)
    )
    outcome.meta = {
        "model": getattr(response, "model", None),
        "input_tokens": getattr(response, "input_tokens", None),
        "output_tokens": getattr(response, "output_tokens", None),
        "latency_ms": getattr(response, "latency_ms", None),
    }

    # Strict-parsed path (provider already JSON-decoded via response_format)
    parsed_strict = getattr(response, "parsed", None)
    if isinstance(parsed_strict, (dict, list)):
        outcome.parsed = parsed_strict
        outcome.ok = True
        outcome.parse_status = "parsed_ok"
        outcome.redacted_top_level_type, outcome.redacted_top_level_keys = (
            _redacted_shape(parsed_strict)
        )
        return outcome

    # Loose path: try plain json.loads then bounded repair
    if not content:
        outcome.parse_status = "not_attempted"
        outcome.parse_failure_category = "empty_content"
        outcome.fallback_reason = "no_content"
        return outcome

    try:
        loose = json.loads(content)
    except Exception:  # noqa: BLE001
        # Try bounded repair (smart quotes, fences, balanced extract)
        try:
            from ..llm.json_repair import repair_and_parse
            r = repair_and_parse(content, schema=None)
            if r.parsed is not None and r.status in ("parsed_ok", "repaired_ok"):
                outcome.loose_parsed = r.parsed
                outcome.repair_attempted = True
                outcome.repair_status = r.status
                outcome.parse_status = "repaired_ok"
                outcome.redacted_top_level_type, outcome.redacted_top_level_keys = (
                    _redacted_shape(r.parsed)
                )
                # Adapter will decide if this is good enough
                outcome.ok = False  # loose only; adapter must validate
                return outcome
            else:
                outcome.repair_attempted = True
                outcome.repair_status = r.status
                outcome.parse_status = r.status
                outcome.parse_failure_category = r.status
                outcome.fallback_reason = "repair_failed"
                return outcome
        except Exception as exc2:  # noqa: BLE001
            outcome.parse_status = "invalid_json"
            outcome.parse_failure_category = "invalid_json"
            outcome.fallback_reason = "invalid_json"
            return outcome

    # json.loads succeeded — loose parsed
    outcome.loose_parsed = loose
    outcome.parse_status = "parsed_ok"
    outcome.redacted_top_level_type, outcome.redacted_top_level_keys = (
        _redacted_shape(loose)
    )
    outcome.ok = False  # adapter decides on shape
    return outcome


def llm_agent_output(
    entity_type: str,
    parsed: dict[str, Any],
    meta: dict[str, Any],
    validation_warnings: list[str] | None = None,
) -> AgentOutput:
    """Build AgentOutput from a successful LLM call."""
    return AgentOutput(
        output_entity_type=entity_type,
        output_entity=parsed,
        evidence_refs=[],
        unknowns=parsed.get("unknowns", []),
        assumptions=parsed.get("assumptions", []),
        confidence=parsed.get("confidence", "medium"),
        warnings=(validation_warnings or []) + parsed.get("warnings", []),
        questions_for_user=parsed.get("questions_for_user", []),
        quality_gate_status="preliminary",
        trace_notes=[
            f"LLM model: {meta.get('model', '?')}",
            f"Tokens: {meta.get('input_tokens', 0)}+{meta.get('output_tokens', 0)}",
            f"Latency: {meta.get('latency_ms', 0):.0f}ms",
        ],
        evidence_status="INFERENCE",
        llm_usage=meta,
    )
