"""Regression tests for discipline matcher output truncation.

ARCH-SEM-001 update: truncation, invalid JSON, and provider errors now
raise SemanticLLMRequiredError instead of silently falling back to
keyword-only results. These tests verify the error is raised with
correct metadata.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kairoskopion.agents.contract import AgentInput
from kairoskopion.agents.discipline_matcher import DisciplineMatcherAgent
from kairoskopion.llm.openai_compat import SemanticLLMRequiredError
from kairoskopion.llm.response import LLMResponse


def _make_input(summary: str = "Activity Theory in HCI") -> AgentInput:
    return AgentInput(
        operation_id="test_truncation",
        agent_role_id="discipline_matcher",
        raw_text=summary,
        entities={
            "article_summary": summary,
            "region": "ru",
        },
    )


def _make_provider(
    content: str = '{"matched": [], "confidence": "low"}',
    parsed: dict | None = None,
    finish_reason: str = "stop",
    output_tokens: int = 100,
    model: str = "test-model",
    max_tokens_received: list | None = None,
) -> MagicMock:
    provider = MagicMock()

    def _complete(messages, *, response_schema=None, temperature=0.0,
                  max_tokens=4096, agent_role=""):
        if max_tokens_received is not None:
            max_tokens_received.append(max_tokens)
        return LLMResponse(
            content=content,
            parsed=parsed if parsed is not None else (
                {"matched": [], "confidence": "low", "new_candidate": None}
                if finish_reason == "stop" else None
            ),
            model=model,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
            requested_model=model,
            effective_model=model,
            attempts=[],
            agent_role=agent_role,
        )

    provider.complete = _complete
    return provider


class TestMaxTokensValue:
    def test_discipline_matcher_sends_8192(self):
        received = []
        provider = _make_provider(max_tokens_received=received)
        agent = DisciplineMatcherAgent()
        agent.execute(_make_input(), provider)
        assert received == [8192], f"Expected max_tokens=8192, got {received}"


class TestTruncationRaisesError:
    """ARCH-SEM-001: truncation raises SemanticLLMRequiredError."""

    def test_length_finish_reason_raises(self):
        provider = _make_provider(
            content='{"matched": [{"discipline_id": "x", "trunca',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        agent = DisciplineMatcherAgent()
        with pytest.raises(SemanticLLMRequiredError) as exc_info:
            agent.execute(_make_input(), provider)
        assert exc_info.value.error_code == "OUTPUT_TRUNCATED"

    def test_invalid_json_raises(self):
        provider = _make_provider(
            content="This is not JSON at all",
            finish_reason="end_turn",
            output_tokens=500,
        )
        agent = DisciplineMatcherAgent()
        with pytest.raises(SemanticLLMRequiredError) as exc_info:
            agent.execute(_make_input(), provider)
        assert exc_info.value.error_code == "INVALID_JSON"

    def test_provider_error_raises(self):
        provider = MagicMock()
        provider.complete.side_effect = RuntimeError("connection refused")
        agent = DisciplineMatcherAgent()
        with pytest.raises(SemanticLLMRequiredError) as exc_info:
            agent.execute(_make_input(), provider)
        assert exc_info.value.agent_role == "discipline_matcher"

    def test_stop_finish_reason_not_truncated(self):
        provider = _make_provider(
            finish_reason="stop",
            output_tokens=2000,
            parsed={"matched": [], "confidence": "low", "new_candidate": None},
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)
        assert out.output_entity.get("confidence") == "low"


class TestRerunAfterFailure:
    def test_rerun_discipline_after_truncation(self):
        """First call truncated (raises), second call succeeds."""
        agent = DisciplineMatcherAgent()

        provider_bad = _make_provider(
            content='{"matched": [',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        with pytest.raises(SemanticLLMRequiredError):
            agent.execute(_make_input(), provider_bad)

        provider_good = _make_provider(
            finish_reason="stop",
            output_tokens=3000,
            parsed={
                "matched": [
                    {"discipline_id": "test-disc", "strength": "primary",
                     "display_name": "Test", "confidence": "high",
                     "why": "Good match.", "supporting_evidence": [],
                     "contradicting_evidence": [], "position_rationale": "ok",
                     "relation_type_ru": "основное поле"},
                ],
                "confidence": "high",
                "new_candidate": None,
            },
        )
        out2 = agent.execute(_make_input(), provider_good)
        assert out2.confidence == "high"
