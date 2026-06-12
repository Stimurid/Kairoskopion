"""Mismatch Mapper — wraps services/mismatch_mapping.py."""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...schema import FitAssessment
from ...services.mismatch_mapping import build_mismatch_map


class MismatchMapperAgent(AgentRole):
    role_id = "mismatch_mapper"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        fit_data = inp.entities.get("fit_assessment")
        if not fit_data:
            return missing_input_output("MismatchMap", "fit_assessment")

        fit = FitAssessment.from_dict(fit_data)
        mm = build_mismatch_map(fit)

        return service_output(
            "MismatchMap",
            mm.to_dict(),
            unknowns=mm.unknowns if hasattr(mm, "unknowns") and mm.unknowns else [],
            confidence="medium",
            trace_notes=[f"mismatches={len(mm.mismatches)}"],
        )
