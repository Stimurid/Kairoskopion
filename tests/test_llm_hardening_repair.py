"""Tests for LLM hardening repair: attempt history, agent_role propagation,
error propagation chain, size rotation, and classify_llm_response bridge.

Spec steps 5, 8: focused acceptance tests for the contract gaps repaired
on branch feature/llm-timeout-fallback-session-logging.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kairoskopion.llm.attempt_metadata import (
    FALLBACK_REASON_PROVIDER_ERROR,
    LLMAttemptMetadata,
    LLMModelAttempt,
    classify_llm_response,
)
from kairoskopion.llm.session_log import (
    DEFAULT_MAX_BYTES,
    LLMSessionLog,
    MAX_PROCESS_FILES,
    _rotate_fifo,
)


# ---------------------------------------------------------------------------
# A. LLMModelAttempt round-trip
# ---------------------------------------------------------------------------

class TestLLMModelAttemptRoundTrip:
    def test_to_dict_from_dict_identity(self):
        a = LLMModelAttempt(
            attempt_index=2,
            model="gpt-4o-mini",
            agent_role="article_modeler",
            started_at="2026-07-07T12:00:00",
            latency_ms=1234.5,
            provider_status="ok",
            response_status="ok",
            parse_status="parsed_ok",
            error_code="",
            retryable=False,
            transition="success",
        )
        d = a.to_dict()
        b = LLMModelAttempt.from_dict(d)
        assert b.attempt_index == 2
        assert b.model == "gpt-4o-mini"
        assert b.agent_role == "article_modeler"
        assert b.transition == "success"
        assert b.latency_ms == 1234.5

    def test_from_dict_defaults(self):
        a = LLMModelAttempt.from_dict({})
        assert a.attempt_index == 0
        assert a.model == ""
        assert a.retryable is False


# ---------------------------------------------------------------------------
# B. LLMAttemptMetadata new fields
# ---------------------------------------------------------------------------

class TestLLMAttemptMetadataNewFields:
    def test_parse_ok_carries_attempt_history(self):
        attempts = [
            LLMModelAttempt(attempt_index=0, model="m1", transition="retry"),
            LLMModelAttempt(attempt_index=1, model="m2", transition="success"),
        ]
        meta = LLMAttemptMetadata.parse_ok(
            provider="openai_compatible",
            model="m2",
            latency_ms=500.0,
            content_present=True,
            requested_model="m1",
            effective_model="m2",
            attempt_count=2,
            attempts=attempts,
            agent_role="article_modeler",
        )
        assert meta.requested_model == "m1"
        assert meta.effective_model == "m2"
        assert meta.attempt_count == 2
        assert len(meta.attempts) == 2
        assert meta.agent_role == "article_modeler"

    def test_fallback_carries_error_code_and_attempts(self):
        attempts = [
            LLMModelAttempt(attempt_index=0, model="m1", error_code="HTTP_429"),
        ]
        meta = LLMAttemptMetadata.fallback(
            reason=FALLBACK_REASON_PROVIDER_ERROR,
            provider="openai_compatible",
            requested_model="m1",
            effective_model=None,
            attempt_count=1,
            attempts=attempts,
            final_error_code="RETRIES_EXHAUSTED",
            agent_role="venue_profiler",
        )
        assert meta.final_error_code == "RETRIES_EXHAUSTED"
        assert meta.agent_role == "venue_profiler"
        assert len(meta.attempts) == 1

    def test_not_attempted_carries_agent_role(self):
        meta = LLMAttemptMetadata.not_attempted(agent_role="fit_assessor")
        assert meta.agent_role == "fit_assessor"
        assert meta.llm_attempted is False

    def test_to_dict_from_dict_round_trip_with_attempts(self):
        attempts = [
            LLMModelAttempt(attempt_index=0, model="m1", transition="retry"),
        ]
        meta = LLMAttemptMetadata.parse_ok(
            provider="test",
            model="m1",
            latency_ms=100,
            content_present=True,
            requested_model="m1",
            effective_model="m1",
            attempt_count=1,
            attempts=attempts,
            agent_role="test_agent",
        )
        d = meta.to_dict()
        restored = LLMAttemptMetadata.from_dict(d)
        assert restored.requested_model == "m1"
        assert restored.agent_role == "test_agent"
        assert len(restored.attempts) == 1
        assert isinstance(restored.attempts[0], LLMModelAttempt)
        assert restored.attempts[0].transition == "retry"


# ---------------------------------------------------------------------------
# C. classify_llm_response bridge
# ---------------------------------------------------------------------------

@dataclass
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
    attempts: list = None  # type: ignore[assignment]
    agent_role: str = ""

    def __post_init__(self):
        if self.attempts is None:
            self.attempts = []


class TestClassifyLLMResponseBridge:
    def test_parsed_ok_propagates_attempt_fields(self):
        attempts = [
            LLMModelAttempt(attempt_index=0, model="m1", transition="success"),
        ]
        resp = _FakeResponse(
            parsed={"title": "Test"},
            requested_model="m1",
            effective_model="m1",
            attempt_count=1,
            attempts=attempts,
            agent_role="article_modeler",
        )
        parsed, meta, _, _ = classify_llm_response(resp, schema=None)
        assert parsed == {"title": "Test"}
        assert meta.requested_model == "m1"
        assert meta.effective_model == "m1"
        assert meta.agent_role == "article_modeler"
        assert len(meta.attempts) == 1

    def test_fallback_response_marks_primary_model_failed(self):
        attempts = [
            LLMModelAttempt(attempt_index=0, model="m1", error_code="HTTP_429", transition="retry"),
            LLMModelAttempt(attempt_index=1, model="m2", transition="success"),
        ]
        resp = _FakeResponse(
            parsed={"title": "Test"},
            requested_model="m1",
            effective_model="m2",
            fallback_used=True,
            attempt_count=2,
            attempts=attempts,
            agent_role="venue_profiler",
        )
        parsed, meta, _, _ = classify_llm_response(resp, schema=None)
        assert parsed is not None
        assert meta.fallback_used is True
        assert meta.fallback_reason == "primary_model_failed"
        assert meta.effective_model == "m2"
        assert meta.requested_model == "m1"

    def test_invalid_json_fallback_carries_attempts(self):
        attempts = [
            LLMModelAttempt(attempt_index=0, model="m1", transition="success"),
        ]
        resp = _FakeResponse(
            content="not json at all",
            parsed=None,
            requested_model="m1",
            effective_model="m1",
            attempt_count=1,
            attempts=attempts,
            agent_role="semantic_profiler",
        )
        parsed, meta, _, _ = classify_llm_response(resp, schema=None)
        assert parsed is None
        assert meta.fallback_used is True
        assert meta.agent_role == "semantic_profiler"
        assert len(meta.attempts) == 1


# ---------------------------------------------------------------------------
# D. Error propagation through agent layer
# ---------------------------------------------------------------------------

class TestErrorPropagationThroughAgent:
    """Scenario A/B/C from spec step 5."""

    def test_scenario_a_auth_error_propagates_to_extraction_attempt(self):
        """AUTH_FAILED → agent catches → extraction_attempt has
        fallback_used=True, fallback_reason=provider_error."""
        from kairoskopion.agents.article_modeler import ArticleModelerAgent
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.llm.openai_compat import LLMError

        class _AuthFailProvider:
            def complete(self, *a, **kw):
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

        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="test_auth",
            agent_role_id="article_modeler",
            raw_text="Тестовый текст для проверки ошибки авторизации. " * 5,
        )
        out = agent.execute(inp, _AuthFailProvider())
        ea = out.output_entity.get("extraction_attempt")
        assert ea is not None
        assert ea["fallback_used"] is True
        assert ea["fallback_reason"] == "provider_error"

    def test_scenario_b_retries_exhausted_surfaces_in_agent_output(self):
        """RETRIES_EXHAUSTED → deterministic fallback with honest metadata."""
        from kairoskopion.agents.article_modeler import ArticleModelerAgent
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.llm.openai_compat import LLMError

        class _ExhaustedProvider:
            def complete(self, *a, **kw):
                err = LLMError("All models failed", error_code="RETRIES_EXHAUSTED")
                err.attempts = [  # type: ignore[attr-defined]
                    LLMModelAttempt(attempt_index=0, model="m1", error_code="HTTP_429", transition="retry"),
                    LLMModelAttempt(attempt_index=1, model="m2", error_code="HTTP_500", transition="exhausted"),
                ]
                raise err

        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="test_exhaust",
            agent_role_id="article_modeler",
            raw_text="Тестовый текст для проверки полного отказа провайдера. " * 5,
        )
        out = agent.execute(inp, _ExhaustedProvider())
        ea = out.output_entity.get("extraction_attempt")
        assert ea is not None
        assert ea["fallback_used"] is True
        assert ea["parse_status"] == "not_attempted"

    def test_scenario_c_successful_llm_call_has_agent_role(self):
        """Successful LLM call → extraction_attempt includes agent_role."""
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.agents.citation_ecology import CitationEcologyAgent

        class _SuccessProvider:
            def complete(self, *a, **kw):
                return _FakeResponse(
                    parsed={
                        "gaps": [],
                        "bridge_references": [],
                        "ecology_health": "adequate",
                        "citation_role_map": [],
                        "venue_alignment_assessment": "ok",
                        "summary": "test",
                        "confidence": "medium",
                        "unknowns": [],
                    },
                    model="gpt-4o-mini",
                    requested_model="gpt-4o-mini",
                    effective_model="gpt-4o-mini",
                    attempt_count=1,
                    attempts=[
                        LLMModelAttempt(
                            attempt_index=0,
                            model="gpt-4o-mini",
                            agent_role="citation_ecology",
                            transition="success",
                        ),
                    ],
                    agent_role="citation_ecology",
                )

        agent = CitationEcologyAgent()
        inp = AgentInput(
            operation_id="test_role",
            agent_role_id="citation_ecology",
            entities={
                "article": {"title_current": "Test"},
                "venue": {"canonical_name": "Test Journal"},
                "bibliography": {},
            },
        )
        out = agent.execute(inp, _SuccessProvider())
        ea = out.output_entity.get("extraction_attempt")
        assert ea is not None
        assert ea.get("agent_role") == "citation_ecology"
        assert ea.get("attempt_count") == 1
        assert len(ea.get("attempts", [])) == 1


# ---------------------------------------------------------------------------
# E. Size rotation
# ---------------------------------------------------------------------------

class TestSizeRotation:
    def test_rotation_triggers_on_max_bytes(self, tmp_path):
        log = LLMSessionLog(
            session_id="size_test",
            log_dir=tmp_path,
            max_bytes=200,
        )
        original_path = log.path
        for i in range(20):
            log.log_call(model=f"m{i}", parse_status="ok", messages_preview="x" * 50)
        assert log.path != original_path

    def test_max_bytes_env_var(self, tmp_path):
        with patch.dict(os.environ, {"KAIROSKOPION_LLM_LOG_MAX_BYTES": "500"}):
            log = LLMSessionLog(session_id="env_test", log_dir=tmp_path)
            assert log.max_bytes == 500

    def test_max_files_env_var(self, tmp_path):
        with patch.dict(os.environ, {"KAIROSKOPION_LLM_LOG_MAX_FILES": "10"}):
            log = LLMSessionLog(session_id="env_test2", log_dir=tmp_path)
            for i in range(15):
                (tmp_path / f"old_{i:02d}.jsonl").write_text("x\n")
            _rotate_fifo(tmp_path, max_files=10)
            remaining = list(tmp_path.glob("*.jsonl"))
            assert len(remaining) <= 11  # 10 old + 1 current


# ---------------------------------------------------------------------------
# F. Agent role propagation — verify all agents pass agent_role
# ---------------------------------------------------------------------------

class TestAgentRolePropagation:
    """Verify that provider.complete() is called with agent_role kwarg
    for key agents (not exhaustive, but covers the critical path)."""

    def test_article_modeler_passes_agent_role(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent
        from kairoskopion.agents.contract import AgentInput

        call_kwargs: dict[str, Any] = {}

        class _SpyProvider:
            def complete(self, messages, **kw):
                call_kwargs.update(kw)
                return _FakeResponse(
                    parsed={
                        "title": "Test",
                        "language": "ru",
                        "confidence": "medium",
                    },
                    agent_role=kw.get("agent_role", ""),
                )

        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="spy",
            agent_role_id="article_modeler",
            raw_text="Текст для тестирования передачи agent_role. " * 5,
        )
        agent.execute(inp, _SpyProvider())
        assert call_kwargs.get("agent_role") == "article_modeler"

    def test_fit_assessor_passes_agent_role(self):
        from kairoskopion.agents.fit_assessor import FitAssessorAgent
        from kairoskopion.agents.contract import AgentInput

        call_kwargs: dict[str, Any] = {}

        class _SpyProvider:
            def complete(self, messages, **kw):
                call_kwargs.update(kw)
                return _FakeResponse(
                    parsed={
                        "axes": {},
                        "overall_label": "possible",
                        "mismatches": [],
                        "confidence": "medium",
                        "unknowns": [],
                    },
                    agent_role=kw.get("agent_role", ""),
                )

        agent = FitAssessorAgent()
        inp = AgentInput(
            operation_id="spy",
            agent_role_id="fit_assessor",
            entities={
                "article": {"title_current": "Test"},
                "venue": {"canonical_name": "Journal"},
            },
        )
        agent.execute(inp, _SpyProvider())
        assert call_kwargs.get("agent_role") == "fit_assessor"


# ---------------------------------------------------------------------------
# G. Provider diagnostic log terminology
# ---------------------------------------------------------------------------

class TestProviderDiagnosticLogTerminology:
    def test_log_record_uses_process_file_not_session(self, tmp_path):
        log = LLMSessionLog(session_id="term_test", log_dir=tmp_path)
        log.log_call(model="m", parse_status="ok")
        content = log.path.read_text(encoding="utf-8").strip()
        rec = json.loads(content)
        assert "process_file" in rec
        assert "session" not in rec

    def test_agent_role_in_log_record(self, tmp_path):
        log = LLMSessionLog(session_id="role_test", log_dir=tmp_path)
        log.log_call(model="m", agent_role="article_modeler", parse_status="ok")
        rec = json.loads(log.path.read_text(encoding="utf-8").strip())
        assert rec["agent_role"] == "article_modeler"
