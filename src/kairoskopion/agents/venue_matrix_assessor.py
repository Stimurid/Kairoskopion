"""VenueMatrixAssessor agent — Organ #4.

Produces per-candidate semantic assessment on fit axes.
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
from ..prompts.venue_matrix_assessment import (
    VENUE_MATRIX_FAMILY,
    validate_venue_matrix,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


class VenueMatrixAssessorAgent(AgentRole):
    role_id = "venue_matrix_assessor"

    def execute(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        candidates = inp.entities.get("candidates", [])
        article_context = inp.entities.get("article_context", {})

        if not candidates:
            meta = LLMAttemptMetadata.not_attempted()
            return AgentOutput(
                output_entity_type="VenueMatrixAssessment",
                output_entity={
                    "assessments": [],
                    "extraction_attempt": meta.to_dict(),
                },
                confidence="high",
                quality_gate_status="preliminary",
            )

        family = VENUE_MATRIX_FAMILY
        user_prompt = family["user_prompt_template"].format(
            article_context=json.dumps(
                article_context, ensure_ascii=False, indent=2,
            ),
            candidates_json=json.dumps(
                candidates, ensure_ascii=False, indent=2,
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
                max_tokens=4096,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("VenueMatrixAssessor LLM call failed: %s", exc)
            meta = LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_PROVIDER_ERROR,
                provider="openai_compatible",
                validation_errors=[str(exc)[:200]],
                parse_status="not_attempted",
            )
            return self._honest_fallback(candidates, meta)

        parsed, meta, _repair_steps, _errors = classify_llm_response(
            response, family["output_schema"],
        )
        if parsed is None:
            return self._honest_fallback(candidates, meta)

        warnings = validate_venue_matrix(parsed)

        assessments = parsed.get("assessments", [])
        assessed_ids = {
            a.get("venue_candidate_id")
            for a in assessments if isinstance(a, dict)
        }
        for c in candidates:
            cid = c.get("venue_candidate_id", "")
            if cid and cid not in assessed_ids:
                assessments.append({
                    "venue_candidate_id": cid,
                    "canonical_name": c.get("canonical_name", ""),
                    "semantic_assessment": {
                        "topic_fit": "unknown",
                        "discipline_fit": "unknown",
                        "core_risk": "unknown",
                        "overall_impression": "not assessed by LLM",
                        "confidence": "low",
                    },
                })

        return AgentOutput(
            output_entity_type="VenueMatrixAssessment",
            output_entity={
                "assessments": assessments,
                "extraction_attempt": meta.to_dict(),
                "unknowns": parsed.get("unknowns", []),
            },
            confidence="medium",
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
        candidates: list[dict[str, Any]],
        meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        assessments = [
            {
                "venue_candidate_id": c.get("venue_candidate_id", ""),
                "canonical_name": c.get("canonical_name", ""),
                "semantic_assessment": "NOT_ASSESSED_NEEDS_LLM",
            }
            for c in candidates
        ]
        return AgentOutput(
            output_entity_type="VenueMatrixAssessment",
            output_entity={
                "assessments": assessments,
                "extraction_attempt": meta.to_dict(),
            },
            confidence="none",
            warnings=[
                "LLM venue matrix assessor unavailable — "
                "all candidates remain NOT_ASSESSED_NEEDS_LLM"
            ],
            quality_gate_status="blocked",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        candidates = inp.entities.get("candidates", [])
        return self._honest_fallback(
            candidates=candidates,
            meta=LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_LLM_UNAVAILABLE,
                provider="none",
            ),
        )
