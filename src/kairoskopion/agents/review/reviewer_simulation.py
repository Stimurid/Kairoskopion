"""Reviewer Simulation — contract-only stub (future: LLM-required)."""

from __future__ import annotations

from ..base_shell import contract_only_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class ReviewerSimulationAgent(AgentRole):
    role_id = "reviewer_simulation"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return contract_only_output(
            "SimulatedReview",
            "Reviewer simulation requires LLM — not yet implemented",
            unknowns=["simulated_review_outcome", "predicted_objections"],
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        return contract_only_output(
            "SimulatedReview",
            "No deterministic path for reviewer simulation",
        )
