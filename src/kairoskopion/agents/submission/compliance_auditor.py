"""Compliance Auditor — wraps services/compliance.py."""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...schema import ArticleModel, ManuscriptModel, VenueModel
from ...services.compliance import build_compliance_checklist


class ComplianceAuditorAgent(AgentRole):
    role_id = "compliance_auditor"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        article_data = inp.entities.get("article")
        venue_data = inp.entities.get("venue")
        if not article_data or not venue_data:
            return missing_input_output("ComplianceChecklist", "article and venue")

        article = ArticleModel.from_dict(article_data)
        venue = VenueModel.from_dict(venue_data)

        manuscript_data = inp.entities.get("manuscript")
        if manuscript_data:
            manuscript = ManuscriptModel.from_dict(manuscript_data)
        else:
            manuscript = ManuscriptModel(
                manuscript_id="ms-from-agent",
                article_model_id=article.article_model_id,
                title=article.title,
                abstract=article.abstract,
                keywords=list(article.keywords) if article.keywords else [],
                sections=[],
                word_count=0,
                language=article.language if hasattr(article, "language") else "en",
            )

        guidelines_text = inp.entities.get("venue_guidelines_text", "")

        checklist = build_compliance_checklist(article, manuscript, venue, guidelines_text)

        return service_output(
            "ComplianceChecklist",
            checklist.to_dict(),
            confidence="medium",
            trace_notes=[
                f"items={len(checklist.checklist_items)}",
                f"missing={len(checklist.missing_items)}",
            ],
        )
