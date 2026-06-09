"""Base contracts for external adapters (OpenAlex, Crossref, OpenCitations).

Adapters return deterministic mock data in MVP. Real API calls are not
implemented. All results are explicitly marked is_mock=True and evidence
status is VENDOR_CLAIM (not FACT_FROM_SOURCE) for mock data.
"""

from __future__ import annotations

import dataclasses as dc
from typing import Any

from ..enums import AdapterStatus, EvidenceStatus
from ..ids import adapter_result_id
from ..schema import _DictMixin, _field, _list, _now


@dc.dataclass
class AdapterRecord(_DictMixin):
    record_id: str = ""
    title: str | None = _field()
    authors: list[str] = _list()
    year: int | None = _field()
    doi: str | None = _field()
    venue_name: str | None = _field()
    source_kind: str = "unknown"
    abstract_snippet: str | None = _field()
    citation_count: int | None = _field()
    is_open_access: bool | None = _field()
    raw_data: dict[str, Any] = dc.field(default_factory=dict)


@dc.dataclass
class AdapterError(_DictMixin):
    code: str = ""
    message: str = ""
    recoverable: bool = True


@dc.dataclass
class AdapterConfig(_DictMixin):
    adapter_name: str = ""
    base_url: str | None = _field()
    api_key: str | None = _field()
    timeout_seconds: int = 30
    max_results: int = 10
    is_mock: bool = True


@dc.dataclass
class AdapterResult(_DictMixin):
    adapter_result_id: str = dc.field(default_factory=adapter_result_id)
    adapter_name: str = ""
    query: str = ""
    status: str = AdapterStatus.MOCK.value
    records: list[dict[str, Any]] = _list()
    errors: list[dict[str, Any]] = _list()
    retrieved_at: str = dc.field(default_factory=_now)
    evidence_status: str = EvidenceStatus.VENDOR_CLAIM.value
    is_mock: bool = True
    warnings: list[str] = _list()
    unknowns: list[str] = _list()
    total_available: int | None = _field()
    disclaimer: str = "Mock adapter result. Not retrieved from external API."
