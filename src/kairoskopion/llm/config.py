"""LLM provider configuration.

Aligned with litops/quint pattern:
- KAIROSKOPION_LLM_* env vars (primary)
- LLM_* env vars (fallback, shared with litops)
- Default: 302.ai / gpt-4.1-mini (same as quint)
- Provider mode: "openai_compatible" or "none"
"""

from __future__ import annotations

import dataclasses as dc
import os


def _env(primary: str, fallback: str, default: str = "") -> str:
    return os.environ.get(primary) or os.environ.get(fallback) or default


DEFAULT_BASE_URL = "https://api.302.ai/v1"
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_RETRIES = 3


MODEL_PRESETS = [
    {
        "label": "302.ai / GPT-4.1 mini",
        "base_url": "https://api.302.ai/v1",
        "model": "gpt-4.1-mini",
    },
    {
        "label": "302.ai / DeepSeek Chat",
        "base_url": "https://api.302.ai/v1",
        "model": "deepseek-chat",
    },
    {
        "label": "302.ai / GPT-4o mini",
        "base_url": "https://api.302.ai/v1",
        "model": "gpt-4o-mini",
    },
    {
        "label": "OpenAI / GPT-4o",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
    },
    {
        "label": "OpenAI / GPT-4o mini",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
]


@dc.dataclass
class LLMConfig:
    """LLM provider configuration.

    Reads from env vars with two-level fallback:
      KAIROSKOPION_LLM_MODEL → LLM_MODEL → default
    """

    provider: str = "openai_compatible"
    model: str = ""
    base_url: str = ""
    api_key_env: str = "KAIROSKOPION_LLM_API_KEY"
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout_seconds: float = DEFAULT_TIMEOUT_MS / 1000
    max_retries: int = DEFAULT_MAX_RETRIES

    @classmethod
    def from_env(cls) -> LLMConfig | None:
        """Build config from env vars; returns None if provider is 'none' or model not set."""
        provider = _env("KAIROSKOPION_LLM_PROVIDER", "LLM_PROVIDER", "openai_compatible")
        if provider == "none":
            return None

        model = _env("KAIROSKOPION_LLM_MODEL", "LLM_MODEL", "")
        if not model:
            return None

        base_url = _env("KAIROSKOPION_LLM_BASE_URL", "LLM_BASE_URL", DEFAULT_BASE_URL)
        api_key_env = _env(
            "KAIROSKOPION_LLM_API_KEY_ENV", "LLM_API_KEY_ENV", "KAIROSKOPION_LLM_API_KEY",
        )
        timeout_ms_str = _env("KAIROSKOPION_LLM_TIMEOUT_MS", "LLM_TIMEOUT_MS", "")
        timeout_s = (
            int(timeout_ms_str) / 1000
            if timeout_ms_str.isdigit()
            else DEFAULT_TIMEOUT_MS / 1000
        )

        return cls(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            timeout_seconds=timeout_s,
        )

    @property
    def api_key(self) -> str:
        """Read API key from the env var named by api_key_env.

        Falls back to LLM_API_KEY if primary is empty.
        """
        val = os.environ.get(self.api_key_env, "")
        if not val and self.api_key_env != "LLM_API_KEY":
            val = os.environ.get("LLM_API_KEY", "")
        return val


def is_llm_available() -> bool:
    """Check whether LLM is configured and usable (no network call)."""
    cfg = LLMConfig.from_env()
    if cfg is None:
        return False
    return bool(cfg.model and cfg.base_url)


def provider_status() -> dict:
    """Diagnostic dict for CLI/status commands. No secrets leaked."""
    cfg = LLMConfig.from_env()
    if cfg is None:
        return {
            "available": False,
            "provider": "none",
            "reason": "LLM not configured (set KAIROSKOPION_LLM_MODEL or LLM_MODEL)",
        }
    has_key = bool(cfg.api_key)
    return {
        "available": bool(cfg.model and cfg.base_url),
        "provider": cfg.provider,
        "model": cfg.model,
        "base_url": cfg.base_url,
        "has_api_key": has_key,
        "timeout_seconds": cfg.timeout_seconds,
        "max_retries": cfg.max_retries,
    }
