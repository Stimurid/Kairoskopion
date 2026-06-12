"""Rewrite Planner — wraps services/rewrite_planning.py."""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...schema import FitAssessment, MismatchMap
from ...services.rewrite_planning import build_rewrite_plan


class RewritePlannerAgent(AgentRole):
    role_id = "rewrite_planner"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        mm_data = inp.entities.get("mismatch_map")
        fit_data = inp.entities.get("fit_assessment")
        if not mm_data:
            return missing_input_output("RewritePlan", "mismatch_map")

        mm = MismatchMap.from_dict(mm_data)
        fit = FitAssessment.from_dict(fit_data) if fit_data else None
        plan = build_rewrite_plan(mm, fit)

        return service_output(
            "RewritePlan",
            plan.to_dict(),
            unknowns=plan.unknowns if hasattr(plan, "unknowns") and plan.unknowns else [],
            confidence="medium",
            trace_notes=[f"actions={len(plan.actions) if hasattr(plan, 'actions') else 0}"],
        )
