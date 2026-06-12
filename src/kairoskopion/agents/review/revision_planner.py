"""Revision Planner — contract-only stub (future: LLM-required)."""

from __future__ import annotations

from ..base_shell import contract_only_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class RevisionPlannerAgent(AgentRole):
    role_id = "revision_planner"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return contract_only_output(
            "RevisionPlan",
            "Revision planning requires LLM — not yet implemented",
            unknowns=["revision_actions", "priority_order"],
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        return contract_only_output(
            "RevisionPlan",
            "No deterministic path for revision planning",
        )
