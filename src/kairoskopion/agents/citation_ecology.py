"""CitationEcology agent — Organ #9.

Analyzes bibliography × venue context for semantic gaps and strategies.
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
from ..prompts.citation_ecology_analysis import (
    CITATION_ECOLOGY_FAMILY,
    validate_citation_ecology,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)

_ARTICLE_COMPACT_FIELDS = (
    "title_current", "language", "problem_statement",
    "core_claims", "key_terms", "method_status",
    "disciplinary_register_current",
)

_VENUE_COMPACT_FIELDS = (
    "canonical_name", "venue_type", "scope_summary",
    "article_types_supported",
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


class CitationEcologyAgent(AgentRole):
    role_id = "citation_ecology"

    def execute(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        article = inp.entities.get("article", {})
        venue = inp.entities.get("venue", {})
        bibliography = inp.entities.get("bibliography", {})
        venue_guidelines = inp.entities.get("venue_guidelines", "")

        family = CITATION_ECOLOGY_FAMILY
        user_prompt = family["user_prompt_template"].format(
            article_compact=_compact(article, _ARTICLE_COMPACT_FIELDS),
            bibliography_json=json.dumps(
                bibliography, ensure_ascii=False, indent=2,
            )[:4000],
            venue_compact=_compact(venue, _VENUE_COMPACT_FIELDS),
            venue_guidelines=str(venue_guidelines)[:2000]
            if venue_guidelines else "(not available)",
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
            logger.warning("CitationEcology LLM call failed: %s", exc)
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

        warnings = validate_citation_ecology(parsed)

        return AgentOutput(
            output_entity_type="CitationEcologyReport",
            output_entity={
                "gaps": parsed.get("gaps", []),
                "bridge_references": parsed.get("bridge_references", []),
                "ecology_health": parsed.get("ecology_health", "adequate"),
                "venue_canon_alignment": parsed.get(
                    "venue_canon_alignment", "",
                ),
                "summary": parsed.get("summary", ""),
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
            output_entity_type="CitationEcologyReport",
            output_entity={
                "gaps": [],
                "bridge_references": [],
                "ecology_health": "unknown",
                "venue_canon_alignment": "",
                "summary": "needs_llm",
                "extraction_attempt": meta.to_dict(),
                "confidence": "none",
                "unknowns": [
                    "LLM citation ecology analysis unavailable",
                ],
            },
            confidence="none",
            warnings=[
                "LLM citation ecology agent unavailable — "
                "report blocked"
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
