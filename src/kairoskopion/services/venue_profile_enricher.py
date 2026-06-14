"""Venue profile enricher — closes coverage gaps on existing VPKGs.

Operates on records ALREADY in the durable `VenueProfileRegistry`.
Does NOT do broad discovery. Does NOT invent fields.

Each enrichment step is honest about source + access status + evidence.

Steps:

C1. ISSN → OpenAlex Sources lookup (then title fallback when ISSN absent).
C2. Homepage URL discovery from OpenAlex Source record.
C3. Corpus hull build/refresh via the existing venue_corpus_miner.

NO LLM. NO scraping beyond the existing adapter contract.
"""

from __future__ import annotations

import logging
from typing import Any

from ..schema import VenueProfilePackage
from .venue_corpus_miner import mine_venue_corpus
from .venue_profile_registry import VenueProfileRegistry

logger = logging.getLogger(__name__)


def enrich_openalex_identity(
    vpkg: VenueProfilePackage, *, allow_title_fallback: bool = True,
) -> dict[str, Any]:
    """Try to attach an OpenAlex source id via ISSN or title.

    Returns a dict with:
      - matched: bool
      - method: 'issn' | 'title' | None
      - openalex_source_id: str | None
      - homepage_url: str | None
      - ambiguous: bool  # when title search returned >1 plausible candidates
      - access_status: 'opened' | 'inaccessible' | 'unknown'
      - confidence: 'high' (ISSN) | 'medium' (title exact) | 'low'
    """
    if vpkg.openalex_source_id:
        return {"matched": True, "method": "preexisting",
                "openalex_source_id": vpkg.openalex_source_id,
                "homepage_url": vpkg.homepage_url, "ambiguous": False,
                "access_status": "opened", "confidence": "high"}

    # Import HTTP layer lazily so services stay urllib-free at module load
    from ..adapters.venue.openalex_works import (
        lookup_source_by_issn,
        search_source_by_title,
    )

    # ISSN path
    for issn in vpkg.issns or []:
        rec = lookup_source_by_issn(issn)
        if rec and rec.get("id"):
            return {
                "matched": True,
                "method": "issn",
                "openalex_source_id": rec.get("id"),
                "homepage_url": rec.get("homepage_url"),
                "ambiguous": False,
                "access_status": "opened",
                "confidence": "high",
                "matched_issn": issn,
            }

    if not allow_title_fallback or not vpkg.canonical_name:
        return {"matched": False, "method": None, "openalex_source_id": None,
                "homepage_url": None, "ambiguous": False,
                "access_status": "opened", "confidence": "low"}

    # Title path
    candidates = search_source_by_title(vpkg.canonical_name, max_results=5)
    name_norm = vpkg.canonical_name.strip().lower()
    exact = [c for c in candidates
             if (c.get("display_name") or "").strip().lower() == name_norm]
    if exact:
        rec = exact[0]
        return {
            "matched": True,
            "method": "title_exact",
            "openalex_source_id": rec.get("id"),
            "homepage_url": rec.get("homepage_url"),
            "ambiguous": False,
            "access_status": "opened",
            "confidence": "medium",
        }
    if not candidates:
        return {"matched": False, "method": "title", "openalex_source_id": None,
                "homepage_url": None, "ambiguous": False,
                "access_status": "opened", "confidence": "low"}
    # Ambiguous
    return {
        "matched": False,
        "method": "title_ambiguous",
        "openalex_source_id": candidates[0].get("id"),
        "homepage_url": candidates[0].get("homepage_url"),
        "ambiguous": True,
        "access_status": "opened",
        "confidence": "low",
        "candidate_count": len(candidates),
    }


