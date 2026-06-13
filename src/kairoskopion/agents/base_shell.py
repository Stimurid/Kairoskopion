"""Base agent shell — shared utilities for all agent shells.

Provides helpers for wrapping existing deterministic services as
agent-compatible shells with consistent error handling, unknown
propagation, and contract-only stub generation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .contract import AgentInput, AgentOutput

logger = logging.getLogger(__name__)


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
