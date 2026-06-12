"""Base agent shell — shared utilities for all agent shells.

Provides helpers for wrapping existing deterministic services as
agent-compatible shells with consistent error handling, unknown
propagation, and contract-only stub generation.
"""

from __future__ import annotations

from typing import Any

from .contract import AgentInput, AgentOutput


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
