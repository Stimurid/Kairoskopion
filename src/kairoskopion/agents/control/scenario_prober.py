"""Scenario Prober — builds SubmissionScenario from user constraints.

LLM-backed scenario interview with deterministic fallback.
"""

from __future__ import annotations

import json

from ..base_shell import llm_agent_output, missing_input_output, service_output, try_llm_call
from ..contract import AgentInput, AgentOutput, AgentRole
from ..prompt_families.scenario_interview import SCENARIO_INTERVIEW_FAMILY
from ...llm.provider import LLMProvider
from ...services.scenario import build_scenario_from_dict


class ScenarioProberAgent(AgentRole):
    role_id = "scenario_prober"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        scenario_data = inp.entities.get("scenario") or inp.user_constraints
        if not scenario_data:
            return missing_input_output("SubmissionScenario", "scenario or user_constraints")

        user_brief = scenario_data.get("goal", "") or scenario_data.get("brief", "") or json.dumps(scenario_data, ensure_ascii=False)
        article_json = json.dumps(inp.entities.get("article", {}), ensure_ascii=False, indent=2)

        result = try_llm_call(provider, SCENARIO_INTERVIEW_FAMILY, {
            "user_brief": user_brief,
            "article_json": article_json,
        })
        if result is None:
            return self.execute_deterministic(inp)

        parsed, meta = result
        warnings = SCENARIO_INTERVIEW_FAMILY["validator"](parsed)
        return llm_agent_output("SubmissionScenario", parsed, meta, warnings)

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
