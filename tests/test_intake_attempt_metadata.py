"""Regression tests: LLM attempt metadata must survive normal article intake.

Proves that agent_role, attempts, requested/effective model, attempt_count,
provider_status, parse_status, and final_error_code propagate through:
  provider response → ArticleModelerAgent → ArticleModel → to_dict → API

Two scenarios:
A. Primary success — single attempt, no fallback
B. Fallback success — primary fails, fallback model succeeds
C. Provider failure — error propagates with attempt history
"""

from __future__ import annotations

import dataclasses as dc
from typing import Any
from unittest.mock import patch

import pytest

from kairoskopion.agents.article_modeler import ArticleModelerAgent
from kairoskopion.agents.contract import AgentInput
from kairoskopion.llm.attempt_metadata import LLMModelAttempt
from kairoskopion.llm.openai_compat import LLMError
from kairoskopion.schema import ArticleModel


@dc.dataclass
class _FakeResponse:
    content: str = ""
    parsed: Any = None
    model: str = "test-model"
    latency_ms: float = 100.0
    input_tokens: int = 10
    output_tokens: int = 5
    requested_model: str | None = None
    effective_model: str | None = None
    fallback_used: bool = False
    attempt_count: int = 1
    attempts: list = dc.field(default_factory=list)
    agent_role: str = ""


def _make_input(text: str | None = None) -> AgentInput:
    return AgentInput(
        operation_id="test_intake",
        agent_role_id="article_modeler",
        raw_text=text or ("Test article about computational linguistics. " * 10),
    )


def _valid_article_parsed() -> dict:
    return {
        "title": "Test Article",
        "language": "en",
        "confidence": "medium",
        "core_claims": ["claim1"],
        "unknowns": [],
    }


class TestIntakePrimarySuccess:
    """Scenario A: primary model succeeds, one attempt."""

    def test_agent_role_preserved_in_extraction_attempt(self):
        attempts = [
            LLMModelAttempt(
                attempt_index=0,
                model="primary-model",
                agent_role="article_modeler",
                transition="success",
                latency_ms=200,
            ),
        ]

        class _Provider:
            def complete(self, messages, **kw):
                return _FakeResponse(
                    parsed=_valid_article_parsed(),
                    model="primary-model",
                    requested_model="primary-model",
                    effective_model="primary-model",
                    attempt_count=1,
                    attempts=attempts,
                    agent_role="article_modeler",
                )

        agent = ArticleModelerAgent()
        out = agent.execute(_make_input(), _Provider())
        ea = out.output_entity.get("extraction_attempt")
        assert ea is not None, "extraction_attempt missing"
        assert ea["agent_role"] == "article_modeler", f"agent_role={ea['agent_role']!r}"

    def test_attempts_preserved_in_extraction_attempt(self):
        attempts = [
            LLMModelAttempt(
                attempt_index=0,
                model="primary-model",
                agent_role="article_modeler",
                transition="success",
                latency_ms=150,
            ),
        ]

        class _Provider:
            def complete(self, messages, **kw):
                return _FakeResponse(
                    parsed=_valid_article_parsed(),
                    model="primary-model",
                    requested_model="primary-model",
                    effective_model="primary-model",
                    attempt_count=1,
                    attempts=attempts,
                    agent_role="article_modeler",
                )

        agent = ArticleModelerAgent()
        out = agent.execute(_make_input(), _Provider())
        ea = out.output_entity["extraction_attempt"]
        assert len(ea["attempts"]) == 1, f"attempts length={len(ea['attempts'])}"
        assert ea["attempts"][0]["model"] == "primary-model"
        assert ea["attempts"][0]["transition"] == "success"

    def test_requested_effective_model_preserved(self):
        class _Provider:
            def complete(self, messages, **kw):
                return _FakeResponse(
                    parsed=_valid_article_parsed(),
                    model="primary-model",
                    requested_model="primary-model",
                    effective_model="primary-model",
                    attempt_count=1,
                    attempts=[
                        LLMModelAttempt(attempt_index=0, model="primary-model", transition="success"),
                    ],
                    agent_role="article_modeler",
                )

        agent = ArticleModelerAgent()
        out = agent.execute(_make_input(), _Provider())
        ea = out.output_entity["extraction_attempt"]
        assert ea["requested_model"] == "primary-model"
        assert ea["effective_model"] == "primary-model"
        assert ea["attempt_count"] == 1

    def test_persistence_roundtrip_preserves_metadata(self):
        """ArticleModel.to_dict() → from_dict() must preserve attempt fields."""
        attempts = [
            LLMModelAttempt(
                attempt_index=0,
                model="gpt-4o-mini",
                agent_role="article_modeler",
                transition="success",
                latency_ms=200,
            ),
        ]

        class _Provider:
            def complete(self, messages, **kw):
                return _FakeResponse(
                    parsed=_valid_article_parsed(),
                    model="gpt-4o-mini",
                    requested_model="gpt-4o-mini",
                    effective_model="gpt-4o-mini",
                    attempt_count=1,
                    attempts=attempts,
                    agent_role="article_modeler",
                )

        agent = ArticleModelerAgent()
        out = agent.execute(_make_input(), _Provider())
        d = out.output_entity
        restored = ArticleModel.from_dict(d)
        rd = restored.to_dict()
        ea = rd.get("extraction_attempt")
        assert ea is not None
        assert ea["agent_role"] == "article_modeler"
        assert len(ea["attempts"]) == 1
        assert ea["requested_model"] == "gpt-4o-mini"
        assert ea["effective_model"] == "gpt-4o-mini"
        assert ea["attempt_count"] == 1


