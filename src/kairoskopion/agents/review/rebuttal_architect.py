"""Rebuttal Architect — contract-only stub (future: LLM-required)."""

from __future__ import annotations

from ..base_shell import contract_only_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class RebuttalArchitectAgent(AgentRole):
    role_id = "rebuttal_architect"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return contract_only_output(
            "RebuttalStrategy",
            "Rebuttal architecture requires LLM — not yet implemented",
            unknowns=["rebuttal_structure", "evidence_marshalling"],
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        return contract_only_output(
            "RebuttalStrategy",
            "No deterministic path for rebuttal architecture",
        )
