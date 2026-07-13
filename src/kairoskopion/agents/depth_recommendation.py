"""DepthRecommendationAgent — Organ #5.

Canonical 5-mode depth strategy with mechanical cost awareness.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..llm.attempt_metadata import (
    FALLBACK_REASON_LLM_UNAVAILABLE,
    FALLBACK_REASON_PROVIDER_ERROR,
    LLMAttemptMetadata,
    classify_llm_response,
)
from ..llm.config import max_tokens_for_role
from ..llm.provider import LLMProvider
from ..prompts.depth_recommendation import (
    DEPTH_RECOMMENDATION_FAMILY,
    validate_depth_recommendation,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


def _safe_json(obj: Any) -> str:
    if obj is None:
        return "not available"
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, ensure_ascii=False, default=str)[:4000]


class DepthRecommendationAgent(AgentRole):
    role_id = "depth_recommendation"

    def execute(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        entities = inp.entities or {}
        uc = inp.user_constraints or {}
        current_depth = uc.get(
            "current_depth", "light_profile",
        )

        family = DEPTH_RECOMMENDATION_FAMILY
        user_prompt = family["user_prompt_template"].format(
            article_complexity=_safe_json(
                entities.get("article_complexity"),
            ),
            venue_uncertainty=_safe_json(
                entities.get("venue_uncertainty"),
            ),
            epistemic_regime=_safe_json(
                entities.get("epistemic_regime"),
            ),
            protected_core_risk=_safe_json(
                entities.get("protected_core_risk"),
            ),
            submission_stakes=_safe_json(
                uc.get("submission_stakes"),
            ),
            budget_constraints=_safe_json(
                uc.get("budget_constraints"),
            ),
            current_depth=current_depth,
            organ_statuses=_safe_json(
                entities.get("organ_statuses"),
            ),
            cost_estimates=_safe_json(
                entities.get("cost_estimates"),
            ),
            source_availability=_safe_json(
                entities.get("source_availability"),
            ),
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
                max_tokens=max_tokens_for_role(self.role_id),
                agent_role="depth_recommendation",
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
                "why_not_shallower": parsed.get(
                    "why_not_shallower", "",
                ),
                "why_not_deeper": parsed.get("why_not_deeper", ""),
                "organs_to_run": parsed.get("organs_to_run", []),
                "cost_risk_tradeoff": parsed.get(
                    "cost_risk_tradeoff", "",
                ),
                "expected_uncertainty_reduction": parsed.get(
                    "expected_uncertainty_reduction", [],
                ),
                "user_decision_required": parsed.get(
                    "user_decision_required", [],
                ),
                "stop_conditions": parsed.get("stop_conditions", []),
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
                "why_not_shallower": "",
                "why_not_deeper": "",
                "extraction_attempt": meta.to_dict(),
                "confidence": "none",
                "warnings": [
                    "LLM depth recommendation unavailable — "
                    "current mode unchanged",
                ],
            },
            confidence="none",
            warnings=[
                "LLM depth recommendation unavailable — "
                "keeping current depth mode"
            ],
            quality_gate_status="preliminary",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        current_depth = (inp.user_constraints or {}).get(
            "current_depth", "light_profile",
        )
        return self._honest_fallback(
            current_depth=current_depth,
            meta=LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_LLM_UNAVAILABLE,
                provider="none",
            ),
        )
