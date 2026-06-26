"""VenueFunnelPlanner agent — Organ #2.

Given parsed discipline intent, produces venue family plan.
"""

from __future__ import annotations

import json
import logging

from ..llm.attempt_metadata import (
    FALLBACK_REASON_LLM_UNAVAILABLE,
    FALLBACK_REASON_PROVIDER_ERROR,
    LLMAttemptMetadata,
    classify_llm_response,
)
from ..llm.provider import LLMProvider
from ..prompts.venue_funnel_planning import (
    VENUE_FUNNEL_FAMILY,
    validate_venue_funnel,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


class VenueFunnelPlannerAgent(AgentRole):
    role_id = "venue_funnel_planner"

    def execute(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        intent_result = inp.entities.get("discipline_intent", {})
        region_hint = inp.user_constraints.get("region_hint", "")
        constraints = inp.user_constraints.get("constraints", [])

        family = VENUE_FUNNEL_FAMILY
        user_prompt = family["user_prompt_template"].format(
            intent_json=json.dumps(intent_result, ensure_ascii=False, indent=2),
            region_hint=region_hint or "not specified",
            user_constraints=json.dumps(constraints, ensure_ascii=False)
            if isinstance(constraints, list) else str(constraints),
        )
        messages = [
            {"role": "system", "content": family["system_prompt"]},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = provider.complete(
                messages,
                response_schema=family["output_schema"],
                temperature=0.3,
                max_tokens=3072,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("VenueFunnelPlanner LLM call failed: %s", exc)
            meta = LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_PROVIDER_ERROR,
                provider="openai_compatible",
                validation_errors=[str(exc)[:200]],
                parse_status="not_attempted",
            )
            return self._honest_fallback(meta)

        parsed, meta, _repair_steps, _errors = classify_llm_response(
            response, family["output_schema"],
        )
        if parsed is None:
            return self._honest_fallback(meta)

        warnings = validate_venue_funnel(parsed)

        families = parsed.get("venue_families", [])
        for f in families:
            if isinstance(f, dict):
                f.setdefault("evidence_status", "llm_inference")

        return AgentOutput(
            output_entity_type="VenueFunnelPlan",
            output_entity={
                "venue_families": families,
                "search_priorities": parsed.get("search_priorities", []),
                "venue_families_status": "planned",
                "extraction_attempt": meta.to_dict(),
                "confidence": parsed.get("confidence", "medium"),
                "unknowns": parsed.get("unknowns", []),
                "reasoning": parsed.get("reasoning", ""),
            },
            confidence=parsed.get("confidence", "medium"),
            warnings=warnings,
            quality_gate_status="preliminary",
            trace_notes=[
                f"LLM model: {response.model}",
                f"Tokens: {response.input_tokens}+{response.output_tokens}",
                f"Latency: {response.latency_ms:.0f}ms",
            ],
            evidence_status="llm_inference",
            llm_usage={
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
                "extraction_attempt": meta.to_dict(),
            },
        )

    def _honest_fallback(
        self,
        meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        return AgentOutput(
            output_entity_type="VenueFunnelPlan",
            output_entity={
                "venue_families": [],
                "search_priorities": [],
                "venue_families_status": "FUNNEL_BLOCKED_NEEDS_LLM",
                "extraction_attempt": meta.to_dict(),
                "confidence": "none",
                "unknowns": ["LLM venue funnel planner unavailable"],
                "reasoning": "",
            },
            confidence="none",
            warnings=[
                "LLM venue funnel planner unavailable — "
                "venue_families_status remains 'FUNNEL_BLOCKED_NEEDS_LLM'"
            ],
            quality_gate_status="blocked",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        return self._honest_fallback(
            meta=LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_LLM_UNAVAILABLE,
                provider="none",
            ),
        )
