"""Citation Planner — wraps services/citation_ecology.py."""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...schema import ArticleModel, VenueModel
from ...services.bibliography_parsing import build_bibliography_profile
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

        bib_data = inp.entities.get("bibliography_profile")
        if bib_data:
            from ...schema import BibliographyProfile
            bib_profile = BibliographyProfile.from_dict(bib_data)
        else:
            manuscript_text = inp.raw_text or ""
            bib_profile = build_bibliography_profile(manuscript_text)

        guidelines_text = inp.entities.get("venue_guidelines_text", "")

        report = build_citation_ecology_report(bib_profile, article, venue, guidelines_text)

        return service_output(
            "CitationEcologyReport",
            report.to_dict(),
            unknowns=report.unknowns if hasattr(report, "unknowns") and report.unknowns else [],
            confidence="medium",
            trace_notes=["citation ecology via deterministic service"],
        )
