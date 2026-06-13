"""Venue adapter base: typed interface for venue evidence adapters."""

from __future__ import annotations

import dataclasses as dc
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class VenueAdapterMode(str, Enum):
    OFFLINE_STUB = "offline_stub"
    FIXTURE = "fixture"
    CACHED = "cached"
    LIVE_API = "live_api"

    # Backward compat alias
    CACHED_SNAPSHOT = "cached_snapshot"


@dc.dataclass
class VenueAdapterConfig:
    """Per-adapter configuration."""

    enabled: bool = True
    mode: str = VenueAdapterMode.OFFLINE_STUB.value
    timeout: int = 30
    retry_count: int = 2
    user_agent: str = (
        "Kairoskopion/0.2 "
        "(https://github.com/Stimurid/Kairoskopion; "
        "mailto:kairoskopion@proton.me)"
    )
    cache_dir: str | None = None
    cache_max_age: int = 86400

    def to_dict(self) -> dict[str, Any]:
        return dc.asdict(self)


@dc.dataclass
class SourceAcquisitionConfig:
    """Global source acquisition configuration."""

    live_enabled: bool = False
    adapters: dict[str, VenueAdapterConfig] = dc.field(default_factory=dict)
    vault_root: str | None = None
    default_timeout: int = 30
    default_retry_count: int = 2
    default_user_agent: str = (
        "Kairoskopion/0.2 "
        "(https://github.com/Stimurid/Kairoskopion; "
        "mailto:kairoskopion@proton.me)"
    )

    def adapter_config(self, adapter_id: str) -> VenueAdapterConfig:
        return self.adapters.get(adapter_id, VenueAdapterConfig())

    def effective_mode(self, adapter_id: str) -> VenueAdapterMode:
        cfg = self.adapter_config(adapter_id)
        if not cfg.enabled:
            return VenueAdapterMode.OFFLINE_STUB
        if not self.live_enabled and cfg.mode == VenueAdapterMode.LIVE_API.value:
            return VenueAdapterMode.OFFLINE_STUB
        return VenueAdapterMode(cfg.mode)

    def to_dict(self) -> dict[str, Any]:
        return {
            "live_enabled": self.live_enabled,
            "adapters": {k: v.to_dict() for k, v in self.adapters.items()},
            "vault_root": self.vault_root,
            "default_timeout": self.default_timeout,
            "default_retry_count": self.default_retry_count,
        }


class VenueAdapterStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    NO_RESULTS = "no_results"
    ERROR = "error"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"


class VenueAdapterError(str, Enum):
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"
    HTTP_ERROR = "http_error"
    RATE_LIMITED = "rate_limited"
    NOT_FOUND = "not_found"
    NETWORK_UNAVAILABLE = "network_unavailable"
    DISABLED = "disabled"
    UNSUPPORTED_MODE = "unsupported_mode"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    status: str = VenueAdapterStatus.SUCCESS.value
    source_access_mode: str = ""
    authority_assessment: dict[str, Any] | None = None
    evidence_status: str = "UNKNOWN"
    source_role: str = ""
    claims: list[VenueAdapterClaim] = dc.field(default_factory=list)
    unsupported_claims: list[str] = dc.field(default_factory=list)
    prohibited_claims: list[str] = dc.field(default_factory=list)
    raw_data: dict[str, Any] | None = None
    vault_ref: str | None = None
    cache_ref: str | None = None
    error: str | None = None
    unknowns: list[str] = dc.field(default_factory=list)
    provenance: str = ""
    fetched_at: str | None = None
    cached_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "mode": self.mode,
            "query": self.query,
            "status": self.status,
            "source_access_mode": self.source_access_mode,
            "authority_assessment": self.authority_assessment,
            "evidence_status": self.evidence_status,
            "source_role": self.source_role,
            "claims": [c.to_dict() for c in self.claims],
            "unsupported_claims": self.unsupported_claims,
            "prohibited_claims": self.prohibited_claims,
            "raw_data": self.raw_data,
            "vault_ref": self.vault_ref,
            "cache_ref": self.cache_ref,
            "error": self.error,
            "unknowns": self.unknowns,
            "provenance": self.provenance,
            "fetched_at": self.fetched_at,
            "cached_at": self.cached_at,
        }

    @property
    def is_available(self) -> bool:
        return self.status not in (
            VenueAdapterStatus.ERROR.value,
            VenueAdapterStatus.UNAVAILABLE.value,
        )


class VenueAdapter(ABC):
    """Base class for venue evidence adapters."""

    adapter_id: str = "base"
    source_role: str = ""
    source_access_mode: str = ""

    def __init__(self, mode: VenueAdapterMode = VenueAdapterMode.OFFLINE_STUB) -> None:
        self._mode = mode

    @property
    def mode(self) -> VenueAdapterMode:
        return self._mode

    @abstractmethod
    def lookup_venue(
        self,
        *,
        name: str | None = None,
        issn: str | None = None,
        url: str | None = None,
    ) -> VenueAdapterResult:
        ...

    def degrade_gracefully(self, query: dict[str, Any], reason: str) -> VenueAdapterResult:
        return VenueAdapterResult(
            adapter_id=self.adapter_id,
            mode=self._mode.value,
            query=query,
            status=VenueAdapterStatus.UNAVAILABLE.value,
            source_access_mode=self.source_access_mode,
            evidence_status="UNKNOWN",
            source_role=self.source_role,
            error=reason,
            unknowns=[f"{self.adapter_id}: {reason}"],
            provenance=self.adapter_id,
        )

    def _attach_authority(self, result: VenueAdapterResult) -> VenueAdapterResult:
        """Attach SourceAuthorityAssessment to result."""
        if not self.source_access_mode:
            return result
        from ...services.source_authority import assess_source_authority
        assessment = assess_source_authority(
            source_ref=self.adapter_id,
            access_modes=[self.source_access_mode],
        )
        result.source_access_mode = self.source_access_mode
        result.authority_assessment = assessment.to_dict()
        result.prohibited_claims = assessment.prohibited_scopes
        result.provenance = self.adapter_id
        return result
