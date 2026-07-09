"""VenueFunnelPlanner agent — Organ #2.

Produces venue family plan using corpus/evidence, no model-memory facts.
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
from ..prompts.venue_funnel_planning import (
    VENUE_FUNNEL_FAMILY,
    validate_venue_funnel,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


def _safe_json(obj: Any) -> str:
    if obj is None:
        return "not available"
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, ensure_ascii=False, default=str)[:4000]


class VenueFunnelPlannerAgent(AgentRole):
    role_id = "venue_funnel_planner"

    def execute(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        entities = inp.entities or {}
        uc = inp.user_constraints or {}
        intent_result = entities.get("discipline_intent", {})
        region_hint = uc.get("region_hint", "")
        constraints = uc.get("constraints", [])

        family = VENUE_FUNNEL_FAMILY
        user_prompt = family["user_prompt_template"].format(
            intent_json=json.dumps(
                intent_result, ensure_ascii=False, indent=2,
            ),
            article_summary=_safe_json(entities.get("article")),
            semantic_profile=_safe_json(
                entities.get("semantic_profile"),
            ),
            scenario_json=_safe_json(entities.get("scenario")),
            corpus_summaries=_safe_json(
                entities.get("corpus_summaries"),
            ),
            evidence_summaries=_safe_json(
                entities.get("evidence_summaries"),
            ),
            venue_memory=_safe_json(entities.get("venue_memory")),
            registry_records=_safe_json(
                entities.get("registry_records"),
            ),
            user_constraints=json.dumps(constraints, ensure_ascii=False)
            if isinstance(constraints, list) else str(constraints),
            region_hint=region_hint or "not specified",
            budget=_safe_json(uc.get("budget")),
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
                agent_role="venue_funnel_planner",
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

        return AgentOutput(
            output_entity_type="VenueFunnelPlan",
            output_entity={
                "known_corpus_candidates": parsed.get(
                    "known_corpus_candidates", [],
                ),
                "candidate_families": parsed.get(
                    "candidate_families", [],
                ),
                "external_discovery_tasks": parsed.get(
                    "external_discovery_tasks", [],
                ),
                "corpus_coverage_gaps": parsed.get(
                    "corpus_coverage_gaps", [],
                ),
                "not_enough_evidence": parsed.get(
                    "not_enough_evidence", [],
                ),
                "next_user_decision": parsed.get("next_user_decision"),
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
                "known_corpus_candidates": [],
                "candidate_families": [],
                "external_discovery_tasks": [],
                "corpus_coverage_gaps": [],
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
