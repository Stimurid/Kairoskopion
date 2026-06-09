"""Crossref adapter: mock mode (deterministic) and real mode (HTTP API).

Mock mode: returns fixed records, no network calls, is_mock=True.
Real mode: calls api.crossref.org with caching and rate limiting.
All real results are marked is_mock=False, evidence_status=VENDOR_CLAIM.
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path

from ..enums import AdapterStatus, EvidenceStatus
from .base import AdapterConfig, AdapterRecord, AdapterResult
from .http_client import HttpError, fetch_json

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


# ---------------------------------------------------------------------------
# Real mode
# ---------------------------------------------------------------------------

_CROSSREF_BASE = "https://api.crossref.org"


def _parse_crossref_work(item: dict) -> AdapterRecord:
    """Parse a Crossref works API item into an AdapterRecord."""
    title_parts = item.get("title", [])
    title = title_parts[0] if title_parts else None
    authors = []
    for a in item.get("author", []):
        name = f"{a.get('given', '')} {a.get('family', '')}".strip()
        if name:
            authors.append(name)
    year = None
    for date_field in ("published-print", "published-online", "created"):
        dp = item.get(date_field, {}).get("date-parts", [[]])
        if dp and dp[0] and dp[0][0]:
            year = dp[0][0]
            break
    venue = None
    containers = item.get("container-title", [])
    if containers:
        venue = containers[0]
    return AdapterRecord(
        record_id=f"cr_{item.get('DOI', 'unknown')[:30]}",
        title=title,
        authors=authors,
        year=year,
        doi=item.get("DOI"),
        venue_name=venue,
        source_kind=item.get("type", "unknown"),
        citation_count=item.get("is-referenced-by-count"),
        is_open_access=None,
        raw_data=item,
    )


def lookup_doi(
    doi: str,
    *,
    config: AdapterConfig | None = None,
    cache_dir: Path | None = None,
) -> AdapterResult:
    """Look up DOI metadata via the Crossref API (real mode).

    Makes a real HTTP call to api.crossref.org. Results are cached locally.
    """
    url = f"{_CROSSREF_BASE}/works/{urllib.parse.quote(doi, safe='')}"
    try:
        data = fetch_json(url, cache_dir=cache_dir)
    except HttpError as exc:
        if exc.status == 404:
            return AdapterResult(
                adapter_name="crossref",
                query=f"doi:{doi}",
                status=AdapterStatus.NO_RESULTS.value,
                records=[],
                evidence_status=EvidenceStatus.UNKNOWN.value,
                is_mock=False,
                total_available=0,
                warnings=[f"DOI not found: {doi}"],
            )
        return AdapterResult(
            adapter_name="crossref",
            query=f"doi:{doi}",
            status=AdapterStatus.ERROR.value,
            records=[],
            errors=[{"code": str(exc.status), "message": str(exc)}],
            evidence_status=EvidenceStatus.UNKNOWN.value,
            is_mock=False,
            total_available=0,
        )

    item = data.get("message", {})
    record = _parse_crossref_work(item)
    return AdapterResult(
        adapter_name="crossref",
        query=f"doi:{doi}",
        status=AdapterStatus.SUCCESS.value,
        records=[record.to_dict()],
        evidence_status=EvidenceStatus.VENDOR_CLAIM.value,
        is_mock=False,
        total_available=1,
        disclaimer="Retrieved from Crossref API. Metadata is publisher-supplied.",
    )


def search_works(
    query: str,
    *,
    config: AdapterConfig | None = None,
    max_results: int = 10,
    cache_dir: Path | None = None,
) -> AdapterResult:
    """Search Crossref works API (real mode).

    Makes a real HTTP call. Results are cached locally.
    """
    params = urllib.parse.urlencode({
        "query": query,
        "rows": min(max_results, 50),
    })
    url = f"{_CROSSREF_BASE}/works?{params}"
    try:
        data = fetch_json(url, cache_dir=cache_dir)
    except HttpError as exc:
        return AdapterResult(
            adapter_name="crossref",
            query=query,
            status=AdapterStatus.ERROR.value,
            records=[],
            errors=[{"code": str(exc.status), "message": str(exc)}],
            evidence_status=EvidenceStatus.UNKNOWN.value,
            is_mock=False,
            total_available=0,
        )

    items = data.get("message", {}).get("items", [])
    total = data.get("message", {}).get("total-results", len(items))
    records = [_parse_crossref_work(it).to_dict() for it in items]
    return AdapterResult(
        adapter_name="crossref",
        query=query,
        status=AdapterStatus.SUCCESS.value,
        records=records,
        evidence_status=EvidenceStatus.VENDOR_CLAIM.value,
        is_mock=False,
        total_available=total,
        disclaimer="Retrieved from Crossref API. Metadata is publisher-supplied.",
    )


def lookup_doi_auto(
    doi: str,
    *,
    mode: str = "mock",
    config: AdapterConfig | None = None,
    cache_dir: Path | None = None,
) -> AdapterResult:
    """Dispatch to mock or real DOI lookup based on mode."""
    if mode == "real":
        return lookup_doi(doi, config=config, cache_dir=cache_dir)
    return lookup_doi_mock(doi, config=config)


def search_works_auto(
    query: str,
    *,
    mode: str = "mock",
    config: AdapterConfig | None = None,
    max_results: int = 10,
    cache_dir: Path | None = None,
) -> AdapterResult:
    """Dispatch to mock or real search based on mode."""
    if mode == "real":
        return search_works(query, config=config, max_results=max_results,
                            cache_dir=cache_dir)
    return search_works_mock(query, config=config, max_results=max_results)
