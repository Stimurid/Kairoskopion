"""Mavrinsky real venue selection v2.

Steps:

  1. Open the durable VenueProfileRegistry from `.kairoskopion/`.
  2. Snapshot coverage BEFORE seeding.
  3. Upsert the operator-seeded canonical venue list (bounded, no
     broad discovery).
  4. Enrich the registry (C1 OpenAlex identity + C3 corpus hull build)
     — for newly-seeded venues this is the first enrichment; for
     pre-existing venues this is a no-op.
  5. Snapshot coverage AFTER enrichment.
  6. Run selection v2 with calibrated bucketer.
  7. Persist outputs under private_inputs/runs/.

NO LLM. NO broad discovery. NO new architecture. NO paid APIs.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from kairoskopion.config import env as env_cfg  # noqa: E402
from kairoskopion.services.mavrinsky_venue_selection import (  # noqa: E402
    run_selection_over_registry,
)
from kairoskopion.services.venue_operator_seed import (  # noqa: E402
    SEED_ORIGIN,
    seed_canonical_venues_into_registry,
)
from kairoskopion.services.venue_profile_enricher import enrich_registry  # noqa: E402
from kairoskopion.services.venue_profile_registry import (  # noqa: E402
    VenueProfileRegistry,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("selection-v2")


def _coverage_snapshot(reg) -> dict:
    total = 0
    with_oa = 0
    with_hull = 0
    with_board = 0
    with_formal = 0
    with_cyberleninka = 0
    seeded_origin = 0
    per_venue = []
    for vpkg in reg.list_all():
        total += 1
        cd = vpkg.completeness or {}
        has_oa = bool(vpkg.openalex_source_id)
        has_hull = cd.get("PublishedCorpusHull") in ("present", "partial")
        has_board = cd.get("EditorialBoardCloud") in ("present", "partial")
        has_formal = cd.get("FormalSubmissionProfile") in ("present", "partial")
        has_cl = bool(vpkg.cyberleninka_source_id)
        is_seeded = SEED_ORIGIN in (vpkg.discovery_sources or [])
        if has_oa: with_oa += 1
        if has_hull: with_hull += 1
        if has_board: with_board += 1
        if has_formal: with_formal += 1
        if has_cl: with_cyberleninka += 1
        if is_seeded: seeded_origin += 1
        per_venue.append({
            "canonical_name": vpkg.canonical_name,
            "openalex_source_id": vpkg.openalex_source_id,
            "has_openalex_id": has_oa,
            "has_corpus_hull": has_hull,
            "has_board_cloud": has_board,
            "has_formal_profile": has_formal,
            "has_cyberleninka": has_cl,
            "is_operator_seeded": is_seeded,
            "discovery_sources": list(vpkg.discovery_sources or []),
            "languages": list(vpkg.languages or []),
            "completeness": dict(cd),
        })
    return {
        "total_vpkgs": total,
        "with_openalex_id": with_oa,
        "with_corpus_hull": with_hull,
        "with_editorial_board": with_board,
        "with_formal_profile": with_formal,
        "with_cyberleninka_id": with_cyberleninka,
        "operator_seeded": seeded_origin,
        "per_venue": per_venue,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--storage-root", default=".kairoskopion")
    ap.add_argument("--skip-enrich", action="store_true")
    ap.add_argument("--corpus-max-works", type=int, default=25)
    args = ap.parse_args()

    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    log.info("Env config presence: %s", env_cfg.config_summary())

    reg = VenueProfileRegistry(storage_root=args.storage_root)
    log.info("Registry loaded: %d VPKGs", reg.count())

    before = _coverage_snapshot(reg)
    (out / "coverage_before.json").write_text(
        json.dumps(before, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info(
        "BEFORE: total=%d openalex=%d hull=%d board=%d formal=%d seeded=%d",
        before["total_vpkgs"], before["with_openalex_id"],
        before["with_corpus_hull"], before["with_editorial_board"],
        before["with_formal_profile"], before["operator_seeded"],
    )

    log.info("=== Operator seed upsert (canonical venues) ===")
    seed_summary = seed_canonical_venues_into_registry(reg)
    (out / "seed_summary.json").write_text(
        json.dumps(seed_summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info(
        "Seed: total=%d new=%d merged=%d",
        seed_summary["total_seeds"], seed_summary["newly_inserted"],
        seed_summary["merged_into_existing"],
    )

    if not args.skip_enrich:
        log.info("=== Enrichment pass (C1 identity + C3 corpus) ===")
        enrich_summary = enrich_registry(
            reg, do_identity=True, do_corpus=True,
            corpus_max_works=args.corpus_max_works,
        )
        (out / "enrich_summary.json").write_text(
            json.dumps(enrich_summary, ensure_ascii=False, indent=2,
                       default=str),
            encoding="utf-8",
        )
        log.info(
            "Enrichment: id_attached=%d ambiguous=%d corpus_built=%d",
            enrich_summary.get("identity_attached", 0),
            enrich_summary.get("identity_ambiguous", 0),
            enrich_summary.get("corpus_built", 0),
        )

    after = _coverage_snapshot(reg)
    (out / "coverage_after.json").write_text(
        json.dumps(after, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info(
        "AFTER:  total=%d openalex=%d hull=%d board=%d formal=%d seeded=%d",
        after["total_vpkgs"], after["with_openalex_id"],
        after["with_corpus_hull"], after["with_editorial_board"],
        after["with_formal_profile"], after["operator_seeded"],
    )

    log.info("=== Selection v2 (calibrated) ===")
    artefacts = run_selection_over_registry(reg, output_dir=out)
    bc = artefacts["_meta"]["bucket_counts"]
    print("\n=== BUCKETS (v2 calibrated) ===")
    print(json.dumps(bc, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
