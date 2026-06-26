"""Registry integration service (P6.1).

The single product-path entry point for registry-first operations.
All Case/API/Pipeline flows call through this service — no direct
agent calls bypass it for operations that need registry awareness.

Provides:
- Registry-first discipline lookup (before DisciplineSourceAcquisition)
- Registry candidate enrichment for VenueFunnel
- VenueProfiler output → provisional registry records
- Downstream status propagation helpers
- Family context from registry evidence
- Provenance enrichment for candidates
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .models import (
    EvidenceRef,
    VenueRegistryRecord,
    VenueSectionRecord,
    VenueClassificationRecord,
    VenueMetricRecord,
    SourceAcquisitionTask,
)
from .store import BaseRegistry
from .status import record_usage_status
from .services import RegistryHub

logger = logging.getLogger(__name__)


class RegistryIntegrationService:
    """Product-path integration layer for registry-first operations.

    Every Case method that touches discipline/venue data delegates
    here. This ensures:
    - Local registry checked before any LLM/external call
    - Extraction outputs stored as provisional records
    - All product output carries provenance metadata
    - Status propagation (canonical/provisional/rejected/unknown)
    """

    def __init__(self, hub: RegistryHub | None = None, data_dir: Path | None = None):
        self.hub = hub or RegistryHub(data_dir=data_dir)

    # ==================================================================
    # Track 3: Discipline registry-first lookup
    # ==================================================================

    def discipline_lookup(
        self,
        query: str,
        *,
        agent_name: str | None = None,
        case_id: str | None = None,
    ) -> dict[str, Any]:
        """Registry-first discipline lookup.

        1. Search discipline registry for accepted/provisional match
        2. If accepted → return canonical, no LLM needed
        3. If provisional → return with warning
        4. If nothing → create SourceAcquisitionTask
        """
        return self.hub.lookup_discipline(
            query, agent_name=agent_name, case_id=case_id,
        )

    # ==================================================================
    # Track 4: VenueFunnel registry candidate enrichment
    # ==================================================================

    def build_registry_candidates_for_funnel(
        self,
        *,
        query: str | None = None,
        issn: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Build known corpus candidates from registry for VenueFunnel.

        Returns list of candidate dicts with record_id, source_status,
        usage_status, and evidence provenance. Rejected records excluded.
        """
        candidates: list[dict[str, Any]] = []

        venues_reg = self.hub.venues()
        venue_records: list[Any] = []

        if issn:
            for rec in venues_reg.list_all():
                if rec.issn == issn or rec.eissn == issn:
                    venue_records.append(rec)
                    break

        if not venue_records and query:
            venue_records = venues_reg.search(query, limit=limit)

        if not venue_records:
            venue_records = venues_reg.list_all()[:limit]

        for rec in venue_records:
            status = record_usage_status(rec)
            if status == "rejected_unusable":
                continue
            cand = {
                "record_id": rec.venue_id,
                "candidate_type": "venue",
                "canonical_name": rec.canonical_name,
                "issn": rec.issn,
                "source_status": rec.source_status,
                "review_status": rec.review_status,
                "usage_status": status,
                "known_corpus_candidate": True,
                "evidence_refs": [e.to_dict() for e in rec.evidence_refs],
            }
            if status == "provisional_with_warning":
                cand["warnings"] = ["provisional — not curator-confirmed"]
            candidates.append(cand)

            sections = self.hub.lookup_venue_sections(rec.venue_id)
            for sec in sections:
                sec_status = record_usage_status(sec)
                if sec_status == "rejected_unusable":
                    continue
                sec_cand = {
                    "record_id": sec.section_id,
                    "candidate_type": "venue_section",
                    "section_name": sec.section_name,
                    "section_type": sec.section_type,
                    "parent_venue_id": sec.parent_venue_id,
                    "scope": sec.scope,
                    "source_status": sec.source_status,
                    "review_status": sec.review_status,
                    "usage_status": sec_status,
                    "known_corpus_candidate": True,
                    "evidence_refs": [e.to_dict() for e in sec.evidence_refs],
                }
                if sec_status == "provisional_with_warning":
                    sec_cand["warnings"] = [
                        "provisional section — not curator-confirmed",
                    ]
                candidates.append(sec_cand)

        return candidates

    def create_venue_discovery_tasks(
        self,
        queries: list[str],
        *,
        agent_name: str | None = None,
        case_id: str | None = None,
    ) -> list[SourceAcquisitionTask]:
        """Create acquisition tasks for venue discovery when registry empty."""
        tasks = []
        for q in queries:
            result = self.hub.lookup_venue(
                q, agent_name=agent_name, case_id=case_id,
            )
            if not result["found"] and result["task"]:
                tasks.append(result["task"])
        return tasks

    # ==================================================================
    # Track 5: VenueFamilyContext registry enrichment
    # ==================================================================

    def build_family_context(
        self,
        venue_id: str,
    ) -> dict[str, Any]:
        """Build family context from registry evidence only.

        Returns dict with neighboring venues/sections from registry.
        No model-memory sibling names.
        """
        venue = self.hub.venues().get(venue_id)
        if venue is None:
            return {
                "venue_id": venue_id,
                "status": "incomplete",
                "reason": "venue not in registry",
                "neighbors": [],
                "sections": [],
            }

        sections = self.hub.lookup_venue_sections(venue_id)
        section_data = []
        for sec in sections:
            status = record_usage_status(sec)
            if status == "rejected_unusable":
                continue
            section_data.append({
                "section_id": sec.section_id,
                "section_name": sec.section_name,
                "scope": sec.scope,
                "usage_status": status,
            })

        neighbors = []
        if venue.parent_venue_id:
            parent = self.hub.venues().get(venue.parent_venue_id)
            if parent:
                neighbors.append({
                    "venue_id": parent.venue_id,
                    "canonical_name": parent.canonical_name,
                    "relation": "parent",
                    "usage_status": record_usage_status(parent),
                })

        for rec in self.hub.venues().list_all():
            if rec.parent_venue_id == venue_id:
                neighbors.append({
                    "venue_id": rec.venue_id,
                    "canonical_name": rec.canonical_name,
                    "relation": "child",
                    "usage_status": record_usage_status(rec),
                })

        has_evidence = bool(sections or neighbors)
        return {
            "venue_id": venue_id,
            "canonical_name": venue.canonical_name,
            "status": "evidence_based" if has_evidence else "insufficient_evidence",
            "usage_status": record_usage_status(venue),
            "neighbors": neighbors,
            "sections": section_data,
        }

    # ==================================================================
    # Track 6: VenueMatrix provenance enrichment
    # ==================================================================

    def enrich_candidates_with_provenance(
        self,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Enrich candidate list with registry provenance.

        - Candidates with record_id get usage_status from registry
        - Candidates without provenance get a warning
        """
        enriched = []
        for cand in candidates:
            cand = dict(cand)
            rid = cand.get("record_id")

            if rid:
                venue_rec = self.hub.venues().get(rid)
                if venue_rec:
                    cand["source_status"] = venue_rec.source_status
                    cand["review_status"] = venue_rec.review_status
                    cand["usage_status"] = record_usage_status(venue_rec)
                    cand["evidence_refs"] = [
                        e.to_dict() for e in venue_rec.evidence_refs
                    ]
                else:
                    sec_rec = self.hub.venue_sections().get(rid)
                    if sec_rec:
                        cand["source_status"] = sec_rec.source_status
                        cand["review_status"] = sec_rec.review_status
                        cand["usage_status"] = record_usage_status(sec_rec)
                        cand["evidence_refs"] = [
                            e.to_dict() for e in sec_rec.evidence_refs
                        ]

            if "usage_status" not in cand:
                cand["usage_status"] = "unknown"
            if not cand.get("evidence_refs") and not cand.get("source_ref"):
                cand.setdefault("warnings", [])
                cand["warnings"].append("no provenance — requires evidence")

            enriched.append(cand)
        return enriched

    # ==================================================================
    # Track 7: VenueProfiler output → provisional registry records
    # ==================================================================

    def venue_extraction_to_provisional(
        self,
        extraction_output: dict[str, Any],
        *,
        source_url: str | None = None,
        source_type: str = "author_guidelines",
    ) -> dict[str, Any]:
        """Convert VenueProfiler/VenueFactExtraction output to provisional
        registry records.

        Returns dict with created record IDs and types.
        """
        created: list[dict[str, str]] = []

        evidence_ref = EvidenceRef(
            source_type=source_type,
            source_url=source_url,
            evidence_status="source_grounded" if source_url else "llm_inference",
        )

        # Parent venue record
        venue_name = extraction_output.get("canonical_name")
        parent_venue_id: str | None = None
        if venue_name:
            venue_reg = self.hub.venues()
            existing = None
            issn = extraction_output.get("issn")
            if issn:
                for rec in venue_reg.list_all():
                    if rec.issn == issn:
                        existing = rec
                        break
            if existing is None:
                venue_rec = VenueRegistryRecord(
                    canonical_name=venue_name,
                    issn=extraction_output.get("issn"),
                    eissn=extraction_output.get("eissn"),
                    publisher=extraction_output.get("publisher_or_owner"),
                    official_urls=extraction_output.get("official_urls", []),
                )
                venue_reg.add_provisional(venue_rec, evidence_refs=[evidence_ref])
                created.append({
                    "type": "venue",
                    "record_id": venue_rec.venue_id,
                    "name": venue_name,
                })
                parent_venue_id = venue_rec.venue_id
            else:
                parent_venue_id = existing.venue_id

        # Sections
        for sec_data in extraction_output.get("sections", []):
            sec_name = sec_data.get("name") or sec_data.get("section_name")
            if not sec_name:
                continue
            sec_rec = VenueSectionRecord(
                parent_venue_id=parent_venue_id,
                section_name=sec_name,
                section_type=sec_data.get("type", "section"),
                scope=sec_data.get("scope"),
            )
            self.hub.venue_sections().add_provisional(
                sec_rec, evidence_refs=[evidence_ref],
            )
            created.append({
                "type": "venue_section",
                "record_id": sec_rec.section_id,
                "name": sec_name,
            })

        # Indexing claims → VenueClassificationRecord (vendor_claim)
        for claim in extraction_output.get("indexing_claims", []):
            db_name = claim if isinstance(claim, str) else claim.get("database", "")
            if not db_name:
                continue
            clf_rec = VenueClassificationRecord(
                venue_id=parent_venue_id,
                source_ref=source_url,
                evidence_status="vendor_claim",
            )
            self.hub.venue_classifications().add_provisional(clf_rec)
            created.append({
                "type": "venue_classification",
                "record_id": clf_rec.record_id,
                "name": db_name,
            })

        # Metrics claims → VenueMetricRecord (per db/year/category)
        for metric_data in extraction_output.get("metrics_claims", []):
            if not isinstance(metric_data, dict):
                continue
            met_rec = VenueMetricRecord(
                venue_id=parent_venue_id,
                database=metric_data.get("database"),
                subject_category_id=metric_data.get("subject_category_id"),
                year=metric_data.get("year"),
                metric_type=metric_data.get("metric_type"),
                metric_value=metric_data.get("metric_value"),
                source_ref=source_url,
                evidence_status="vendor_claim",
            )
            self.hub.venue_metrics().add_provisional(met_rec)
            created.append({
                "type": "venue_metric",
                "record_id": met_rec.metric_id,
                "name": (
                    f"{metric_data.get('database', '?')}"
                    f"/{metric_data.get('year', '?')}"
                ),
            })

        return {
            "created_count": len(created),
            "records": created,
            "parent_venue_id": parent_venue_id,
        }

    # ==================================================================
    # Track 8: Downstream status propagation
    # ==================================================================

    def propagate_status(
        self,
        output: dict[str, Any],
    ) -> dict[str, Any]:
        """Add usage_status to any output dict that references registry records.

        Scans for record_id, venue_id, discipline_id fields and annotates
        with _registry_status from registry.
        """
        output = dict(output)

        for key in ("record_id", "venue_id", "discipline_id"):
            rid = output.get(key)
            if not rid:
                continue

            rec = None
            for reg_type in ("venue", "discipline", "venue_section"):
                reg = self.hub._get_registry(reg_type)
                rec = reg.get(rid)
                if rec:
                    break

            if rec:
                output["_registry_status"] = {
                    "source_status": rec.source_status,
                    "review_status": rec.review_status,
                    "usage_status": record_usage_status(rec),
                }

        # Recurse into lists of candidates/assessments
        for list_key in ("candidates", "assessments", "known_corpus_candidates"):
            items = output.get(list_key)
            if isinstance(items, list):
                output[list_key] = [
                    self.propagate_status(item) if isinstance(item, dict) else item
                    for item in items
                ]

        return output

    # ==================================================================
    # Product-path: investigate_venue with registry
    # ==================================================================

    def investigate_venue_registry_first(
        self,
        venue_name: str | None = None,
        issn: str | None = None,
    ) -> dict[str, Any]:
        """Check registry before venue investigation.

        Returns: {"found": bool, "record": VenueRegistryRecord|None,
                  "usage_status": str, "candidates": [...],
                  "family_context": dict|None}
        """
        result = self.hub.lookup_venue(
            venue_name or "",
            issn=issn,
            agent_name="investigate_venue",
        )

        if result["found"]:
            rec = result["record"]
            family = self.build_family_context(rec.venue_id)
            candidates = self.build_registry_candidates_for_funnel(
                issn=rec.issn,
                query=rec.canonical_name,
            )
            return {
                "found": True,
                "record": rec,
                "usage_status": result["usage_status"],
                "candidates": candidates,
                "family_context": family,
            }

        return {
            "found": False,
            "record": None,
            "usage_status": "unknown",
            "candidates": [],
            "family_context": None,
            "task": result.get("task"),
        }

    def store_venue_extraction(
        self,
        venue_dict: dict[str, Any],
        *,
        source_url: str | None = None,
        source_type: str = "author_guidelines",
    ) -> dict[str, Any]:
        """After VenueProfiler runs, store its output as provisional records.

        This is the post-extraction hook that wires Track 7 into
        the investigate_venue product path.
        """
        extraction_data = {
            "canonical_name": venue_dict.get("canonical_name"),
            "issn": venue_dict.get("issn"),
            "eissn": venue_dict.get("eissn"),
            "publisher_or_owner": venue_dict.get("publisher"),
            "official_urls": venue_dict.get("official_urls", []),
            "sections": venue_dict.get("sections", []),
            "indexing_claims": venue_dict.get("indexing_claims", []),
            "metrics_claims": venue_dict.get("metrics_claims", []),
        }
        return self.venue_extraction_to_provisional(
            extraction_data,
            source_url=source_url,
            source_type=source_type,
        )
