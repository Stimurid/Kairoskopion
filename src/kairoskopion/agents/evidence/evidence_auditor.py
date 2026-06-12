"""Evidence Auditor — wraps services/evidence_audit.py."""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...schema import (
    ArticleModel, ComplianceChecklist, FitAssessment,
    MismatchMap, RiskReport, VenueModel,
)
from ...services.evidence_audit import audit_pipeline_evidence


class EvidenceAuditorAgent(AgentRole):
    role_id = "evidence_auditor"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        e = inp.entities
        required = ["article", "venue", "fit_assessment", "mismatch_map",
                     "risk_report", "compliance"]
        missing = [k for k in required if not e.get(k)]
        if missing:
            return missing_input_output("QualityGateResult", ", ".join(missing))

        article = ArticleModel.from_dict(e["article"])
        venue = VenueModel.from_dict(e["venue"])
        fit = FitAssessment.from_dict(e["fit_assessment"])
        mm = MismatchMap.from_dict(e["mismatch_map"])
        risk = RiskReport.from_dict(e["risk_report"])
        cc = ComplianceChecklist.from_dict(e["compliance"])

        result = audit_pipeline_evidence(article, venue, fit, mm, risk, cc)

        return service_output(
            "QualityGateResult",
            result.to_dict(),
            confidence="high",
            evidence_status="CORPUS",
            trace_notes=[
                f"gate_status={result.status}",
                f"warnings={len(result.warnings)}",
                f"blocking={len(result.blocking_issues)}",
            ],
        )
