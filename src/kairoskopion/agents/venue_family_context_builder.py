"""VenueFamilyContextBuilder agent — Organ #3.

Infers venue discipline family context from corpus evidence only.
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
from ..prompts.venue_family_context import (
    VENUE_FAMILY_CONTEXT_FAMILY,
    validate_venue_family_context,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


def _safe_json(obj: Any) -> str:
    if obj is None:
        return "not available"
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, ensure_ascii=False, default=str)[:4000]


class VenueFamilyContextBuilderAgent(AgentRole):
    role_id = "venue_family_context_builder"

    def execute(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        entities = inp.entities or {}
        venue = entities.get("venue", {})

        family = VENUE_FAMILY_CONTEXT_FAMILY
        user_prompt = family["user_prompt_template"].format(
            venue_json=json.dumps(venue, ensure_ascii=False, indent=2),
            corpus_summaries=_safe_json(
                entities.get("corpus_summaries"),
            ),
            venue_memory=_safe_json(entities.get("venue_memory")),
            article_summary=_safe_json(entities.get("article")),
            discipline_intent=_safe_json(
                entities.get("discipline_intent"),
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
                agent_role="venue_family_context_builder",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("VenueFamilyContextBuilder LLM failed: %s", exc)
            meta = LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_PROVIDER_ERROR,
                provider="openai_compatible",
                validation_errors=[str(exc)[:200]],
                parse_status="not_attempted",
            )
            return self._honest_fallback(venue, meta)

        parsed, meta, _repair_steps, _errors = classify_llm_response(
            response, family["output_schema"],
        )
        if parsed is None:
            return self._honest_fallback(venue, meta)

        warnings = validate_venue_family_context(parsed)

        return AgentOutput(
            output_entity_type="VenueFamilyContext",
            output_entity={
                "source_venue": parsed.get("source_venue", ""),
                "families": parsed.get("families", []),
                "corpus_coverage_warning": parsed.get(
                    "corpus_coverage_warning",
                ),
                "recommended_next_action": parsed.get(
                    "recommended_next_action",
                ),
                "families_status": parsed.get(
                    "families_status", "assessed",
                ),
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
        venue: dict[str, Any],
        meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        return AgentOutput(
            output_entity_type="VenueFamilyContext",
            output_entity={
                "source_venue": venue.get("canonical_name", ""),
                "families": [],
                "families_status": "BLOCKED_NEEDS_LLM",
                "extraction_attempt": meta.to_dict(),
                "confidence": "none",
                "unknowns": [
                    "LLM venue family context builder unavailable",
                ],
                "reasoning": "",
            },
            confidence="none",
            warnings=[
                "LLM venue family context builder unavailable — "
                "families_status remains 'BLOCKED_NEEDS_LLM'"
            ],
            quality_gate_status="blocked",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        venue = (inp.entities or {}).get("venue", {})
        return self._honest_fallback(
            venue=venue,
            meta=LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_LLM_UNAVAILABLE,
                provider="none",
            ),
        )
