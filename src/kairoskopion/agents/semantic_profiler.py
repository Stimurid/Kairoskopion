"""Article Semantic Profiler agent (UC-1 step 3, extended Article Modeler).

Builds ArticleSemanticProfile — the extended disciplinary/school/tradition/
argument-move profile that goes beyond ArticleModel's base fields.

This is the profiling step that feeds into DisciplinaryPathwayMapper
and ultimately into Venue Pool Discovery.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..enums import ArgumentMoveType, EvidenceStatus
from ..ids import article_semantic_profile_id
from ..llm.attempt_metadata import (
    FALLBACK_REASON_PROVIDER_ERROR,
    LLMAttemptMetadata,
    classify_llm_response,
)
from ..llm.provider import LLMProvider
from ..prompts.semantic_profiling import (
    SEMANTIC_PROFILING_FAMILY,
    validate_semantic_profile,
)
from ..schema import ArticleSemanticProfile
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


def _build_known_disciplines_context(article_dict: dict, text: str) -> str:
    """Build a compact block of registry-known disciplines that look
    plausibly relevant to this article, by keyword pre-filter.

    Best-effort: returns a placeholder if the registry can't be loaded
    (e.g. data dir missing in tests). NEVER raises — the semantic
    profile should still run when the registry is unavailable.
    """
    try:
        from ..services.discipline_registry import load_default_registry
        registry = load_default_registry()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Discipline registry unavailable: %s", exc)
        return "(registry unavailable)"
    if len(registry) == 0:
        return "(registry empty)"
    # Build a lightweight haystack from the article fields + first
    # slice of text — enough for the keyword pre-filter, not enough to
    # blow the prompt budget.
    article_blob = " ".join(
        str(v) for v in article_dict.values() if isinstance(v, (str, list))
    )
    haystack = (article_blob + " " + (text[:2000] if text else ""))[:6000]
    candidates = registry.candidates_keyword(haystack, region="auto", limit=15)
    if not candidates:
        return "(no registry candidates surfaced by keyword pre-filter)"
    return "\n".join(f"- {d.summary_for_context(600)}" for d in candidates)


class ArticleSemanticProfilerAgent(AgentRole):
    role_id = "article_semantic_profiler"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        article_dict = inp.entities.get("article", {})
        text = inp.raw_text or ""

        # Phase B: pull discipline candidates from the registry to feed
        # the LLM as soft context. Caller may inject a pre-narrowed
        # block; otherwise we build one here from the article fields.
        known_disciplines_context = (
            inp.entities.get("known_disciplines_context")
            or _build_known_disciplines_context(article_dict, text)
        )

        family = SEMANTIC_PROFILING_FAMILY
        user_prompt = family["user_prompt_template"].format(
            article_json=json.dumps(article_dict, ensure_ascii=False, indent=2),
            manuscript_text=text[:8000] if text else "(no raw text available)",
            known_disciplines_context=known_disciplines_context,
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
                max_tokens=4096,
            )
        except Exception as e:
            logger.warning("LLM call failed for semantic_profiler, falling back: %s", e)
            meta = LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_PROVIDER_ERROR,
                provider="openai_compatible",
                model=None,
                validation_errors=[str(e)[:240]],
                parse_status="invalid_json",
            )
            return self._deterministic_with_attempt(inp, meta)

        parsed, meta, repair_steps, errors = classify_llm_response(
            response, family["output_schema"],
        )
        if parsed is None:
            logger.warning(
                "LLM semantic_profiler fallback: reason=%s steps=%s",
                meta.fallback_reason, repair_steps,
            )
            return self._deterministic_with_attempt(inp, meta)

        validation_warnings = validate_semantic_profile(parsed)
        profile = _build_from_llm(parsed, article_dict.get("article_model_id"))
        profile.extraction_attempt = meta.to_dict()

        return AgentOutput(
            output_entity_type="ArticleSemanticProfile",
            output_entity=profile.to_dict(),
            evidence_refs=[],
            unknowns=parsed.get("unknowns", []),
            assumptions=[],
            confidence=parsed.get("confidence", "medium"),
            warnings=validation_warnings,
            questions_for_user=parsed.get("questions_for_user", []),
            quality_gate_status="preliminary",
            trace_notes=[
                f"LLM model: {response.model}",
                f"Tokens: {response.input_tokens}+{response.output_tokens}",
                f"Latency: {response.latency_ms:.0f}ms",
                f"parse_status: {meta.parse_status}",
            ],
            evidence_status=EvidenceStatus.INFERENCE.value,
            llm_usage={
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
                "extraction_attempt": meta.to_dict(),
            },
        )

    def _deterministic_with_attempt(
        self, inp: AgentInput, meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        """Annotate the deterministic-fallback semantic profile with
        the captured LLM attempt metadata."""
        out = self.execute_deterministic(inp)
        meta_dict = meta.to_dict()
        if isinstance(out.output_entity, dict):
            out.output_entity["extraction_attempt"] = meta_dict
        out.trace_notes = list(out.trace_notes or []) + [
            f"fallback_reason: {meta.fallback_reason}",
            f"parse_status: {meta.parse_status}",
        ]
        if meta.warning_for_user:
            out.warnings = list(out.warnings or []) + [meta.warning_for_user]
        return out

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        article_dict = inp.entities.get("article", {})

        profile = ArticleSemanticProfile(
            article_model_id=article_dict.get("article_model_id"),
            disciplinary_registers=[
                article_dict.get("disciplinary_register_current", "unknown")
            ],
            primary_discipline=article_dict.get("disciplinary_register_current"),
            schools_and_traditions=[],
            theoretical_shoulders=article_dict.get("theoretical_shoulders", []),
            protected_core_candidates=article_dict.get("protected_core", []),
            mutable_zones=article_dict.get("mutable_zones", []),
        )

        return AgentOutput(
            output_entity_type="ArticleSemanticProfile",
            output_entity=profile.to_dict(),
            evidence_refs=[],
            unknowns=["Deterministic mode: cannot detect schools, argument moves, or traditions"],
            assumptions=[],
            confidence="low",
            warnings=["Deterministic fallback: minimal semantic profile"],
            questions_for_user=[],
            quality_gate_status="preliminary",
            trace_notes=["Deterministic fallback from ArticleModel fields"],
            evidence_status="heuristic",
        )


def _build_from_llm(
    parsed: dict[str, Any],
    article_model_id: str | None,
) -> ArticleSemanticProfile:
    move_type = parsed.get("argument_move_type")
    if move_type:
        try:
            move_type = ArgumentMoveType(move_type).value
        except ValueError:
            move_type = ArgumentMoveType.UNKNOWN.value

    return ArticleSemanticProfile(
        article_model_id=article_model_id,
        disciplinary_registers=parsed.get("disciplinary_registers", []),
        primary_discipline=parsed.get("primary_discipline"),
        schools_and_traditions=parsed.get("schools_and_traditions", []),
        theoretical_shoulders=parsed.get("theoretical_shoulders", []),
        opponents_or_foils=parsed.get("opponents_or_foils", []),
        argument_move_type=move_type,
        argument_move_description=parsed.get("argument_move_description"),
        citation_bridges_needed=parsed.get("citation_bridges_needed", []),
        citation_ecology_description=parsed.get("citation_ecology_description"),
        protected_core_candidates=parsed.get("protected_core_candidates", []),
        mutable_zones=parsed.get("mutable_zones", []),
        field_core_nonnegotiables=parsed.get("field_core_nonnegotiables", []),
        intended_audience=parsed.get("intended_audience"),
        audience_expertise_level=parsed.get("audience_expertise_level"),
        unknowns=parsed.get("unknowns", []),
        confidence=parsed.get("confidence"),
    )
