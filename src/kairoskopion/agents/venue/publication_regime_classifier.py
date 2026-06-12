"""Publication Regime Classifier — classifies how publication works at a venue.

Wraps venue_profiling service for regime extraction.
"""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class PublicationRegimeClassifierAgent(AgentRole):
    role_id = "publication_regime_classifier"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        venue = inp.entities.get("venue", {})
        if not venue:
            return missing_input_output("PublicationRegimeModel", "venue")

        regime = venue.get("publication_regime", {})
        regime_type = venue.get("regime_type") or regime.get("regime_type", "unknown")

        return service_output(
            "PublicationRegimeModel",
            {
                "regime_type": regime_type,
                "review_type": venue.get("review_type", "unknown"),
                "open_access_model": venue.get("open_access", "unknown"),
                "submission_window": "unknown",
                "venue_model_id": venue.get("venue_model_id"),
            },
            unknowns=["Regime classification from VenueModel fields only — no deep analysis"],
            confidence="low",
            trace_notes=["extracted regime from VenueModel fields"],
        )
