"""DisciplineMatcherAgent (Phase B).

Picks up to 10 disciplines from the registry that the article would
legitimately be read in. May propose ONE new_candidate per call.

ARCH-SEM-001: all matched disciplines MUST be LLM-produced.
Deterministic candidate retrieval is used only as INPUT to the prompt,
never as user-facing output. If LLM is unavailable or fails,
SemanticLLMRequiredError is raised — no silent fallback.
"""

from __future__ import annotations

import logging

from ..llm.attempt_metadata import (
    FALLBACK_REASON_LLM_UNAVAILABLE,
    FALLBACK_REASON_PROVIDER_ERROR,
    LLMAttemptMetadata,
)
from ..llm.config import max_tokens_for_role
from ..llm.openai_compat import SemanticLLMRequiredError
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

try:
    from ..prompts.discipline_matching import (
        DISCIPLINE_MATCHING_V3_FAMILY,
        validate_discipline_match_v3,
    )
except ImportError:
    DISCIPLINE_MATCHING_V3_FAMILY = None
    validate_discipline_match_v3 = None
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

        family = (
            DISCIPLINE_MATCHING_V3_FAMILY
            if DISCIPLINE_MATCHING_V3_FAMILY is not None
            else DISCIPLINE_MATCHING_V2_FAMILY
        )
        user_prompt = family["user_prompt_template"].format(
            article_summary=summary[:_SUMMARY_CHAR_CAP],
            region=region,
            candidate_block=candidate_block,
        )
        messages = [
            {"role": "system", "content": family["system_prompt"]},
            {"role": "user", "content": user_prompt},
        ]

        role_max_tokens = max_tokens_for_role(self.role_id)
        try:
            response = provider.complete(
                messages,
                response_schema=family["output_schema"],
                temperature=0.0,
                max_tokens=role_max_tokens,
                agent_role="discipline_matcher",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "LLM call failed for discipline_matcher: %s", exc,
            )
            raise SemanticLLMRequiredError(
                f"Discipline matching requires LLM — provider error: {exc}",
                agent_role="discipline_matcher",
                error_code="SEMANTIC_LLM_REQUIRED",
                attempts=[str(exc)[:240]],
            ) from exc

        truncated = response.finish_reason == "length"
        if truncated:
            logger.warning(
                "Discipline matcher output truncated (finish_reason=length, "
                "output_tokens=%s, max_tokens=%s)",
                response.output_tokens, role_max_tokens,
            )
            raise SemanticLLMRequiredError(
                "Discipline matching output truncated — increase max_tokens or reduce input",
                agent_role="discipline_matcher",
                error_code="OUTPUT_TRUNCATED",
                attempts=[
                    f"finish_reason=length; output_tokens={response.output_tokens}; "
                    f"model={response.effective_model or response.model}"
                ],
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
                    "Discipline matcher returned non-JSON / unrepairable "
                    "(finish_reason=%s)",
                    response.finish_reason,
                )
                raise SemanticLLMRequiredError(
                    "Discipline matching LLM returned non-JSON / unrepairable output",
                    agent_role="discipline_matcher",
                    error_code="INVALID_JSON",
                    attempts=list(response.attempts),
                )

        validator = (
            validate_discipline_match_v3
            if validate_discipline_match_v3 is not None
            and DISCIPLINE_MATCHING_V3_FAMILY is not None
            else validate_discipline_match
        )
        warnings = validator(parsed)

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
        # ARCH-SEM-001: no deterministic padding. If LLM returned <10,
        # record the count as-is. The caller may request a repair call.
        if len(cleaned) < 10:
            warnings.append(
                f"LLM returned {len(cleaned)} disciplines (contract asks 10) — "
                f"consider a repair call"
            )
        parsed["matched"] = cleaned

        return AgentOutput(
            output_entity_type="DisciplineMatch",
            output_entity=parsed,
            confidence=parsed.get("confidence", "low"),
            warnings=warnings,
            quality_gate_status="preliminary",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        """ARCH-SEM-001: deterministic semantic discipline matching is prohibited."""
        raise SemanticLLMRequiredError(
            "Discipline matching requires LLM — deterministic semantic fallback "
            "is prohibited by ARCH-SEM-001",
            agent_role="discipline_matcher",
            error_code="SEMANTIC_LLM_REQUIRED",
        )
