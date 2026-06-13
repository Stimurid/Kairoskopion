"""Web search provider abstraction."""

from __future__ import annotations

import dataclasses as dc
import enum
from abc import ABC, abstractmethod


class SearchDepth(str, enum.Enum):
    NONE = "none"
    LIGHT = "light"
    DEEP = "deep"


@dc.dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = ""


class WebSearchProvider(ABC):
    """ABC for web search backends."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
