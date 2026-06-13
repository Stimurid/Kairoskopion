"""Risk Officer — LLM-backed risk analysis with deterministic fallback."""

from __future__ import annotations

import json

from ..base_shell import llm_agent_output, missing_input_output, service_output, try_llm_call
from ..contract import AgentInput, AgentOutput, AgentRole
from ..prompt_families.risk_reporting import RISK_REPORTING_FAMILY
from ...llm.provider import LLMProvider
from ...schema import (
    ArticleModel, FitAssessment, MismatchMap,
    SubmissionScenario, VenueModel,
)
from ...services.risk_reporting import build_risk_report


class RiskOfficerAgent(AgentRole):
    role_id = "risk_officer"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        article_data = inp.entities.get("article")
        venue_data = inp.entities.get("venue")
        fit_data = inp.entities.get("fit_assessment")
        mm_data = inp.entities.get("mismatch_map")

        if not article_data or not venue_data:
            return missing_input_output("RiskReport", "article, venue, and scenario")

        result = try_llm_call(provider, RISK_REPORTING_FAMILY, {
            "article_json": json.dumps(article_data, ensure_ascii=False, indent=2),
            "venue_json": json.dumps(venue_data, ensure_ascii=False, indent=2),
            "fit_json": json.dumps(fit_data or {}, ensure_ascii=False, indent=2),
            "mismatch_json": json.dumps(mm_data or {}, ensure_ascii=False, indent=2),
        })
        if result is None:
            return self.execute_deterministic(inp)

        parsed, meta = result
        warnings = RISK_REPORTING_FAMILY["validator"](parsed)
        return llm_agent_output("RiskReport", parsed, meta, warnings)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        article_data = inp.entities.get("article")
        venue_data = inp.entities.get("venue")
        scenario_data = inp.entities.get("scenario")
        fit_data = inp.entities.get("fit_assessment")
        mm_data = inp.entities.get("mismatch_map")

        if not article_data or not venue_data or not scenario_data:
            return missing_input_output("RiskReport", "article, venue, and scenario")

        article = ArticleModel.from_dict(article_data)
        venue = VenueModel.from_dict(venue_data)
        scenario = SubmissionScenario.from_dict(scenario_data)
        fit = FitAssessment.from_dict(fit_data) if fit_data else None
        mm = MismatchMap.from_dict(mm_data) if mm_data else None

        if not fit or not mm:
            return missing_input_output("RiskReport", "fit_assessment and mismatch_map")

        report = build_risk_report(article, venue, scenario, fit, mm)

        return service_output(
            "RiskReport",
            report.to_dict(),
            unknowns=report.unknowns if hasattr(report, "unknowns") and report.unknowns else [],
            confidence="medium",
            trace_notes=[f"risk_items={len(report.risk_items)}"],
        )
