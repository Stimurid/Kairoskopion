"""Venue Evidence Stack service (Phase 5).

Orchestrates depth-driven venue evidence collection:
- selects depth policy from purpose
- runs adapters at appropriate levels
- assembles VenueEvidencePack + VenueDepthCoverage
- reports unknowns and degradation honestly
- passes authority assessments and evidence conflicts through
"""

from __future__ import annotations

from typing import Any

from ..adapters.venue.base import VenueAdapterMode, VenueAdapterResult, VenueAdapterStatus
from ..adapters.venue.crossref import CrossrefVenueAdapter
from ..adapters.venue.doaj import DOAJVenueAdapter
from ..adapters.venue.openalex import OpenAlexVenueAdapter
from ..adapters.venue.opencitations import OpenCitationsVenueAdapter
from ..adapters.venue.snapshot_crawler import VenueSnapshotCrawler
from ..schema import VenueEvidencePack, VenueModel, VenueRecord
from ..source_authority import EvidenceConflict, SourceAuthorityAssessment
from ..venue_depth import (
    DEPTH_LEVEL_ORDER,
    LevelCoverage,
    VenueAnalysisPurpose,
    VenueDepthCoverage,
    VenueDepthPolicy,
    VenueEvidenceDepthLevel,
    depth_level_index,
    get_depth_policy,
    levels_in_range,
)


def _adapter_mode_from_flag(offline: bool) -> VenueAdapterMode:
    return VenueAdapterMode.OFFLINE_STUB if offline else VenueAdapterMode.LIVE_API


def build_venue_evidence_stack(
    *,
    venue_name: str | None = None,
    venue_issn: str | None = None,
    venue_url: str | None = None,
    venue_model: VenueModel | None = None,
    venue_record: VenueRecord | None = None,
    existing_evidence_pack: VenueEvidencePack | None = None,
    purpose: str = VenueAnalysisPurpose.QUICK_LOOK.value,
    offline: bool = True,
    vault: Any | None = None,
    adapter_fixtures: dict[str, dict] | None = None,
    use_source_adapters: bool = False,
) -> VenueEvidenceStackResult:
    """Build venue evidence stack to the depth required by purpose.

    Returns a result with evidence pack, depth coverage, and degradation notes.
    When use_source_adapters=True, DOAJ adapter is added at L5.
    """
    policy = get_depth_policy(purpose)
    mode = _adapter_mode_from_flag(offline)

    # Resolve venue identity from inputs
    effective_name = venue_name
    effective_issn = venue_issn
    effective_url = venue_url

    if venue_model:
        effective_name = effective_name or venue_model.canonical_name
        effective_issn = effective_issn or getattr(venue_model, "issn", None)
        if venue_model.official_urls:
            effective_url = effective_url or venue_model.official_urls[0]

    if venue_record:
        effective_name = effective_name or venue_record.canonical_name
        effective_issn = effective_issn or venue_record.issn
        if venue_record.official_urls:
            effective_url = effective_url or venue_record.official_urls[0]

    venue_id = ""
    if venue_model:
        venue_id = venue_model.venue_model_id
    elif venue_record:
        venue_id = venue_record.venue_record_id
    elif effective_name:
        venue_id = f"pending:{effective_name}"

    # Collect evidence level by level
    level_results: dict[str, list[VenueAdapterResult]] = {}
    level_coverages: dict[str, LevelCoverage] = {}
    all_claims: list[dict[str, Any]] = []
    all_unknowns: list[str] = []
    missing_required: list[str] = []
    unavailable: list[str] = []
    build_log: list[str] = []
    authority_assessments: list[SourceAuthorityAssessment] = []
    evidence_conflicts: list[EvidenceConflict] = []

    target_levels = levels_in_range(policy.min_depth, policy.target_depth)

    for level in target_levels:
        results = _collect_level(
            level, mode, effective_name, effective_issn, effective_url,
            vault, adapter_fixtures, policy,
            use_source_adapters=use_source_adapters,
        )
        level_results[level.value] = results

        sources = sum(1 for r in results if r.is_available)
        claims_count = sum(len(r.claims) for r in results)
        unknowns = []
        for r in results:
            unknowns.extend(r.unknowns)
            for c in r.claims:
                all_claims.append(c.to_dict())

            # Collect authority assessments from adapters
            if r.authority_assessment:
                try:
                    assessment = SourceAuthorityAssessment.from_dict(r.authority_assessment)
                    authority_assessments.append(assessment)
                except Exception:
                    pass

        # Check required source roles for this level
        from ..venue_depth import LEVEL_SOURCE_ROLES
        level_roles = LEVEL_SOURCE_ROLES.get(level, [])
        achieved_roles = {r.source_role for r in results if r.is_available}
        required_for_level = [
            role for role in policy.required_source_roles
            if role in level_roles and role not in achieved_roles
        ]
        for role in required_for_level:
            missing_required.append(f"{level.value}:{role}")

        for r in results:
            if not r.is_available:
                unavailable.append(f"{r.adapter_id}:{r.error or 'unavailable'}")

        status = "fresh" if sources > 0 else "never_run"
        if sources > 0 and unknowns:
            status = "partial"

        confidence = "none"
        if sources >= 2:
            confidence = "medium"
        elif sources == 1:
            confidence = "low"
        if claims_count >= 5 and sources >= 2:
            confidence = "high"

        lc = LevelCoverage(
            level=level,
            status=status,
            source_count=sources,
            claim_count=claims_count,
            unknown_count=len(unknowns),
            evidence_refs=[r.adapter_id for r in results if r.is_available],
            confidence=confidence,
        )
        level_coverages[level.value] = lc
        all_unknowns.extend(unknowns)

        build_log.append(
            f"{level.value}: {sources} sources, {claims_count} claims, "
            f"{len(unknowns)} unknowns, confidence={confidence}"
        )

    # Levels beyond target are marked as never_run
    beyond_target = DEPTH_LEVEL_ORDER[depth_level_index(policy.target_depth) + 1:]
    for level in beyond_target:
        lc = LevelCoverage(level=level, status="never_run")
        level_coverages[level.value] = lc
        if level.value <= policy.max_depth.value:
            all_unknowns.append(f"{level.value}: not collected (beyond target depth for {purpose})")

    # Determine reached depth
    completed = [
        l for l in target_levels
        if level_coverages[l.value].status in ("fresh", "partial")
    ]
    reached = completed[-1] if completed else VenueEvidenceDepthLevel.L0_IDENTITY

    coverage = VenueDepthCoverage(
        venue_id=venue_id,
        purpose=purpose,
        reached_depth=reached,
        completed_levels=completed,
        level_coverage=level_coverages,
        missing_required_sources=missing_required,
        unavailable_sources=unavailable,
        stale_sources=[],
        unknowns=all_unknowns,
    )

    # Build or update evidence pack
    pack = existing_evidence_pack or VenueEvidencePack(venue_record_id=venue_id)
    for claim in all_claims:
        es = claim.get("evidence_status", "UNKNOWN")
        summary = f"{claim.get('claim_path', '?')}={claim.get('claim_value', '?')}"
        if es == "FACT_FROM_SOURCE":
            pack.official_facts.append(summary)
        elif es == "FACT_FROM_API_METADATA":
            pack.external_claims.append(summary)
        elif es == "VENDOR_CLAIM":
            pack.external_claims.append(summary)
        elif es in ("CORPUS_OBSERVATION", "INFERENCE"):
            pack.inferences.append(summary)
    pack.unknowns = list(set(pack.unknowns + all_unknowns))
    pack.build_log.extend(build_log)

    # Detect cross-adapter conflicts for overlapping claims
    _detect_stack_conflicts(level_results, evidence_conflicts)

    return VenueEvidenceStackResult(
        venue_id=venue_id,
        purpose=purpose,
        policy=policy,
        evidence_pack=pack,
        depth_coverage=coverage,
        adapter_results={k: [r.to_dict() for r in v] for k, v in level_results.items()},
        build_log=build_log,
        authority_assessments=authority_assessments,
        evidence_conflicts=evidence_conflicts,
    )


