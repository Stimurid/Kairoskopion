"""Submission Pack Builder — wraps services/submission_pack.py."""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...schema import (
    ArticleModel, ComplianceChecklist, FitAssessment,
    MismatchMap, RewritePlan, RiskReport, VenueModel,
)
from ...services.submission_pack import build_submission_pack


class SubmissionPackBuilderAgent(AgentRole):
    role_id = "submission_pack_builder"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        e = inp.entities
        if not e.get("article") or not e.get("venue"):
            return missing_input_output("SubmissionPack", "article and venue")

        article = ArticleModel.from_dict(e["article"])
        venue = VenueModel.from_dict(e["venue"])
        fit = FitAssessment.from_dict(e["fit_assessment"]) if e.get("fit_assessment") else None
        mm = MismatchMap.from_dict(e["mismatch_map"]) if e.get("mismatch_map") else None
        rw = RewritePlan.from_dict(e["rewrite_plan"]) if e.get("rewrite_plan") else None
        risk = RiskReport.from_dict(e["risk_report"]) if e.get("risk_report") else None
        cc = ComplianceChecklist.from_dict(e["compliance"]) if e.get("compliance") else None

        pack = build_submission_pack(
            article=article, venue=venue, fit=fit,
            mismatch_map=mm, rewrite_plan=rw,
            risk_report=risk, compliance=cc,
        )

        return service_output(
            "SubmissionPack",
            pack.to_dict(),
            confidence="medium",
            trace_notes=[f"readiness={pack.readiness}"],
        )
