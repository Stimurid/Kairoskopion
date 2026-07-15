"""Venue Profiler agent (spec §56).

LLM-backed extraction of VenueModel from venue guidelines/pages.

ARCH-SEM-001: semantic venue profiling requires LLM. If LLM is
unavailable or returns invalid output, SemanticLLMRequiredError
is raised — no deterministic semantic fallback.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..enums import (
    EvidenceStatus,
    LifecycleStatus,
    RegimeType,
    StalenessStatus,
    VenueType,
)
from ..ids import publication_regime_id, venue_model_id
from ..llm.config import max_tokens_for_role
from ..llm.openai_compat import SemanticLLMRequiredError
from ..llm.provider import LLMProvider
from ..prompts.venue_fact_extraction import (
    VENUE_FACT_EXTRACTION_FAMILY,
    validate_venue_extraction,
)
from ..schema import PublicationRegimeModel, VenueModel
from ..services.venue_profiling import (
    build_venue_model as _deterministic_venue,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


class VenueProfilerAgent(AgentRole):
    role_id = "venue_profiler"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        text = inp.raw_text or ""
        source_ref = inp.source_refs[0] if inp.source_refs else None

        family = dict(VENUE_FACT_EXTRACTION_FAMILY)
        _ovr = getattr(self, "_prompt_family_override", None)
        if _ovr:
            if "system_prompt" in _ovr:
                family["system_prompt"] = _ovr["system_prompt"]
            if "user_prompt_template" in _ovr:
                family["user_prompt_template"] = _ovr["user_prompt_template"]
        user_prompt = family["user_prompt_template"].format(
            venue_text=text,
            source_type=inp.user_constraints.get("source_type", "author_guidelines"),
            source_url=inp.user_constraints.get("source_url", "unknown"),
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
                max_tokens=max_tokens_for_role(self.role_id),
                agent_role="venue_profiler",
            )
        except Exception as e:
            logger.warning("LLM call failed for venue_profiler: %s", e)
            raise SemanticLLMRequiredError(
                f"Venue profiling requires LLM — provider error: {e}",
                agent_role="venue_profiler",
                error_code="SEMANTIC_LLM_REQUIRED",
            ) from e

        parsed = response.parsed
        if not parsed:
            try:
                parsed = json.loads(response.content)
            except (json.JSONDecodeError, TypeError) as parse_err:
                raise SemanticLLMRequiredError(
                    "Venue profiling LLM returned non-JSON output",
                    agent_role="venue_profiler",
                    error_code="INVALID_JSON",
                ) from parse_err

        validation_warnings = validate_venue_extraction(parsed)

        venue, regime = _build_from_llm(parsed, text, source_ref)

        # Combine venue + regime into single output dict
        output = venue.to_dict()
        output["_regime"] = regime.to_dict()

        return AgentOutput(
            output_entity_type="VenueModel",
            output_entity=output,
            evidence_refs=[source_ref] if source_ref else [],
            unknowns=parsed.get("unknowns", []),
            assumptions=[],
            confidence=parsed.get("confidence", "medium"),
            warnings=validation_warnings + parsed.get("warnings", []),
            questions_for_user=[],
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
        """ARCH-SEM-001: deterministic semantic venue profiling is prohibited."""
        raise SemanticLLMRequiredError(
            "Venue profiling requires LLM — deterministic semantic fallback "
            "is prohibited by ARCH-SEM-001",
            agent_role="venue_profiler",
            error_code="SEMANTIC_LLM_REQUIRED",
        )


def _build_from_llm(
    parsed: dict[str, Any],
    text: str,
    source_ref: str | None,
) -> tuple[VenueModel, PublicationRegimeModel]:
    """Build VenueModel + PublicationRegimeModel from LLM output."""
    # Extract language policy
    lang_obj = parsed.get("language_policy")
    language = None
    if isinstance(lang_obj, dict):
        language = lang_obj.get("article_body")
    elif isinstance(lang_obj, str):
        language = lang_obj

    # Extract article types
    article_types: list[str] = []
    for at in parsed.get("article_types", []):
        if isinstance(at, dict):
            article_types.append(at.get("name", ""))
        elif isinstance(at, str):
            article_types.append(at)

    # Extract review model
    review_obj = parsed.get("review_model")
    review_model = None
    if isinstance(review_obj, dict):
        review_model = review_obj.get("type")
    elif isinstance(review_obj, str):
        review_model = review_obj

    # Extract word limits
    word_limits_obj = parsed.get("word_limits")
    word_limits: dict[str, str] | None = None
    if isinstance(word_limits_obj, dict):
        word_limits = {}
        if word_limits_obj.get("max_words"):
            word_limits["word_range"] = str(word_limits_obj["max_words"])
        if word_limits_obj.get("min_words") and word_limits_obj.get("max_words"):
            word_limits["word_range"] = f"{word_limits_obj['min_words']}–{word_limits_obj['max_words']}"
        if word_limits_obj.get("abstract_max_words"):
            word_limits["abstract_limit"] = str(word_limits_obj["abstract_max_words"])
        if word_limits_obj.get("notes"):
            word_limits["notes"] = word_limits_obj["notes"]

    # Extract indexing claims
    indexing_claims = [c.get("database", "") for c in parsed.get("indexing_claims", [])
                       if isinstance(c, dict)]

    # Venue type mapping
    vtype_map = {
        "journal": VenueType.JOURNAL.value,
        "conference_proceedings": VenueType.CONFERENCE_PROCEEDINGS.value,
        "special_issue": VenueType.SPECIAL_ISSUE.value,
    }
    venue_type_raw = parsed.get("venue_type", "")
    if isinstance(venue_type_raw, dict):
        venue_type_raw = venue_type_raw.get("type", venue_type_raw.get("value", ""))
    venue_type = vtype_map.get(venue_type_raw, VenueType.JOURNAL.value)

    # Regime type
    rtype = RegimeType.CLASSIC_JOURNAL_ARTICLE.value
    if venue_type_raw == "special_issue":
        rtype = RegimeType.SPECIAL_ISSUE_ARTICLE.value
    elif venue_type_raw == "conference_proceedings":
        rtype = RegimeType.CONFERENCE_PROCEEDINGS.value

    # Open access
    oa_obj = parsed.get("open_access_status")
    open_access = None
    if isinstance(oa_obj, dict):
        open_access = oa_obj.get("status")
    elif isinstance(oa_obj, str):
        open_access = oa_obj

    # APC
    apc_obj = parsed.get("apc_policy")
    apc_policy = None
    if isinstance(apc_obj, dict):
        if apc_obj.get("has_apc") is False:
            apc_policy = "no_apc"
        elif apc_obj.get("amount"):
            apc_policy = f"apc: {apc_obj['amount']}"
        elif apc_obj.get("has_apc") is True:
            apc_policy = "apc_required"
    elif isinstance(apc_obj, str):
        apc_policy = apc_obj

    regime = PublicationRegimeModel(
        publication_regime_id=publication_regime_id(),
        regime_type=rtype,
        description=f"Peer-reviewed, {review_model or 'unknown review model'}",
        review_model=review_model,
        typical_article_forms=article_types,
        evidence_refs=[source_ref] if source_ref else [],
    )

    venue = VenueModel(
        venue_model_id=venue_model_id(),
        canonical_name=parsed.get("canonical_name"),
        venue_type=venue_type,
        official_urls=parsed.get("official_urls", []),
        scope_summary=parsed.get("scope_summary"),
        author_guidelines_refs=[source_ref] if source_ref else [],
        article_types_supported=article_types,
        language_policy=language,
        publication_regime_id=regime.publication_regime_id,
        publisher_or_owner=parsed.get("publisher_or_owner"),
        source_refs=[source_ref] if source_ref else [],
        unknowns=parsed.get("unknowns", []),
        confidence=parsed.get("confidence", "medium"),
        staleness_status=StalenessStatus.FRESH.value,
        lifecycle_status=LifecycleStatus.DRAFT.value,
        aims_scope_summary=parsed.get("scope_summary"),
        indexing_claims=indexing_claims,
        open_access_status=open_access,
        apc_policy=apc_policy,
        review_process_claims=review_model or "unknown",
        word_limits=word_limits,
        anonymization_policy=parsed.get("anonymization_policy"),
        ai_policy=parsed.get("ai_policy"),
        data_policy=parsed.get("data_policy"),
        ethics_policy=parsed.get("ethics_policy"),
        freshness_status="fresh",
    )

    return venue, regime
