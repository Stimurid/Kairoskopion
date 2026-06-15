"""LLM attempt metadata.

Tracks per-agent-call evidence of what happened with the LLM:
whether it was attempted, whether parsing/repair succeeded, why we
fell back if we did. Used by:

  - `agents/article_modeler.py` to annotate the ArticleModel;
  - `agents/disciplinary_pathway_mapper.py` to annotate pathways;
  - `services/human_readable_card.py` to surface a user-facing
    warning when validation failed and fallback was used;
  - API responses to surface a structured `extraction_attempt` payload
    that the cockpit can inspect in technical view.

Sanitized: NO raw LLM output is captured by default. NO API keys. NO
prompt content. Only structural status, latency, model id, and
short error summaries (truncated).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Fallback reason taxonomy (task spec §B).
FALLBACK_REASON_NOT_APPLICABLE = "not_applicable"
FALLBACK_REASON_LLM_UNAVAILABLE = "llm_unavailable"
FALLBACK_REASON_LLM_TIMEOUT = "llm_timeout"
FALLBACK_REASON_INVALID_JSON = "invalid_json"
FALLBACK_REASON_SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
FALLBACK_REASON_REPAIR_FAILED = "repair_failed"
FALLBACK_REASON_PROVIDER_ERROR = "provider_error"
FALLBACK_REASON_UNKNOWN = "unknown"


_USER_WARNINGS = {
    "schema_validation_failed": (
        "LLM-анализ был запущен, но его ответ не прошёл структурную "
        "проверку. Система показывает безопасную предварительную модель "
        "с UNKNOWN-полями. Это не значит, что текст непонятен; это значит, "
        "что произошёл сбой структурирования ответа."
    ),
    "invalid_json": (
        "LLM-анализ был запущен, но вернул нераспознаваемый ответ "
        "(не JSON). Система показывает безопасную предварительную модель "
        "с UNKNOWN-полями."
    ),
    "repair_failed": (
        "LLM-ответ был частично повреждён, и автоматическое восстановление "
        "не помогло. Показана безопасная предварительная модель."
    ),
    "llm_timeout": (
        "LLM не успел ответить за отведённое время. Показана детерминированная "
        "модель — её достаточно, чтобы начать, но она поверхностна."
    ),
    "llm_unavailable": (
        "LLM не настроен или недоступен. Показана детерминированная модель — "
        "поля помечены UNKNOWN там, где нужен LLM."
    ),
    "provider_error": (
        "LLM-провайдер вернул ошибку. Показана детерминированная модель."
    ),
    "unknown": (
        "LLM-извлечение не завершилось успешно. Показана детерминированная "
        "модель — пожалуйста, проверьте поля, отмеченные UNKNOWN."
    ),
}


def user_warning_for(reason: str) -> str | None:
    """Return a Russian-language warning suitable for the human view.

    None when no fallback happened.
    """
    if reason == FALLBACK_REASON_NOT_APPLICABLE or not reason:
        return None
    return _USER_WARNINGS.get(reason, _USER_WARNINGS["unknown"])


@dataclass
class LLMAttemptMetadata:
    """Per-agent-call audit record.

    All fields are JSON-serializable. `raw_output_ref` defaults to None
    and is reserved for an optional debug-only sanitized excerpt (we do
    NOT capture raw content by default).
    """

    llm_attempted: bool = False
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_latency_ms: float | None = None
    llm_raw_output_present: bool = False

    # One of llm.json_repair.PARSE_STATUS_*
    parse_status: str = "not_attempted"

    repair_attempted: bool = False
    # One of: "not_needed", "repaired_ok", "failed", "skipped"
    repair_status: str = "not_needed"
    repair_steps: list[str] = field(default_factory=list)

    # One of FALLBACK_REASON_*
    fallback_used: bool = False
    fallback_reason: str = FALLBACK_REASON_NOT_APPLICABLE

    # Up to ~6 short error strings; truncated for safety.
    validation_errors_summary: list[str] = field(default_factory=list)

    # Russian-language warning shown to the author when fallback fired.
    # None when no fallback.
    warning_for_user: str | None = None

    # Reserved hook for sanitized debug output. None by default.
    raw_output_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "llm_attempted": self.llm_attempted,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_latency_ms": self.llm_latency_ms,
            "llm_raw_output_present": self.llm_raw_output_present,
            "parse_status": self.parse_status,
            "repair_attempted": self.repair_attempted,
            "repair_status": self.repair_status,
            "repair_steps": list(self.repair_steps),
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "validation_errors_summary": [
                e[:240] for e in self.validation_errors_summary[:8]
            ],
            "warning_for_user": self.warning_for_user,
            "raw_output_ref": self.raw_output_ref,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LLMAttemptMetadata":
        return cls(
            llm_attempted=bool(d.get("llm_attempted", False)),
            llm_provider=d.get("llm_provider"),
            llm_model=d.get("llm_model"),
            llm_latency_ms=d.get("llm_latency_ms"),
            llm_raw_output_present=bool(d.get("llm_raw_output_present", False)),
            parse_status=d.get("parse_status", "not_attempted"),
            repair_attempted=bool(d.get("repair_attempted", False)),
            repair_status=d.get("repair_status", "not_needed"),
            repair_steps=list(d.get("repair_steps") or []),
            fallback_used=bool(d.get("fallback_used", False)),
            fallback_reason=d.get(
                "fallback_reason", FALLBACK_REASON_NOT_APPLICABLE
            ),
            validation_errors_summary=list(
                d.get("validation_errors_summary") or []
            ),
            warning_for_user=d.get("warning_for_user"),
            raw_output_ref=d.get("raw_output_ref"),
        )

    @classmethod
    def parse_ok(cls, *, provider, model, latency_ms, content_present, repaired=False, repair_steps=None) -> "LLMAttemptMetadata":
        m = cls(
            llm_attempted=True,
            llm_provider=provider,
            llm_model=model,
            llm_latency_ms=latency_ms,
            llm_raw_output_present=content_present,
            parse_status=("repaired_ok" if repaired else "parsed_ok"),
            repair_attempted=repaired,
            repair_status=("repaired_ok" if repaired else "not_needed"),
            repair_steps=list(repair_steps or []),
            fallback_used=False,
            fallback_reason=FALLBACK_REASON_NOT_APPLICABLE,
            warning_for_user=None,
        )
        return m

    @classmethod
    def fallback(
        cls,
        *,
        reason: str,
        provider: str | None = None,
        model: str | None = None,
        latency_ms: float | None = None,
        content_present: bool = False,
        repair_attempted: bool = False,
        repair_steps: list[str] | None = None,
        validation_errors: list[str] | None = None,
        parse_status: str = "fallback_used",
    ) -> "LLMAttemptMetadata":
        return cls(
            llm_attempted=True,
            llm_provider=provider,
            llm_model=model,
            llm_latency_ms=latency_ms,
            llm_raw_output_present=content_present,
            parse_status=parse_status,
            repair_attempted=repair_attempted,
            repair_status=("failed" if repair_attempted else "not_needed"),
            repair_steps=list(repair_steps or []),
            fallback_used=True,
            fallback_reason=reason,
            validation_errors_summary=list(validation_errors or []),
            warning_for_user=user_warning_for(reason),
        )

    @classmethod
    def not_attempted(cls) -> "LLMAttemptMetadata":
        """When no LLM provider was configured for this call."""
        return cls(
            llm_attempted=False,
            parse_status="not_attempted",
            fallback_used=True,
            fallback_reason=FALLBACK_REASON_LLM_UNAVAILABLE,
            warning_for_user=user_warning_for(FALLBACK_REASON_LLM_UNAVAILABLE),
        )
