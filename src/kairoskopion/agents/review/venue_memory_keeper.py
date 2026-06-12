"""Venue Memory Keeper — contract-only stub (future: LLM-required)."""

from __future__ import annotations

from ..base_shell import contract_only_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class VenueMemoryKeeperAgent(AgentRole):
    role_id = "venue_memory_keeper"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return contract_only_output(
            "VenueMemoryUpdate",
            "Venue memory keeping requires LLM — not yet implemented",
            unknowns=["updated_venue_memory", "accumulated_experience"],
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        return contract_only_output(
            "VenueMemoryUpdate",
            "No deterministic path for venue memory keeping",
        )
