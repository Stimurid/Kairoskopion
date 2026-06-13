"""Submission Pack Builder — LLM-backed readiness assessment with deterministic fallback."""

from __future__ import annotations

import json

from ..base_shell import llm_agent_output, missing_input_output, service_output, try_llm_call
from ..contract import AgentInput, AgentOutput, AgentRole
from ..prompt_families.submission_pack import SUBMISSION_PACK_FAMILY
from ...llm.provider import LLMProvider
from ...schema import (
    ArticleModel, ComplianceChecklist, FitAssessment,
    RiskReport, SubmissionScenario, VenueModel,
)
from ...services.submission_pack import build_submission_pack


class SubmissionPackBuilderAgent(AgentRole):
    role_id = "submission_pack_builder"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        e = inp.entities
        if not e.get("article") or not e.get("venue") or not e.get("scenario"):
            return missing_input_output("SubmissionPack", "article, venue, and scenario")

        result = try_llm_call(provider, SUBMISSION_PACK_FAMILY, {
            "article_json": json.dumps(e["article"], ensure_ascii=False, indent=2),
            "venue_json": json.dumps(e["venue"], ensure_ascii=False, indent=2),
            "scenario_json": json.dumps(e["scenario"], ensure_ascii=False, indent=2),
            "compliance_json": json.dumps(e.get("compliance", {}), ensure_ascii=False, indent=2),
            "risk_json": json.dumps(e.get("risk_report", {}), ensure_ascii=False, indent=2),
        })
        if result is None:
            return self.execute_deterministic(inp)

        parsed, meta = result
        warnings = SUBMISSION_PACK_FAMILY["validator"](parsed)
        return llm_agent_output("SubmissionPack", parsed, meta, warnings)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        e = inp.entities
        if not e.get("article") or not e.get("venue") or not e.get("scenario"):
            return missing_input_output("SubmissionPack", "article, venue, and scenario")

        article = ArticleModel.from_dict(e["article"])
        venue = VenueModel.from_dict(e["venue"])
        scenario = SubmissionScenario.from_dict(e["scenario"])
        fit = FitAssessment.from_dict(e["fit_assessment"]) if e.get("fit_assessment") else None
        risk = RiskReport.from_dict(e["risk_report"]) if e.get("risk_report") else None
        cc = ComplianceChecklist.from_dict(e["compliance"]) if e.get("compliance") else None

        pack = build_submission_pack(
            article=article, venue=venue, scenario=scenario,
            fit=fit, risk=risk, compliance=cc,
        )

        return service_output(
            "SubmissionPack",
            pack.to_dict(),
            confidence="medium",
            trace_notes=[f"readiness={pack.ready_status}"],
        )