def enrich_vpkg(
    vpkg: VenueProfilePackage,
    *,
    do_identity: bool = True,
    do_corpus: bool = True,
    corpus_max_works: int = 30,
) -> tuple[VenueProfilePackage, dict[str, Any]]:
    """Run enrichment on a single VPKG.

    Returns the updated VPKG and an audit dict of what happened.
    Does NOT persist; caller upserts to registry.
    """
    audit: dict[str, Any] = {
        "vpkg_id": vpkg.venue_profile_package_id,
        "canonical_name": vpkg.canonical_name,
        "actions": [],
    }

    if do_identity and not vpkg.openalex_source_id:
        ident = enrich_openalex_identity(vpkg)
        audit["actions"].append({"step": "C1_identity", **ident})
        if ident.get("matched") and ident["method"] != "preexisting":
            vpkg.openalex_source_id = ident["openalex_source_id"]
            if ident.get("homepage_url") and not vpkg.homepage_url:
                vpkg.homepage_url = ident["homepage_url"]
            sources = list(vpkg.discovery_sources)
            if "OpenAlex" not in sources:
                sources.append("OpenAlex")
                vpkg.discovery_sources = sources
            vpkg.warnings.append(
                f"OpenAlex identity attached via {ident['method']} "
                f"(confidence: {ident['confidence']})"
            )
        elif ident.get("ambiguous"):
            vpkg.unknowns.append(
                f"OpenAlex title search returned {ident.get('candidate_count', '?')} "
                "candidates with no exact name match — identity NOT attached"
            )
        else:
            vpkg.unknowns.append(
                "OpenAlex identity not resolved via ISSN or title"
            )

    if do_corpus and vpkg.openalex_source_id and vpkg.completeness.get(
        "PublishedCorpusHull"
    ) in (None, "missing"):
        try:
            venue_fpm, hull = mine_venue_corpus(
                vpkg.openalex_source_id,
                venue_model_id=None,
                max_works=corpus_max_works,
            )
            vpkg.venue_field_position_id = venue_fpm.field_position_id
            vpkg.published_corpus_hull_id = hull.published_corpus_hull_id
            present = hull.works_fetched > 0
            vpkg.completeness["PublishedCorpusHull"] = (
                "present" if present and hull.abstracts_available > 0
                else ("partial" if present else "missing")
            )
            vpkg.completeness["VenueFieldPosition"] = (
                "present" if present else "missing"
            )
            audit["actions"].append({
                "step": "C3_corpus",
                "works_fetched": hull.works_fetched,
                "abstracts_available": hull.abstracts_available,
                "year_range": [hull.year_range_min, hull.year_range_max],
                "warnings": hull.warnings[:3],
            })
            for w in hull.warnings:
                if w not in vpkg.warnings:
                    vpkg.warnings.append(w)
        except Exception as exc:  # noqa: BLE001
            logger.warning("corpus enrichment failed for %s: %s",
                           vpkg.canonical_name, exc)
            audit["actions"].append({
                "step": "C3_corpus", "error": str(exc),
            })

    # Recompute confidence
    present = sum(1 for v in vpkg.completeness.values() if v == "present")
    partial = sum(1 for v in vpkg.completeness.values() if v == "partial")
    if present >= 5:
        vpkg.confidence = "high"
    elif present + partial >= 4:
        vpkg.confidence = "medium"
    else:
        vpkg.confidence = "low"
    return vpkg, audit


def enrich_registry(
    registry: VenueProfileRegistry,
    *,
    do_identity: bool = True,
    do_corpus: bool = True,
    corpus_max_works: int = 30,
) -> dict[str, Any]:
    """Enrich every VPKG in the registry. Persist upserts."""
    summary = {
        "total": registry.count(),
        "identity_attached": 0,
        "identity_ambiguous": 0,
        "corpus_built": 0,
        "audits": [],
    }
    for vpkg in list(registry.list_all()):
        updated, audit = enrich_vpkg(
            vpkg,
            do_identity=do_identity,
            do_corpus=do_corpus,
            corpus_max_works=corpus_max_works,
        )
        for a in audit["actions"]:
            if a.get("step") == "C1_identity" and a.get("matched"):
                if a.get("method") != "preexisting":
                    summary["identity_attached"] += 1
            elif a.get("step") == "C1_identity" and a.get("ambiguous"):
                summary["identity_ambiguous"] += 1
            elif a.get("step") == "C3_corpus" and not a.get("error") \
                    and (a.get("works_fetched") or 0) > 0:
                summary["corpus_built"] += 1
        summary["audits"].append(audit)
        registry.upsert(updated)
    return summary
