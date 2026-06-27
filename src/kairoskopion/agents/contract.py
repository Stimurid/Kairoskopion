"""Agent contract base (spec §53).

Every agent has typed input/output, evidence contract, unknown policy,
and failure/escalation contract. Two execution paths: LLM-backed and
deterministic fallback.
"""

from __future__ import annotations

import dataclasses as dc
from abc import ABC, abstractmethod
from typing import Any

from ..llm.provider import LLMProvider


@dc.dataclass
class AgentInput:
    """Typed input bundle for any agent (spec §53.1)."""

    operation_id: str
    agent_role_id: str
    input_entity_refs: list[str] = dc.field(default_factory=list)
    source_refs: list[str] = dc.field(default_factory=list)
    raw_text: str | None = None
    entities: dict[str, Any] = dc.field(default_factory=dict)
    user_constraints: dict[str, Any] = dc.field(default_factory=dict)


@dc.dataclass
class AgentOutput:
    """Structured output from any agent (spec §53.2)."""

    output_entity_type: str
    output_entity: dict[str, Any] = dc.field(default_factory=dict)
    evidence_refs: list[str] = dc.field(default_factory=list)
    unknowns: list[str] = dc.field(default_factory=list)
    assumptions: list[str] = dc.field(default_factory=list)
    confidence: str = "low"
    warnings: list[str] = dc.field(default_factory=list)
    questions_for_user: list[str] = dc.field(default_factory=list)
    quality_gate_status: str = "preliminary"
    trace_notes: list[str] = dc.field(default_factory=list)
    evidence_status: str = "INFERENCE"
    llm_usage: dict[str, Any] | None = None


class AgentRole(ABC):
    """Base class for all Kairoskopion agent roles."""

    role_id: str = ""

    @abstractmethod
    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        """Execute with LLM provider."""
        ...

    @abstractmethod
    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        """Execute with deterministic heuristics (fallback)."""
        ...

    def run(
        self,
        inp: AgentInput,
        provider: LLMProvider | None = None,
        *,
        prompt_family_override: dict[str, str] | None = None,
    ) -> AgentOutput:
        """Run the agent: LLM if provider available, else deterministic.

        ``prompt_family_override`` — if provided, a dict with optional keys
        ``system_prompt`` and/or ``user_prompt_template`` that replace the
        canonical family values for this single call.  The canonical source
        is never mutated.
        """
        self._prompt_family_override = prompt_family_override
        if provider is not None:
            return self.execute(inp, provider)
        return self.execute_deterministic(inp)
