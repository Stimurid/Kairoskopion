"""ComplianceAssessor agent — Organ #13.

Semantic compliance assessment layered on top of structural pre-check.
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
from ..prompts.compliance_assessment import (
    COMPLIANCE_ASSESSMENT_FAMILY,
    validate_compliance_assessment,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)

_ARTICLE_COMPACT_FIELDS = (
    "title_current", "language", "abstract",
    "word_count", "genre_current", "method_status",
)

_VENUE_COMPACT_FIELDS = (
    "canonical_name", "venue_type", "scope_summary",
    "language_policy", "word_limits",
    "anonymization_policy", "ai_policy", "data_policy",
    "ethics_policy",
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


class ComplianceAssessorAgent(AgentRole):
    role_id = "compliance_assessor"

    def execute(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        article = inp.entities.get("article", {})
        venue = inp.entities.get("venue", {})
        structural_checklist = inp.entities.get(
            "structural_checklist", {},
        )

        family = COMPLIANCE_ASSESSMENT_FAMILY
        user_prompt = family["user_prompt_template"].format(
            structural_checklist_json=json.dumps(
                structural_checklist, ensure_ascii=False, indent=2,
            )[:4000],
            article_compact=_compact(article, _ARTICLE_COMPACT_FIELDS),
            venue_compact=_compact(venue, _VENUE_COMPACT_FIELDS),
        )
        messages = [
            {"role": "system", "content": family["system_prompt"]},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = provider.complete(
                messages,
                response_schema=family["output_schema"],
                temperature=0.1,
                max_tokens=4096,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("ComplianceAssessor LLM call failed: %s", exc)
            meta = LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_PROVIDER_ERROR,
                provider="openai_compatible",
                validation_errors=[str(exc)[:200]],
                parse_status="not_attempted",
            )
            return self._honest_fallback(structural_checklist, meta)

        parsed, meta, _repair_steps, _errors = classify_llm_response(
            response, family["output_schema"],
        )
        if parsed is None:
            return self._honest_fallback(structural_checklist, meta)

        warnings = validate_compliance_assessment(parsed)

        return AgentOutput(
            output_entity_type="ComplianceChecklist",
            output_entity={
                "items": parsed.get("items", []),
                "overall_compliance": parsed.get(
                    "overall_compliance", "insufficient_data",
                ),
                "summary": parsed.get("summary", ""),
                "semantic_pass": True,
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
        structural_checklist: dict[str, Any],
        meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        return AgentOutput(
            output_entity_type="ComplianceChecklist",
            output_entity={
                "items": structural_checklist.get("items", []),
                "overall_compliance": "insufficient_data",
                "summary": "structural_only — semantic assessment needs LLM",
                "semantic_pass": False,
                "extraction_attempt": meta.to_dict(),
                "confidence": "structural_only",
                "unknowns": [
                    "LLM compliance assessor unavailable — "
                    "structural checklist preserved",
                ],
            },
            confidence="low",
            warnings=[
                "LLM compliance assessor unavailable — "
                "structural-only checklist preserved"
            ],
            quality_gate_status="preliminary",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        structural_checklist = inp.entities.get(
            "structural_checklist", {},
        )
        return self._honest_fallback(
            structural_checklist=structural_checklist,
            meta=LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_LLM_UNAVAILABLE,
                provider="none",
            ),
        )
