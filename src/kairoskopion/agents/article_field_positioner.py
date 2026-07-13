"""Article Field Positioner — extract FieldPositionModel coordinates for an article.

Uses ARTICLE_FIELD_POSITION_FAMILY to position the article as a point in the
unified disciplinary space. Falls back to a minimal deterministic FPM derived
from ArticleModel + ArticleSemanticProfile fields when LLM is unavailable.
"""

from __future__ import annotations

import json
from typing import Any

from ..llm.config import max_tokens_for_role
from ..llm.provider import LLMProvider
from ..prompts.field_positioning import ARTICLE_FIELD_POSITION_FAMILY
from ..schema import FieldPositionModel
from .base_shell import (
    llm_agent_output,
    missing_input_output,
    service_output,
    try_llm_call,
)
from .contract import AgentInput, AgentOutput, AgentRole


class ArticleFieldPositionerAgent(AgentRole):
    role_id = "article_field_positioner"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        article = inp.entities.get("article", {})
        if not article:
            return missing_input_output("FieldPositionModel", "article")

        text = inp.raw_text or ""
        result = try_llm_call(
            provider,
            ARTICLE_FIELD_POSITION_FAMILY,
            {
                "article_json": json.dumps(article, ensure_ascii=False, indent=2),
                "manuscript_text": text[:8000] if text else "(no raw text available)",
            },
            temperature=0.2,
            max_tokens=max_tokens_for_role(self.role_id),
        )
        if result is None:
            return self.execute_deterministic(inp)

        parsed, meta = result
        warnings = ARTICLE_FIELD_POSITION_FAMILY["validator"](parsed)
        fpm = _build_fpm_from_parsed(parsed, article, semantic=inp.entities.get("semantic_profile"))
        out = llm_agent_output("FieldPositionModel", fpm.to_dict(), meta, warnings)
        return out

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        article = inp.entities.get("article", {})
        if not article:
            return missing_input_output("FieldPositionModel", "article")
        semantic = inp.entities.get("semantic_profile") or {}
        fpm = _deterministic_fpm(article, semantic)
        return service_output(
            "FieldPositionModel",
            fpm.to_dict(),
            unknowns=[
                "Deterministic FPM: vectors derived from ArticleModel fields only",
            ],
            confidence="low",
            trace_notes=[
                "deterministic article FPM (no LLM)",
            ],
        )


def _build_fpm_from_parsed(
    parsed: dict[str, Any],
    article: dict[str, Any],
    semantic: dict[str, Any] | None = None,
) -> FieldPositionModel:
    return FieldPositionModel(
        entity_type="article",
        entity_id=article.get("article_model_id"),
        discipline_vector=parsed.get("discipline_vector", {}) or {},
        subdiscipline_address=parsed.get("subdiscipline_address", {}) or {},
        framework_affiliation_vector=parsed.get("framework_affiliation_vector", {}) or {},
        citation_network_signature=parsed.get("citation_network_signature", {}) or {},
        opponents_and_foils=parsed.get("opponents_and_foils", {}) or {},
        argument_move_vector=parsed.get("argument_move_vector", {}) or {},
        novelty_mode=parsed.get("novelty_mode", {}) or {},
        evidence_type_profile=parsed.get("evidence_type_profile", {}) or {},
        method_stance=parsed.get("method_stance", {}) or {},
        formalization_level=parsed.get("formalization_level"),
        audience_level=parsed.get("audience_level", {}) or {},
        language_register=parsed.get("language_register", {}) or {},
        genre_position=parsed.get("genre_position", {}) or {},
        geographic_affinity=parsed.get("geographic_affinity", {}) or {},
        temporal_position=parsed.get("temporal_position", {}) or {},
        article_readiness=parsed.get("article_readiness") or {},
        unknowns=parsed.get("unknowns", []) or [],
        confidence=parsed.get("confidence"),
    )


def _deterministic_fpm(
    article: dict[str, Any],
    semantic: dict[str, Any],
) -> FieldPositionModel:
    """Best-effort FPM from ArticleModel + ArticleSemanticProfile fields."""
    primary = (
        semantic.get("primary_discipline")
        or article.get("disciplinary_register_current")
        or "unknown"
    )
    discipline_vector: dict[str, float] = {}
    for reg in semantic.get("disciplinary_registers", []) or []:
        if isinstance(reg, str):
            discipline_vector[reg] = 1.0
    if not discipline_vector:
        discipline_vector[primary] = 1.0

    schools = semantic.get("schools_and_traditions", []) or []
    school_vector = {s: 1.0 for s in schools if isinstance(s, str)}

    return FieldPositionModel(
        entity_type="article",
        entity_id=article.get("article_model_id"),
        discipline_vector=discipline_vector,
        subdiscipline_address={"primary": primary},
        framework_affiliation_vector=school_vector,
        citation_network_signature={
            "must_cite": semantic.get("theoretical_shoulders", []) or [],
        },
        argument_move_vector={
            semantic.get("argument_move_type") or "unknown": 1.0,
        },
        language_register={"language": article.get("language")},
        unknowns=[
            "Deterministic FPM has no formalization_level, no envelopes, no method_stance"
        ],
        confidence="low",
    )
