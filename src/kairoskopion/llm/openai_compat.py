"""OpenAI-compatible LLM provider.

Works with OpenAI, Anthropic (via proxy), Azure OpenAI, local servers
(Ollama, vLLM, llama.cpp), 302.ai — anything exposing /v1/chat/completions.

Error taxonomy aligned with litops:
- PROVIDER_HTTP_ERROR — non-200 status (non-retryable)
- PROVIDER_TIMEOUT — request exceeded timeout
- NETWORK_ERROR — connection/DNS failure
- INVALID_JSON — response body not valid JSON
- EMPTY_RESPONSE_TEXT — empty content from API
- RETRIES_EXHAUSTED — all retry attempts failed
- AUTH_FAILED — 401/403, API key invalid or expired
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from .attempt_metadata import LLMModelAttempt
from .config import LLMConfig
from .response import LLMResponse
from .session_log import get_session_log

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when LLM call fails after retries."""

    def __init__(self, message: str, *, error_code: str = "UNKNOWN") -> None:
        super().__init__(message)
        self.error_code = error_code


class OpenAICompatProvider:
    """LLM provider using the OpenAI chat completions API."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config

    @property
    def model(self) -> str:
        return self._config.model

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        response_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        agent_role: str = "",
    ) -> LLMResponse:
        models_to_try = [self._config.model] + list(self._config.fallback_models)
        last_error: LLMError | None = None
        all_attempts: list[LLMModelAttempt] = []
        attempt_counter = 0
        requested_model = self._config.model

        for model_idx, model_name in enumerate(models_to_try):
            is_fallback = model_idx > 0
            if is_fallback:
                logger.info(
                    "Falling back to model %s (attempt %d/%d)",
                    model_name, model_idx + 1, len(models_to_try),
                )
            try:
                result = self._complete_single(
                    messages,
                    model=model_name,
                    response_schema=response_schema,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    agent_role=agent_role,
                    is_fallback=is_fallback,
                    attempt_collector=all_attempts,
                    attempt_offset=attempt_counter,
                )
                result.requested_model = requested_model
                result.effective_model = model_name
                result.fallback_used = is_fallback
                result.attempt_count = len(all_attempts)
                result.attempts = list(all_attempts)
                result.agent_role = agent_role
                return result
            except LLMError as e:
                last_error = e
                attempt_counter = len(all_attempts)
                slog = get_session_log()
                slog.log_error(
                    agent_role=agent_role,
                    model=model_name,
                    error_code=e.error_code,
                    error_message=str(e),
                )
                if e.error_code == "AUTH_FAILED":
                    e.attempts = list(all_attempts)  # type: ignore[attr-defined]
                    raise
                if model_idx < len(models_to_try) - 1:
                    logger.warning(
                        "Model %s failed (%s), trying next fallback",
                        model_name, e.error_code,
                    )
                    continue
                e.attempts = list(all_attempts)  # type: ignore[attr-defined]
                raise

        err = last_error or LLMError("No models available", error_code="NO_MODELS")
        err.attempts = list(all_attempts)  # type: ignore[attr-defined]
        raise err

    def _complete_single(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        response_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        agent_role: str = "",
        is_fallback: bool = False,
        attempt_collector: list[LLMModelAttempt] | None = None,
        attempt_offset: int = 0,
    ) -> LLMResponse:
        temp = temperature if temperature is not None else self._config.temperature
        tokens = max_tokens if max_tokens is not None else self._config.max_tokens

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens,
        }
        if response_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.get("title", "output"),
                    "strict": True,
                    "schema": response_schema,
                },
            }

        url = self._config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        api_key = self._config.api_key
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        last_error: Exception | None = None
        last_code: str = "UNKNOWN"

        msg_preview = ""
        if messages:
            last_msg = messages[-1].get("content", "")
            msg_preview = last_msg[:200]

        slog = get_session_log()

        def _record_attempt(
            error_code: str, latency: float, retryable: bool,
            transition: str, provider_status: str = "error",
            response_status: str = "", parse_status: str = "",
        ) -> None:
            rec = LLMModelAttempt(
                attempt_index=attempt_offset + len(attempt_collector) if attempt_collector is not None else 0,
                model=model,
                agent_role=agent_role,
                latency_ms=latency,
                provider_status=provider_status,
                response_status=response_status,
                parse_status=parse_status,
                error_code=error_code,
                retryable=retryable,
                transition=transition,
            )
            if attempt_collector is not None:
                attempt_collector.append(rec)

        for attempt in range(self._config.max_retries):
            if attempt > 0:
                backoff = min(2 ** attempt, 30)
                logger.info("LLM retry %d after %ds (model=%s)", attempt + 1, backoff, model)
                time.sleep(backoff)

            t0 = time.monotonic()
            try:
                req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
                    raw_bytes = resp.read().decode("utf-8")
                latency = (time.monotonic() - t0) * 1000

                try:
                    raw = json.loads(raw_bytes)
                except json.JSONDecodeError as je:
                    _record_attempt("INVALID_JSON", latency, False, "terminal")
                    slog.log_error(
                        agent_role=agent_role, model=model,
                        error_code="INVALID_JSON",
                        error_message=f"Response not JSON: {raw_bytes[:200]}",
                        attempt=attempt + 1, latency_ms=latency,
                    )
                    raise LLMError(
                        f"LLM returned invalid JSON: {raw_bytes[:200]}",
                        error_code="INVALID_JSON",
                    ) from je

                choices = raw.get("choices") or []
                if not choices:
                    _record_attempt("MALFORMED_RESPONSE", latency, False, "terminal")
                    slog.log_error(
                        agent_role=agent_role, model=model,
                        error_code="MALFORMED_RESPONSE",
                        error_message=f"No choices in response: {raw_bytes[:200]}",
                        attempt=attempt + 1, latency_ms=latency,
                    )
                    raise LLMError(
                        f"LLM response has no choices: {raw_bytes[:200]}",
                        error_code="MALFORMED_RESPONSE",
                    )
                choice = choices[0]
                message = choice.get("message") or {}
                content = message.get("content") or ""
                reasoning = message.get("reasoning_content") or ""
                usage = raw.get("usage", {})

                if not content and not reasoning:
                    _record_attempt("EMPTY_RESPONSE_TEXT", latency, False, "terminal")
                    slog.log_error(
                        agent_role=agent_role, model=model,
                        error_code="EMPTY_RESPONSE_TEXT",
                        error_message="LLM returned empty content",
                        attempt=attempt + 1, latency_ms=latency,
                    )
                    raise LLMError(
                        "LLM returned empty response",
                        error_code="EMPTY_RESPONSE_TEXT",
                    )

                parsed = None
                if response_schema is not None and content:
                    parsed = _parse_json_robust(content)
                    if parsed is None:
                        logger.warning(
                            "LLM returned non-JSON despite schema request "
                            "(preview=%r)", content[:120]
                        )

                _record_attempt(
                    "", latency, False, "success",
                    provider_status="ok", response_status="200",
                    parse_status="parsed" if parsed else "text_only",
                )

                llm_response = LLMResponse(
                    content=content,
                    parsed=parsed,
                    model=raw.get("model"),
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    latency_ms=latency,
                    finish_reason=choice.get("finish_reason"),
                )

                slog.log_call(
                    agent_role=agent_role,
                    model=raw.get("model") or model,
                    messages_preview=msg_preview,
                    response_preview=content[:500],
                    latency_ms=latency,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    parse_status="parsed" if parsed else "text_only",
                    fallback_model=model if is_fallback else "",
                    attempt=attempt + 1,
                )

                return llm_response

            except LLMError:
                raise
            except urllib.error.HTTPError as e:
                latency = (time.monotonic() - t0) * 1000
                last_error = e

                if e.code in (401, 403):
                    error_msg = f"API key invalid or expired (HTTP {e.code})"
                    _record_attempt("AUTH_FAILED", latency, False, "terminal",
                                    response_status=str(e.code))
                    slog.log_error(
                        agent_role=agent_role, model=model,
                        error_code="AUTH_FAILED",
                        error_message=error_msg,
                        attempt=attempt + 1, latency_ms=latency,
                    )
                    raise LLMError(error_msg, error_code="AUTH_FAILED") from e

                if e.code in (408, 429, 500, 502, 503, 504, 529):
                    last_code = "PROVIDER_HTTP_ERROR"
                    transition = "retry" if attempt < self._config.max_retries - 1 else "exhausted"
                    _record_attempt(f"HTTP_{e.code}", latency, True, transition,
                                    response_status=str(e.code))
                    logger.warning("LLM HTTP %d on attempt %d (model=%s)", e.code, attempt + 1, model)
                    slog.log_error(
                        agent_role=agent_role, model=model,
                        error_code=f"HTTP_{e.code}",
                        error_message=f"HTTP {e.code}: {e.reason}",
                        attempt=attempt + 1, latency_ms=latency,
                    )
                    continue

                _record_attempt(f"HTTP_{e.code}", latency, False, "terminal",
                                response_status=str(e.code))
                slog.log_error(
                    agent_role=agent_role, model=model,
                    error_code=f"HTTP_{e.code}",
                    error_message=f"HTTP {e.code}: {e.reason}",
                    attempt=attempt + 1, latency_ms=latency,
                )
                raise LLMError(
                    f"LLM HTTP {e.code}: {e.reason}",
                    error_code="PROVIDER_HTTP_ERROR",
                ) from e

            except urllib.error.URLError as e:
                latency = (time.monotonic() - t0) * 1000
                last_error = e
                last_code = "NETWORK_ERROR"
                transition = "retry" if attempt < self._config.max_retries - 1 else "exhausted"
                _record_attempt("NETWORK_ERROR", latency, True, transition)
                logger.warning("LLM network error on attempt %d (model=%s): %s", attempt + 1, model, e)
                slog.log_error(
                    agent_role=agent_role, model=model,
                    error_code="NETWORK_ERROR",
                    error_message=str(e)[:200],
                    attempt=attempt + 1, latency_ms=latency,
                )
                continue

            except (TimeoutError, OSError) as e:
                latency = (time.monotonic() - t0) * 1000
                last_error = e
                last_code = "PROVIDER_TIMEOUT"
                transition = "retry" if attempt < self._config.max_retries - 1 else "exhausted"
                _record_attempt("PROVIDER_TIMEOUT", latency, True, transition)
                logger.warning("LLM timeout on attempt %d (model=%s, timeout=%.0fs)", attempt + 1, model, self._config.timeout_seconds)
                slog.log_error(
                    agent_role=agent_role, model=model,
                    error_code="PROVIDER_TIMEOUT",
                    error_message=f"Timeout after {self._config.timeout_seconds:.0f}s",
                    attempt=attempt + 1, latency_ms=latency,
                )
                continue

        raise LLMError(
            f"LLM failed after {self._config.max_retries} attempts: {last_error}",
            error_code="RETRIES_EXHAUSTED",
        )


def _parse_json_robust(text: str) -> Any | None:
    """Parse JSON from a model response, tolerating common wrappers.

    Handles: plain JSON, ```json ... ``` fences, ``` ... ``` fences,
    leading/trailing prose. Falls back to extracting the first balanced
    {...} block when nothing else works.
    """
    s = (text or "").strip()
    if not s:
        return None

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl != -1:
            inner = s[first_nl + 1:]
            if inner.rstrip().endswith("```"):
                inner = inner.rstrip()[:-3]
            try:
                return json.loads(inner.strip())
            except json.JSONDecodeError:
                pass

    lo = s.find("{")
    hi = s.rfind("}")
    if lo != -1 and hi != -1 and hi > lo:
        candidate = s[lo:hi + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None
