"""Real Source Acquisition service.

Orchestrates multiple venue adapters, collects results with authority
assessments, detects cross-adapter evidence conflicts, and produces
a unified acquisition result.

No broad crawling. Adapters are offline by default. Live mode is opt-in.
"""

from __future__ import annotations

import dataclasses as dc
from datetime import datetime, timezone
from typing import Any

from ..adapters.venue.base import (
    SourceAcquisitionConfig,
    VenueAdapterMode,
    VenueAdapterResult,
    VenueAdapterStatus,
)
from ..adapters.venue.crossref import CrossrefVenueAdapter
from ..adapters.venue.doaj import DOAJVenueAdapter
from ..adapters.venue.openalex import OpenAlexVenueAdapter
from ..adapters.venue.opencitations import OpenCitationsVenueAdapter
from ..adapters.venue.snapshot_crawler import VenueSnapshotCrawler
from ..adapters.venue.unpaywall import UnpaywallAdapter
from ..enums import SourceAccessMode
from ..services.source_authority import (
    assess_source_authority,
    detect_conflicts,
)
from ..source_authority import (
    EvidenceConflict,
    SourceAuthorityClaim,
    SourceAuthorityAssessment,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ALL_ADAPTER_IDS = [
    "openalex_venue",
    "crossref_venue",
    "doaj_venue",
    "unpaywall",
    "opencitations_venue",
    "venue_snapshot_crawler",
]


@dc.dataclass
class AcquisitionResult:
    """Result of running all enabled adapters for a venue/article."""

    venue_name: str | None = None
    venue_issn: str | None = None
    venue_url: str | None = None
    article_doi: str | None = None
    adapter_results: list[dict[str, Any]] = dc.field(default_factory=list)
    authority_assessments: list[dict[str, Any]] = dc.field(default_factory=list)
    evidence_conflicts: list[dict[str, Any]] = dc.field(default_factory=list)
    all_claims: list[dict[str, Any]] = dc.field(default_factory=list)
    unknowns: list[str] = dc.field(default_factory=list)
    degradation_notes: list[str] = dc.field(default_factory=list)
    acquired_at: str = dc.field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return dc.asdict(self)

    @property
    def successful_adapters(self) -> int:
        return sum(
            1 for r in self.adapter_results
            if r.get("status") not in ("error", "unavailable")
        )

    @property
    def failed_adapters(self) -> int:
        return sum(
            1 for r in self.adapter_results
            if r.get("status") in ("error", "unavailable")
        )


def _build_adapter(
    adapter_id: str,
    mode: VenueAdapterMode,
    config: SourceAcquisitionConfig,
    vault: Any | None = None,
) -> Any:
    """Create adapter instance with appropriate mode and config."""
    cfg = config.adapter_config(adapter_id)
    cache_dir = cfg.cache_dir or config.vault_root
    timeout = cfg.timeout or config.default_timeout

    if adapter_id == "openalex_venue":
        return OpenAlexVenueAdapter(mode, cache_dir=cache_dir, timeout=timeout)
    elif adapter_id == "crossref_venue":
        return CrossrefVenueAdapter(mode, cache_dir=cache_dir, timeout=timeout)
    elif adapter_id == "doaj_venue":
        return DOAJVenueAdapter(mode, cache_dir=cache_dir, timeout=timeout)
    elif adapter_id == "unpaywall":
        return UnpaywallAdapter(mode, cache_dir=cache_dir, timeout=timeout)
    elif adapter_id == "opencitations_venue":
        return OpenCitationsVenueAdapter(mode, cache_dir=cache_dir, timeout=timeout)
    elif adapter_id == "venue_snapshot_crawler":
        return VenueSnapshotCrawler(mode, vault=vault, timeout=timeout)
    return None


def acquire_venue_sources(
    *,
    venue_name: str | None = None,
    venue_issn: str | None = None,
    venue_url: str | None = None,
    article_doi: str | None = None,
    config: SourceAcquisitionConfig | None = None,
    vault: Any | None = None,
    adapter_fixtures: dict[str, dict] | None = None,
    enabled_adapters: list[str] | None = None,
) -> AcquisitionResult:
    """Run enabled adapters and collect results with authority assessments.

    Default mode is offline_stub (no network). Live mode requires explicit
    config.live_enabled=True and per-adapter configuration.
    """
    config = config or SourceAcquisitionConfig()
    fixtures = adapter_fixtures or {}

    adapter_ids = enabled_adapters or [
        "openalex_venue", "crossref_venue", "doaj_venue",
        "opencitations_venue", "venue_snapshot_crawler",
    ]
    if article_doi and "unpaywall" not in adapter_ids:
        adapter_ids.append("unpaywall")

    adapter_results: list[VenueAdapterResult] = []
    authority_assessments: list[SourceAuthorityAssessment] = []
    all_claims_raw: list[dict[str, Any]] = []
    unknowns: list[str] = []
    degradation: list[str] = []

    for adapter_id in adapter_ids:
        cfg = config.adapter_config(adapter_id)
        if not cfg.enabled:
            degradation.append(f"{adapter_id}: disabled")
            continue

        effective_mode = config.effective_mode(adapter_id)

        # Use fixture if provided
        if adapter_id in fixtures:
            effective_mode = VenueAdapterMode.FIXTURE

        adapter = _build_adapter(adapter_id, effective_mode, config, vault)
        if adapter is None:
            degradation.append(f"{adapter_id}: unknown adapter")
            continue

        try:
            if adapter_id in fixtures:
                result = adapter.parse_response(fixtures[adapter_id])
            elif adapter_id == "unpaywall" and article_doi:
                result = adapter.lookup_by_doi(article_doi)
            else:
                result = adapter.lookup_venue(
                    name=venue_name, issn=venue_issn, url=venue_url,
                )
        except Exception as exc:
            result = VenueAdapterResult(
                adapter_id=adapter_id,
                mode=effective_mode.value,
                query={"name": venue_name, "issn": venue_issn},
                status=VenueAdapterStatus.ERROR.value,
                error=f"exception: {type(exc).__name__}: {exc}",
                unknowns=[f"{adapter_id}: unexpected error"],
                provenance=adapter_id,
            )

        adapter_results.append(result)

        # Collect authority assessment
        if result.authority_assessment:
            assessment = SourceAuthorityAssessment.from_dict(result.authority_assessment)
            authority_assessments.append(assessment)

        # Collect claims
        for claim in result.claims:
            all_claims_raw.append({
                "adapter_id": adapter_id,
                "source_access_mode": result.source_access_mode,
                **claim.to_dict(),
            })

        unknowns.extend(result.unknowns)

        if not result.is_available:
            degradation.append(f"{adapter_id}: {result.error or result.status}")

    # Detect cross-adapter conflicts
    conflicts = _detect_cross_adapter_conflicts(adapter_results)

    return AcquisitionResult(
        venue_name=venue_name,
        venue_issn=venue_issn,
        venue_url=venue_url,
        article_doi=article_doi,
        adapter_results=[r.to_dict() for r in adapter_results],
        authority_assessments=[a.to_dict() for a in authority_assessments],
        evidence_conflicts=[c.to_dict() for c in conflicts],
        all_claims=all_claims_raw,
        unknowns=unknowns,
        degradation_notes=degradation,
    )


def _detect_cross_adapter_conflicts(
    results: list[VenueAdapterResult],
) -> list[EvidenceConflict]:
    """Detect conflicts where different adapters disagree on the same field."""
    conflicts: list[EvidenceConflict] = []

    # Group claims by claim_path across adapters
    claims_by_path: dict[str, list[SourceAuthorityClaim]] = {}
    for result in results:
        if not result.is_available:
            continue
        for claim in result.claims:
            path = claim.claim_path
            sa_claim = SourceAuthorityClaim(
                source_ref=result.adapter_id,
                access_mode=result.source_access_mode,
                claim_key=path,
                claim_value=claim.claim_value,
                authority_strength=_confidence_to_strength(claim.confidence),
            )
            claims_by_path.setdefault(path, []).append(sa_claim)

    # Check each path for conflicts
    for path, claims in claims_by_path.items():
        if len(claims) < 2:
            continue
        conflict = detect_conflicts(
            entity_id="venue",
            field_name=path,
            claims=claims,
        )
        if conflict is not None:
            conflicts.append(conflict)

    return conflicts


def _confidence_to_strength(confidence: str) -> str:
    from ..enums import AuthorityStrength
    mapping = {
        "high": AuthorityStrength.AUTHORITATIVE.value,
        "medium": AuthorityStrength.SUPPORTED.value,
        "low": AuthorityStrength.WEAK.value,
    }
    return mapping.get(confidence, AuthorityStrength.WEAK.value)


def list_available_adapters() -> list[dict[str, str]]:
    """List all known adapter IDs with their source access modes."""
    return [
        {"adapter_id": "openalex_venue", "source_access_mode": SourceAccessMode.METADATA_API.value, "description": "OpenAlex venue/source metadata"},
        {"adapter_id": "crossref_venue", "source_access_mode": SourceAccessMode.METADATA_API.value, "description": "Crossref journal metadata"},
        {"adapter_id": "doaj_venue", "source_access_mode": SourceAccessMode.INDEX_REGISTRY.value, "description": "DOAJ journal inclusion and OA metadata"},
        {"adapter_id": "unpaywall", "source_access_mode": SourceAccessMode.METADATA_API.value, "description": "Unpaywall article OA access by DOI"},
        {"adapter_id": "opencitations_venue", "source_access_mode": SourceAccessMode.CITATION_GRAPH.value, "description": "OpenCitations citation ecology"},
        {"adapter_id": "venue_snapshot_crawler", "source_access_mode": SourceAccessMode.OFFICIAL_WEBPAGE.value, "description": "Official webpage snapshot (explicit URL only)"},
    ]


def inspect_adapter(adapter_id: str) -> dict[str, Any] | None:
    """Return details about a specific adapter."""
    for info in list_available_adapters():
        if info["adapter_id"] == adapter_id:
            return info
    return None
