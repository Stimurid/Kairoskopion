"""Venue Identifier — resolves venue references to VenueModel IDs.

Deterministic: matches by name, ISSN, URL against known venue records.
"""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class VenueIdentifierAgent(AgentRole):
    role_id = "venue_identifier"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        venue_ref = inp.entities.get("venue_reference", {})
        name = venue_ref.get("name", inp.raw_text or "")
        issn = venue_ref.get("issn")

        if not name and not issn:
            return missing_input_output("VenueIdentification", "venue_reference (name or ISSN)")

        return service_output(
            "VenueIdentification",
            {
                "query_name": name,
                "query_issn": issn,
                "resolved_venue_id": None,
                "candidates": [],
                "resolution_status": "needs_sources",
            },
            unknowns=["No local venue registry queried in this version"],
            confidence="low",
            trace_notes=["venue identification from reference, no registry lookup yet"],
        )
