"""Review Outcome Analyst — contract-only stub (future: LLM-required)."""

from __future__ import annotations

from ..base_shell import contract_only_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class ReviewOutcomeAnalystAgent(AgentRole):
    role_id = "review_outcome_analyst"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return contract_only_output(
            "ReviewOutcomeAnalysis",
            "Review outcome analysis requires LLM — not yet implemented",
            unknowns=["outcome_interpretation", "response_strategy"],
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        return contract_only_output(
            "ReviewOutcomeAnalysis",
            "No deterministic path for review outcome analysis",
        )
