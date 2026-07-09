"""Fit Assessor agent (spec §59).

LLM-backed multi-axis FitAssessment comparing ArticleModel × VenueModel ×
SubmissionScenario, with deterministic fallback.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..enums import (
    AssessmentLevel,
    EvidenceStatus,
    FitAxisValue,
    FitLabel,
    LifecycleStatus,
)
from ..ids import fit_assessment_id
from ..llm.attempt_metadata import (
    FALLBACK_REASON_PROVIDER_ERROR,
    LLMAttemptMetadata,
    classify_llm_response,
)
from ..llm.provider import LLMProvider
from ..prompts.fit_assessment import (
    FIT_ASSESSMENT_FAMILY,
    FIT_ASSESSMENT_VPKG_FAMILY,
    validate_fit_assessment,
    validate_fit_assessment_vpkg,
)
from ..schema import FitAssessment
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)

_VALUE_MAP = {
    "strong": FitAxisValue.STRONG.value,
    "moderate": FitAxisValue.MEDIUM.value,
    "medium": FitAxisValue.MEDIUM.value,
    "weak": FitAxisValue.WEAK.value,
    "poor": FitAxisValue.BAD.value,
    "bad": FitAxisValue.BAD.value,
    "unknown": FitAxisValue.UNKNOWN.value,
}

_LABEL_MAP = {
    "strong_candidate": FitLabel.STRONG_CANDIDATE.value,
    "possible": FitLabel.POSSIBLE.value,
    "possible_but_costly": FitLabel.POSSIBLE_BUT_COSTLY.value,
    "poor_fit": FitLabel.POOR_FIT.value,
    "high_risk": FitLabel.HIGH_RISK.value,
    "not_enough_data": FitLabel.NOT_ENOUGH_DATA.value,
}

_AXIS_NORMALIZE: dict[str, str] = {
    "topic_fit": "topic",
    "discipline_fit": "discipline",
    "genre_fit": "genre",
    "argument_structure_fit": "argument_structure",
    "method_fit": "method",
    "citation_ecology_fit": "citation_ecology",
    "novelty_positioning_fit": "novelty_positioning",
    "language_register_fit": "language_register",
    "audience_fit": "audience",
    "formal_compliance_fit": "formal_compliance",
    "author_eligibility_fit": "author_eligibility",
    "publication_regime_fit": "publication_regime",
    "timeline_fit": "timeline",
    "apc_fit": "apc",
    "strategic_value": "strategic_value",
    "field_core_preservation_risk": "field_core_preservation_risk",
}


class FitAssessorAgent(AgentRole):
    role_id = "fit_assessor"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        article_dict = inp.entities.get("article", {})
        venue_dict = inp.entities.get("venue", {})
        scenario_dict = inp.entities.get("scenario", {})

        family = dict(FIT_ASSESSMENT_FAMILY)
        _ovr = getattr(self, "_prompt_family_override", None)
        if _ovr:
            if "system_prompt" in _ovr:
                family["system_prompt"] = _ovr["system_prompt"]
            if "user_prompt_template" in _ovr:
                family["user_prompt_template"] = _ovr["user_prompt_template"]
        user_prompt = family["user_prompt_template"].format(
            article_json=json.dumps(article_dict, ensure_ascii=False, indent=2),
            venue_json=json.dumps(venue_dict, ensure_ascii=False, indent=2),
            scenario_json=json.dumps(scenario_dict, ensure_ascii=False, indent=2),
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
                agent_role="fit_assessor",
            )
        except Exception as e:
            logger.warning("LLM call failed for fit_assessor, falling back: %s", e)
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
                "LLM fit_assessor fallback: reason=%s steps=%s",
                meta.fallback_reason, repair_steps,
            )
            return self._deterministic_with_attempt(inp, meta)

        validation_warnings = validate_fit_assessment(parsed)

        fit = _build_from_llm(
            parsed,
            article_id=article_dict.get("article_model_id"),
            venue_id=venue_dict.get("venue_model_id"),
            scenario_id=scenario_dict.get("submission_scenario_id"),
        )
        fit.extraction_attempt = meta.to_dict()

        return AgentOutput(
            output_entity_type="FitAssessment",
            output_entity=fit.to_dict(),
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
        """Annotate deterministic-fallback fit assessment with attempt
        metadata so the API + UI surface the visible warning."""
        out = self._fallback_deterministic(inp)
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

    def execute_vpkg(
        self, inp: AgentInput, provider: LLMProvider,
    ) -> AgentOutput:
        """16-axis VPKG assessment for Mavrinsky semantic organ (#10)."""
        article_dict = inp.entities.get("article", {})
        vpkg_dict = inp.entities.get("vpkg", {})
        corpus_titles = inp.entities.get("corpus_titles", [])

        family = FIT_ASSESSMENT_VPKG_FAMILY
        if isinstance(corpus_titles, list):
            corpus_text = "\n".join(
                f"- {t}" for t in corpus_titles[:50]
            ) or "(no corpus titles available)"
        else:
            corpus_text = str(corpus_titles)[:3000]

        user_prompt = family["user_prompt_template"].format(
            article_json=json.dumps(
                article_dict, ensure_ascii=False, indent=2,
            ),
            vpkg_json=json.dumps(
                vpkg_dict, ensure_ascii=False, indent=2,
            )[:6000],
            corpus_titles=corpus_text,
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
                max_tokens=6144,
                agent_role="fit_assessor",
            )
        except Exception as e:
            logger.warning("VPKG fit assessment LLM failed: %s", e)
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
            return self._deterministic_with_attempt(inp, meta)

        validation_warnings = validate_fit_assessment_vpkg(parsed)

        fit = _build_from_llm(
            parsed,
            article_id=article_dict.get("article_model_id"),
            venue_id=vpkg_dict.get("venue_model_id"),
            scenario_id=None,
        )
        fit.extraction_attempt = meta.to_dict()

        return AgentOutput(
            output_entity_type="FitAssessment",
            output_entity=fit.to_dict(),
            evidence_refs=[],
            unknowns=parsed.get("unknowns", []),
            assumptions=[],
            confidence=parsed.get("confidence", "medium"),
            warnings=validation_warnings,
            questions_for_user=parsed.get("questions_for_user", []),
            quality_gate_status="preliminary",
            trace_notes=[
                f"VPKG 16-axis mode",
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

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        return self._fallback_deterministic(inp)

    def _fallback_deterministic(self, inp: AgentInput) -> AgentOutput:
        article_dict = inp.entities.get("article", {})
        venue_dict = inp.entities.get("venue", {})
        scenario_dict = inp.entities.get("scenario", {})

        all_unknown_axes = [
            {
                "axis": axis_name,
                "value": FitAxisValue.UNKNOWN.value,
                "notes": "LLM assessment unavailable — axis not evaluated",
                "evidence_refs": [],
                "unknowns": ["requires LLM for semantic assessment"],
            }
            for axis_name in (
                "topic", "discipline", "genre", "argument_structure",
                "method", "citation_ecology", "novelty_positioning",
                "language_register", "audience", "formal_compliance",
                "author_eligibility", "publication_regime",
            )
        ]

        fit = FitAssessment(
            fit_assessment_id=fit_assessment_id(),
            article_model_id=article_dict.get("article_model_id"),
            venue_model_id=venue_dict.get("venue_model_id"),
            submission_scenario_id=scenario_dict.get("submission_scenario_id"),
            assessment_level=AssessmentLevel.LIGHT_PROFILE.value,
            overall_label=FitLabel.NOT_ENOUGH_DATA.value,
            axes=all_unknown_axes,
            confidence="none",
            unknowns=["All axes require LLM for semantic assessment"],
            recommendation=None,
            lifecycle_status=LifecycleStatus.PRELIMINARY.value,
        )

        return AgentOutput(
            output_entity_type="FitAssessment",
            output_entity=fit.to_dict(),
            evidence_refs=[],
            unknowns=fit.unknowns,
            assumptions=[],
            confidence="none",
            warnings=[
                "LLM fit assessor unavailable — all axes set to 'unknown', "
                "overall label 'not_enough_data'. No deterministic semantic "
                "fallback used."
            ],
            questions_for_user=[],
            quality_gate_status="blocked",
            trace_notes=[
                "All-unknown assessment (no deterministic semantic fallback)"
            ],
            evidence_status="none",
        )


def _build_from_llm(
    parsed: dict[str, Any],
    article_id: str | None,
    venue_id: str | None,
    scenario_id: str | None,
) -> FitAssessment:
    """Build FitAssessment from LLM output."""
    axes = []
    all_unknowns: list[str] = list(parsed.get("unknowns", []))

    # Accept several common axis-container key names AND both list/dict shapes.
    # The 302.ai-flavored output often returns axes as
    #   "axes": {"topic_fit": {"value": "strong", ...}, ...}
    # instead of the strict-schema list.
    raw_axes_obj = None
    for key in ("axes", "fit_axes", "fit_vector", "dimensions",
                "fit_dimensions", "assessments", "axis_assessments"):
        v = parsed.get(key)
        if v:
            raw_axes_obj = v
            break

    raw_axes: list = []
    if isinstance(raw_axes_obj, list):
        raw_axes = raw_axes_obj
    elif isinstance(raw_axes_obj, dict):
        for k, v in raw_axes_obj.items():
            if isinstance(v, dict):
                raw_axes.append({"axis": k, **v})
            else:
                raw_axes.append({"axis": k, "value": v})

    for ax in raw_axes:
        if not isinstance(ax, dict):
            continue
        value_raw = (
            ax.get("value")
            or ax.get("status")
            or ax.get("strength")
            or ax.get("rating")
            or "unknown"
        )
        if isinstance(value_raw, str):
            value_raw = value_raw.lower().strip()
        value = _VALUE_MAP.get(value_raw, FitAxisValue.UNKNOWN.value)
        axis_unknowns = ax.get("unknowns", []) or []
        if isinstance(axis_unknowns, str):
            axis_unknowns = [axis_unknowns]
        all_unknowns.extend(axis_unknowns)
        notes = (
            ax.get("reasoning")
            or ax.get("notes")
            or ax.get("explanation")
            or ax.get("rationale")
            or ""
        )
        if isinstance(notes, list):
            notes = "; ".join(str(x) for x in notes)
        raw_axis_name = ax.get("axis", "") or ax.get("name", "")
        axis_name = _AXIS_NORMALIZE.get(raw_axis_name, raw_axis_name)
        axes.append({
            "axis": axis_name,
            "value": value,
            "notes": str(notes),
            "evidence_refs": ax.get("evidence_refs", []) or [],
            "unknowns": axis_unknowns,
        })

    overall_raw = parsed.get("overall_label", "not_enough_data")
    overall = _LABEL_MAP.get(overall_raw, FitLabel.NOT_ENOUGH_DATA.value)

    values = [a["value"] for a in axes]
    unknown_count = values.count(FitAxisValue.UNKNOWN.value)
    has_evidence = bool(article_id and venue_id)
    lifecycle = (LifecycleStatus.PRELIMINARY.value
                 if not has_evidence or unknown_count > 3
                 else LifecycleStatus.ANALYZED.value)

    return FitAssessment(
        fit_assessment_id=fit_assessment_id(),
        article_model_id=article_id,
        venue_model_id=venue_id,
        submission_scenario_id=scenario_id,
        assessment_level=AssessmentLevel.LIGHT_PROFILE.value,
        overall_label=overall,
        axes=axes,
        confidence=parsed.get("confidence", "medium"),
        unknowns=all_unknowns,
        recommendation=parsed.get("recommendation"),
        lifecycle_status=lifecycle,
    )
