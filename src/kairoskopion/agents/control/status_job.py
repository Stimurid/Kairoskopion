"""Status Job — reports current pipeline/workflow state."""

from __future__ import annotations

from ..base_shell import service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider


class StatusJobAgent(AgentRole):
    role_id = "status_job"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        entities = inp.entities
        summary = {
            "entity_count": len(entities),
            "entity_types": sorted(entities.keys()),
            "has_article": "article" in entities,
            "has_venue": "venue" in entities,
            "has_fit": "fit_assessment" in entities,
            "has_risk": "risk_report" in entities,
        }
        return service_output(
            "StatusReport", summary,
            confidence="high",
            trace_notes=["status report generated"],
        )
