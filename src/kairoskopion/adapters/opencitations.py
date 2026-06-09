"""OpenCitations adapter stub with deterministic mock data.

No real API calls. Returns fixed mock citation relationship records.
All results are marked is_mock=True.
"""

from __future__ import annotations

import dataclasses as dc
from typing import Any

from ..enums import AdapterStatus, EvidenceStatus
from .base import AdapterConfig, AdapterResult, _DictMixin, _field

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
