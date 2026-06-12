"""Citation Planner — wraps services/citation_ecology.py."""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...schema import ArticleModel, VenueModel
from ...services.citation_ecology import build_citation_ecology_report


class CitationPlannerAgent(AgentRole):
    role_id = "citation_planner"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        article_data = inp.entities.get("article")
        venue_data = inp.entities.get("venue")
        if not article_data or not venue_data:
            return missing_input_output("CitationEcologyReport", "article and venue")

        article = ArticleModel.from_dict(article_data)
        venue = VenueModel.from_dict(venue_data)
        report = build_citation_ecology_report(article, venue)

        return service_output(
            "CitationEcologyReport",
            report.to_dict(),
            unknowns=report.unknowns if hasattr(report, "unknowns") and report.unknowns else [],
            confidence="medium",
            trace_notes=["citation ecology via deterministic service"],
        )
