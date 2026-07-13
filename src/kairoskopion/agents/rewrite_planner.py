"""RewritePlanner agent — Organ #8.

Given MismatchMap, produces RewritePlan with semantic justification.
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
from ..prompts.rewrite_planning import (
    REWRITE_PLANNING_FAMILY,
    validate_rewrite_plan,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)

_ARTICLE_COMPACT_FIELDS = (
    "title_current", "language", "problem_statement",
    "object_of_inquiry", "core_claims", "key_terms",
    "method_status", "genre_current", "argument_structure_current",
    "novelty_mode", "disciplinary_register_current",
)

_VENUE_COMPACT_FIELDS = (
    "canonical_name", "venue_type", "scope_summary",
    "article_types_supported", "language_policy",
    "open_access_status", "anonymization_policy",
    "review_process_claims",
)


def _compact(data: dict[str, Any], fields: tuple[str, ...]) -> str:
    out: list[str] = []
    for f in fields:
        v = data.get(f)
        if v in (None, "", [], {}):
            continue
        if isinstance(v, list):
            v = "; ".join(str(x) for x in v if x)
        if isinstance(v, str) and len(v) > 400:
            v = v[:400] + "…"
        out.append(f"{f}: {v}")
    return "\n".join(out) or "(empty)"


class RewritePlannerAgent(AgentRole):
    role_id = "rewrite_planner"

    def execute(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        article = inp.entities.get("article", {})
        venue = inp.entities.get("venue", {})
        mismatches = inp.entities.get("mismatches", [])

        if not mismatches:
            meta = LLMAttemptMetadata.not_attempted()
            return AgentOutput(
                output_entity_type="RewritePlan",
                output_entity={
                    "changes": [],
                    "summary": "No mismatches — no rewrite needed.",
                    "extraction_attempt": meta.to_dict(),
                },
                confidence="high",
                quality_gate_status="preliminary",
            )

        def _safe(key: str) -> str:
            v = inp.entities.get(key)
            if v is None:
                return "not available"
            if isinstance(v, str):
                return v[:4000]
            return json.dumps(v, ensure_ascii=False, default=str)[:4000]

        family = REWRITE_PLANNING_FAMILY
        user_prompt = family["user_prompt_template"].format(
            article_compact=_compact(article, _ARTICLE_COMPACT_FIELDS),
            protected_core=_safe("protected_core"),
            venue_compact=_compact(venue, _VENUE_COMPACT_FIELDS),
            fit_assessment=_safe("fit_assessment"),
            mismatches_json=json.dumps(
                mismatches, ensure_ascii=False, indent=2,
            ),
            risk_report=_safe("risk_report"),
            citation_plan=_safe("citation_plan"),
            compliance_checklist=_safe("compliance_checklist"),
            scenario_json=_safe("scenario"),
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
                agent_role="rewrite_planner",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("RewritePlanner LLM call failed: %s", exc)
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

        warnings = validate_rewrite_plan(parsed)

        return AgentOutput(
            output_entity_type="RewritePlan",
            output_entity={
                "changes": parsed.get("changes", []),
                "summary": parsed.get("summary", ""),
                "total_estimated_difficulty": parsed.get(
                    "total_estimated_difficulty", "",
                ),
                "extraction_attempt": meta.to_dict(),
                "confidence": parsed.get("confidence", "medium"),
                "unknowns": parsed.get("unknowns", []),
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
            output_entity_type="RewritePlan",
            output_entity={
                "changes": [],
                "summary": "needs_llm_rewrite_planner",
                "extraction_attempt": meta.to_dict(),
                "lifecycle_status": "blocked",
            },
            confidence="none",
            warnings=[
                "LLM rewrite planner unavailable — "
                "rewrite plan blocked"
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
