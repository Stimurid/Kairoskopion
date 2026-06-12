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
from ..llm.provider import LLMProvider
from ..prompts.fit_assessment import (
    FIT_ASSESSMENT_FAMILY,
    validate_fit_assessment,
)
from ..schema import ArticleModel, FitAssessment, SubmissionScenario, VenueModel
from ..services.fit_assessment import assess_fit as _deterministic_fit
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


class FitAssessorAgent(AgentRole):
    role_id = "fit_assessor"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        article_dict = inp.entities.get("article", {})
        venue_dict = inp.entities.get("venue", {})
        scenario_dict = inp.entities.get("scenario", {})

        family = FIT_ASSESSMENT_FAMILY
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
            )
        except Exception as e:
            logger.warning("LLM call failed for fit_assessor, falling back: %s", e)
            return self._fallback_deterministic(inp)

        parsed = response.parsed
        if not parsed:
            try:
                parsed = json.loads(response.content)
            except (json.JSONDecodeError, TypeError):
                logger.warning("LLM returned non-JSON, falling back to deterministic")
                return self._fallback_deterministic(inp)

        validation_warnings = validate_fit_assessment(parsed)

        fit = _build_from_llm(
            parsed,
            article_id=article_dict.get("article_model_id"),
            venue_id=venue_dict.get("venue_model_id"),
            scenario_id=scenario_dict.get("submission_scenario_id"),
        )

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
        return self._fallback_deterministic(inp)

    def _fallback_deterministic(self, inp: AgentInput) -> AgentOutput:
        article_dict = inp.entities.get("article", {})
        venue_dict = inp.entities.get("venue", {})
        scenario_dict = inp.entities.get("scenario", {})

        article = ArticleModel.from_dict(article_dict)
        venue = VenueModel.from_dict(venue_dict)
        scenario = SubmissionScenario.from_dict(scenario_dict)

        fit = _deterministic_fit(article, venue, scenario)

        return AgentOutput(
            output_entity_type="FitAssessment",
            output_entity=fit.to_dict(),
            evidence_refs=[],
            unknowns=fit.unknowns,
            assumptions=[],
            confidence=fit.confidence or "low",
            warnings=["Deterministic assessment: limited depth"],
            questions_for_user=[],
            quality_gate_status="preliminary",
            trace_notes=["Deterministic rule-based assessment (no LLM)"],
            evidence_status="heuristic",
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

    for ax in parsed.get("axes", []):
        value_raw = ax.get("value", "unknown")
        value = _VALUE_MAP.get(value_raw, FitAxisValue.UNKNOWN.value)
        axis_unknowns = ax.get("unknowns", [])
        all_unknowns.extend(axis_unknowns)
        axes.append({
            "axis": ax.get("axis", ""),
            "value": value,
            "notes": ax.get("reasoning", ""),
            "evidence_refs": ax.get("evidence_refs", []),
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
