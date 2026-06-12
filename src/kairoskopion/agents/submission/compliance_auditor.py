"""Compliance Auditor — wraps services/compliance.py."""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...schema import ArticleModel, VenueModel
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
        checklist = build_compliance_checklist(article, venue)

        return service_output(
            "ComplianceChecklist",
            checklist.to_dict(),
            confidence="medium",
            trace_notes=[
                f"items={len(checklist.checklist_items)}",
                f"missing={len(checklist.missing_items)}",
            ],
        )
