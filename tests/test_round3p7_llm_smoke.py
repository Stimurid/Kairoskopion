"""P7 Phase 1 — E2E LLM smoke tests.

Verify the full LLM execution path through agents, provider, JSON repair,
and fallback — all with mocked HTTP (no real API calls).

Covers:
  1. Provider construction: _get_llm_provider returns provider when env configured
  2. Provider disabled: returns None when provider=none or no model
  3. Agent LLM path: ArticleModelerAgent.execute() produces ArticleModel via LLM
  4. Agent fallback on provider error: falls back to deterministic
  5. Agent fallback on invalid JSON: repair fails → deterministic
  6. Agent fallback on schema validation failure: missing required fields
  7. JSON repair: fenced JSON, trailing commas, smart quotes
  8. Per-role model routing via env vars
  9. Input classification agent LLM path
 10. Case.intake_text() uses LLM when provider available
 11. LLMAttemptMetadata audit trail on LLM success
 12. LLMAttemptMetadata audit trail on fallback
 13. classify_llm_response shared helper
 14. OpenAICompatProvider retry on 429/5xx
 15. OpenAICompatProvider non-retryable error
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from kairoskopion.llm.config import LLMConfig, is_llm_available, provider_status
from kairoskopion.llm.response import LLMResponse
from kairoskopion.llm.openai_compat import OpenAICompatProvider, LLMError
from kairoskopion.llm.json_repair import (
    repair_and_parse,
    PARSE_STATUS_PARSED_OK,
    PARSE_STATUS_REPAIRED_OK,
    PARSE_STATUS_REPAIR_FAILED,
    PARSE_STATUS_SCHEMA_VALIDATION_FAILED,
)
from kairoskopion.llm.attempt_metadata import (
    LLMAttemptMetadata,
    classify_llm_response,
    FALLBACK_REASON_NOT_APPLICABLE,
    FALLBACK_REASON_PROVIDER_ERROR,
    FALLBACK_REASON_INVALID_JSON,
    FALLBACK_REASON_SCHEMA_VALIDATION_FAILED,
)
from kairoskopion.agents.contract import AgentInput, AgentOutput


# ===================================================================
# Fixtures
# ===================================================================

SAMPLE_MANUSCRIPT = """\
# Трансформация институциональных условий предпринимательства

## Введение

Данная статья исследует трансформацию институциональных условий
предпринимательской деятельности в условиях цифровой экономики.
Проблема институциональной среды предпринимательства остаётся
актуальной в контексте быстрых технологических изменений.

## Постановка проблемы

Исследовательский вопрос: каким образом цифровизация трансформирует
институциональные условия предпринимательской деятельности в России?

## Теоретические основания

Работа опирается на теорию институциональных изменений Д. Норта,
концепцию предпринимательской экосистемы Б. Айзенберга и подход
к цифровой экономике А. Гелбрейта. Также учитываются работы
российских исследователей — В.М. Полтеровича и Р.И. Капелюшникова.

## Методология

Использован комбинированный подход: институциональный анализ,
сравнительный анализ регулятивных практик и контент-анализ
нормативных актов за период 2018-2024 гг.

## Основные результаты

Показано, что цифровизация создаёт новый тип институционального
ландшафта, характеризующийся: (1) размыванием традиционных
барьеров входа, (2) формированием платформенных экосистем,
(3) трансформацией механизмов государственного регулирования.

## Список литературы

