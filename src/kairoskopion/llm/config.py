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

    @classmethod
    def for_role(cls, role_id: str | None = None) -> "LLMConfig | None":
        """Return a per-role-overridden LLMConfig or fall through to global.

        Per-role override env var pattern:
            KAIROSKOPION_LLM_MODEL_<ROLE_UPPER>
        where ``<ROLE_UPPER>`` is the agent ``role_id`` uppercased with
        hyphens replaced by underscores (e.g. ``input_classifier`` →
        ``KAIROSKOPION_LLM_MODEL_INPUT_CLASSIFIER``).

        Only the *model* alias can be overridden per-role. All other
        provider params (base_url, api_key_env, timeout, retries) come
        from the global config. Per-call tuning of those belongs to
        Agentum, not Kairoskopion.

        ``role_id=None`` or unknown role → returns the unchanged global
        config. Missing override env var → returns the unchanged global
        config. Empty override value → returns the unchanged global
        config (treats blank as "use default").
        """
        base = cls.from_env()
        if base is None or not role_id:
            return base
        env_name = (
            f"KAIROSKOPION_LLM_MODEL_{role_id.upper().replace('-', '_')}"
        )
        override = os.environ.get(env_name, "").strip()
        if not override or override == base.model:
            return base
        return dc.replace(base, model=override)

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
    # Per-call routing seam (Track C): resolve known role overrides.
    # Each role_id matches an existing agent registry entry; the env var
    # name is documented in docs/operations/PER_CALL_MODEL_ROUTING_SPEC.md.
    # We only expose the *model* per role — never the key, base_url, or
    # timeout (those remain global).
    routed_roles = (
        "input_classifier",
        "article_modeler",
        "article_semantic_profiler",
        "discipline_matcher",
        "disciplinary_pathway_mapper",
        "fit_assessor",
        "mismatch_narrator",
        "venue_profiler",
        "article_field_positioner",
        "venue_field_positioner",
        "venue_discovery",
        "discipline_source_acquisition",
        "discipline_seeder",
    )
    per_role_models: dict[str, str] = {}
    overridden_roles: list[str] = []
    for role in routed_roles:
        rcfg = LLMConfig.for_role(role)
        if rcfg is None:
            continue
        per_role_models[role] = rcfg.model
        if rcfg.model != cfg.model:
            overridden_roles.append(role)
    return {
        "available": bool(cfg.model and cfg.base_url),
        "provider": cfg.provider,
        "model": cfg.model,
        "base_url": cfg.base_url,
        "has_api_key": has_key,
        "timeout_seconds": cfg.timeout_seconds,
        "max_retries": cfg.max_retries,
        "model_default": cfg.model,
        "model_per_role": per_role_models,
        "overridden_roles": overridden_roles,
    }
