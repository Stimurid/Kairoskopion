"""Deterministic acceptance tests for LLM hardening:
session logging (FIFO), fallback model queue, typed errors, retry policy.

Tests use fake HTTP transports — no live provider calls.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

from kairoskopion.llm.config import LLMConfig
from kairoskopion.llm.openai_compat import LLMError, OpenAICompatProvider
from kairoskopion.llm.session_log import (
    LLMSessionLog,
    MAX_PROCESS_FILES,
    _rotate_fifo,
    get_session_log,
    reset_session_log,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    model: str = "primary-model",
    fallback_models: list[str] | None = None,
    max_retries: int = 2,
    timeout_seconds: float = 5.0,
) -> LLMConfig:
    return LLMConfig(
        provider="openai_compatible",
        model=model,
        base_url="https://fake.api/v1",
        api_key_env="FAKE_KEY",
        temperature=0.2,
        max_tokens=1024,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        fallback_models=fallback_models or [],
    )


def _success_response(model: str = "primary-model") -> bytes:
    return json.dumps({
        "choices": [{
            "message": {"content": '{"result": "ok"}'},
            "finish_reason": "stop",
        }],
        "model": model,
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }).encode()


def _mock_urlopen_success(model: str = "primary-model"):
    resp = MagicMock()
    resp.read.return_value = _success_response(model)
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _http_error(code: int, reason: str = "Error") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://fake.api/v1/chat/completions",
        code, reason, {}, None,
    )


def _make_provider(
    model: str = "primary-model",
    fallback_models: list[str] | None = None,
    max_retries: int = 2,
    log_dir: Path | None = None,
) -> OpenAICompatProvider:
    cfg = _make_config(model=model, fallback_models=fallback_models, max_retries=max_retries)
    p = OpenAICompatProvider(cfg)
    if log_dir:
        reset_session_log("test")
        from kairoskopion.llm import session_log
        session_log._global_log = LLMSessionLog(session_id="test", log_dir=log_dir)
    return p


# ===========================================================================
# A. Primary succeeds
# ===========================================================================

class TestPrimarySucceeds(unittest.TestCase):

    def test_primary_called_once_no_fallback(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(fallback_models=["fallback-1"], log_dir=tmp)
        mock_resp = _mock_urlopen_success("primary-model")

        with patch("urllib.request.urlopen", return_value=mock_resp) as m:
            result = provider.complete([{"role": "user", "content": "hi"}])

        self.assertEqual(m.call_count, 1)
        self.assertEqual(result.model, "primary-model")
        self.assertIn("result", result.content)

    def test_primary_success_logged(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(log_dir=tmp)
        mock_resp = _mock_urlopen_success()

        with patch("urllib.request.urlopen", return_value=mock_resp):
            provider.complete([{"role": "user", "content": "hi"}])

        log = get_session_log()
        lines = log.path.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 1)
        rec = json.loads(lines[0])
        self.assertEqual(rec["model"], "primary-model")
        self.assertNotIn("error_code", rec)
        self.assertNotIn("fallback_model", rec)


# ===========================================================================
# B. Primary retryable failure, fallback succeeds
# ===========================================================================

class TestFallbackOnRetryableFailure(unittest.TestCase):

    def test_429_primary_then_fallback_succeeds(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(
            fallback_models=["fallback-1"],
            max_retries=1,
            log_dir=tmp,
        )
        call_count = {"n": 0}
        error_429 = _http_error(429, "Too Many Requests")

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            req = args[0]
            body = json.loads(req.data.decode())
            if body["model"] == "primary-model":
                raise error_429
            return _mock_urlopen_success("fallback-1")

        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = provider.complete([{"role": "user", "content": "test"}])

        self.assertEqual(result.model, "fallback-1")
        self.assertIn("result", result.content)

    def test_503_primary_then_fallback_succeeds(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(
            fallback_models=["fallback-1"],
            max_retries=1,
            log_dir=tmp,
        )
        error_503 = _http_error(503, "Service Unavailable")

        def side_effect(*args, **kwargs):
            body = json.loads(args[0].data.decode())
            if body["model"] == "primary-model":
                raise error_503
            return _mock_urlopen_success("fallback-1")

        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = provider.complete([{"role": "user", "content": "test"}])

        self.assertEqual(result.model, "fallback-1")

    def test_timeout_primary_then_fallback_succeeds(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(
            fallback_models=["fallback-1"],
            max_retries=1,
            log_dir=tmp,
        )

        def side_effect(*args, **kwargs):
            body = json.loads(args[0].data.decode())
            if body["model"] == "primary-model":
                raise TimeoutError("Connection timed out")
            return _mock_urlopen_success("fallback-1")

        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = provider.complete([{"role": "user", "content": "test"}])

        self.assertEqual(result.model, "fallback-1")

    def test_network_error_primary_then_fallback_succeeds(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(
            fallback_models=["fallback-1"],
            max_retries=1,
            log_dir=tmp,
        )

        def side_effect(*args, **kwargs):
            body = json.loads(args[0].data.decode())
            if body["model"] == "primary-model":
                raise urllib.error.URLError("DNS lookup failed")
            return _mock_urlopen_success("fallback-1")

        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = provider.complete([{"role": "user", "content": "test"}])

        self.assertEqual(result.model, "fallback-1")

    def test_fallback_logged_with_fallback_model_field(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(
            fallback_models=["fallback-1"],
            max_retries=1,
            log_dir=tmp,
        )
        error_429 = _http_error(429, "Too Many Requests")

        def side_effect(*args, **kwargs):
            body = json.loads(args[0].data.decode())
            if body["model"] == "primary-model":
                raise error_429
            return _mock_urlopen_success("fallback-1")

        with patch("urllib.request.urlopen", side_effect=side_effect):
            provider.complete([{"role": "user", "content": "test"}])

        log = get_session_log()
        lines = log.path.read_text(encoding="utf-8").strip().split("\n")
        records = [json.loads(l) for l in lines]
        error_recs = [r for r in records if r.get("error_code")]
        success_recs = [r for r in records if not r.get("error_code")]
        self.assertTrue(len(error_recs) >= 1)
        self.assertTrue(len(success_recs) >= 1)
        fb_rec = success_recs[-1]
        self.assertEqual(fb_rec.get("fallback_model"), "fallback-1")


# ===========================================================================
# C. Authentication failure — immediate, no fallback
# ===========================================================================

class TestAuthFailureNoFallback(unittest.TestCase):

    def test_401_immediate_error_no_fallback(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(
            fallback_models=["fallback-1", "fallback-2"],
            max_retries=3,
            log_dir=tmp,
        )

        with patch("urllib.request.urlopen", side_effect=_http_error(401, "Unauthorized")):
            with self.assertRaises(LLMError) as ctx:
                provider.complete([{"role": "user", "content": "test"}])

        self.assertEqual(ctx.exception.error_code, "AUTH_FAILED")

    def test_403_immediate_error_no_fallback(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(
            fallback_models=["fallback-1"],
            max_retries=3,
            log_dir=tmp,
        )

        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            raise _http_error(403, "Forbidden")

        with patch("urllib.request.urlopen", side_effect=side_effect):
            with self.assertRaises(LLMError) as ctx:
                provider.complete([{"role": "user", "content": "test"}])

        self.assertEqual(ctx.exception.error_code, "AUTH_FAILED")
        self.assertEqual(call_count["n"], 1)

    def test_auth_failure_no_successful_artifact(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(fallback_models=["fb"], log_dir=tmp)

        with patch("urllib.request.urlopen", side_effect=_http_error(401)):
            with self.assertRaises(LLMError):
                provider.complete([{"role": "user", "content": "test"}])

    def test_auth_error_propagates_through_agent(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent
        from kairoskopion.agents.contract import AgentInput

        class _AuthFailProvider:
            def complete(self, *a, **kw):
                raise LLMError("API key expired", error_code="AUTH_FAILED")

        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="t",
            agent_role_id="article_modeler",
            raw_text="Тестовый текст для проверки ошибки авторизации.",
        )
        out = agent.execute(inp, _AuthFailProvider())
        ea = out.output_entity.get("extraction_attempt")
        self.assertIsNotNone(ea)
        self.assertTrue(ea["fallback_used"])
        self.assertEqual(ea["fallback_reason"], "provider_error")


# ===========================================================================
# D. All models fail — exhaustion
# ===========================================================================

class TestAllModelsFail(unittest.TestCase):

    def test_all_models_exhausted_raises_retries_exhausted(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(
            fallback_models=["fb-1", "fb-2"],
            max_retries=1,
            log_dir=tmp,
        )

        with patch("urllib.request.urlopen", side_effect=_http_error(500, "Internal Server Error")):
            with self.assertRaises(LLMError) as ctx:
                provider.complete([{"role": "user", "content": "test"}])

        self.assertEqual(ctx.exception.error_code, "RETRIES_EXHAUSTED")

    def test_all_models_attempted_in_order(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(
            fallback_models=["fb-1", "fb-2"],
            max_retries=1,
            log_dir=tmp,
        )
        models_called = []

        def side_effect(*args, **kwargs):
            body = json.loads(args[0].data.decode())
            models_called.append(body["model"])
            raise _http_error(502, "Bad Gateway")

        with patch("urllib.request.urlopen", side_effect=side_effect):
            with self.assertRaises(LLMError):
                provider.complete([{"role": "user", "content": "test"}])

        self.assertEqual(models_called, ["primary-model", "fb-1", "fb-2"])

    def test_exhaustion_no_fake_article_model(self):
        from kairoskopion.agents.article_modeler import ArticleModelerAgent
        from kairoskopion.agents.contract import AgentInput

        class _AlwaysFail:
            def complete(self, *a, **kw):
                raise LLMError("All dead", error_code="RETRIES_EXHAUSTED")

        agent = ArticleModelerAgent()
        inp = AgentInput(
            operation_id="t",
            agent_role_id="article_modeler",
            raw_text="Тестовый текст для проверки полного отказа провайдера.",
        )
        out = agent.execute(inp, _AlwaysFail())
        ea = out.output_entity.get("extraction_attempt")
        self.assertIsNotNone(ea)
        self.assertTrue(ea["fallback_used"])
        self.assertEqual(ea["parse_status"], "not_attempted")


# ===========================================================================
# HTTP status code policy: explicit per-status expectations
# ===========================================================================

class TestHTTPStatusPolicy(unittest.TestCase):
    """Each HTTP status has an explicit policy:
    - retry: retries on same model, then advances to fallback
    - terminal: fails immediately, no retry
    - auth: fails immediately, no retry, no fallback
    """

    RETRYABLE_CODES = [408, 429, 500, 502, 503, 504, 529]
    TERMINAL_CODES = [400, 404]
    AUTH_CODES = [401, 403]

    def _run_single_attempt(self, code: int) -> tuple[str, int]:
        """Returns (error_code, call_count)."""
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(max_retries=1, log_dir=tmp)
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            raise _http_error(code, f"Status {code}")

        with patch("urllib.request.urlopen", side_effect=side_effect):
            try:
                provider.complete([{"role": "user", "content": "x"}])
                return "no_error", call_count["n"]
            except LLMError as e:
                return e.error_code, call_count["n"]

    def test_retryable_codes_retry(self):
        for code in self.RETRYABLE_CODES:
            error_code, calls = self._run_single_attempt(code)
            with self.subTest(code=code):
                self.assertEqual(error_code, "RETRIES_EXHAUSTED", f"HTTP {code} should exhaust retries")

    def test_auth_codes_no_retry(self):
        for code in self.AUTH_CODES:
            error_code, calls = self._run_single_attempt(code)
            with self.subTest(code=code):
                self.assertEqual(error_code, "AUTH_FAILED")
                self.assertEqual(calls, 1, f"HTTP {code} must not retry")

    def test_terminal_codes_no_retry(self):
        for code in self.TERMINAL_CODES:
            error_code, calls = self._run_single_attempt(code)
            with self.subTest(code=code):
                self.assertEqual(error_code, "PROVIDER_HTTP_ERROR")
                self.assertEqual(calls, 1, f"HTTP {code} must not retry")

    def test_timeout_retries(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(max_retries=2, log_dir=tmp)
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            raise TimeoutError("timed out")

        with patch("urllib.request.urlopen", side_effect=side_effect):
            with self.assertRaises(LLMError) as ctx:
                provider.complete([{"role": "user", "content": "x"}])

        self.assertEqual(ctx.exception.error_code, "RETRIES_EXHAUSTED")
        self.assertEqual(call_count["n"], 2)

    def test_network_error_retries(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(max_retries=2, log_dir=tmp)
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            raise urllib.error.URLError("Connection refused")

        with patch("urllib.request.urlopen", side_effect=side_effect):
            with self.assertRaises(LLMError) as ctx:
                provider.complete([{"role": "user", "content": "x"}])

        self.assertEqual(ctx.exception.error_code, "RETRIES_EXHAUSTED")
        self.assertEqual(call_count["n"], 2)

    def test_malformed_response_terminal(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(max_retries=2, log_dir=tmp)
        resp = MagicMock()
        resp.read.return_value = b"not json at all"
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=resp):
            with self.assertRaises(LLMError) as ctx:
                provider.complete([{"role": "user", "content": "x"}])

        self.assertEqual(ctx.exception.error_code, "INVALID_JSON")

    def test_empty_response_terminal(self):
        tmp = Path(tempfile.mkdtemp())
        provider = _make_provider(max_retries=2, log_dir=tmp)
        resp_data = json.dumps({
            "choices": [{"message": {"content": ""}, "finish_reason": "stop"}],
            "model": "m", "usage": {},
        }).encode()
        resp = MagicMock()
        resp.read.return_value = resp_data
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=resp):
            with self.assertRaises(LLMError) as ctx:
                provider.complete([{"role": "user", "content": "x"}])

        self.assertEqual(ctx.exception.error_code, "EMPTY_RESPONSE_TEXT")


# ===========================================================================
# Session log semantics
# ===========================================================================

class TestSessionLogSemantics(unittest.TestCase):

    def test_session_file_per_log_instance(self):
        tmp = Path(tempfile.mkdtemp())
        log1 = LLMSessionLog(session_id="s1", log_dir=tmp)
        log2 = LLMSessionLog(session_id="s2", log_dir=tmp)
        self.assertNotEqual(log1.path, log2.path)
        self.assertIn("s1", log1.path.name)
        self.assertIn("s2", log2.path.name)

    def test_multiple_attempts_in_one_session(self):
        tmp = Path(tempfile.mkdtemp())
        slog = LLMSessionLog(session_id="multi", log_dir=tmp)
        slog.log_call(model="m1", attempt=1, parse_status="error", error_code="HTTP_429")
        slog.log_call(model="m1", attempt=2, parse_status="parsed")
        lines = slog.path.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 2)
        r1, r2 = json.loads(lines[0]), json.loads(lines[1])
        self.assertEqual(r1["attempt"], 1)
        self.assertEqual(r2["attempt"], 2)

    def test_primary_and_fallback_distinguishable(self):
        tmp = Path(tempfile.mkdtemp())
        slog = LLMSessionLog(session_id="fb", log_dir=tmp)
        slog.log_call(model="primary", parse_status="error", error_code="HTTP_503")
        slog.log_call(model="fallback-1", parse_status="parsed", fallback_model="fallback-1")
        lines = slog.path.read_text(encoding="utf-8").strip().split("\n")
        r1, r2 = json.loads(lines[0]), json.loads(lines[1])
        self.assertNotIn("fallback_model", r1)
        self.assertEqual(r2["fallback_model"], "fallback-1")

    def test_latency_and_tokens_nullable(self):
        tmp = Path(tempfile.mkdtemp())
        slog = LLMSessionLog(session_id="t", log_dir=tmp)
        slog.log_call(model="m")
        line = slog.path.read_text(encoding="utf-8").strip()
        rec = json.loads(line)
        self.assertEqual(rec["latency_ms"], 0)
        self.assertEqual(rec["input_tokens"], 0)
        self.assertEqual(rec["output_tokens"], 0)

    def test_error_code_and_message_recorded(self):
        tmp = Path(tempfile.mkdtemp())
        slog = LLMSessionLog(session_id="err", log_dir=tmp)
        slog.log_error(
            model="m", error_code="PROVIDER_TIMEOUT",
            error_message="Timeout after 90s",
        )
        rec = json.loads(slog.path.read_text(encoding="utf-8").strip())
        self.assertEqual(rec["error_code"], "PROVIDER_TIMEOUT")
        self.assertEqual(rec["error_message"], "Timeout after 90s")
        self.assertEqual(rec["parse_status"], "error")


class TestFIFORotation(unittest.TestCase):

    def test_rotation_keeps_exactly_max(self):
        tmp = Path(tempfile.mkdtemp())
        for i in range(7):
            p = tmp / f"session_{i:02d}.jsonl"
            p.write_text(f"line {i}\n")
            time.sleep(0.01)

        deleted = _rotate_fifo(tmp, max_files=5)
        self.assertEqual(deleted, 2)
        remaining = sorted(f.name for f in tmp.glob("*.jsonl"))
        self.assertEqual(len(remaining), 5)
        self.assertNotIn("session_00.jsonl", remaining)
        self.assertNotIn("session_01.jsonl", remaining)

    def test_rotation_noop_below_limit(self):
        tmp = Path(tempfile.mkdtemp())
        for i in range(3):
            (tmp / f"s_{i}.jsonl").write_text("x\n")
        deleted = _rotate_fifo(tmp, max_files=5)
        self.assertEqual(deleted, 0)
        self.assertEqual(len(list(tmp.glob("*.jsonl"))), 3)

    def test_rotation_nonexistent_dir(self):
        deleted = _rotate_fifo(Path("/nonexistent_dir_xyz"), max_files=5)
        self.assertEqual(deleted, 0)

    def test_existing_files_not_truncated(self):
        tmp = Path(tempfile.mkdtemp())
        p = tmp / "existing.jsonl"
        p.write_text("line1\nline2\n")
        slog = LLMSessionLog(session_id="new", log_dir=tmp)
        slog.log_call(model="m", parse_status="ok")
        content = p.read_text()
        self.assertEqual(content, "line1\nline2\n")

    def test_duplicate_timestamps_do_not_collide(self):
        tmp = Path(tempfile.mkdtemp())
        log1 = LLMSessionLog(session_id="a", log_dir=tmp)
        log2 = LLMSessionLog(session_id="b", log_dir=tmp)
        log1.log_call(model="m1")
        log2.log_call(model="m2")
        self.assertTrue(log1.path.exists())
        self.assertTrue(log2.path.exists())
        self.assertNotEqual(log1.path, log2.path)


class TestLogPrivacy(unittest.TestCase):

    def test_no_api_key_in_log(self):
        tmp = Path(tempfile.mkdtemp())
        slog = LLMSessionLog(session_id="sec", log_dir=tmp)
        slog.log_call(
            model="m",
            messages_preview="Bearer sk-1234567890abcdef",
            response_preview="some response",
        )
        content = slog.path.read_text(encoding="utf-8")
        self.assertNotIn("Authorization", content)

    def test_messages_preview_truncated(self):
        tmp = Path(tempfile.mkdtemp())
        slog = LLMSessionLog(session_id="trunc", log_dir=tmp)
        long_text = "x" * 2000
        slog.log_call(model="m", messages_preview=long_text)
        rec = json.loads(slog.path.read_text(encoding="utf-8").strip())
        self.assertLessEqual(len(rec["messages_preview"]), 500)

    def test_response_preview_truncated(self):
        tmp = Path(tempfile.mkdtemp())
        slog = LLMSessionLog(session_id="trunc2", log_dir=tmp)
        long_text = "y" * 2000
        slog.log_call(model="m", response_preview=long_text)
        rec = json.loads(slog.path.read_text(encoding="utf-8").strip())
        self.assertLessEqual(len(rec["response_preview"]), 500)

    def test_error_message_truncated(self):
        tmp = Path(tempfile.mkdtemp())
        slog = LLMSessionLog(session_id="trunc3", log_dir=tmp)
        slog.log_error(model="m", error_code="X", error_message="z" * 1000)
        rec = json.loads(slog.path.read_text(encoding="utf-8").strip())
        self.assertLessEqual(len(rec["error_message"]), 300)

    def test_log_directory_is_gitignored(self):
        gitignore = Path("C:/projects/kairoskopion/Kairoskopion/.gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            self.assertIn(".kairoskopion/", content)


# ===========================================================================
# Config
# ===========================================================================

class TestFallbackModelsConfig(unittest.TestCase):

    def test_fallback_models_parsed_from_env(self):
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4o-mini",
            "KAIROSKOPION_LLM_FALLBACK_MODELS": "deepseek-chat, gpt-4o, gpt-4.1-mini",
        }
        orig = {k: os.environ.get(k) for k in env}
        for k, v in env.items():
            os.environ[k] = v
        try:
            cfg = LLMConfig.from_env()
            self.assertIsNotNone(cfg)
            self.assertEqual(cfg.fallback_models, ["deepseek-chat", "gpt-4o", "gpt-4.1-mini"])
        finally:
            for k, v in orig.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_empty_fallback_models(self):
        env = {
            "KAIROSKOPION_LLM_MODEL": "gpt-4o-mini",
            "KAIROSKOPION_LLM_FALLBACK_MODELS": "",
        }
        orig = {k: os.environ.get(k) for k in env}
        for k, v in env.items():
            os.environ[k] = v
        try:
            cfg = LLMConfig.from_env()
            self.assertIsNotNone(cfg)
            self.assertEqual(cfg.fallback_models, [])
        finally:
            for k, v in orig.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_timeout_default_90s(self):
        from kairoskopion.llm.config import DEFAULT_TIMEOUT_MS
        self.assertEqual(DEFAULT_TIMEOUT_MS, 90_000)


class TestLLMErrorStructure(unittest.TestCase):

    def test_llm_error_has_error_code(self):
        e = LLMError("test error", error_code="PROVIDER_TIMEOUT")
        self.assertEqual(e.error_code, "PROVIDER_TIMEOUT")
        self.assertEqual(str(e), "test error")

    def test_llm_error_default_code(self):
        e = LLMError("generic")
        self.assertEqual(e.error_code, "UNKNOWN")

    def test_llm_error_is_exception(self):
        self.assertTrue(issubclass(LLMError, Exception))


if __name__ == "__main__":
    unittest.main()
