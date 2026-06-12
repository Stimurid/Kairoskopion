"""Risk Officer — wraps services/risk_reporting.py."""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...schema import ArticleModel, FitAssessment, MismatchMap, VenueModel
from ...services.risk_reporting import build_risk_report


class RiskOfficerAgent(AgentRole):
    role_id = "risk_officer"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        article_data = inp.entities.get("article")
        venue_data = inp.entities.get("venue")
        fit_data = inp.entities.get("fit_assessment")
        mm_data = inp.entities.get("mismatch_map")

        if not article_data or not venue_data:
            return missing_input_output("RiskReport", "article and venue")

        article = ArticleModel.from_dict(article_data)
        venue = VenueModel.from_dict(venue_data)
        fit = FitAssessment.from_dict(fit_data) if fit_data else None
        mm = MismatchMap.from_dict(mm_data) if mm_data else None

        report = build_risk_report(article, venue, fit, mm)

        return service_output(
            "RiskReport",
            report.to_dict(),
            unknowns=report.unknowns if hasattr(report, "unknowns") and report.unknowns else [],
            confidence="medium",
            trace_notes=[f"risk_items={len(report.risk_items)}"],
        )
