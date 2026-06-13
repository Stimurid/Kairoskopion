"""Reference Verifier agent — wraps services/reference_verification.py."""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...services.bibliography_parsing import build_bibliography_profile
from ...services.reference_verification import verify_references


class ReferenceVerifierAgent(AgentRole):
    role_id = "reference_verifier"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        bib_data = inp.entities.get("bibliography_profile")

        if bib_data:
            from ...schema import BibliographyProfile
            bib_profile = BibliographyProfile.from_dict(bib_data)
        elif inp.raw_text:
            bib_profile = build_bibliography_profile(inp.raw_text)
        else:
            return missing_input_output(
                "ReferenceVerificationResult",
                "bibliography_profile or raw_text",
            )

        result = verify_references(bib_profile)

        unknowns = result.unknowns or []
        warnings: list[str] = []
        if result.doi_unresolved_count > 0:
            warnings.append(
                f"{result.doi_unresolved_count} DOI(s) could not be resolved"
            )
        if result.padding_risk_count > 0:
            warnings.append(
                f"{result.padding_risk_count} reference(s) flagged for padding risk"
            )

        return service_output(
            "ReferenceVerificationResult",
            result.to_dict(),
            unknowns=unknowns,
            warnings=warnings,
            confidence="medium",
            trace_notes=["reference verification via deterministic service"],
        )
