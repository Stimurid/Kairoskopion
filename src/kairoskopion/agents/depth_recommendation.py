"""DepthRecommendationAgent — Organ #5.

Recommends optimal depth mode given article complexity and venue state.
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
from ..prompts.depth_recommendation import (
    DEPTH_RECOMMENDATION_FAMILY,
    validate_depth_recommendation,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


class DepthRecommendationAgent(AgentRole):
    role_id = "depth_recommendation"

    def execute(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        article_summary = inp.entities.get("article_summary", "")
        venue_summary = inp.entities.get("venue_summary", "")
        current_depth = inp.user_constraints.get("current_depth", "standard")
        budget = inp.user_constraints.get("budget_constraints", "none")
        state = inp.user_constraints.get("investigation_state", "initial")

        if isinstance(article_summary, dict):
            article_summary = json.dumps(
                article_summary, ensure_ascii=False, indent=2,
            )
        if isinstance(venue_summary, dict):
            venue_summary = json.dumps(
                venue_summary, ensure_ascii=False, indent=2,
            )

        family = DEPTH_RECOMMENDATION_FAMILY
        user_prompt = family["user_prompt_template"].format(
            article_summary=article_summary or "not available",
            venue_summary=venue_summary or "not available",
            current_depth=current_depth,
            budget_constraints=budget or "none",
            investigation_state=state,
        )
        messages = [
            {"role": "system", "content": family["system_prompt"]},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = provider.complete(
                messages,
                response_schema=family["output_schema"],
                temperature=0.2,
                max_tokens=1024,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("DepthRecommendation LLM call failed: %s", exc)
            meta = LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_PROVIDER_ERROR,
                provider="openai_compatible",
                validation_errors=[str(exc)[:200]],
                parse_status="not_attempted",
            )
            return self._honest_fallback(current_depth, meta)

        parsed, meta, _repair_steps, _errors = classify_llm_response(
            response, family["output_schema"],
        )
        if parsed is None:
            return self._honest_fallback(current_depth, meta)

        warnings = validate_depth_recommendation(parsed)

        return AgentOutput(
            output_entity_type="DepthRecommendation",
            output_entity={
                "recommended_depth": parsed.get(
                    "recommended_depth", current_depth,
                ),
                "reasoning": parsed.get("reasoning", ""),
                "cost_tradeoff": parsed.get("cost_tradeoff", ""),
                "extraction_attempt": meta.to_dict(),
                "confidence": parsed.get("confidence", "medium"),
                "warnings": parsed.get("warnings", []),
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
        current_depth: str,
        meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        return AgentOutput(
            output_entity_type="DepthRecommendation",
            output_entity={
                "recommended_depth": current_depth,
                "reasoning": "",
                "cost_tradeoff": "",
                "extraction_attempt": meta.to_dict(),
                "confidence": "none",
                "warnings": ["LLM depth recommendation unavailable — "
                             "current mode unchanged"],
            },
            confidence="none",
            warnings=[
                "LLM depth recommendation unavailable — "
                "keeping current depth mode"
            ],
            quality_gate_status="preliminary",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        current_depth = inp.user_constraints.get("current_depth", "standard")
        return self._honest_fallback(
            current_depth=current_depth,
            meta=LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_LLM_UNAVAILABLE,
                provider="none",
            ),
        )
