"""OpenAlex adapter stub with deterministic mock data.

No real API calls. Returns fixed mock records for testing the adapter
contract and evidence bridge. All results are marked is_mock=True.
"""

from __future__ import annotations

from ..enums import AdapterStatus, EvidenceStatus
from .base import AdapterConfig, AdapterRecord, AdapterResult

_MOCK_CONFIG = AdapterConfig(
    adapter_name="openalex",
    base_url="https://api.openalex.org",
    is_mock=True,
)

_MOCK_WORKS = [
    AdapterRecord(
        record_id="W2741809807",
        title="The Hard Problem of Consciousness",
        authors=["David Chalmers"],
        year=1995,
        doi="10.1093/acprof:oso/9780195117899.001.0001",
        venue_name="Journal of Consciousness Studies",
        source_kind="journal_article",
        abstract_snippet="Why is it that physical processes give rise to experience?",
        citation_count=4200,
        is_open_access=False,
        raw_data={"openalex_id": "W2741809807", "type": "journal-article"},
    ),
    AdapterRecord(
        record_id="W1234567890",
        title="Consciousness and Complexity",
        authors=["Giulio Tononi", "Christof Koch"],
        year=2015,
        doi="10.1126/science.1234567",
        venue_name="Science",
        source_kind="journal_article",
        abstract_snippet="Integrated information theory proposes that consciousness corresponds to...",
        citation_count=890,
        is_open_access=True,
        raw_data={"openalex_id": "W1234567890", "type": "journal-article"},
    ),
    AdapterRecord(
        record_id="W9876543210",
        title="What Is It Like to Be a Bat?",
        authors=["Thomas Nagel"],
        year=1974,
        doi="10.2307/2183914",
        venue_name="The Philosophical Review",
        source_kind="journal_article",
        abstract_snippet="Consciousness is what makes the mind-body problem really intractable.",
        citation_count=7500,
        is_open_access=False,
        raw_data={"openalex_id": "W9876543210", "type": "journal-article"},
    ),
]


def search_works_mock(
    query: str,
    *,
    config: AdapterConfig | None = None,
    max_results: int = 10,
) -> AdapterResult:
    """Return deterministic mock OpenAlex work records.

    No network calls. Always returns the same 3 mock records regardless
    of query, with is_mock=True and evidence_status=VENDOR_CLAIM.
    """
    cfg = config or _MOCK_CONFIG
    records = [r.to_dict() for r in _MOCK_WORKS[:max_results]]
    return AdapterResult(
        adapter_name="openalex",
        query=query,
        status=AdapterStatus.MOCK.value,
        records=records,
        evidence_status=EvidenceStatus.VENDOR_CLAIM.value,
        is_mock=True,
        total_available=len(records),
        warnings=["Mock data — not retrieved from OpenAlex API"],
        unknowns=[
            "Real citation counts unknown (mock values)",
            "Open access status unverified (mock values)",
        ],
        disclaimer="Mock OpenAlex adapter. No real API call was made.",
    )
