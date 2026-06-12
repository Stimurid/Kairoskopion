"""Tacit Signal Structurer — contract-only stub (future: LLM-required)."""

from __future__ import annotations

from ..base_shell import contract_only_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class TacitSignalStructurerAgent(AgentRole):
    role_id = "tacit_signal_structurer"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return contract_only_output(
            "TacitSignalReport",
            "Tacit signal structuring requires LLM — not yet implemented",
            unknowns=["implicit_reviewer_signals", "editorial_preference_patterns"],
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        return contract_only_output(
            "TacitSignalReport",
            "No deterministic path for tacit signal structuring",
        )
