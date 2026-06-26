"""Venue Field Positioner — extract FieldPositionModel envelope for a venue.

Uses VENUE_FIELD_POSITION_FAMILY to position the venue as an extended region
(envelope) in the same disciplinary space as articles. Falls back to a minimal
deterministic FPM derived from VenueModel fields when LLM is unavailable.
"""

from __future__ import annotations

import json
from typing import Any

from ..llm.provider import LLMProvider
from ..prompts.field_positioning import VENUE_FIELD_POSITION_FAMILY
from ..schema import FieldPositionModel
from .base_shell import (
    llm_agent_output,
    missing_input_output,
    service_output,
    try_llm_call,
)
from .contract import AgentInput, AgentOutput, AgentRole


class VenueFieldPositionerAgent(AgentRole):
    role_id = "venue_field_positioner"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        venue = inp.entities.get("venue", {})
        if not venue:
            return missing_input_output("FieldPositionModel", "venue")

        editorial = inp.entities.get("editorial_board", {})
        corpus = inp.entities.get("corpus_summary", {})
        guidelines = (
            inp.entities.get("venue_guidelines_text")
            or inp.raw_text
            or ""
        )

        result = try_llm_call(
            provider,
            VENUE_FIELD_POSITION_FAMILY,
            {
                "venue_json": json.dumps(venue, ensure_ascii=False, indent=2),
                "editorial_board_json": json.dumps(editorial, ensure_ascii=False, indent=2),
                "corpus_json": json.dumps(corpus, ensure_ascii=False, indent=2),
                "guidelines_text": guidelines[:4000] if guidelines else "(no guidelines available)",
            },
            temperature=0.2,
            max_tokens=4096,
        )
        if result is None:
            return self.execute_deterministic(inp)

        parsed, meta = result
        warnings = VENUE_FIELD_POSITION_FAMILY["validator"](parsed)
        fpm = _build_fpm_from_parsed(parsed, venue)
        return llm_agent_output("FieldPositionModel", fpm.to_dict(), meta, warnings)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        venue = inp.entities.get("venue", {})
        if not venue:
            return missing_input_output("FieldPositionModel", "venue")
        fpm = _deterministic_fpm(venue)
        return service_output(
            "FieldPositionModel",
            fpm.to_dict(),
            unknowns=[
                "Deterministic venue FPM: no vectors, no envelopes",
            ],
            confidence="low",
            trace_notes=["deterministic venue FPM (no LLM)"],
        )


def _build_fpm_from_parsed(parsed: dict[str, Any], venue: dict[str, Any]) -> FieldPositionModel:
    return FieldPositionModel(
        entity_type="venue",
        entity_id=venue.get("venue_model_id"),
        discipline_vector=parsed.get("discipline_vector", {}) or {},
        discipline_envelope=parsed.get("discipline_envelope"),
        subdiscipline_address=parsed.get("subdiscipline_address", {}) or {},
        framework_affiliation_vector=parsed.get("framework_affiliation_vector", {}) or {},
        framework_envelope=parsed.get("framework_envelope"),
        citation_network_signature=parsed.get("citation_network_signature", {}) or {},
        opponents_and_foils=parsed.get("opponents_and_foils", {}) or {},
        argument_move_vector=parsed.get("argument_move_vector", {}) or {},
        argument_move_envelope=parsed.get("argument_move_envelope"),
        novelty_mode=parsed.get("novelty_mode", {}) or {},
        evidence_type_profile=parsed.get("evidence_type_profile", {}) or {},
        method_stance=parsed.get("method_stance", {}) or {},
        formalization_level=parsed.get("formalization_level"),
        audience_level=parsed.get("audience_level", {}) or {},
        language_register=parsed.get("language_register", {}) or {},
        genre_position=parsed.get("genre_position", {}) or {},
        geographic_affinity=parsed.get("geographic_affinity", {}) or {},
        institutional_signals=parsed.get("institutional_signals", {}) or {},
        temporal_position=parsed.get("temporal_position", {}) or {},
        unknowns=parsed.get("unknowns", []) or [],
        confidence=parsed.get("confidence"),
    )


def _deterministic_fpm(venue: dict[str, Any]) -> FieldPositionModel:
    """Honest fallback: do NOT fabricate a discipline_vector by
    tokenising scope_summary. That produced fake vector entries like
    ``"and": 1.0`` and ``"the": 1.0`` from stopwords, then those leaked
    into downstream fit assessment and venue-candidate screening as if
    they were real discipline weights.

    Keep ONLY the formally extractable institutional signals + language.
    Discipline positioning requires the LLM-backed
    ``VenueFieldPositionerAgent`` path. When LLM is unavailable, emit
    an empty ``discipline_vector`` and an explicit unknown so the UI
    can warn rather than show a garbage chart.
    """
    return FieldPositionModel(
        entity_type="venue",
        entity_id=venue.get("venue_model_id"),
        discipline_vector={},
        institutional_signals={
            "prestige_tier": "unknown",
            "open_access": venue.get("open_access_model") or venue.get("open_access"),
            "review_model": venue.get("review_type"),
        },
        language_register={"language": (venue.get("languages") or [None])[0]
                            if isinstance(venue.get("languages"), list)
                            else venue.get("language")},
        unknowns=[
            "Deterministic venue FPM: no discipline vector — needs LLM "
            "VenueFieldPositionerAgent. Institutional signals only.",
        ],
        confidence="low",
    )
