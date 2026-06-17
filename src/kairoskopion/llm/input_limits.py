"""Input-size guards for LLM-fed text.

Why these exist
---------------
The synchronous intake endpoint chains 3–4 LLM calls in one HTTP request.
A very long manuscript pasted into the cockpit (e.g. 90k+ characters of
Russian = ~25k tokens) makes each call slow enough that any reverse
proxy in front of uvicorn (nginx default 60s, Cloudflare 100s, etc.)
returns a bare 504 with no body, and the UI shows ``API 504:`` with
nothing useful.

LLM provider parameters (temperature / max_tokens / timeout / retry /
model-per-call-site) belong to the sibling Agentum project — we do not
tune them here. What we *can* do is cap how much raw text gets injected
into the LLM prompt before the call is made. The full original text is
still kept on the Case for deterministic processing and persistence.

Two thresholds:

* ``LLM_INPUT_CHAR_CAP`` — text fed into an LLM prompt is truncated to
  this many characters. Picked to keep a single round-trip well under
  typical proxy windows even on slower providers.
* ``INTAKE_HARD_CHAR_CAP`` — request bodies above this size are rejected
  outright with HTTP 413. Picked to forbid accidental dumps (whole
  books, scraped HTML) that would slow even the deterministic path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# Tunable by env later if needed, but for now hardcoded — these are
# input-shaping guards, not LLM parameters. Sized empirically for the
# current ManuscriptVenueFitPipeline and 302.ai default models.
LLM_INPUT_CHAR_CAP: Final[int] = 150_000
INTAKE_HARD_CHAR_CAP: Final[int] = 400_000

TRUNCATION_MARKER: Final[str] = (
    "\n\n[... текст обрезан для отправки в LLM "
    "(см. метаданные input_truncated_for_llm) ...]"
)


@dataclass(frozen=True)
class TruncationInfo:
    """Result of a truncation pass — safe to surface in API responses."""

    original_chars: int
    used_chars: int
    cap: int

    @property
    def truncated(self) -> bool:
        return self.used_chars < self.original_chars

    def to_dict(self) -> dict[str, int | bool]:
        return {
            "original_chars": self.original_chars,
            "used_chars": self.used_chars,
            "cap": self.cap,
            "truncated": self.truncated,
        }


def cap_llm_input(text: str, cap: int = LLM_INPUT_CHAR_CAP) -> tuple[str, TruncationInfo]:
    """Return (text_for_llm, info). If text fits, returned unchanged.

    The truncation marker is appended so the model knows the prompt was
    clipped. The marker itself does not leak any raw payload.
    """
    if text is None:
        return "", TruncationInfo(0, 0, cap)
    original = len(text)
    if original <= cap:
        return text, TruncationInfo(original, original, cap)
    head = text[:cap].rstrip()
    return head + TRUNCATION_MARKER, TruncationInfo(original, len(head), cap)