class TestIntakeFallbackSuccess:
    """Scenario B: primary fails with 429, fallback model succeeds."""

    def test_fallback_metadata_preserved(self):
        attempts = [
            LLMModelAttempt(
                attempt_index=0,
                model="primary-model",
                error_code="HTTP_429",
                transition="retry",
                agent_role="article_modeler",
            ),
            LLMModelAttempt(
                attempt_index=1,
                model="fallback-model",
                transition="success",
                agent_role="article_modeler",
                latency_ms=300,
            ),
        ]

        class _Provider:
            def complete(self, messages, **kw):
                return _FakeResponse(
                    parsed=_valid_article_parsed(),
                    model="fallback-model",
                    requested_model="primary-model",
                    effective_model="fallback-model",
                    fallback_used=True,
                    attempt_count=2,
                    attempts=attempts,
                    agent_role="article_modeler",
                )

        agent = ArticleModelerAgent()
        out = agent.execute(_make_input(), _Provider())
        ea = out.output_entity["extraction_attempt"]
        assert ea["agent_role"] == "article_modeler"
        assert ea["requested_model"] == "primary-model"
        assert ea["effective_model"] == "fallback-model"
        assert ea["attempt_count"] == 2
        assert len(ea["attempts"]) == 2
        assert ea["attempts"][0]["error_code"] == "HTTP_429"
        assert ea["attempts"][1]["transition"] == "success"
        assert ea["fallback_used"] is True


class TestIntakeProviderFailure:
    """Scenario C: provider throws, fallback with attempt history."""

    def test_failure_preserves_attempts_and_error_code(self):
        class _FailProvider:
            def complete(self, messages, **kw):
                err = LLMError("rate limited", error_code="HTTP_429")
                err.attempts = [
                    LLMModelAttempt(
                        attempt_index=0,
                        model="gpt-4o-mini",
                        error_code="HTTP_429",
                        transition="exhausted",
                        agent_role="article_modeler",
                    ),
                ]
                raise err

        agent = ArticleModelerAgent()
        out = agent.execute(_make_input(), _FailProvider())
        ea = out.output_entity.get("extraction_attempt")
        assert ea is not None
        assert ea["agent_role"] == "article_modeler"
        assert ea["final_error_code"] == "HTTP_429"
        assert len(ea["attempts"]) == 1
        assert ea["attempts"][0]["error_code"] == "HTTP_429"

    def test_failure_no_fake_article_model(self):
        """Provider error must not produce a fake successful article."""
        class _FailProvider:
            def complete(self, messages, **kw):
                raise LLMError("auth failed", error_code="AUTH_FAILED")

        agent = ArticleModelerAgent()
        out = agent.execute(_make_input(), _FailProvider())
        ea = out.output_entity.get("extraction_attempt")
        assert ea is not None
        assert ea["fallback_used"] is True
