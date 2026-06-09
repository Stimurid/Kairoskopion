"""OpenAlex adapter: mock mode (deterministic) and real mode (HTTP API).

Mock mode: returns fixed records, no network calls, is_mock=True.
Real mode: calls api.openalex.org with caching and rate limiting.
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path

from ..enums import AdapterStatus, EvidenceStatus
from .base import AdapterConfig, AdapterRecord, AdapterResult
from .http_client import HttpError, fetch_json

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


# ---------------------------------------------------------------------------
# Real mode
# ---------------------------------------------------------------------------

_OPENALEX_BASE = "https://api.openalex.org"


def _parse_openalex_work(item: dict) -> AdapterRecord:
    """Parse an OpenAlex work object into an AdapterRecord."""
    title = item.get("title")
    authors = []
    for authorship in item.get("authorships", []):
        author = authorship.get("author", {})
        name = author.get("display_name")
        if name:
            authors.append(name)
    year = item.get("publication_year")
    doi = item.get("doi")
    if doi and doi.startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]
    venue = None
    primary_loc = item.get("primary_location") or {}
    source = primary_loc.get("source") or {}
    venue = source.get("display_name")
    oa = item.get("open_access", {})
    return AdapterRecord(
        record_id=item.get("id", "unknown"),
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        venue_name=venue,
        source_kind=item.get("type", "unknown"),
        abstract_snippet=None,
        citation_count=item.get("cited_by_count"),
        is_open_access=oa.get("is_oa"),
        raw_data=item,
    )


def search_works(
    query: str,
    *,
    config: AdapterConfig | None = None,
    max_results: int = 10,
    cache_dir: Path | None = None,
    email: str | None = None,
) -> AdapterResult:
    """Search OpenAlex works API (real mode).

    Makes a real HTTP call. Results are cached locally.
    Providing email enables the polite pool (faster rate limits).
    """
    params: dict[str, str | int] = {
        "search": query,
        "per_page": min(max_results, 50),
    }
    if email:
        params["mailto"] = email
    url = f"{_OPENALEX_BASE}/works?{urllib.parse.urlencode(params)}"
    try:
        data = fetch_json(url, cache_dir=cache_dir)
    except HttpError as exc:
        return AdapterResult(
            adapter_name="openalex",
            query=query,
            status=AdapterStatus.ERROR.value,
            records=[],
            errors=[{"code": str(exc.status), "message": str(exc)}],
            evidence_status=EvidenceStatus.UNKNOWN.value,
            is_mock=False,
            total_available=0,
        )

    results = data.get("results", [])
    total = data.get("meta", {}).get("count", len(results))
    records = [_parse_openalex_work(it).to_dict() for it in results]
    return AdapterResult(
        adapter_name="openalex",
        query=query,
        status=AdapterStatus.SUCCESS.value,
        records=records,
        evidence_status=EvidenceStatus.VENDOR_CLAIM.value,
        is_mock=False,
        total_available=total,
        disclaimer="Retrieved from OpenAlex API. Citation counts are approximate.",
    )


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
