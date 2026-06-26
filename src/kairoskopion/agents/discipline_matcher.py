"""DisciplineMatcherAgent (Phase B).

Picks 0-4 disciplines from the registry that the article would
legitimately be read in. May propose ONE new_candidate per call.

Inputs (via AgentInput.entities):
- ``article_summary`` (str) — concise summary of the article (built
  by the caller from ArticleModel + semantic profile)
- ``region`` (str) — operator hint: ``ru`` / ``international`` / etc.
  Drives initial candidate filtering. Cross-region matching still
  works because ``international_mapping`` is honored.

The LLM path scores the candidates and may propose new_candidates.
The deterministic fallback is honest: it returns the keyword-matcher's
output verbatim and marks the verdict ``confidence='low'``, asking the
caller to surface "no LLM matcher available, here's the keyword hint".

NEVER returns a single ``unknown`` placeholder pretending to be a
discipline. If nothing matches, returns an empty list.
"""

from __future__ import annotations

import logging

from ..llm.attempt_metadata import (
    FALLBACK_REASON_LLM_UNAVAILABLE,
    FALLBACK_REASON_PROVIDER_ERROR,
    LLMAttemptMetadata,
)
from ..llm.json_repair import (
    PARSE_STATUS_PARSED_OK,
    PARSE_STATUS_REPAIRED_OK,
    repair_and_parse,
)
from ..llm.provider import LLMProvider
from ..prompts.discipline_matching import (
    DISCIPLINE_MATCHING_FAMILY,
    DISCIPLINE_MATCHING_V2_FAMILY,
    validate_discipline_match,
)
from ..services.discipline_registry import DisciplineRegistry, load_default_registry
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)

# Cap on how many candidate cards we feed into the LLM prompt. The
# user's design note: "even with 100 disciplines, build the matcher
# interface as if 500 were already loaded" — so we always narrow
# before LLM, never dump the whole registry.
_CANDIDATE_FEED_CAP = 20
# Cap on the article summary the LLM sees — the matcher's job is
# semantic, not extractive. A long article need not flood the prompt.
_SUMMARY_CHAR_CAP = 4_000


def _build_candidate_block(disciplines, summary_chars: int = 800) -> str:
    if not disciplines:
        return "(empty — registry has no region-matching disciplines yet)"
    lines = [f"- {d.summary_for_context(summary_chars)}" for d in disciplines]
    return "\n".join(lines)


class DisciplineMatcherAgent(AgentRole):
    role_id = "discipline_matcher"

    def __init__(self, registry: DisciplineRegistry | None = None):
        self._registry = registry

    def _get_registry(self) -> DisciplineRegistry:
        if self._registry is None:
            self._registry = load_default_registry()
        return self._registry

    def _gather_candidates(self, summary: str, region: str):
        registry = self._get_registry()
        if not summary or not summary.strip():
            return registry.by_region(region)[:_CANDIDATE_FEED_CAP]
        # Keyword pre-filter — recall-oriented, may over-fetch.
        candidates = registry.candidates_keyword(
            summary, region=region, limit=_CANDIDATE_FEED_CAP,
        )
        if not candidates:
            # Fallback: just give the region's top entries by usage.
            pool = registry.by_region(region)
            pool.sort(key=lambda d: (-d.times_seen, d.discipline_id))
            candidates = pool[:_CANDIDATE_FEED_CAP]
        return candidates

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        summary = (inp.entities.get("article_summary") or inp.raw_text or "").strip()
        region = (inp.entities.get("region") or "auto").strip() or "auto"

        candidates = self._gather_candidates(summary, region)
        candidate_block = _build_candidate_block(candidates)

        family = DISCIPLINE_MATCHING_V2_FAMILY
        user_prompt = family["user_prompt_template"].format(
            article_summary=summary[:_SUMMARY_CHAR_CAP],
            region=region,
            candidate_block=candidate_block,
        )
        messages = [
            {"role": "system", "content": family["system_prompt"]},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = provider.complete(
                messages,
                response_schema=family["output_schema"],
                temperature=0.0,
                max_tokens=1024,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "LLM call failed for discipline_matcher: %s", exc,
            )
            return self._deterministic_with_attempt(
                candidates,
                LLMAttemptMetadata.fallback(
                    reason=FALLBACK_REASON_PROVIDER_ERROR,
                    provider="openai_compatible",
                    validation_errors=[str(exc)[:240]],
                ),
            )

        parsed = response.parsed
        if not isinstance(parsed, dict):
            outcome = repair_and_parse(
                response.content, schema=family.get("output_schema"),
            )
            parsed = outcome.parsed
            if parsed is None or outcome.status not in (
                PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK,
            ):
                logger.warning(
                    "Discipline matcher returned non-JSON / unrepairable",
                )
                return self._deterministic_with_attempt(
                    candidates,
                    LLMAttemptMetadata.fallback(
                        reason="invalid_json",
                        provider="openai_compatible",
                    ),
                )

        warnings = validate_discipline_match(parsed)

        # Filter matched ids that are not in the candidate set — the
        # model occasionally hallucinates ids. Drop silently rather
        # than fail; record as warning.
        valid_ids = {d.discipline_id for d in candidates}
        cleaned = []
        for m in parsed.get("matched", []):
            if m.get("discipline_id") in valid_ids:
                cleaned.append(m)
            else:
                warnings.append(
                    f"dropped matched id not in candidate set: "
                    f"{m.get('discipline_id')!r}"
                )
        parsed["matched"] = cleaned

        return AgentOutput(
            output_entity_type="DisciplineMatch",
            output_entity=parsed,
            confidence=parsed.get("confidence", "low"),
            warnings=warnings,
            quality_gate_status="preliminary",
        )

    def _deterministic_with_attempt(
        self,
        candidates,
        attempt: LLMAttemptMetadata,
    ) -> AgentOutput:
        """Fallback that NEVER fabricates a match. Returns the keyword
        candidates verbatim, tagged with confidence='low' and a
        Russian reasoning sentence."""
        matched = [
            {
                "discipline_id": d.discipline_id,
                "strength": "tangential",
                "why": "Кандидат предложен keyword-фильтром реестра — без LLM-проверки.",
            }
            for d in candidates[:4]
        ]
        return AgentOutput(
            output_entity_type="DisciplineMatch",
            output_entity={
                "matched": matched,
                "new_candidate": None,
                "confidence": "low",
                "reasoning": (
                    "LLM-матчер недоступен; показаны kandidatы из "
                    "keyword-фильтра. Перезапустите при доступном "
                    "LLM-провайдере."
                ),
                "extraction_attempt": attempt.to_dict(),
            },
            confidence="low",
            warnings=["LLM matcher unavailable — keyword fallback only"],
            quality_gate_status="preliminary",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        summary = (inp.entities.get("article_summary") or inp.raw_text or "").strip()
        region = (inp.entities.get("region") or "auto").strip() or "auto"
        candidates = self._gather_candidates(summary, region)
        return self._deterministic_with_attempt(
            candidates,
            LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_LLM_UNAVAILABLE,
                provider="none",
            ),
        )
