"""Regression tests for discipline matcher output truncation.

Root cause (2026-07-10): V3 prompt with 10 candidates and 7-10 sentence
rationales in Russian consistently exceeded max_tokens=4096. The provider
returned finish_reason='length', the JSON was truncated mid-object,
and the agent silently fell back to keyword-only results.

These tests ensure:
- the configured max_tokens value reaches the provider;
- finish_reason='length' is classified as output_truncated, not invalid_json;
- truncated JSON is never reported as successful semantic analysis;
- keyword fallback carries the truncation metadata, not a clean slate;
- attempt metadata and parse diagnostics survive the failure;
- the user can rerun after a truncation failure.
"""

from __future__ import annotations

import dataclasses as dc
from unittest.mock import MagicMock, patch

import pytest

from kairoskopion.agents.contract import AgentInput, AgentOutput
from kairoskopion.agents.discipline_matcher import DisciplineMatcherAgent
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
    """Build a mock provider that records the max_tokens it receives."""
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
    """The configured max_tokens reaches the provider call."""

    def test_discipline_matcher_sends_8192(self):
        received = []
        provider = _make_provider(max_tokens_received=received)
        agent = DisciplineMatcherAgent()
        agent.execute(_make_input(), provider)
        assert received == [8192], f"Expected max_tokens=8192, got {received}"


class TestTruncationDetection:
    """finish_reason='length' is classified as output_truncated."""

    def test_length_finish_reason_triggers_truncation_fallback(self):
        provider = _make_provider(
            content='{"matched": [{"discipline_id": "x", "trunca',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        ea = out.output_entity.get("extraction_attempt", {})
        assert ea.get("fallback_used") is True
        assert ea.get("fallback_reason") == "output_truncated"

    def test_truncated_not_classified_as_invalid_json(self):
        provider = _make_provider(
            content='{"matched": [{"discipline_id": "x"',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        ea = out.output_entity.get("extraction_attempt", {})
        assert ea.get("fallback_reason") != "invalid_json"
        assert ea.get("fallback_reason") == "output_truncated"

    def test_stop_finish_reason_not_truncated(self):
        provider = _make_provider(
            finish_reason="stop",
            output_tokens=2000,
            parsed={"matched": [], "confidence": "low", "new_candidate": None},
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        ea = out.output_entity.get("extraction_attempt", {})
        assert ea.get("fallback_reason") != "output_truncated"


class TestTruncatedNotReportedAsSuccess:
    """Truncated JSON must not be reported as successful semantic analysis."""

    def test_truncated_response_has_low_confidence(self):
        provider = _make_provider(
            content='{"matched": [{"discipline_id": "x"',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        assert out.confidence == "low"

    def test_truncated_response_has_keyword_only_candidates(self):
        provider = _make_provider(
            content='{"matched": [{"discipline_id": "x"',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        for m in out.output_entity.get("matched", []):
            assert "keyword" in m.get("why", "").lower() or "реестр" in m.get("why", "").lower()

    def test_truncated_response_not_quality_gate_pass(self):
        provider = _make_provider(
            content='{"matched": [',
            parsed=None,
            finish_reason="length",
            output_tokens=8192,
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        assert out.quality_gate_status != "pass"


class TestKeywordFallbackCarriesMetadata:
    """Keyword candidates must not silently replace a failed LLM result."""

    def test_fallback_has_extraction_attempt(self):
        provider = _make_provider(
            content='{"matched": [',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        ea = out.output_entity.get("extraction_attempt")
        assert ea is not None, "extraction_attempt must be present on fallback"

    def test_fallback_records_llm_attempted(self):
        provider = _make_provider(
            content='{"matched": [',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        ea = out.output_entity["extraction_attempt"]
        assert ea["llm_attempted"] is True

    def test_fallback_records_final_error_code(self):
        provider = _make_provider(
            content='{"matched": [',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        ea = out.output_entity["extraction_attempt"]
        assert ea.get("final_error_code") == "OUTPUT_TRUNCATED"

    def test_fallback_records_agent_role(self):
        provider = _make_provider(
            content='{"matched": [',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        ea = out.output_entity["extraction_attempt"]
        assert ea.get("agent_role") == "discipline_matcher"

    def test_fallback_validation_errors_contain_token_info(self):
        provider = _make_provider(
            content='{"matched": [',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        ea = out.output_entity["extraction_attempt"]
        errors = ea.get("validation_errors_summary", [])
        joined = " ".join(errors)
        assert "finish_reason=length" in joined
        assert "4096" in joined


class TestAttemptMetadataSurvival:
    """Attempt metadata and parse diagnostics survive the failure."""

    def test_invalid_json_fallback_also_has_metadata(self):
        provider = _make_provider(
            content="This is not JSON at all",
            finish_reason="end_turn",
            output_tokens=500,
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        ea = out.output_entity.get("extraction_attempt")
        assert ea is not None
        assert ea["fallback_used"] is True
        assert ea["fallback_reason"] == "invalid_json"
        assert ea["llm_attempted"] is True

    def test_provider_error_fallback_has_metadata(self):
        provider = MagicMock()
        provider.complete.side_effect = RuntimeError("connection refused")
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        ea = out.output_entity.get("extraction_attempt")
        assert ea is not None
        assert ea["fallback_used"] is True
        assert ea["llm_attempted"] is True


class TestRerunAfterFailure:
    """The user can rerun after a truncation failure."""

    def test_rerun_discipline_after_truncation(self):
        """Simulates: first call truncated, second call succeeds."""
        agent = DisciplineMatcherAgent()

        # First call: truncated
        provider_bad = _make_provider(
            content='{"matched": [',
            parsed=None,
            finish_reason="length",
            output_tokens=4096,
        )
        out1 = agent.execute(_make_input(), provider_bad)
        assert out1.output_entity["extraction_attempt"]["fallback_reason"] == "output_truncated"

        # Second call: succeeds (simulating rerun with higher budget or shorter output)
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
        assert "extraction_attempt" not in out2.output_entity


class TestFinishReasonPersisted:
    """If the provider returns a finish_reason signal, it is persisted."""

    def test_truncation_validation_errors_include_finish_reason(self):
        provider = _make_provider(
            content='{"trunc',
            parsed=None,
            finish_reason="length",
            output_tokens=8191,
            model="claude-sonnet-4-5-20250929",
        )
        agent = DisciplineMatcherAgent()
        out = agent.execute(_make_input(), provider)

        ea = out.output_entity["extraction_attempt"]
        errors = ea.get("validation_errors_summary", [])
        assert any("finish_reason=length" in e for e in errors)
        assert any("8191" in e for e in errors)
        assert any("claude-sonnet" in e for e in errors)
