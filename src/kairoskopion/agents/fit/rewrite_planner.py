"""Rewrite Planner — LLM-backed rewrite planning with deterministic fallback + protected core gate."""

from __future__ import annotations

import json

from ..base_shell import llm_agent_output, missing_input_output, service_output, try_llm_call
from ..contract import AgentInput, AgentOutput, AgentRole
from ..prompt_families.rewrite_planning import REWRITE_PLANNING_FAMILY
from ...llm.provider import LLMProvider
from ...schema import MismatchMap
from ...services.protected_core import apply_core_gate, validate_rewrite_plan
from ...services.rewrite_planning import build_rewrite_plan


class RewritePlannerAgent(AgentRole):
    role_id = "rewrite_planner"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        mm_data = inp.entities.get("mismatch_map")
        if not mm_data:
            return missing_input_output("RewritePlan", "mismatch_map")

        article_data = inp.entities.get("article", {})
        venue_data = inp.entities.get("venue", {})

        result = try_llm_call(provider, REWRITE_PLANNING_FAMILY, {
            "mismatch_json": json.dumps(mm_data, ensure_ascii=False, indent=2),
            "article_json": json.dumps(article_data, ensure_ascii=False, indent=2),
            "venue_json": json.dumps(venue_data, ensure_ascii=False, indent=2),
        })
        if result is None:
            return self.execute_deterministic(inp)

        parsed, meta = result
        warnings = REWRITE_PLANNING_FAMILY["validator"](parsed)
        return llm_agent_output("RewritePlan", parsed, meta, warnings)

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