1. North D.C. Institutions, Institutional Change and Economic Performance. Cambridge, 1990.
2. Isenberg D. The Entrepreneurship Ecosystem Strategy as a New Paradigm. 2011.
3. Полтерович В.М. Институциональные ловушки. Экономика и математические методы. 1999.
"""


def _fake_openai_response(parsed: dict, model: str = "gpt-4.1-mini") -> bytes:
    """Build a fake OpenAI API JSON response."""
    content = json.dumps(parsed, ensure_ascii=False)
    body = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 500,
            "completion_tokens": 200,
            "total_tokens": 700,
        },
    }
    return json.dumps(body).encode("utf-8")


def _mock_urlopen(response_bytes: bytes):
    """Create a mock for urllib.request.urlopen that returns response_bytes."""
    mock_response = MagicMock()
    mock_response.read.return_value = response_bytes
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


VALID_INPUT_CLASSIFICATION = {
    "input_type": "manuscript",
    "confidence": "high",
    "needs_user_choice": False,
    "language_detected": "ru",
    "reasoning": "Academic text with thesis, methods, and bibliography.",
}

VALID_ARTICLE_EXTRACTION = {
    "title": "Трансформация институциональных условий предпринимательства",
    "abstract_summary": "Исследование трансформации институциональных условий.",
    "language": "ru",
    "article_stage": "full_manuscript",
    "problem_statement": "Трансформация институциональных условий в цифровой экономике",
    "research_question": "Как цифровизация трансформирует институциональные условия?",
    "object_of_inquiry": "Институциональные условия предпринимательства",
    "core_claims": ["Цифровизация создаёт новый тип институционального ландшафта"],
    "secondary_claims": [],
    "argument_structure": "deductive",
    "method_status": "empirical_method",
    "method_description": "Институциональный и сравнительный анализ",
    "genre_current": "research_article",
    "disciplinary_register_current": "Экономика, институциональная экономика",
    "novelty_mode": "extension",
    "theoretical_shoulders": ["Д. Норт", "Б. Айзенберг"],
    "opponents_or_contrasts": [],
    "key_terms": ["институциональные условия", "цифровизация", "предпринимательство"],
    "protected_core_candidate": ["Тезис о новом типе институционального ландшафта"],
    "mutable_zones": ["Список литературы", "Оформление"],
    "citation_ecology_description": "Ссылается на Норта, Айзенберга, Полтеровича",
    "unknowns": [],
    "assumptions": ["Статья ориентирована на российскую аудиторию"],
    "confidence": "high",
    "warnings": [],
    "questions_for_user": [],
}


# ===================================================================
# Track 1: LLMConfig and provider construction
# ===================================================================

class TestLLMConfig:

    def test_from_env_returns_none_when_no_model(self):
        env = {"KAIROSKOPION_LLM_PROVIDER": "openai_compatible"}
        with patch.dict(os.environ, env, clear=True):
            cfg = LLMConfig.from_env()
            assert cfg is None

    def test_from_env_returns_none_when_provider_none(self):
        env = {
            "KAIROSKOPION_LLM_PROVIDER": "none",
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = LLMConfig.from_env()
            assert cfg is None

    def test_from_env_returns_config_when_model_set(self):
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
            "KAIROSKOPION_LLM_BASE_URL": "https://api.302.ai/v1",
            "KAIROSKOPION_LLM_API_KEY": "test-key-123",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = LLMConfig.from_env()
            assert cfg is not None
            assert cfg.model == "gpt-4.1-mini"
            assert cfg.base_url == "https://api.302.ai/v1"
            assert cfg.api_key == "test-key-123"

    def test_for_role_overrides_model(self):
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
            "KAIROSKOPION_LLM_MODEL_ARTICLE_MODELER": "deepseek-chat",
            "KAIROSKOPION_LLM_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = LLMConfig.for_role("article_modeler")
            assert cfg is not None
            assert cfg.model == "deepseek-chat"

    def test_for_role_falls_through_when_no_override(self):
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
            "KAIROSKOPION_LLM_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = LLMConfig.for_role("article_modeler")
            assert cfg is not None
            assert cfg.model == "gpt-4.1-mini"

    def test_is_llm_available_true(self):
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
            "KAIROSKOPION_LLM_BASE_URL": "https://api.302.ai/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            assert is_llm_available() is True

    def test_is_llm_available_false(self):
        with patch.dict(os.environ, {}, clear=True):
            assert is_llm_available() is False

    def test_provider_status_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            status = provider_status()
            assert status["available"] is False

    def test_provider_status_with_config(self):
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
            "KAIROSKOPION_LLM_BASE_URL": "https://api.302.ai/v1",
            "KAIROSKOPION_LLM_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env, clear=True):
            status = provider_status()
            assert status["available"] is True
            assert status["model"] == "gpt-4.1-mini"
            assert status["has_api_key"] is True


# ===================================================================
# Track 2: _get_llm_provider integration
# ===================================================================

class TestGetLLMProvider:

    def test_returns_provider_when_configured(self):
        from kairoskopion.api.cases import _get_llm_provider
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
            "KAIROSKOPION_LLM_BASE_URL": "https://api.302.ai/v1",
            "KAIROSKOPION_LLM_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env, clear=True):
            provider = _get_llm_provider("article_modeler")
            assert provider is not None
            assert isinstance(provider, OpenAICompatProvider)

    def test_returns_none_when_no_key(self):
        from kairoskopion.api.cases import _get_llm_provider
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
            "KAIROSKOPION_LLM_BASE_URL": "https://api.302.ai/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            provider = _get_llm_provider("article_modeler")
            assert provider is None

    def test_returns_none_when_no_model(self):
        from kairoskopion.api.cases import _get_llm_provider
        with patch.dict(os.environ, {}, clear=True):
            provider = _get_llm_provider("article_modeler")
            assert provider is None

    def test_per_role_routing(self):
        from kairoskopion.api.cases import _get_llm_provider
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
            "KAIROSKOPION_LLM_BASE_URL": "https://api.302.ai/v1",
            "KAIROSKOPION_LLM_API_KEY": "test-key",
            "KAIROSKOPION_LLM_MODEL_INPUT_CLASSIFIER": "deepseek-chat",
        }
        with patch.dict(os.environ, env, clear=True):
            p_default = _get_llm_provider("article_modeler")
            p_routed = _get_llm_provider("input_classifier")
            assert p_default._config.model == "gpt-4.1-mini"
            assert p_routed._config.model == "deepseek-chat"


# ===================================================================
# Track 3: OpenAICompatProvider — HTTP mock tests
# ===================================================================

class TestOpenAICompatProvider:

    def _make_provider(self) -> OpenAICompatProvider:
        cfg = LLMConfig(
            model="gpt-4.1-mini",
            base_url="https://api.302.ai/v1",
            api_key_env="KAIROSKOPION_LLM_API_KEY",
            max_retries=1,
            timeout_seconds=5,
        )
        with patch.dict(os.environ, {"KAIROSKOPION_LLM_API_KEY": "test-key"}):
            return OpenAICompatProvider(cfg)

    def test_complete_success(self):
        provider = self._make_provider()
        parsed = {"input_type": "manuscript", "confidence": "high"}
        resp_bytes = _fake_openai_response(parsed)
        mock_resp = _mock_urlopen(resp_bytes)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = provider.complete(
                [{"role": "user", "content": "test"}],
            )
        assert isinstance(result, LLMResponse)
        assert result.model == "gpt-4.1-mini"
        assert result.input_tokens == 500
        assert result.output_tokens == 200
        # parsed is None when no response_schema; content has JSON
        assert result.parsed is None
        assert json.loads(result.content) == parsed

    def test_complete_with_schema(self):
        provider = self._make_provider()
        parsed = VALID_INPUT_CLASSIFICATION.copy()
        resp_bytes = _fake_openai_response(parsed)
        mock_resp = _mock_urlopen(resp_bytes)

        schema = {
            "type": "object",
            "properties": {"input_type": {"type": "string"}},
            "required": ["input_type"],
        }
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = provider.complete(
                [{"role": "user", "content": "test"}],
                response_schema=schema,
            )
        assert result.parsed is not None
        assert result.parsed["input_type"] == "manuscript"

    def test_complete_non_retryable_error(self):
        provider = self._make_provider()
        http_error = urllib.error.HTTPError(
            "https://api.302.ai/v1/chat/completions",
            401, "Unauthorized", {}, None,
        )
        with patch("urllib.request.urlopen", side_effect=http_error):
            with pytest.raises(LLMError) as exc_info:
                provider.complete([{"role": "user", "content": "test"}])
            assert exc_info.value.error_code == "AUTH_FAILED"

    def test_complete_retries_on_429(self):
        provider = self._make_provider()
        http_429 = urllib.error.HTTPError(
            "https://api.302.ai/v1/chat/completions",
            429, "Too Many Requests", {}, None,
        )
        with patch("urllib.request.urlopen", side_effect=http_429):
            with pytest.raises(LLMError) as exc_info:
                provider.complete([{"role": "user", "content": "test"}])
            assert exc_info.value.error_code == "RETRIES_EXHAUSTED"

    def test_complete_empty_response_raises(self):
        provider = self._make_provider()
        body = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "model": "gpt-4.1-mini",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": ""}, "finish_reason": "stop"}],
            "usage": {},
        }
        resp_bytes = json.dumps(body).encode()
        mock_resp = _mock_urlopen(resp_bytes)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(LLMError) as exc_info:
                provider.complete([{"role": "user", "content": "test"}])
            assert exc_info.value.error_code == "EMPTY_RESPONSE_TEXT"

    def test_complete_missing_choices_raises_llm_error(self):
        # Some proxies return HTTP 200 with an error body and no choices;
        # must surface as LLMError, not raw KeyError/IndexError
        provider = self._make_provider()
        for body in (
            {"id": "chatcmpl-test", "object": "chat.completion", "choices": []},
            {"error": {"message": "quota exceeded"}},
        ):
            resp_bytes = json.dumps(body).encode()
            mock_resp = _mock_urlopen(resp_bytes)
            with patch("urllib.request.urlopen", return_value=mock_resp):
                with pytest.raises(LLMError) as exc_info:
                    provider.complete([{"role": "user", "content": "test"}])
                assert exc_info.value.error_code == "MALFORMED_RESPONSE"


# ===================================================================
# Track 4: JSON repair smoke
# ===================================================================

class TestJSONRepairSmoke:

    def test_valid_json_parses_ok(self):
        result = repair_and_parse('{"key": "value"}')
        assert result.parsed == {"key": "value"}
        assert result.status == PARSE_STATUS_PARSED_OK

    def test_fenced_json_repaired(self):
        raw = '```json\n{"key": "value"}\n```'
        result = repair_and_parse(raw)
        assert result.parsed == {"key": "value"}
        assert result.status == PARSE_STATUS_REPAIRED_OK

    def test_trailing_comma_repaired(self):
        raw = '{"key": "value",}'
        result = repair_and_parse(raw)
        assert result.parsed == {"key": "value"}
        assert result.status == PARSE_STATUS_REPAIRED_OK

    def test_smart_quotes_repaired(self):
        raw = '“ key ” : “ value ”'
        raw_obj = '{“key”: “value”}'
        result = repair_and_parse(raw_obj)
        assert result.parsed == {"key": "value"}
        assert result.status == PARSE_STATUS_REPAIRED_OK

    def test_prose_around_json_extracted(self):
        raw = 'Here is the result:\n\n{"key": "value"}\n\nHope this helps!'
        result = repair_and_parse(raw)
        assert result.parsed == {"key": "value"}

    def test_invalid_json_fails(self):
        result = repair_and_parse("not json at all")
        assert result.parsed is None
        assert result.status == PARSE_STATUS_REPAIR_FAILED

    def test_schema_validation_fails_on_missing_required(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }
        result = repair_and_parse('{"name": "test"}', schema=schema)
        assert result.status == PARSE_STATUS_SCHEMA_VALIDATION_FAILED

    def test_optional_fields_filled(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "tags": {"type": "array"},
            },
            "required": ["name"],
        }
        result = repair_and_parse('{"name": "test"}', schema=schema)
        assert result.parsed["tags"] == []
        assert result.status == PARSE_STATUS_PARSED_OK


# ===================================================================
# Track 5: ArticleModelerAgent LLM path
# ===================================================================

class TestArticleModelerAgentLLM:

    def test_execute_produces_article_model(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent

        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="test-op",
            agent_role_id="article_modeler",
            raw_text=SAMPLE_MANUSCRIPT,
        )

        mock_provider = MagicMock()
        mock_provider.complete.return_value = LLMResponse(
            content=json.dumps(VALID_ARTICLE_EXTRACTION, ensure_ascii=False),
            parsed=VALID_ARTICLE_EXTRACTION,
            model="gpt-4.1-mini",
            input_tokens=500,
            output_tokens=200,
            latency_ms=1200.0,
            finish_reason="stop",
        )

        output = agent.execute(inp, mock_provider)

        assert output.output_entity_type == "ArticleModel"
        assert isinstance(output.output_entity, dict)
        assert output.output_entity["title_current"] is not None
        assert output.confidence == "high"
        assert output.evidence_status == "INFERENCE"
        assert output.llm_usage is not None
        assert output.llm_usage["model"] == "gpt-4.1-mini"

        attempt = output.output_entity.get("extraction_attempt")
        assert attempt is not None
        assert attempt["llm_attempted"] is True
        assert attempt["fallback_used"] is False
        assert attempt["parse_status"] == "parsed_ok"

    def test_execute_falls_back_on_provider_error(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent

        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="test-op",
            agent_role_id="article_modeler",
            raw_text=SAMPLE_MANUSCRIPT,
        )

        mock_provider = MagicMock()
        mock_provider.complete.side_effect = LLMError(
            "HTTP 500", error_code="PROVIDER_HTTP_ERROR",
        )

        output = agent.execute(inp, mock_provider)

        assert output.output_entity_type == "ArticleModel"
        assert isinstance(output.output_entity, dict)
        attempt = output.output_entity.get("extraction_attempt")
        assert attempt is not None
        assert attempt["llm_attempted"] is True
        assert attempt["fallback_used"] is True
        assert attempt["fallback_reason"] == "provider_error"

    def test_execute_falls_back_on_invalid_json(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent

        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="test-op",
            agent_role_id="article_modeler",
            raw_text=SAMPLE_MANUSCRIPT,
        )

        mock_provider = MagicMock()
        mock_provider.complete.return_value = LLMResponse(
            content="I cannot parse this text properly. Here is my analysis...",
            parsed=None,
            model="gpt-4.1-mini",
            input_tokens=500,
            output_tokens=50,
            latency_ms=800.0,
        )

        output = agent.execute(inp, mock_provider)

        assert output.output_entity_type == "ArticleModel"
        attempt = output.output_entity.get("extraction_attempt")
        assert attempt is not None
        assert attempt["fallback_used"] is True
        assert attempt["fallback_reason"] in ("invalid_json", "repair_failed")

    def test_run_dispatches_to_llm_when_provider_given(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent

        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="test-op",
            agent_role_id="article_modeler",
            raw_text=SAMPLE_MANUSCRIPT,
        )

        mock_provider = MagicMock()
        mock_provider.complete.return_value = LLMResponse(
            content=json.dumps(VALID_ARTICLE_EXTRACTION),
            parsed=VALID_ARTICLE_EXTRACTION,
            model="gpt-4.1-mini",
            input_tokens=500,
            output_tokens=200,
            latency_ms=1000.0,
        )

        output = agent.run(inp, provider=mock_provider)
        mock_provider.complete.assert_called_once()
        assert output.evidence_status == "INFERENCE"

    def test_run_dispatches_to_deterministic_when_no_provider(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent

        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="test-op",
            agent_role_id="article_modeler",
            raw_text=SAMPLE_MANUSCRIPT,
        )

        output = agent.run(inp, provider=None)
        assert output.output_entity_type == "ArticleModel"
        assert output.evidence_status == "heuristic"


# ===================================================================
# Track 6: InputClassifierAgent LLM path
# ===================================================================

class TestInputClassifierAgentLLM:

    def test_execute_classifies_manuscript(self):
        from kairoskopion.agents.input_classifier import InputClassifierAgent

        agent = InputClassifierAgent()
        inp = AgentInput(
            operation_id="test-op",
            agent_role_id="input_classifier",
            raw_text=SAMPLE_MANUSCRIPT,
        )

        mock_provider = MagicMock()
        mock_provider.complete.return_value = LLMResponse(
            content=json.dumps(VALID_INPUT_CLASSIFICATION),
            parsed=VALID_INPUT_CLASSIFICATION,
            model="gpt-4.1-mini",
            input_tokens=300,
            output_tokens=50,
            latency_ms=400.0,
        )

        output = agent.execute(inp, mock_provider)
        assert output.output_entity.get("input_type") == "manuscript"
        assert output.output_entity.get("confidence") == "high"


# ===================================================================
# Track 7: classify_llm_response shared helper
# ===================================================================

class TestClassifyLLMResponse:

    def test_fast_path_parsed_dict(self):
        response = LLMResponse(
            content='{"key": "value"}',
            parsed={"key": "value"},
            model="gpt-4.1-mini",
            latency_ms=100.0,
        )
        parsed, meta, steps, errors = classify_llm_response(response, None)
        assert parsed == {"key": "value"}
        assert meta.llm_attempted is True
        assert meta.fallback_used is False
        assert meta.parse_status == "parsed_ok"

    def test_repair_path_fenced_json(self):
        response = LLMResponse(
            content='```json\n{"key": "value"}\n```',
            parsed=None,
            model="gpt-4.1-mini",
            latency_ms=100.0,
        )
        parsed, meta, steps, errors = classify_llm_response(response, None)
        assert parsed == {"key": "value"}
        assert meta.parse_status == "repaired_ok"

    def test_fallback_path_invalid_json(self):
        response = LLMResponse(
            content="not json at all",
            parsed=None,
            model="gpt-4.1-mini",
            latency_ms=100.0,
        )
        parsed, meta, steps, errors = classify_llm_response(response, None)
        assert parsed is None
        assert meta.fallback_used is True
        assert meta.fallback_reason in ("invalid_json", "repair_failed")


# ===================================================================
# Track 8: LLMAttemptMetadata
# ===================================================================

class TestLLMAttemptMetadata:

    def test_parse_ok_metadata(self):
        meta = LLMAttemptMetadata.parse_ok(
            provider="openai_compatible",
            model="gpt-4.1-mini",
            latency_ms=1200.0,
            content_present=True,
        )
        assert meta.llm_attempted is True
        assert meta.fallback_used is False
        assert meta.parse_status == "parsed_ok"
        d = meta.to_dict()
        assert d["llm_model"] == "gpt-4.1-mini"

    def test_fallback_metadata(self):
        meta = LLMAttemptMetadata.fallback(
            reason=FALLBACK_REASON_PROVIDER_ERROR,
            provider="openai_compatible",
            model="gpt-4.1-mini",
            validation_errors=["HTTP 500"],
        )
        assert meta.llm_attempted is True
        assert meta.fallback_used is True
        assert meta.fallback_reason == "provider_error"
        assert meta.warning_for_user is not None
        assert "ошибку" in meta.warning_for_user

    def test_not_attempted_metadata(self):
        meta = LLMAttemptMetadata.not_attempted()
        assert meta.llm_attempted is False
        assert meta.fallback_used is True
        assert meta.fallback_reason == "llm_unavailable"
        assert meta.warning_for_user is not None

    def test_roundtrip_to_from_dict(self):
        meta = LLMAttemptMetadata.parse_ok(
            provider="openai_compatible",
            model="gpt-4.1-mini",
            latency_ms=1000.0,
            content_present=True,
            repaired=True,
            repair_steps=["fences_stripped"],
        )
        d = meta.to_dict()
        restored = LLMAttemptMetadata.from_dict(d)
        assert restored.llm_model == meta.llm_model
        assert restored.parse_status == meta.parse_status
        assert restored.repair_steps == meta.repair_steps


# ===================================================================
# Track 9: Case.intake_text with mocked LLM
# ===================================================================

class TestCaseIntakeWithLLM:

    def test_intake_uses_llm_for_classification(self, tmp_path):
        from kairoskopion.api.cases import Case
        from kairoskopion.registry.integration import RegistryIntegrationService
        from kairoskopion.registry.services import RegistryHub

        reg_dir = tmp_path / "registry"
        reg_dir.mkdir(parents=True)
        hub = RegistryHub(data_dir=reg_dir)
        svc = RegistryIntegrationService(hub=hub)
        case = Case(registry_service=svc)

        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
            "KAIROSKOPION_LLM_BASE_URL": "https://api.302.ai/v1",
            "KAIROSKOPION_LLM_API_KEY": "test-key",
        }

        classification_response = _fake_openai_response(VALID_INPUT_CLASSIFICATION)
        article_response = _fake_openai_response(VALID_ARTICLE_EXTRACTION)

        call_count = [0]

        def fake_urlopen(req, **kwargs):
            nonlocal call_count
            call_count[0] += 1
            if call_count[0] == 1:
                return _mock_urlopen(classification_response)
            return _mock_urlopen(article_response)

        with patch.dict(os.environ, env, clear=True):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = case.intake_text(SAMPLE_MANUSCRIPT)

        assert result is not None
        assert case.input_type in ("manuscript", "article")

    def test_intake_falls_back_without_llm(self, tmp_path):
        from kairoskopion.api.cases import Case
        from kairoskopion.registry.integration import RegistryIntegrationService
        from kairoskopion.registry.services import RegistryHub

        reg_dir = tmp_path / "registry"
        reg_dir.mkdir(parents=True)
        hub = RegistryHub(data_dir=reg_dir)
        svc = RegistryIntegrationService(hub=hub)
        case = Case(registry_service=svc)

        with patch.dict(os.environ, {}, clear=True):
            result = case.intake_text(SAMPLE_MANUSCRIPT)

        assert result is not None
        assert case.input_type is not None


# ===================================================================
# Track 10: Per-role model routing E2E
# ===================================================================

class TestPerRoleRoutingE2E:

    def test_different_models_for_different_roles(self):
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
            "KAIROSKOPION_LLM_BASE_URL": "https://api.302.ai/v1",
            "KAIROSKOPION_LLM_API_KEY": "test-key",
            "KAIROSKOPION_LLM_MODEL_ARTICLE_MODELER": "deepseek-chat",
            "KAIROSKOPION_LLM_MODEL_FIT_ASSESSOR": "gpt-4o",
        }
        with patch.dict(os.environ, env, clear=True):
            status = provider_status()
            assert status["model_per_role"]["article_modeler"] == "deepseek-chat"
            assert status["model_per_role"]["fit_assessor"] == "gpt-4o"
            assert status["model_per_role"]["input_classifier"] == "gpt-4.1-mini"
            assert "article_modeler" in status["overridden_roles"]
            assert "fit_assessor" in status["overridden_roles"]
            assert "input_classifier" not in status["overridden_roles"]

    def test_provider_status_lists_all_routed_roles(self):
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4.1-mini",
            "KAIROSKOPION_LLM_BASE_URL": "https://api.302.ai/v1",
            "KAIROSKOPION_LLM_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env, clear=True):
            status = provider_status()
            assert "model_per_role" in status
            assert len(status["model_per_role"]) >= 10


# ===================================================================
# Track 11: LLM input limits
# ===================================================================

class TestLLMInputLimits:

    def test_input_cap_constant_exists(self):
        from kairoskopion.llm.input_limits import LLM_INPUT_CHAR_CAP, INTAKE_HARD_CHAR_CAP
        assert LLM_INPUT_CHAR_CAP == 150_000
        assert INTAKE_HARD_CHAR_CAP == 400_000

    def test_short_text_unchanged(self):
        from kairoskopion.llm.input_limits import cap_llm_input
        short_text = "Short text under cap"
        text, info = cap_llm_input(short_text)
        assert text == short_text
        assert info.truncated is False

    def test_long_text_truncated(self):
        from kairoskopion.llm.input_limits import cap_llm_input
        long_text = "x" * 200_000
        text, info = cap_llm_input(long_text)
        assert info.truncated is True
        assert info.original_chars == 200_000
        assert info.used_chars <= 150_000
