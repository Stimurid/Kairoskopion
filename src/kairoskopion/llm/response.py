"""LLM response container."""

from __future__ import annotations

import dataclasses as dc
from typing import Any


@dc.dataclass
class LLMResponse:
    content: str
    parsed: dict[str, Any] | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str | None = None
