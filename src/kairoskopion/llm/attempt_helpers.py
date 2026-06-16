"""Shared helpers for LLM attempt metadata.

Used by `services/human_readable_card.py` (and any other surface that
renders or aggregates `extraction_attempt` payloads) to avoid
re-implementing the same parse / format logic per layer.

Sanitized: never returns raw LLM output, raw provider errors, or
stack traces. Every public function returns Russian-language strings
suitable for direct rendering to non-technical authors, plus compact
ASCII technical hints suitable for cockpit badges.

The metadata shape is `LLMAttemptMetadata.to_dict()` — a plain dict
that survives CaseStore JSONL persistence. All helpers tolerate
None / empty dict gracefully and return safe defaults.
"""

from __future__ import annotations

from typing import Any

from .attempt_metadata import (
    FALLBACK_REASON_NOT_APPLICABLE,
    user_warning_for,
)


def is_fallback_attempt(attempt: dict[str, Any] | None) -> bool:
    """True iff the attempt represents a fallback (LLM failed, or never
    attempted but with fallback metadata stamped)."""
    if not attempt:
        return False
    return bool(attempt.get("fallback_used"))


def parse_status(attempt: dict[str, Any] | None) -> str:
    """Return the parse_status, defaulting to 'not_attempted' on None."""
    if not attempt:
        return "not_attempted"
    return str(attempt.get("parse_status") or "not_attempted")


def fallback_reason(attempt: dict[str, Any] | None) -> str:
    """Return the fallback_reason, defaulting to 'not_applicable'."""
    if not attempt:
        return FALLBACK_REASON_NOT_APPLICABLE
    return str(attempt.get("fallback_reason") or FALLBACK_REASON_NOT_APPLICABLE)


def warning_text(attempt: dict[str, Any] | None) -> str | None:
    """Pull a user-facing Russian warning out of the attempt.

    Priority: explicit `warning_for_user` field (set by the agent) →
    derived from `fallback_reason` via the canonical dictionary →
    None if no fallback occurred.
    """
    if not is_fallback_attempt(attempt):
        return None
    explicit = (attempt or {}).get("warning_for_user")
    if explicit:
        return str(explicit)
    return user_warning_for(fallback_reason(attempt))


def technical_hint(attempt: dict[str, Any] | None) -> str:
    """Compact, ASCII, no-leakage hint suitable for cockpit badges.

    Always safe to render. Example outputs:
      "parsed_ok"
      "repaired_ok"
      "fallback (provider_error)"
      "fallback (schema_validation_failed)"
      "not_attempted"
    """
    if not attempt:
        return "not_attempted"
    ps = parse_status(attempt)
    if is_fallback_attempt(attempt):
        return f"fallback ({fallback_reason(attempt)})"
    return ps


_LAYER_LABEL_RU = {
    "article_model": "Модель статьи",
    "semantic_profile": "Семантический профиль",
    "pathways": "Дисциплинарная карта",
    "fit_assessment": "Оценка соответствия",
}


def layer_label(layer: str) -> str:
    """Russian-language label for a layer key, used in aggregated warnings."""
    return _LAYER_LABEL_RU.get(layer, layer)


def aggregate_warnings(layers: dict[str, dict[str, Any] | None]) -> str | None:
    """Combine fallback warnings from multiple analysis layers into a single
    markdown block.

    Args:
      layers: ordered mapping of layer-key → attempt-dict (e.g.
        {'article_model': am.extraction_attempt, 'pathways': ...,
         'semantic_profile': ..., 'fit_assessment': ...}).

    Returns:
      A markdown blockquote string ready to drop into the human view,
      or None if no layer used a fallback.

    Format:
      > ⚠ **Несколько слоёв анализа построены в предварительном режиме:**
      >
      > - **Модель статьи** — <warning>
      >   _(parse_status: `…` · fallback_reason: `…`)_
      > - **Дисциплинарная карта** — <warning>
      >   _(parse_status: `…` · fallback_reason: `…`)_

    If only ONE layer has fallback, the format is the single-line shape
    we already used per-layer, so existing tests for one-layer rendering
    keep working.
    """
    failing = [
        (key, attempt)
        for key, attempt in layers.items()
        if is_fallback_attempt(attempt)
    ]
    if not failing:
        return None

    if len(failing) == 1:
        key, attempt = failing[0]
        warn = warning_text(attempt) or ""
        return (
            f"> ⚠ **{layer_label(key)}: {warn}**\n\n"
            f"> _(parse_status: `{parse_status(attempt)}` · "
            f"fallback_reason: `{fallback_reason(attempt)}`)_\n"
        )

    lines = [
        "> ⚠ **Несколько слоёв анализа построены в предварительном режиме.**",
        ">",
    ]
    for key, attempt in failing:
        warn = warning_text(attempt) or ""
        lines.append(f"> - **{layer_label(key)}** — {warn}")
        lines.append(
            f">   _(parse_status: `{parse_status(attempt)}` · "
            f"fallback_reason: `{fallback_reason(attempt)}`)_"
        )
    return "\n".join(lines) + "\n"
