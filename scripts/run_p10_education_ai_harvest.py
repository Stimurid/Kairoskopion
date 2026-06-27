#!/usr/bin/env python3
"""P10 Operational Harvest — RU Education/AI Venue Discovery.

Queries free adapters (OpenAlex, Crossref, DOAJ) in LIVE mode for education/AI
journals, creates provisional venue records, runs verification gate, and exports
a review packet.

Constraints: no paid API, no LLM, no fabricated facts, no auto-promotion.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter
from kairoskopion.adapters.venue.crossref import CrossrefVenueAdapter  # lookup_venue only
from kairoskopion.adapters.venue.doaj import DOAJVenueAdapter
from kairoskopion.adapters.venue.base import VenueAdapterMode, VenueAdapterResult
from kairoskopion.registry.models import VenueRegistryRecord, EvidenceRef
from kairoskopion.registry.store import BaseRegistry
from kairoskopion.registry.services import RegistryHub
from kairoskopion.services.verification_gate import verify_registry, summarize_verification
from kairoskopion.services.review_packet_exporter import (
    build_review_packet, export_markdown, export_jsonl, export_tsv,
)


SEARCH_QUERIES = {
    "openalex": [
        "education Russia",
        "pedagogy",
        "higher education",
        "educational technology",
        "artificial intelligence education",
        "digital education",
    ],
    # crossref has lookup_venue only (single ISSN/name), no search_venues
    # used in enrichment phase, not discovery
    "doaj": [
        "education",
        "pedagogy",
        "educational technology",
        "higher education Russia",
    ],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_name(result: VenueAdapterResult) -> str | None:
    for c in result.claims:
        if c.claim_path == "canonical_name":
            return c.claim_value
    return None


def _extract_issn(result: VenueAdapterResult) -> str | None:
    for c in result.claims:
        if c.claim_path == "issn":
            return c.claim_value
    return None


def _extract_publisher(result: VenueAdapterResult) -> str | None:
    for c in result.claims:
        if c.claim_path == "publisher_or_owner":
            return c.claim_value
    return None


def _extract_url(result: VenueAdapterResult) -> str | None:
    for c in result.claims:
        if c.claim_path in ("homepage_url", "official_urls"):
            v = c.claim_value
            if isinstance(v, list):
                return v[0] if v else None
            return v
    return None


def run_adapter_searches(
    output_dir: Path,
    *,
    dry_run: bool = False,
    cache_dir: Path | None = None,
    per_page: int = 10,
) -> list[VenueAdapterResult]:
    """Query all free adapters in LIVE mode and return combined results."""

    all_results: list[VenueAdapterResult] = []

    adapters = {
        "openalex": OpenAlexVenueAdapter(
            mode=VenueAdapterMode.LIVE_API,
            cache_dir=str(cache_dir) if cache_dir else None,
        ),
        "doaj": DOAJVenueAdapter(
            mode=VenueAdapterMode.LIVE_API,
            cache_dir=str(cache_dir) if cache_dir else None,
        ),
    }

    raw_results_path = output_dir / "adapter_raw_results.jsonl"

    for adapter_name, queries in SEARCH_QUERIES.items():
        adapter = adapters[adapter_name]
        print(f"\n--- {adapter_name.upper()} ---")
        for query in queries:
            print(f"  query: {query!r} ...", end=" ", flush=True)
            if dry_run:
                print("[DRY RUN — skipped]")
                continue
            try:
                results = adapter.search_venues(query, per_page=per_page)
                print(f"{len(results)} results")
                for r in results:
                    all_results.append(r)
                    with open(raw_results_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
            except Exception as exc:
                print(f"ERROR: {exc}")

    return all_results


def deduplicate_results(
    results: list[VenueAdapterResult],
) -> list[VenueAdapterResult]:
    """Deduplicate adapter results by ISSN, then by canonical_name."""
    seen_issns: set[str] = set()
    seen_names: set[str] = set()
    deduped: list[VenueAdapterResult] = []

    for r in results:
        if r.status != "success":
            continue

        issn = _extract_issn(r)
        name = _extract_name(r)

        if issn and issn in seen_issns:
            continue
        if not issn and name and name.lower() in seen_names:
            continue

        if issn:
            seen_issns.add(issn)
        if name:
            seen_names.add(name.lower())
        deduped.append(r)

    return deduped


def results_to_provisional_records(
    results: list[VenueAdapterResult],
) -> list[VenueRegistryRecord]:
    """Convert adapter results to provisional VenueRegistryRecords."""
    records: list[VenueRegistryRecord] = []

    for r in results:
        name = _extract_name(r)
        if not name:
            continue

        issn = _extract_issn(r)
        publisher = _extract_publisher(r)
        url = _extract_url(r)

        evidence = EvidenceRef(
            source_type=f"adapter_{r.adapter_id}",
            source_id=r.adapter_id,
            evidence_status=r.evidence_status,
            retrieval_date=r.fetched_at or _now_iso(),
            notes=f"LIVE search via {r.adapter_id}, query={r.query}",
        )

        rec = VenueRegistryRecord(
            canonical_name=name,
            issn=issn,
            publisher=publisher,
            official_urls=[url] if url else [],
            source_status="provisional",
            review_status="pending",
            evidence_refs=[evidence],
            provenance=f"p10_harvest_{r.adapter_id}",
        )
        records.append(rec)

    return records


def load_records_to_registry(
    records: list[VenueRegistryRecord],
    hub: RegistryHub,
) -> int:
    """Add provisional records to the venue registry, skipping duplicates."""
    venue_reg = hub._get_registry("venue")
    loaded = 0
    for rec in records:
        dup = venue_reg.find_duplicate(rec)
        if dup:
            try:
                print(f"  SKIP (dup of {dup}): {rec.canonical_name}")
            except UnicodeEncodeError:
                print(f"  SKIP (dup): [{rec.issn or 'no ISSN'}]")
            continue
        venue_reg.add_provisional(rec, evidence_refs=rec.evidence_refs)
        try:
            print(f"  ADDED: {rec.canonical_name} ({rec.issn or 'no ISSN'}) [{rec.venue_id}]")
        except UnicodeEncodeError:
            print(f"  ADDED: [non-ASCII name] ({rec.issn or 'no ISSN'}) [{rec.venue_id}]")
        loaded += 1
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(description="P10 Education/AI Venue Harvest")
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("data/seed_registry/education_ai_russia/p10_harvest"),
    )
    parser.add_argument(
        "--registry-dir", type=Path,
        default=Path("data/registry"),
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--per-page", type=int, default=10)
    parser.add_argument(
        "--cache-dir", type=Path,
        default=Path("data/cache/http"),
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    args.registry_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("P10 OPERATIONAL HARVEST — RU Education/AI")
    print(f"Date: {_now_iso()}")
    print(f"Output: {args.output_dir}")
    print(f"Registry: {args.registry_dir}")
    print(f"Cache: {args.cache_dir}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 60)

    # Phase 1: adapter searches
    print("\n[PHASE 1] Running adapter searches (LIVE mode)...")
    raw_results = run_adapter_searches(
        args.output_dir,
        dry_run=args.dry_run,
        cache_dir=args.cache_dir,
        per_page=args.per_page,
    )
    print(f"\nTotal raw results: {len(raw_results)}")

    if args.dry_run:
        print("\n[DRY RUN] No records to process. Exiting.")
        return

    # Phase 2: deduplicate
    print("\n[PHASE 2] Deduplicating results...")
    deduped = deduplicate_results(raw_results)
    print(f"Unique results after dedup: {len(deduped)}")

    # Phase 3: convert to provisional records
    print("\n[PHASE 3] Converting to provisional venue records...")
    records = results_to_provisional_records(deduped)
    print(f"Provisional records created: {len(records)}")

    # Save provisional records to JSONL
    prov_path = args.output_dir / "provisional_venue_records.jsonl"
    with open(prov_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
    print(f"Saved to: {prov_path}")

    # Phase 4: load to registry
    print("\n[PHASE 4] Loading provisional records into registry...")
    hub = RegistryHub(data_dir=args.registry_dir)
    loaded = load_records_to_registry(records, hub)
    print(f"Loaded: {loaded} records")

    # Phase 5: verification gate
    print("\n[PHASE 5] Running verification gate...")
    decisions = verify_registry(hub, no_paid_api=True)
    summary = summarize_verification(decisions)
    print(f"Verification complete: {len(decisions)} decisions")
    print(f"  {json.dumps(summary, indent=2, ensure_ascii=False)}")

    # Save verification decisions
    vdec_path = args.output_dir / "verification_decisions.jsonl"
    with open(vdec_path, "w", encoding="utf-8") as f:
        for d in decisions:
            f.write(json.dumps(d.to_dict(), ensure_ascii=False) + "\n")
    print(f"Saved verification to: {vdec_path}")

    # Phase 6: review packet
    print("\n[PHASE 6] Building review packet...")
    gaps = [
        "Education/AI venue universe is bootstrapped from free adapter queries only",
        "eLibrary.ru data not available (needs API key)",
        "RSCI data not available (needs API key)",
        "Scopus/WoS data not available (paid)",
        "VAK list corroboration done by adapter cross-reference only",
        "Discipline seeds remain llm_draft — no authoritative corroboration yet",
    ]
    packet = build_review_packet(hub, gaps=gaps, no_paid_api=True)

    # Attach verification decisions and summary to packet
    packet.verification_decisions = [d.to_dict() for d in decisions]
    packet.verification_summary = summary

    # Export formats
    md_path = args.output_dir / "review_packet.md"
    jsonl_path = args.output_dir / "review_packet.jsonl"
    tsv_path = args.output_dir / "review_packet.tsv"

    md_path.write_text(export_markdown(packet), encoding="utf-8")
    jsonl_path.write_text(export_jsonl(packet), encoding="utf-8")
    tsv_path.write_text(export_tsv(packet), encoding="utf-8")

    print(f"Review packet exported:")
    print(f"  MD:   {md_path}")
    print(f"  JSONL: {jsonl_path}")
    print(f"  TSV:  {tsv_path}")

    # Phase 7: harvest summary
    summary_path = args.output_dir / "harvest_summary.json"
    harvest_summary = {
        "harvest_id": "p10_education_ai_2026-06-27",
        "date": _now_iso(),
        "raw_results": len(raw_results),
        "deduped_results": len(deduped),
        "provisional_records": len(records),
        "loaded_to_registry": loaded,
        "verification_decisions": len(decisions),
        "verification_summary": summary,
        "gaps": gaps,
        "constraints": {
            "no_paid_api": True,
            "no_llm": True,
            "no_auto_promote": True,
        },
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(harvest_summary, f, indent=2, ensure_ascii=False)
    print(f"\nHarvest summary: {summary_path}")

    print("\n" + "=" * 60)
    print("P10 HARVEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