def _detect_stack_conflicts(
    level_results: dict[str, list[VenueAdapterResult]],
    conflicts: list[EvidenceConflict],
) -> None:
    """Detect conflicts across adapters within the stack."""
    from ..services.source_authority import detect_conflicts as _detect
    from ..source_authority import SourceAuthorityClaim
    from ..enums import AuthorityStrength

    claims_by_path: dict[str, list[SourceAuthorityClaim]] = {}
    for level, results in level_results.items():
        for result in results:
            if not result.is_available:
                continue
            for claim in result.claims:
                sa_claim = SourceAuthorityClaim(
                    source_ref=result.adapter_id,
                    access_mode=result.source_access_mode,
                    claim_key=claim.claim_path,
                    claim_value=claim.claim_value,
                    authority_strength=(
                        AuthorityStrength.AUTHORITATIVE.value if claim.confidence == "high"
                        else AuthorityStrength.SUPPORTED.value if claim.confidence == "medium"
                        else AuthorityStrength.WEAK.value
                    ),
                )
                claims_by_path.setdefault(claim.claim_path, []).append(sa_claim)

    for path, claims in claims_by_path.items():
        if len(claims) < 2:
            continue
        conflict = _detect(entity_id="venue", field_name=path, claims=claims)
        if conflict is not None:
            conflicts.append(conflict)


