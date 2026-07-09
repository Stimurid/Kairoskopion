"""P11 replay trace tests — prove attempt metadata reaches API response.

Four scenarios:
A. Primary success — attempt_metadata present, requested/effective model set
B. Fallback success — fallback_used=True, effective != requested
C. Auth failure — provider_status=error, final_error_code=AUTH_FAILED
D. All-model exhaustion — provider_status=error, final_error_code=RETRIES_EXHAUSTED
"""

from __future__ import annotations

import dataclasses as dc
from typing import Any
from unittest.mock import patch

import pytest

from kairoskopion.api.cases import Case, _get_llm_provider
from kairoskopion.llm.attempt_metadata import LLMModelAttempt
from kairoskopion.llm.openai_compat import LLMError


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


def _build_case_with_article() -> Case:
    """Create a Case with a minimal article model so refinement can run."""
    from kairoskopion.services.article_modeling import (
        build_manuscript_model,
        build_article_model,
    )
    case = Case()
    text = "Тестовый текст для статьи о вычислительной лингвистике. " * 10
    case.input_text = text
    case.intake_text(text)
    ms = build_manuscript_model(text)
    case.article_model = build_article_model(ms, text)
    return case


class TestP11ReplayPrimarySuccess:
    """Scenario A: primary model succeeds on first attempt."""

    def test_attempt_metadata_present_on_success(self):
        case = _build_case_with_article()

        class _SuccessProvider:
            def complete(self, messages, **kw):
                return _FakeResponse(
                    content='{"reply": "Хорошо", "suggestions": []}',
                    model="gpt-4o-mini",
                    requested_model="gpt-4o-mini",
                    effective_model="gpt-4o-mini",
                    fallback_used=False,
                    attempt_count=1,
                    attempts=[
                        LLMModelAttempt(
                            attempt_index=0,
                            model="gpt-4o-mini",
                            agent_role="article_model_replay",
                            transition="success",
                            latency_ms=200,
                        ),
                    ],
                    agent_role="article_model_replay",
                )

        with patch("kairoskopion.api.cases._get_llm_provider", return_value=_SuccessProvider()):
            result = case.refine_article_model("Проверь название")

        meta = result.get("attempt_metadata")
        assert meta is not None, "attempt_metadata missing from replay response"
        assert meta["requested_model"] == "gpt-4o-mini"
        assert meta["effective_model"] == "gpt-4o-mini"
        assert meta["fallback_used"] is False
        assert meta["attempt_count"] == 1
        assert meta["provider_status"] == "ok"
        assert meta["agent_role"] == "article_model_replay"
        assert len(meta["attempts"]) == 1
        assert meta["final_error_code"] is None

    def test_parse_status_set_on_success(self):
        case = _build_case_with_article()

        class _SuccessProvider:
            def complete(self, messages, **kw):
                return _FakeResponse(
                    content='{"reply": "Готово", "suggestions": []}',
                    model="m1",
                    requested_model="m1",
                    effective_model="m1",
                    attempt_count=1,
                    attempts=[],
                    agent_role="article_model_replay",
                )

        with patch("kairoskopion.api.cases._get_llm_provider", return_value=_SuccessProvider()):
            result = case.refine_article_model("Тест")

        meta = result["attempt_metadata"]
        assert meta["parse_status"] == "parsed_ok"


class TestP11ReplayFallbackSuccess:
    """Scenario B: primary fails, fallback model succeeds."""

    def test_fallback_metadata_propagated(self):
        case = _build_case_with_article()

        class _FallbackProvider:
            def complete(self, messages, **kw):
                return _FakeResponse(
                    content='{"reply": "Используем резерв", "suggestions": []}',
                    model="fallback-1",
                    requested_model="primary-model",
                    effective_model="fallback-1",
                    fallback_used=True,
                    attempt_count=2,
                    attempts=[
                        LLMModelAttempt(
                            attempt_index=0,
                            model="primary-model",
                            error_code="HTTP_429",
                            transition="retry",
                        ),
                        LLMModelAttempt(
                            attempt_index=1,
                            model="fallback-1",
                            transition="success",
                        ),
                    ],
                    agent_role="article_model_replay",
                )

        with patch("kairoskopion.api.cases._get_llm_provider", return_value=_FallbackProvider()):
            result = case.refine_article_model("Проверь")

        meta = result["attempt_metadata"]
        assert meta["fallback_used"] is True
        assert meta["requested_model"] == "primary-model"
        assert meta["effective_model"] == "fallback-1"
        assert meta["attempt_count"] == 2
        assert len(meta["attempts"]) == 2
        assert meta["attempts"][0]["error_code"] == "HTTP_429"
        assert meta["attempts"][1]["transition"] == "success"


