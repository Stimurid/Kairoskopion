"""External source adapter registry (P7.2 Track 6).

Records what tools/connectors Kairoskopion can use for source acquisition.
This is Kairoskopion's self-knowledge about its available data channels,
not Claude manually using tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ExternalAdapterRecord:
    adapter_id: str = ""
    adapter_type: str = "other"
    adapter_name: str = ""
    enabled: bool = False
    cost_class: str = "unknown"
    requires_key: bool = False
    can_fetch_full_text: bool = False
    can_search: bool = False
    can_extract_metadata: bool = True
    allowed_domains: list[str] = field(default_factory=list)
    rate_limit_notes: str | None = None
    legal_notes: str | None = None
    output_packet_type: str = "metadata"

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Built-in adapter definitions (seeded from code/config)
# ---------------------------------------------------------------------------

def _builtin_adapters() -> list[ExternalAdapterRecord]:
    return [
        ExternalAdapterRecord(
            adapter_id="local_file",
            adapter_type="local_file",
            adapter_name="Local File Ingest",
            enabled=True,
            cost_class="free",
            can_fetch_full_text=True,
            can_search=False,
            can_extract_metadata=True,
            output_packet_type="full_text",
        ),
        ExternalAdapterRecord(
            adapter_id="manual_url",
            adapter_type="manual_url",
            adapter_name="Manual URL Reference",
            enabled=True,
            cost_class="free",
            can_search=False,
            output_packet_type="url_reference",
        ),
        ExternalAdapterRecord(
            adapter_id="repo_docs",
            adapter_type="local_file",
            adapter_name="Repository Documents",
            enabled=True,
            cost_class="free",
            can_fetch_full_text=True,
            can_search=True,
            output_packet_type="full_text",
            allowed_domains=["docs/", "benchmarks/", "data/"],
        ),
        ExternalAdapterRecord(
            adapter_id="openalex",
            adapter_type="openalex",
            adapter_name="OpenAlex API",
            enabled=True,
            cost_class="free",
            requires_key=False,
            can_search=True,
            can_extract_metadata=True,
            rate_limit_notes="Polite pool with mailto; 10 req/s",
            output_packet_type="metadata",
        ),
        ExternalAdapterRecord(
            adapter_id="crossref",
            adapter_type="crossref",
            adapter_name="Crossref API",
            enabled=True,
            cost_class="free",
            requires_key=False,
            can_search=True,
            can_extract_metadata=True,
            rate_limit_notes="Polite pool with mailto; 50 req/s",
            output_packet_type="metadata",
        ),
        ExternalAdapterRecord(
            adapter_id="doaj",
            adapter_type="doaj",
            adapter_name="DOAJ API",
            enabled=True,
            cost_class="free",
            requires_key=False,
            can_search=True,
            output_packet_type="metadata",
        ),
        ExternalAdapterRecord(
            adapter_id="unpaywall",
            adapter_type="unpaywall",
            adapter_name="Unpaywall API",
            enabled=True,
            cost_class="free",
            requires_key=False,
            can_fetch_full_text=False,
            can_search=False,
            can_extract_metadata=True,
            output_packet_type="oa_status",
        ),
        ExternalAdapterRecord(
            adapter_id="opencitations",
            adapter_type="opencitations",
            adapter_name="OpenCitations COCI",
            enabled=True,
            cost_class="free",
            requires_key=False,
            can_search=False,
            can_extract_metadata=True,
            output_packet_type="citation_links",
        ),
        ExternalAdapterRecord(
            adapter_id="cyberleninka",
            adapter_type="cyberleninka",
            adapter_name="CyberLeninka Search",
            enabled=True,
            cost_class="free",
            requires_key=False,
            can_search=True,
            can_fetch_full_text=True,
            output_packet_type="article_text",
            allowed_domains=["cyberleninka.ru"],
            legal_notes="Russian journals; article-level search",
        ),
        ExternalAdapterRecord(
            adapter_id="semantic_scholar",
            adapter_type="semantic_scholar",
            adapter_name="Semantic Scholar API",
            enabled=False,
            cost_class="free",
            requires_key=True,
            can_search=True,
            can_extract_metadata=True,
            rate_limit_notes="Free signup; rate limited",
            output_packet_type="metadata",
        ),
        ExternalAdapterRecord(
            adapter_id="sherpa_romeo",
            adapter_type="sherpa",
            adapter_name="Sherpa RoMEO",
            enabled=False,
            cost_class="free",
            requires_key=True,
            can_search=True,
            output_packet_type="oa_policy",
        ),
        ExternalAdapterRecord(
            adapter_id="scopus",
            adapter_type="scopus",
            adapter_name="Scopus API",
            enabled=False,
            cost_class="paid",
            requires_key=True,
            can_search=True,
            can_extract_metadata=True,
            legal_notes="Institutional subscription required",
            output_packet_type="metadata",
        ),
        ExternalAdapterRecord(
            adapter_id="wos",
            adapter_type="wos",
            adapter_name="Web of Science API",
            enabled=False,
            cost_class="paid",
            requires_key=True,
            can_search=True,
            can_extract_metadata=True,
            legal_notes="Institutional subscription required",
            output_packet_type="metadata",
        ),
        ExternalAdapterRecord(
            adapter_id="elibrary_ru",
            adapter_type="elibrary",
            adapter_name="eLibrary.ru / РИНЦ",
            enabled=False,
            cost_class="free",
            requires_key=True,
            can_search=True,
            can_extract_metadata=True,
            legal_notes="Authentication required; no public API",
            output_packet_type="metadata",
        ),
    ]


class ExternalAdapterRegistry:
    """Registry of available external source adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, ExternalAdapterRecord] = {}
        for a in _builtin_adapters():
            self._adapters[a.adapter_id] = a

    def list_all(self) -> list[ExternalAdapterRecord]:
        return list(self._adapters.values())

    def list_enabled(self) -> list[ExternalAdapterRecord]:
        return [a for a in self._adapters.values() if a.enabled]

    def list_free(self) -> list[ExternalAdapterRecord]:
        return [a for a in self._adapters.values() if a.cost_class == "free"]

    def get(self, adapter_id: str) -> ExternalAdapterRecord | None:
        return self._adapters.get(adapter_id)

    def is_available(self, adapter_id: str) -> bool:
        a = self._adapters.get(adapter_id)
        return a is not None and a.enabled

    def can_use_for(self, adapter_id: str, *, require_search: bool = False) -> bool:
        a = self._adapters.get(adapter_id)
        if not a or not a.enabled:
            return False
        if require_search and not a.can_search:
            return False
        return True

    def suggest_for_authority_type(self, authority_type: str) -> list[str]:
        mapping: dict[str, list[str]] = {
            "citation_database": ["openalex", "crossref", "opencitations"],
            "metric_source": ["openalex", "scopus", "wos"],
            "national_journal_registry": [
                "openalex", "doaj", "crossref", "elibrary_ru",
            ],
            "journal_archive_source": ["cyberleninka", "openalex"],
            "author_guidelines_source": ["manual_url"],
            "editorial_board_source": ["manual_url", "openalex"],
            "discipline_classification": ["manual_url", "repo_docs"],
            "scholarly_search": ["openalex", "semantic_scholar"],
        }
        candidates = mapping.get(authority_type, ["manual_url", "local_file"])
        return [c for c in candidates if self.is_available(c)]
