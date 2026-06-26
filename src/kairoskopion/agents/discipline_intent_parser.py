"""DisciplineIntentParser agent — Organ #1.

Interprets discipline intent using article evidence and constraints.
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
from ..llm.provider import LLMProvider
from ..prompts.discipline_intent_parsing import (
    DISCIPLINE_INTENT_FAMILY,
    validate_discipline_intent,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


def _safe_json(obj: Any) -> str:
    if obj is None:
        return "not available"
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, ensure_ascii=False, default=str)[:4000]


class DisciplineIntentParserAgent(AgentRole):
    role_id = "discipline_intent_parser"

    def execute(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        intent_text = inp.raw_text or ""
        uc = inp.user_constraints or {}
        entities = inp.entities or {}
        region_hint = uc.get("region_hint", "")
        constraints = uc.get("constraints", [])
        if isinstance(constraints, list):
            constraints_str = json.dumps(constraints, ensure_ascii=False)
        else:
            constraints_str = str(constraints)

        family = DISCIPLINE_INTENT_FAMILY
        user_prompt = family["user_prompt_template"].format(
            intent_text=intent_text,
            article_summary=_safe_json(entities.get("article")),
            semantic_profile=_safe_json(entities.get("semantic_profile")),
            discipline_matches=_safe_json(
                entities.get("discipline_matches"),
            ),
            protected_core=_safe_json(entities.get("protected_core")),
            scenario_constraints=_safe_json(entities.get("scenario")),
            region_hint=region_hint or "not specified",
            user_constraints=constraints_str or "none",
            reframe_tolerance=_safe_json(
                uc.get("reframe_tolerance", "not specified"),
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
                max_tokens=2048,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("DisciplineIntentParser LLM call failed: %s", exc)
            meta = LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_PROVIDER_ERROR,
                provider="openai_compatible",
                validation_errors=[str(exc)[:200]],
                parse_status="not_attempted",
            )
            return self._honest_fallback(intent_text, meta)

        parsed, meta, _repair_steps, _errors = classify_llm_response(
            response, family["output_schema"],
        )
        if parsed is None:
            return self._honest_fallback(intent_text, meta)

        warnings = validate_discipline_intent(parsed)

        return AgentOutput(
            output_entity_type="DisciplineIntentResult",
            output_entity={
                "intent_text": intent_text,
                "parse_result": parsed,
                "extraction_attempt": meta.to_dict(),
                "intent_parse_status": "parsed",
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
        intent_text: str,
        meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        return AgentOutput(
            output_entity_type="DisciplineIntentResult",
            output_entity={
                "intent_text": intent_text,
                "parse_result": None,
                "extraction_attempt": meta.to_dict(),
                "intent_parse_status": "needs_llm",
            },
            confidence="none",
            warnings=[
                "LLM discipline intent interpreter unavailable — "
                "intent_parse_status remains 'needs_llm'"
            ],
            quality_gate_status="blocked",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        intent_text = inp.raw_text or ""
        return self._honest_fallback(
            intent_text=intent_text,
            meta=LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_LLM_UNAVAILABLE,
                provider="none",
            ),
        )
