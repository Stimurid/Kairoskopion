"""Crossref adapter stub with deterministic mock data.

No real API calls. Returns fixed mock records for DOI metadata lookup.
All results are marked is_mock=True.
"""

from __future__ import annotations

from ..enums import AdapterStatus, EvidenceStatus
from .base import AdapterConfig, AdapterRecord, AdapterResult

_MOCK_CONFIG = AdapterConfig(
    adapter_name="crossref",
    base_url="https://api.crossref.org",
    is_mock=True,
)

_MOCK_DOI_RECORDS = {
    "10.1093/acprof:oso/9780195117899.001.0001": AdapterRecord(
        record_id="cr_001",
        title="The Conscious Mind: In Search of a Fundamental Theory",
        authors=["David J. Chalmers"],
        year=1996,
        doi="10.1093/acprof:oso/9780195117899.001.0001",
        venue_name="Oxford University Press",
        source_kind="book",
        citation_count=None,
        raw_data={"type": "book", "publisher": "Oxford University Press"},
    ),
    "10.2307/2183914": AdapterRecord(
        record_id="cr_002",
        title="What Is It Like to Be a Bat?",
        authors=["Thomas Nagel"],
        year=1974,
        doi="10.2307/2183914",
        venue_name="The Philosophical Review",
        source_kind="journal_article",
        citation_count=None,
        raw_data={"type": "journal-article", "publisher": "Duke University Press"},
    ),
}

_MOCK_SEARCH_RECORDS = [
    AdapterRecord(
        record_id="cr_s01",
        title="Facing Up to the Problem of Consciousness",
        authors=["David J. Chalmers"],
        year=1995,
        doi="10.1093/mind/fzaa009",
        venue_name="Journal of Consciousness Studies",
        source_kind="journal_article",
        raw_data={"type": "journal-article"},
    ),
    AdapterRecord(
        record_id="cr_s02",
        title="The Explanatory Gap",
        authors=["Joseph Levine"],
        year=1983,
        doi="10.1111/j.1468-0114.1983.tb00207.x",
        venue_name="Pacific Philosophical Quarterly",
        source_kind="journal_article",
        raw_data={"type": "journal-article"},
    ),
]


def lookup_doi_mock(
    doi: str,
    *,
    config: AdapterConfig | None = None,
) -> AdapterResult:
    """Return deterministic mock Crossref metadata for a DOI.

    No network calls. Returns a match if the DOI is in the mock set,
    otherwise returns no_results status.
    """
    record = _MOCK_DOI_RECORDS.get(doi)
    if record:
        return AdapterResult(
            adapter_name="crossref",
            query=f"doi:{doi}",
            status=AdapterStatus.MOCK.value,
            records=[record.to_dict()],
            evidence_status=EvidenceStatus.VENDOR_CLAIM.value,
            is_mock=True,
            total_available=1,
            warnings=["Mock data — not retrieved from Crossref API"],
            disclaimer="Mock Crossref adapter. No real API call was made.",
        )
    return AdapterResult(
        adapter_name="crossref",
        query=f"doi:{doi}",
        status=AdapterStatus.NO_RESULTS.value,
        records=[],
        evidence_status=EvidenceStatus.UNKNOWN.value,
        is_mock=True,
        total_available=0,
        warnings=["Mock data — DOI not in mock set"],
        unknowns=[f"DOI {doi} not found in mock data; real lookup required"],
        disclaimer="Mock Crossref adapter. No real API call was made.",
    )


def search_works_mock(
    query: str,
    *,
    config: AdapterConfig | None = None,
    max_results: int = 10,
) -> AdapterResult:
    """Return deterministic mock Crossref search results.

    No network calls. Always returns the same 2 mock records.
    """
    records = [r.to_dict() for r in _MOCK_SEARCH_RECORDS[:max_results]]
    return AdapterResult(
        adapter_name="crossref",
        query=query,
        status=AdapterStatus.MOCK.value,
        records=records,
        evidence_status=EvidenceStatus.VENDOR_CLAIM.value,
        is_mock=True,
        total_available=len(records),
        warnings=["Mock data — not retrieved from Crossref API"],
        unknowns=["Real result count unknown (mock data)"],
        disclaimer="Mock Crossref adapter. No real API call was made.",
    )
