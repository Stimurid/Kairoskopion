"""Evidence Auditor — LLM-backed evidence audit with deterministic fallback."""

from __future__ import annotations

import json

from ..base_shell import llm_agent_output, missing_input_output, service_output, try_llm_call
from ..contract import AgentInput, AgentOutput, AgentRole
from ..prompt_families.evidence_audit import EVIDENCE_AUDIT_FAMILY
from ...llm.provider import LLMProvider
from ...schema import (
    ArticleModel, ComplianceChecklist, FitAssessment,
    MismatchMap, RiskReport, VenueModel,
)
from ...services.evidence_audit import audit_pipeline_evidence


class EvidenceAuditorAgent(AgentRole):
    role_id = "evidence_auditor"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        e = inp.entities
        required = ["article", "venue", "fit_assessment", "mismatch_map",
                     "risk_report", "compliance"]
        missing = [k for k in required if not e.get(k)]
        if missing:
            return missing_input_output("QualityGateResult", ", ".join(missing))

        entities_bundle = {k: e[k] for k in required}
        sources = []
        for key in required:
            refs = e[key].get("evidence_refs", []) if isinstance(e[key], dict) else []
            sources.extend(refs)

        result = try_llm_call(provider, EVIDENCE_AUDIT_FAMILY, {
            "entities_json": json.dumps(entities_bundle, ensure_ascii=False, indent=2),
            "sources_json": json.dumps(list(set(sources)), ensure_ascii=False, indent=2),
        })
        if result is None:
            return self.execute_deterministic(inp)

        parsed, meta = result
        warnings = EVIDENCE_AUDIT_FAMILY["validator"](parsed)
        return llm_agent_output("QualityGateResult", parsed, meta, warnings)

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
