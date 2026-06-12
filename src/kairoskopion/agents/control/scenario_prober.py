"""Scenario Prober — builds SubmissionScenario from user constraints.

Wraps services/scenario.py for deterministic path.
"""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...services.scenario import build_scenario_from_dict


class ScenarioProberAgent(AgentRole):
    role_id = "scenario_prober"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        scenario_data = inp.entities.get("scenario") or inp.user_constraints
        if not scenario_data:
            return missing_input_output("SubmissionScenario", "scenario or user_constraints")

        scenario = build_scenario_from_dict(scenario_data)
        return service_output(
            "SubmissionScenario",
            scenario.to_dict(),
            unknowns=scenario.unknowns if hasattr(scenario, "unknowns") else [],
            confidence="medium",
            trace_notes=["built from user constraints via scenario service"],
        )