def _collect_level(
    level: VenueEvidenceDepthLevel,
    mode: VenueAdapterMode,
    name: str | None,
    issn: str | None,
    url: str | None,
    vault: Any | None,
    fixtures: dict[str, dict] | None,
    policy: VenueDepthPolicy,
    *,
    use_source_adapters: bool = False,
) -> list[VenueAdapterResult]:
    results: list[VenueAdapterResult] = []
    fixtures = fixtures or {}

    if level == VenueEvidenceDepthLevel.L0_IDENTITY:
        oa = OpenAlexVenueAdapter(mode)
        if "openalex" in fixtures:
            results.append(oa.parse_response(fixtures["openalex"]))
        else:
            results.append(oa.lookup_venue(name=name, issn=issn))

        cr = CrossrefVenueAdapter(mode)
        if "crossref" in fixtures:
            results.append(cr.parse_response(fixtures["crossref"]))
        else:
            results.append(cr.lookup_venue(name=name, issn=issn))

    elif level == VenueEvidenceDepthLevel.L1_OFFICIAL_FORMAL:
        crawler = VenueSnapshotCrawler(mode, vault=vault)
        if "snapshot_html" in fixtures:
            results.append(crawler.store_html(fixtures["snapshot_html"], url=url or "fixture://guidelines"))
        else:
            results.append(crawler.lookup_venue(name=name, url=url))

    elif level == VenueEvidenceDepthLevel.L2_PUBLICATION_MODEL:
        results.append(VenueAdapterResult(
            adapter_id="publication_model_aggregator",
            mode=mode.value,
            query={"name": name, "issn": issn},
            status="partial",
            evidence_status="INFERENCE",
            source_role="openalex_works_metadata",
            unknowns=["L2 publication model requires L0 data aggregation"],
        ))

    elif level == VenueEvidenceDepthLevel.L3_CORPUS_SAMPLE:
        if "corpus" in fixtures:
            results.append(VenueAdapterResult(
                adapter_id="corpus_fixture",
                mode="offline_stub",
                query={"fixture": True},
                status="success",
                evidence_status="CORPUS_OBSERVATION",
                source_role="openalex_works_sample",
                raw_data=fixtures["corpus"],
            ))
        else:
            results.append(VenueAdapterResult(
                adapter_id="corpus_sampler",
                mode=mode.value,
                query={"name": name},
                status="unavailable",
                evidence_status="UNKNOWN",
                source_role="openalex_works_sample",
                error="No corpus fixture provided and live sampling not run",
                unknowns=["L3 corpus sample not available"],
            ))

    elif level == VenueEvidenceDepthLevel.L4_EDITORIAL_INTELLIGENCE:
        results.append(VenueAdapterResult(
            adapter_id="editorial_board_analyzer",
            mode=mode.value,
            query={"name": name},
            status="unavailable",
            evidence_status="UNKNOWN",
            source_role="editorial_board_page",
            error="Editorial board analysis not yet implemented",
            unknowns=["L4 editorial intelligence not available"],
        ))

    elif level == VenueEvidenceDepthLevel.L5_POLICY_AND_INDEXING:
        oc = OpenCitationsVenueAdapter(mode)
        if "opencitations" in fixtures:
            results.append(oc.parse_response(fixtures["opencitations"]))
        else:
            results.append(oc.lookup_venue(issn=issn))

        # Add DOAJ at L5 when source adapters are enabled
        if use_source_adapters:
            doaj = DOAJVenueAdapter(mode)
            if "doaj" in fixtures:
                results.append(doaj.parse_response(fixtures["doaj"]))
            else:
                results.append(doaj.lookup_venue(name=name, issn=issn))

    elif level == VenueEvidenceDepthLevel.L6_EXTERNAL_GRAPH:
        oc = OpenCitationsVenueAdapter(mode)
        if "opencitations" in fixtures:
            results.append(oc.parse_response(fixtures["opencitations"]))
        else:
            results.append(oc.lookup_venue(issn=issn))

    elif level == VenueEvidenceDepthLevel.L7_USER_MEMORY_AND_OUTCOMES:
        results.append(VenueAdapterResult(
            adapter_id="user_memory",
            mode=mode.value,
            query={},
            status="unavailable",
            evidence_status="UNKNOWN",
            source_role="user_submission_outcome",
            error="No user outcome data provided",
            unknowns=["L7 user memory not available"],
        ))

    return results


class VenueEvidenceStackResult:
    """Result of building a venue evidence stack."""

    def __init__(
        self,
        venue_id: str,
        purpose: str,
        policy: VenueDepthPolicy,
        evidence_pack: VenueEvidencePack,
        depth_coverage: VenueDepthCoverage,
        adapter_results: dict[str, list[dict]],
        build_log: list[str],
        authority_assessments: list[SourceAuthorityAssessment] | None = None,
        evidence_conflicts: list[EvidenceConflict] | None = None,
    ) -> None:
        self.venue_id = venue_id
        self.purpose = purpose
        self.policy = policy
        self.evidence_pack = evidence_pack
        self.depth_coverage = depth_coverage
        self.adapter_results = adapter_results
        self.build_log = build_log
        self.authority_assessments = authority_assessments or []
        self.evidence_conflicts = evidence_conflicts or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue_id": self.venue_id,
            "purpose": self.purpose,
            "policy": self.policy.to_dict(),
            "evidence_pack": self.evidence_pack.to_dict(),
            "depth_coverage": self.depth_coverage.to_dict(),
            "build_log": self.build_log,
            "authority_assessments": [a.to_dict() for a in self.authority_assessments],
            "evidence_conflicts": [c.to_dict() for c in self.evidence_conflicts],
        }

    @property
    def has_coverage_gaps(self) -> bool:
        return self.depth_coverage.has_coverage_gaps
