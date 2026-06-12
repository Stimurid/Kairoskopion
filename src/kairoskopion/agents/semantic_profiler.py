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
from ..llm.provider import LLMProvider
from ..prompts.semantic_profiling import (
    SEMANTIC_PROFILING_FAMILY,
    validate_semantic_profile,
)
from ..schema import ArticleSemanticProfile
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


class ArticleSemanticProfilerAgent(AgentRole):
    role_id = "article_semantic_profiler"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        article_dict = inp.entities.get("article", {})
        text = inp.raw_text or ""

        family = SEMANTIC_PROFILING_FAMILY
        user_prompt = family["user_prompt_template"].format(
            article_json=json.dumps(article_dict, ensure_ascii=False, indent=2),
            manuscript_text=text[:8000] if text else "(no raw text available)",
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
            return self.execute_deterministic(inp)

        parsed = response.parsed
        if not parsed:
            try:
                parsed = json.loads(response.content)
            except (json.JSONDecodeError, TypeError):
                logger.warning("LLM returned non-JSON, falling back to deterministic")
                return self.execute_deterministic(inp)

        validation_warnings = validate_semantic_profile(parsed)
        profile = _build_from_llm(parsed, article_dict.get("article_model_id"))

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
            ],
            evidence_status=EvidenceStatus.INFERENCE.value,
            llm_usage={
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
            },
        )

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
