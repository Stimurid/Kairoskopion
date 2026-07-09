"""Input Classifier agent.

Replaces the prior 9-line Python keyword heuristic
(``api/cases.py::_classify_input``) with an LLM call that reads the
opening of the text and picks one of:
manuscript / venue / review_letter / unknown.

Fallback behavior is deliberately conservative: when the LLM provider
is unavailable or the call fails, this agent returns
``input_type = unknown`` with ``needs_user_choice = true``. It does
NOT default to "manuscript" — a wrong default is worse than asking
the user one extra question.
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
from ..prompts.input_classification import (
    INPUT_CLASSIFICATION_FAMILY,
    NEEDS_USER_CHOICE_TYPES,
    validate_input_classification,
)
from .contract import AgentInput, AgentOutput, AgentRole

logger = logging.getLogger(__name__)

# How many characters of the opening to ship to the LLM. The classifier
# only needs to see intent, not the whole manuscript. 6k chars ≈ ~1.5k
# tokens of Russian — enough for a confident decision and fast enough
# that the latency budget is comfortably under a second on Haiku.
_OPENING_CHAR_BUDGET = 6_000


def _fallback_unknown(reason_msg: str) -> AgentOutput:
    """Conservative fallback: tell the caller we don't know.

    The intake endpoint must then ask the user to pick the type with
    the chip selector instead of silently routing to the wrong branch.
    """
    return AgentOutput(
        output_entity_type="InputClassification",
        output_entity={
            "input_type": "unknown",
            "confidence": "low",
            "needs_user_choice": True,
            "language_detected": "unknown",
            "reasoning": reason_msg,
        },
        confidence="low",
        warnings=[reason_msg],
        quality_gate_status="preliminary",
    )


class InputClassifierAgent(AgentRole):
    role_id = "input_classifier"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        text = inp.raw_text or ""
        if not text.strip():
            return _fallback_unknown("Пустой текст — нечего классифицировать.")

        opening = text[:_OPENING_CHAR_BUDGET]
        family = INPUT_CLASSIFICATION_FAMILY
        user_prompt = family["user_prompt_template"].format(
            full_length=len(text),
            text_opening=opening,
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
                max_tokens=512,
                agent_role="input_classifier",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM call failed for input_classifier: %s", exc)
            out = _fallback_unknown(
                "LLM-классификатор не отозвался — выберите тип вручную."
            )
            out.warnings.append(
                LLMAttemptMetadata.fallback(
                    reason=FALLBACK_REASON_PROVIDER_ERROR,
                    provider="openai_compatible",
                    validation_errors=[str(exc)[:240]],
                ).to_dict().__repr__()
            )
            return out

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
                    "Input classifier returned non-JSON / unrepairable output"
                )
                return _fallback_unknown(
                    "LLM-классификатор вернул невалидный JSON — выберите тип."
                )

        # Soft validation — surface warnings but don't fall back if shape ok.
        warnings = validate_input_classification(parsed)

        # Enforce invariant: any type without an automated pipeline OR
        # low confidence must request user choice. Mirrors the policy
        # documented in prompts/input_classification.py.
        if (
            parsed.get("input_type") in NEEDS_USER_CHOICE_TYPES
            or parsed.get("confidence") == "low"
        ):
            parsed["needs_user_choice"] = True

        return AgentOutput(
            output_entity_type="InputClassification",
            output_entity=parsed,
            confidence=parsed.get("confidence", "low"),
            warnings=warnings,
            quality_gate_status="preliminary",
        )

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        """No LLM available → don't guess. Ask the user."""
        text = inp.raw_text or ""
        if not text.strip():
            return _fallback_unknown("Пустой текст — нечего классифицировать.")
        return _fallback_unknown(
            "LLM-провайдер не сконфигурирован — выберите тип вручную."
        )
