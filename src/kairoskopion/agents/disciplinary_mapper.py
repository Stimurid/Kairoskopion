"""Disciplinary Pathway Mapper agent (UC-1 step 4).

Takes an ArticleModel (or ArticleSemanticProfile) and produces ranked
DisciplinaryPathway list — which academic worlds the article can enter.

This is not genre classification. This is branching of publication
trajectory: philosophy of technology, STS, AI ethics, digital humanities,
education, philosophical anthropology, history of philosophy, etc.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..enums import DisciplinaryFitStrength, EvidenceStatus
from ..ids import disciplinary_pathway_id
from ..llm.attempt_metadata import (
    FALLBACK_REASON_INVALID_JSON,
    FALLBACK_REASON_PROVIDER_ERROR,
    FALLBACK_REASON_REPAIR_FAILED,
    FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
    LLMAttemptMetadata,
)
from ..llm.json_repair import (
    PARSE_STATUS_PARSED_OK,
    PARSE_STATUS_REPAIRED_OK,
    PARSE_STATUS_SCHEMA_VALIDATION_FAILED,
    repair_and_parse,
)
from ..llm.provider import LLMProvider
from ..prompts.disciplinary_mapping import (
    DISCIPLINARY_MAPPING_FAMILY,
    validate_disciplinary_mapping,
)
from ..schema import DisciplinaryPathway
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)


_STRENGTH_MAP = {
    "strong": DisciplinaryFitStrength.STRONG.value,
    "very_high": DisciplinaryFitStrength.STRONG.value,
    "high": DisciplinaryFitStrength.STRONG.value,
    "medium_strong": DisciplinaryFitStrength.STRONG.value,
    "medium": DisciplinaryFitStrength.MEDIUM.value,
    "moderate": DisciplinaryFitStrength.MEDIUM.value,
    "weak_medium": DisciplinaryFitStrength.WEAK.value,
    "weak": DisciplinaryFitStrength.WEAK.value,
    "low": DisciplinaryFitStrength.WEAK.value,
    "incompatible": DisciplinaryFitStrength.INCOMPATIBLE.value,
    "very_low": DisciplinaryFitStrength.INCOMPATIBLE.value,
    "unknown": DisciplinaryFitStrength.UNKNOWN.value,
}


class DisciplinaryPathwayMapperAgent(AgentRole):
    role_id = "disciplinary_pathway_mapper"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        article_dict = inp.entities.get("article", {})
        semantic_profile = inp.entities.get("semantic_profile", {})

        family = DISCIPLINARY_MAPPING_FAMILY
        user_prompt = family["user_prompt_template"].format(
            article_json=json.dumps(article_dict, ensure_ascii=False, indent=2),
            semantic_profile_json=json.dumps(semantic_profile, ensure_ascii=False, indent=2),
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
            logger.warning("LLM call failed for disciplinary_mapper, falling back: %s", e)
            meta = LLMAttemptMetadata.fallback(
                reason=FALLBACK_REASON_PROVIDER_ERROR,
                provider="openai_compatible",
                model=None,
                validation_errors=[str(e)[:240]],
                parse_status="invalid_json",
            )
            return self._deterministic_with_attempt(inp, meta)

        provider_model = response.model
        latency_ms = response.latency_ms
        content_present = bool(response.content)
        parsed = response.parsed

        if isinstance(parsed, dict):
            outcome_status = PARSE_STATUS_PARSED_OK
            outcome_steps: list[str] = []
            outcome_errors: list[str] = []
            repaired = False
        else:
            outcome = repair_and_parse(
                response.content, schema=family.get("output_schema"),
            )
            parsed = outcome.parsed
            outcome_status = outcome.status
            outcome_steps = outcome.repair_steps
            outcome_errors = outcome.validation_errors
            repaired = outcome_status == PARSE_STATUS_REPAIRED_OK
            if parsed is None or outcome_status not in (
                PARSE_STATUS_PARSED_OK, PARSE_STATUS_REPAIRED_OK,
            ):
                reason = (
                    FALLBACK_REASON_SCHEMA_VALIDATION_FAILED
                    if outcome_status == PARSE_STATUS_SCHEMA_VALIDATION_FAILED
                    else (
                        FALLBACK_REASON_REPAIR_FAILED
                        if outcome_steps
                        else FALLBACK_REASON_INVALID_JSON
                    )
                )
                logger.warning(
                    "LLM disciplinary_mapper fallback: reason=%s steps=%s errors=%s",
                    reason, outcome_steps, outcome_errors,
                )
                meta = LLMAttemptMetadata.fallback(
                    reason=reason,
                    provider="openai_compatible",
                    model=provider_model,
                    latency_ms=latency_ms,
                    content_present=content_present,
                    repair_attempted=bool(outcome_steps),
                    repair_steps=outcome_steps,
                    validation_errors=outcome_errors,
                    parse_status=outcome_status,
                )
                return self._deterministic_with_attempt(inp, meta)

        validation_warnings = validate_disciplinary_mapping(parsed)

        pathways = _build_pathways(parsed, article_dict.get("article_model_id"))

        # Attach attempt metadata to every pathway so the API + UI see it
        meta = LLMAttemptMetadata.parse_ok(
            provider="openai_compatible",
            model=provider_model,
            latency_ms=latency_ms,
            content_present=content_present,
            repaired=repaired,
            repair_steps=outcome_steps,
        )
        meta_dict = meta.to_dict()
        for p in pathways:
            p.extraction_attempt = meta_dict

        return AgentOutput(
            output_entity_type="DisciplinaryPathwaySet",
            output_entity={
                "pathways": [p.to_dict() for p in pathways],
                "article_model_id": article_dict.get("article_model_id"),
                "extraction_attempt": meta_dict,
            },
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
                f"Pathways found: {len(pathways)}",
                f"parse_status: {meta.parse_status}",
                f"repair_steps: {','.join(outcome_steps) if outcome_steps else 'none'}",
            ],
            evidence_status=EvidenceStatus.INFERENCE.value,
            llm_usage={
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
                "extraction_attempt": meta_dict,
            },
        )

    def _deterministic_with_attempt(
        self, inp: AgentInput, meta: LLMAttemptMetadata,
    ) -> AgentOutput:
        """Run deterministic fallback, then annotate every pathway with
        the captured LLM attempt metadata so the API + UI surface the
        visible warning."""
        out = self.execute_deterministic(inp)
        meta_dict = meta.to_dict()
        if isinstance(out.output_entity, dict):
            out.output_entity["extraction_attempt"] = meta_dict
            for p in out.output_entity.get("pathways") or []:
                if isinstance(p, dict):
                    p["extraction_attempt"] = meta_dict
        out.trace_notes = list(out.trace_notes or []) + [
            f"fallback_reason: {meta.fallback_reason}",
            f"parse_status: {meta.parse_status}",
        ]
        if meta.warning_for_user:
            out.warnings = list(out.warnings or []) + [meta.warning_for_user]
        return out

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        article_dict = inp.entities.get("article", {})
        discipline = article_dict.get("disciplinary_register_current", "unknown")

        pathway = DisciplinaryPathway(
            article_model_id=article_dict.get("article_model_id"),
            discipline_name=discipline or "unclassified",
            fit_strength=DisciplinaryFitStrength.UNKNOWN.value,
            reasoning="Deterministic fallback: single discipline from ArticleModel register",
            rank=1,
        )

        return AgentOutput(
            output_entity_type="DisciplinaryPathwaySet",
            output_entity={
                "pathways": [pathway.to_dict()],
                "article_model_id": article_dict.get("article_model_id"),
            },
            evidence_refs=[],
            unknowns=["Deterministic mode cannot assess multi-disciplinary pathways"],
            assumptions=[],
            confidence="low",
            warnings=["Deterministic fallback: single pathway only"],
            questions_for_user=[],
            quality_gate_status="preliminary",
            trace_notes=["Deterministic single-discipline fallback"],
            evidence_status="heuristic",
        )


def _build_pathways(
    parsed: dict[str, Any],
    article_model_id: str | None,
) -> list[DisciplinaryPathway]:
    pathways = []
    raw_list = (
        parsed.get("pathways")
        or parsed.get("ranked_pathways")
        or parsed.get("disciplinary_pathways")
        or []
    )
    for i, pw in enumerate(raw_list, start=1):
        if not isinstance(pw, dict):
            continue
        discipline_name = (
            pw.get("discipline_name")
            or pw.get("discipline")
            or pw.get("pathway_name")
            or pw.get("name")
            or "unknown"
        )
        fit_raw = (pw.get("fit_strength") or pw.get("strength") or "unknown")
        if isinstance(fit_raw, str):
            fit_raw = fit_raw.lower().strip()
        strength = _STRENGTH_MAP.get(fit_raw, DisciplinaryFitStrength.UNKNOWN.value)
        reasoning = (
            pw.get("reasoning")
            or pw.get("rationale")
            or pw.get("why_this_pathway")
            or ""
        )
        if isinstance(reasoning, list):
            reasoning = "; ".join(str(x) for x in reasoning)
        adaptations = pw.get("required_adaptations") or pw.get("adaptations") or []
        if isinstance(adaptations, str):
            adaptations = [adaptations]
        pathways.append(DisciplinaryPathway(
            article_model_id=article_model_id,
            discipline_name=str(discipline_name),
            fit_strength=strength,
            reasoning=str(reasoning),
            required_adaptations=list(adaptations),
            field_core_risk=pw.get("field_core_risk") or pw.get("core_risk"),
            venue_type_hints=pw.get("venue_type_hints", []) or [],
            venue_search_queries=pw.get("venue_search_queries", []) or pw.get("example_venue_names", []) or [],
            language_options=pw.get("language_options", []) or [],
            indexing_options=pw.get("indexing_options", []) or [],
            rank=pw.get("rank", i) or i,
            strategic_value_notes=pw.get("strategic_value_notes") or pw.get("strategic_value"),
            unknowns=pw.get("unknowns", []) or [],
            confidence=pw.get("confidence"),
        ))
    return pathways
