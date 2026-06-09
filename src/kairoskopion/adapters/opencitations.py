"""OpenCitations adapter: mock mode (deterministic) and real mode (HTTP API).

Mock mode: returns fixed records, no network calls, is_mock=True.
Real mode: calls opencitations.net COCI API with caching and rate limiting.
"""

from __future__ import annotations

import dataclasses as dc
import urllib.parse
from pathlib import Path
from typing import Any

from ..enums import AdapterStatus, EvidenceStatus
from .base import AdapterConfig, AdapterResult, _DictMixin, _field
from .http_client import HttpError, fetch_json

_MOCK_CONFIG = AdapterConfig(
    adapter_name="opencitations",
    base_url="https://opencitations.net/index/coci/api/v1",
    is_mock=True,
)


@dc.dataclass
class CitationLink(_DictMixin):
    citing_doi: str = ""
    cited_doi: str = ""
    citing_year: int | None = _field()
    cited_year: int | None = _field()
    journal_sc: bool = False

_MOCK_CITATIONS = [
    CitationLink(
        citing_doi="10.1093/mind/fzaa009",
        cited_doi="10.2307/2183914",
        citing_year=1995,
        cited_year=1974,
        journal_sc=False,
    ),
    CitationLink(
        citing_doi="10.1126/science.1234567",
        cited_doi="10.1093/acprof:oso/9780195117899.001.0001",
        citing_year=2015,
        cited_year=1996,
        journal_sc=False,
    ),
    CitationLink(
        citing_doi="10.1126/science.1234567",
        cited_doi="10.2307/2183914",
        citing_year=2015,
        cited_year=1974,
        journal_sc=False,
    ),
]


def get_citations_mock(
    doi: str,
    *,
    config: AdapterConfig | None = None,
    direction: str = "references",
) -> AdapterResult:
    """Return deterministic mock citation links for a DOI.

    No network calls. Returns citation links where the DOI appears
    as citing (direction='references') or cited (direction='citations').
    """
    if direction == "references":
        links = [c for c in _MOCK_CITATIONS if c.citing_doi == doi]
    else:
        links = [c for c in _MOCK_CITATIONS if c.cited_doi == doi]

    records = [link.to_dict() for link in links]
    status = AdapterStatus.MOCK.value

    return AdapterResult(
        adapter_name="opencitations",
        query=f"{direction}:{doi}",
        status=status,
        records=records,
        evidence_status=EvidenceStatus.VENDOR_CLAIM.value,
        is_mock=True,
        total_available=len(records),
        warnings=["Mock data — not retrieved from OpenCitations API"],
        unknowns=[
            "Real citation network unknown (mock data)",
            "Journal self-citation flags unverified (mock data)",
        ],
        disclaimer="Mock OpenCitations adapter. No real API call was made.",
    )


# ---------------------------------------------------------------------------
# Real mode
# ---------------------------------------------------------------------------

_OPENCITATIONS_BASE = "https://opencitations.net/index/coci/api/v1"


def _parse_citation_item(item: dict) -> dict:
    """Parse an OpenCitations COCI API citation item."""
    return CitationLink(
        citing_doi=item.get("citing", ""),
        cited_doi=item.get("cited", ""),
        citing_year=None,  # COCI doesn't always return years directly
        cited_year=None,
        journal_sc=item.get("journal_sc", "no") == "yes",
    ).to_dict()


def get_citations(
    doi: str,
    *,
    config: AdapterConfig | None = None,
    direction: str = "references",
    cache_dir: Path | None = None,
) -> AdapterResult:
    """Get citation links for a DOI via OpenCitations COCI API (real mode).

    direction='references': what this DOI cites.
    direction='citations': what cites this DOI.
    """
    endpoint = "references" if direction == "references" else "citations"
    url = f"{_OPENCITATIONS_BASE}/{endpoint}/{urllib.parse.quote(doi, safe='')}"
    try:
        data = fetch_json(url, cache_dir=cache_dir)
    except HttpError as exc:
        return AdapterResult(
            adapter_name="opencitations",
            query=f"{direction}:{doi}",
            status=AdapterStatus.ERROR.value,
            records=[],
            errors=[{"code": str(exc.status), "message": str(exc)}],
            evidence_status=EvidenceStatus.UNKNOWN.value,
            is_mock=False,
            total_available=0,
        )

    # COCI returns a list of citation objects
    if not isinstance(data, list):
        data = []
    records = [_parse_citation_item(it) for it in data]
    return AdapterResult(
        adapter_name="opencitations",
        query=f"{direction}:{doi}",
        status=AdapterStatus.SUCCESS.value if records else AdapterStatus.NO_RESULTS.value,
        records=records,
        evidence_status=EvidenceStatus.VENDOR_CLAIM.value,
        is_mock=False,
        total_available=len(records),
        disclaimer="Retrieved from OpenCitations COCI API. Coverage varies by publisher.",
    )


def get_citations_auto(
    doi: str,
    *,
    mode: str = "mock",
    config: AdapterConfig | None = None,
    direction: str = "references",
    cache_dir: Path | None = None,
) -> AdapterResult:
    """Dispatch to mock or real citation lookup based on mode."""
    if mode == "real":
        return get_citations(doi, config=config, direction=direction,
                             cache_dir=cache_dir)
    return get_citations_mock(doi, config=config, direction=direction)
