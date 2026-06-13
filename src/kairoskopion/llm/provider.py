"""LLM provider protocol."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .response import LLMResponse


@runtime_checkable
class LLMProvider(Protocol):
    """Abstract interface for LLM backends.

    Any OpenAI-compatible API can back this protocol.
    """

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a chat completion request and return structured response."""
        ...
