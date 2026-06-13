"""Mismatch Mapper — LLM-backed mismatch analysis with deterministic fallback."""

from __future__ import annotations

import json

from ..base_shell import llm_agent_output, missing_input_output, service_output, try_llm_call
from ..contract import AgentInput, AgentOutput, AgentRole
from ..prompt_families.mismatch_mapping import MISMATCH_MAPPING_FAMILY
from ...llm.provider import LLMProvider
from ...schema import FitAssessment
from ...services.mismatch_mapping import build_mismatch_map


class MismatchMapperAgent(AgentRole):
    role_id = "mismatch_mapper"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        fit_data = inp.entities.get("fit_assessment")
        if not fit_data:
            return missing_input_output("MismatchMap", "fit_assessment")

        result = try_llm_call(provider, MISMATCH_MAPPING_FAMILY, {
            "fit_json": json.dumps(fit_data, ensure_ascii=False, indent=2),
            "article_json": json.dumps(inp.entities.get("article", {}), ensure_ascii=False, indent=2),
            "venue_json": json.dumps(inp.entities.get("venue", {}), ensure_ascii=False, indent=2),
        })
        if result is None:
            return self.execute_deterministic(inp)

        parsed, meta = result
        warnings = MISMATCH_MAPPING_FAMILY["validator"](parsed)
        return llm_agent_output("MismatchMap", parsed, meta, warnings)

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
