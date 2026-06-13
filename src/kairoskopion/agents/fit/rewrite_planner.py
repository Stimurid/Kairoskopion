"""Rewrite Planner — wraps services/rewrite_planning.py + protected core gate."""

from __future__ import annotations

from ..base_shell import missing_input_output, service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider
from ...schema import MismatchMap
from ...services.protected_core import apply_core_gate, validate_rewrite_plan
from ...services.rewrite_planning import build_rewrite_plan


class RewritePlannerAgent(AgentRole):
    role_id = "rewrite_planner"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        mm_data = inp.entities.get("mismatch_map")
        if not mm_data:
            return missing_input_output("RewritePlan", "mismatch_map")

        mm = MismatchMap.from_dict(mm_data)

        article_data = inp.entities.get("article", {})
        venue_data = inp.entities.get("venue", {})
        plan = build_rewrite_plan(
            mm,
            article_model_id=article_data.get("article_model_id"),
            manuscript_id=article_data.get("manuscript_id"),
            venue_model_id=venue_data.get("venue_model_id"),
        )

        # Protected core gate
        protected_core = article_data.get("protected_core", [])
        validation = validate_rewrite_plan(plan, protected_core)
        if validation.requires_user_consent:
            plan = apply_core_gate(plan, validation)

        warnings: list[str] = []
        if validation.blocked_count > 0:
            warnings.append(
                f"{validation.blocked_count} change(s) blocked — "
                f"touch protected core, require user consent"
            )

        unknowns: list[str] = []
        if hasattr(plan, "unknowns") and plan.unknowns:
            unknowns.extend(plan.unknowns)
        if validation.unknowns:
            unknowns.extend(validation.unknowns)

        entity = plan.to_dict()
        entity["_core_validation"] = validation.to_dict()

        return service_output(
            "RewritePlan",
            entity,
            unknowns=unknowns,
            warnings=warnings,
            confidence="medium",
            trace_notes=[
                f"changes={len(plan.changes)}",
                f"core_blocked={validation.blocked_count}",
            ],
        )
