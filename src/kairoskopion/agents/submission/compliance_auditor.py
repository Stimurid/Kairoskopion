"""Compliance Auditor — LLM-backed compliance check with deterministic fallback."""

from __future__ import annotations

import json

from ..base_shell import llm_agent_output, missing_input_output, service_output, try_llm_call
from ..contract import AgentInput, AgentOutput, AgentRole
from ..prompt_families.compliance_checklist import COMPLIANCE_CHECKLIST_FAMILY
from ...llm.provider import LLMProvider
from ...schema import ArticleModel, ManuscriptModel, VenueModel
from ...services.compliance import build_compliance_checklist


class ComplianceAuditorAgent(AgentRole):
    role_id = "compliance_auditor"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        article_data = inp.entities.get("article")
        venue_data = inp.entities.get("venue")
        if not article_data or not venue_data:
            return missing_input_output("ComplianceChecklist", "article and venue")

        manuscript_data = inp.entities.get("manuscript", {})
        guidelines_text = inp.entities.get("venue_guidelines_text", "") or inp.raw_text or ""

        result = try_llm_call(provider, COMPLIANCE_CHECKLIST_FAMILY, {
            "article_json": json.dumps(article_data, ensure_ascii=False, indent=2),
            "venue_json": json.dumps(venue_data, ensure_ascii=False, indent=2),
            "manuscript_json": json.dumps(manuscript_data, ensure_ascii=False, indent=2),
            "guidelines_text": guidelines_text,
        })
        if result is None:
            return self.execute_deterministic(inp)

        parsed, meta = result
        warnings = COMPLIANCE_CHECKLIST_FAMILY["validator"](parsed)
        return llm_agent_output("ComplianceChecklist", parsed, meta, warnings)

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
                title=article.title_current,
                abstract=article.abstract_current,
                keywords=list(article.core_claims) if article.core_claims else [],
                sections=[],
                word_count=article.word_count or 0,
                language=article.language or "en",
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
