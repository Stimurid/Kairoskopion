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
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from .config import LLMConfig
from .response import LLMResponse

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

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        response_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        temp = temperature if temperature is not None else self._config.temperature
        tokens = max_tokens if max_tokens is not None else self._config.max_tokens

        body: dict[str, Any] = {
            "model": self._config.model,
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

        payload = json.dumps(body).encode("utf-8")
        last_error: Exception | None = None
        last_code: str = "UNKNOWN"

        for attempt in range(self._config.max_retries):
            if attempt > 0:
                backoff = min(2 ** attempt, 30)
                logger.info("LLM retry %d after %ds", attempt + 1, backoff)
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
                    raise LLMError(
                        f"LLM returned invalid JSON: {raw_bytes[:200]}",
                        error_code="INVALID_JSON",
                    ) from je

                choices = raw.get("choices") or []
                if not choices:
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

                return LLMResponse(
                    content=content,
                    parsed=parsed,
                    model=raw.get("model"),
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    latency_ms=latency,
                    finish_reason=choice.get("finish_reason"),
                )

            except LLMError:
                raise
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code in (429, 500, 502, 503, 529):
                    last_code = "PROVIDER_HTTP_ERROR"
                    logger.warning("LLM HTTP %d on attempt %d", e.code, attempt + 1)
                    continue
                raise LLMError(
                    f"LLM HTTP {e.code}: {e.reason}",
                    error_code="PROVIDER_HTTP_ERROR",
                ) from e
            except urllib.error.URLError as e:
                last_error = e
                last_code = "NETWORK_ERROR"
                logger.warning("LLM network error on attempt %d: %s", attempt + 1, e)
                continue
            except (TimeoutError, OSError) as e:
                last_error = e
                last_code = "PROVIDER_TIMEOUT"
                logger.warning("LLM timeout on attempt %d", attempt + 1)
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