class TestP11ReplayAuthFailure:
    """Scenario C: auth failure — no fake successful model."""

    def test_auth_failure_returns_error_metadata(self):
        case = _build_case_with_article()

        class _AuthFailProvider:
            def complete(self, messages, **kw):
                err = LLMError("API key expired", error_code="AUTH_FAILED")
                err.attempts = [  # type: ignore[attr-defined]
                    LLMModelAttempt(
                        attempt_index=0,
                        model="gpt-4o-mini",
                        error_code="AUTH_FAILED",
                        transition="terminal",
                    ),
                ]
                raise err

        with patch("kairoskopion.api.cases._get_llm_provider", return_value=_AuthFailProvider()):
            result = case.refine_article_model("Тест авторизации")

        assert "Ошибка" in result["reply"]
        assert result["suggestions"] == []
        meta = result.get("attempt_metadata")
        assert meta is not None, "attempt_metadata missing on auth failure"
        assert meta["provider_status"] == "error"
        assert meta["final_error_code"] == "AUTH_FAILED"
        assert meta["parse_status"] == "not_attempted"
        assert meta["agent_role"] == "article_model_replay"
        assert len(meta["attempts"]) == 1
        assert meta["attempts"][0]["error_code"] == "AUTH_FAILED"

    def test_auth_failure_no_fake_article_model_change(self):
        case = _build_case_with_article()
        original_title = case.article_model.title_current if case.article_model else None

        class _AuthFailProvider:
            def complete(self, messages, **kw):
                raise LLMError("401", error_code="AUTH_FAILED")

        with patch("kairoskopion.api.cases._get_llm_provider", return_value=_AuthFailProvider()):
            case.refine_article_model("Change title")

        if case.article_model:
            assert case.article_model.title_current == original_title


class TestP11ReplayAllExhausted:
    """Scenario D: all models fail — explicit exhaustion."""

    def test_exhaustion_returns_error_metadata(self):
        case = _build_case_with_article()

        class _ExhaustedProvider:
            def complete(self, messages, **kw):
                err = LLMError("All models failed", error_code="RETRIES_EXHAUSTED")
                err.attempts = [  # type: ignore[attr-defined]
                    LLMModelAttempt(
                        attempt_index=0,
                        model="m1",
                        error_code="HTTP_429",
                        transition="retry",
                    ),
                    LLMModelAttempt(
                        attempt_index=1,
                        model="m2",
                        error_code="HTTP_500",
                        transition="exhausted",
                    ),
                ]
                raise err

        with patch("kairoskopion.api.cases._get_llm_provider", return_value=_ExhaustedProvider()):
            result = case.refine_article_model("Тест отказа")

        meta = result["attempt_metadata"]
        assert meta["provider_status"] == "error"
        assert meta["final_error_code"] == "RETRIES_EXHAUSTED"
        assert meta["attempt_count"] == 2
        assert len(meta["attempts"]) == 2

    def test_exhaustion_error_visible_through_api_response(self):
        """The reply must contain a safe error message, not a traceback."""
        case = _build_case_with_article()

        class _ExhaustedProvider:
            def complete(self, messages, **kw):
                raise LLMError("All models failed", error_code="RETRIES_EXHAUSTED")

        with patch("kairoskopion.api.cases._get_llm_provider", return_value=_ExhaustedProvider()):
            result = case.refine_article_model("Тест")

        assert "Ошибка" in result["reply"]
        assert "Traceback" not in result["reply"]
        assert "sk-" not in result["reply"]


class TestP11ReplayNoProvider:
    """When LLM provider is not configured, replay says so explicitly."""

    def test_no_provider_returns_llm_unavailable(self):
        case = _build_case_with_article()

        with patch("kairoskopion.api.cases._get_llm_provider", return_value=None):
            result = case.refine_article_model("Тест")

        assert result["llm_available"] is False
        assert "attempt_metadata" not in result or result.get("attempt_metadata") is None
