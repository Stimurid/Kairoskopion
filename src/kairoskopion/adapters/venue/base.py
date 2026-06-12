"""Venue adapter base: typed interface for venue evidence adapters."""

from __future__ import annotations

import dataclasses as dc
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class VenueAdapterMode(str, Enum):
    OFFLINE_STUB = "offline_stub"
    LIVE_API = "live_api"
    CACHED_SNAPSHOT = "cached_snapshot"


@dc.dataclass
class VenueAdapterClaim:
    """A single claim extracted from an adapter response."""

    claim_path: str
    claim_value: Any
    evidence_status: str
    confidence: str = "medium"
    quote_or_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dc.asdict(self)


@dc.dataclass
class VenueAdapterResult:
    """Result from a venue adapter query."""

    adapter_id: str
    mode: str
    query: dict[str, Any] = dc.field(default_factory=dict)
    status: str = "success"  # success | partial | no_results | error | unavailable
    evidence_status: str = "UNKNOWN"
    source_role: str = ""
    claims: list[VenueAdapterClaim] = dc.field(default_factory=list)
    raw_data: dict[str, Any] | None = None
    vault_ref: str | None = None
    error: str | None = None
    unknowns: list[str] = dc.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "mode": self.mode,
            "query": self.query,
            "status": self.status,
            "evidence_status": self.evidence_status,
            "source_role": self.source_role,
            "claims": [c.to_dict() for c in self.claims],
            "raw_data": self.raw_data,
            "vault_ref": self.vault_ref,
            "error": self.error,
            "unknowns": self.unknowns,
        }

    @property
    def is_available(self) -> bool:
        return self.status not in ("error", "unavailable")


class VenueAdapter(ABC):
    """Base class for venue evidence adapters."""

    adapter_id: str = "base"
    source_role: str = ""

    def __init__(self, mode: VenueAdapterMode = VenueAdapterMode.OFFLINE_STUB) -> None:
        self._mode = mode

    @property
    def mode(self) -> VenueAdapterMode:
        return self._mode

    @abstractmethod
    def lookup_venue(self, *, name: str | None = None, issn: str | None = None, url: str | None = None) -> VenueAdapterResult:
        ...

    def degrade_gracefully(self, query: dict[str, Any], reason: str) -> VenueAdapterResult:
        return VenueAdapterResult(
            adapter_id=self.adapter_id,
            mode=self._mode.value,
            query=query,
            status="unavailable",
            evidence_status="UNKNOWN",
            source_role=self.source_role,
            error=reason,
            unknowns=[f"{self.adapter_id}: {reason}"],
        )
