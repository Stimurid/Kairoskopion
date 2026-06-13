"""Publication Regime Classifier — classifies how publication works at a venue.

LLM-backed regime classification with deterministic fallback.
"""

from __future__ import annotations

import json

from ..base_shell import llm_agent_output, missing_input_output, service_output, try_llm_call
from ..contract import AgentInput, AgentOutput, AgentRole
from ..prompt_families.publication_regime import PUBLICATION_REGIME_FAMILY
from ...llm.provider import LLMProvider


class PublicationRegimeClassifierAgent(AgentRole):
    role_id = "publication_regime_classifier"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        venue = inp.entities.get("venue", {})
        if not venue:
            return missing_input_output("PublicationRegimeModel", "venue")

        result = try_llm_call(provider, PUBLICATION_REGIME_FAMILY, {
            "venue_json": json.dumps(venue, ensure_ascii=False, indent=2),
            "guidelines_text": inp.entities.get("venue_guidelines_text", "") or inp.raw_text or "",
        })
        if result is None:
            return self.execute_deterministic(inp)

        parsed, meta = result
        warnings = PUBLICATION_REGIME_FAMILY["validator"](parsed)
        return llm_agent_output("PublicationRegimeModel", parsed, meta, warnings)

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
