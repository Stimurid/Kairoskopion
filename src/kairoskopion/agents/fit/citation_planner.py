"""Citation Planner — LLM-backed citation ecology analysis with deterministic fallback."""

from __future__ import annotations

import json

from ..base_shell import llm_agent_output, missing_input_output, service_output, try_llm_call
from ..contract import AgentInput, AgentOutput, AgentRole
from ..prompt_families.citation_ecology import CITATION_ECOLOGY_FAMILY
from ...llm.provider import LLMProvider
from ...schema import ArticleModel, VenueModel
from ...services.bibliography_parsing import build_bibliography_profile
from ...services.citation_ecology import build_citation_ecology_report


class CitationPlannerAgent(AgentRole):
    role_id = "citation_planner"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        article_data = inp.entities.get("article")
        venue_data = inp.entities.get("venue")
        if not article_data or not venue_data:
            return missing_input_output("CitationEcologyReport", "article and venue")

        bib_data = inp.entities.get("bibliography_profile", {})
        if not bib_data and inp.raw_text:
            bib_profile = build_bibliography_profile(inp.raw_text)
            bib_data = bib_profile.to_dict() if hasattr(bib_profile, "to_dict") else {}

        result = try_llm_call(provider, CITATION_ECOLOGY_FAMILY, {
            "article_json": json.dumps(article_data, ensure_ascii=False, indent=2),
            "venue_json": json.dumps(venue_data, ensure_ascii=False, indent=2),
            "bibliography_json": json.dumps(bib_data, ensure_ascii=False, indent=2),
        })
        if result is None:
            return self.execute_deterministic(inp)

        parsed, meta = result
        warnings = CITATION_ECOLOGY_FAMILY["validator"](parsed)
        return llm_agent_output("CitationEcologyReport", parsed, meta, warnings)

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
