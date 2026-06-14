"""Mavrinsky real venue selection v2.1 stabilization + deep-lite.

Builds on v2 (commit 60e7822). Does NOT expand the pool.

Steps:

  1. Open the durable VenueProfileRegistry from `.kairoskopion/`.
  2. Re-enrich (no-op when already-attached identity + corpus hull).
     B2 fix: merge-upsert now preserves existing board / formal /
     subobject ids.
  3. Run selection with calibrated bucketer (v2 rules).
  4. B1 fix: rank top candidates by bucket FIRST then by within-bucket
     evidence quality (NOT by confidence alone).
  5. For the top candidates (default top 5):
       - controlled homepage -> guidelines/board/scope URL hop;
       - guidelines extractor on the first guidelines URL discovered;
       - corpus pattern light summary (OpenAlex 25 latest works,
         structured fields only).
  6. Persist all artefacts under `private_inputs/runs/`.

NO LLM. NO broad discovery. NO paid APIs. NO secrets committed.
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
    assess_fit_for_vpkg,
    build_mismatch_map,
    mavrinsky_article_model,
    rank_top_candidates,
    select_shortlist,
    stub_citation_plan,
    stub_rewrite_plan,
    stub_risk_report,
)
from kairoskopion.services.venue_profile_enricher import enrich_registry  # noqa: E402
from kairoskopion.services.venue_profile_registry import (  # noqa: E402
    VenueProfileRegistry,
)
from kairoskopion.services.venue_topcand_deeplite import (  # noqa: E402
    corpus_pattern_light_summary,
    discover_for_vpkg,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("selection-v2.1")


def _coverage_snapshot(reg) -> dict:
    out = {
        "total_vpkgs": 0,
        "with_openalex_id": 0,
        "with_corpus_hull": 0,
        "with_editorial_board": 0,
        "with_formal_profile": 0,
        "with_cyberleninka_id": 0,
        "with_homepage_url": 0,
        "per_venue": [],
    }
    for v in reg.list_all():
        cd = v.completeness or {}
        out["total_vpkgs"] += 1
        if v.openalex_source_id:
            out["with_openalex_id"] += 1
        if cd.get("PublishedCorpusHull") in ("present", "partial"):
            out["with_corpus_hull"] += 1
        if cd.get("EditorialBoardCloud") in ("present", "partial"):
            out["with_editorial_board"] += 1
        if cd.get("FormalSubmissionProfile") in ("present", "partial"):
            out["with_formal_profile"] += 1
        if v.cyberleninka_source_id:
            out["with_cyberleninka_id"] += 1
        if v.homepage_url:
            out["with_homepage_url"] += 1
        out["per_venue"].append({
            "canonical_name": v.canonical_name,
            "openalex_source_id": v.openalex_source_id,
            "homepage_url": v.homepage_url,
            "completeness": dict(cd),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--storage-root", default=".kairoskopion")
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--corpus-max-works", type=int, default=25)
    ap.add_argument("--skip-deeplite", action="store_true",
                     help="skip homepage hop + corpus pattern (faster)")
    ap.add_argument("--skip-enrich", action="store_true")
    args = ap.parse_args()

    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    log.info("Env config: %s", env_cfg.config_summary())
    reg = VenueProfileRegistry(storage_root=args.storage_root)
    log.info("Registry: %d VPKGs", reg.count())

    before = _coverage_snapshot(reg)
    (out / "coverage_before.json").write_text(
        json.dumps(before, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info(
        "BEFORE: total=%d openalex=%d hull=%d board=%d formal=%d homepage=%d",
        before["total_vpkgs"], before["with_openalex_id"],
        before["with_corpus_hull"], before["with_editorial_board"],
        before["with_formal_profile"], before["with_homepage_url"],
    )

    if not args.skip_enrich:
        log.info("=== Re-enrichment (B2 merge fix exercised) ===")
        es = enrich_registry(reg, do_identity=True, do_corpus=False,
                              corpus_max_works=args.corpus_max_works)
        (out / "reenrich_summary.json").write_text(
            json.dumps(es, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    # B2 one-shot restoration: if a VPKG carries a subobject id (e.g.
    # editorial_board_cloud_id) but completeness shows 'missing', the
    # subobject exists but its completeness was downgraded by the v2
    # bug before the B2 fix landed. Restore to 'partial' (we know it
    # existed; we cannot re-verify level without re-running the adapter).
    restored = 0
    pairs = (
        ("editorial_board_cloud_id", "EditorialBoardCloud"),
        ("published_corpus_hull_id", "PublishedCorpusHull"),
        ("venue_field_position_id", "VenueFieldPosition"),
    )
    for v in reg.list_all():
        changed = False
        for id_attr, complete_key in pairs:
            if getattr(v, id_attr) and v.completeness.get(complete_key) in (
                None, "missing"
            ):
                v.completeness[complete_key] = "partial"
                v.warnings.append(
                    f"B2 restore: {complete_key} marked partial from "
                    f"orphaned {id_attr}"
                )
                changed = True
        if changed:
            reg.upsert(v)
            restored += 1
    log.info("B2 restoration: %d VPKGs had completeness restored", restored)
    (out / "b2_restoration.json").write_text(
        json.dumps({"restored_count": restored},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    after = _coverage_snapshot(reg)
    (out / "coverage_after.json").write_text(
        json.dumps(after, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info(
        "AFTER:  total=%d openalex=%d hull=%d board=%d formal=%d homepage=%d",
        after["total_vpkgs"], after["with_openalex_id"],
        after["with_corpus_hull"], after["with_editorial_board"],
        after["with_formal_profile"], after["with_homepage_url"],
    )

    log.info("=== Selection v2.1 (B1 ranker fix exercised) ===")
    article = mavrinsky_article_model()
    fits = []
    for v in reg.list_all():
        vd = v.to_dict()
        is_ru = bool(vd.get("cyberleninka_source_id")) or "ru" in (
            vd.get("languages") or []
        )
        fits.append(assess_fit_for_vpkg(
            article, vd,
            corpus_titles=None,
            corpus_works_n=0,
            has_formal_profile=(
                vd.get("completeness", {}).get("FormalSubmissionProfile")
                in ("present", "partial")
            ),
            is_russian_venue=is_ru,
        ))
    buckets = select_shortlist(fits, calibrated=True)
    bucket_counts = {k: len(v) for k, v in buckets.items()}
    (out / "01_article_model.json").write_text(
        json.dumps(article, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (out / "02_fits.json").write_text(
        json.dumps(fits, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (out / "03_shortlist_buckets.json").write_text(
        json.dumps(buckets, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info("Buckets v2.1: %s", bucket_counts)

    top = rank_top_candidates(fits, buckets, n=args.top_n)
    (out / "04_top_candidates.json").write_text(
        json.dumps(top, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info("Top-%d (bucket-first ranker):", args.top_n)
    for i, t in enumerate(top, 1):
        log.info("  %d. [%s] %s", i, t["bucket"], t["canonical_name"])

    # E1-E4 dossiers + F corpus pattern
    fits_by_id = {f["venue_profile_package_id"]: f for f in fits}
    name_to_vpkg = {v.canonical_name: v for v in reg.list_all()}
    mismatch_maps = []
    rewrite_plans = []
    citation_plans = []
    risk_reports = []
    discovery_dossiers = []
    corpus_patterns = []
    for entry in top:
        fit = fits_by_id[entry["venue_profile_package_id"]]
        mismatch_maps.append(build_mismatch_map(article, fit))
        rewrite_plans.append(stub_rewrite_plan(article, fit))
        citation_plans.append(stub_citation_plan(article, fit))
        risk_reports.append(stub_risk_report(article, fit))
        vpkg = name_to_vpkg.get(entry["canonical_name"])
        if not args.skip_deeplite and vpkg is not None:
            try:
                discovery_dossiers.append(discover_for_vpkg(vpkg))
            except Exception as exc:  # noqa: BLE001
                log.warning("discover failed for %s: %s",
                            entry["canonical_name"], exc)
                discovery_dossiers.append({
                    "canonical_name": entry["canonical_name"],
                    "error": str(exc),
                })
            try:
                corpus_patterns.append(corpus_pattern_light_summary(
                    vpkg, max_works=args.corpus_max_works,
                ))
            except Exception as exc:  # noqa: BLE001
                log.warning("corpus pattern failed for %s: %s",
                            entry["canonical_name"], exc)
                corpus_patterns.append({
                    "canonical_name": entry["canonical_name"],
                    "error": str(exc),
                })

    (out / "05_mismatch_maps.json").write_text(
        json.dumps(mismatch_maps, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (out / "06_rewrite_plans.json").write_text(
        json.dumps(rewrite_plans, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (out / "07_citation_plans.json").write_text(
        json.dumps(citation_plans, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (out / "08_risk_reports.json").write_text(
        json.dumps(risk_reports, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (out / "09_discovery_dossiers.json").write_text(
        json.dumps(discovery_dossiers, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (out / "10_corpus_pattern_summaries.json").write_text(
        json.dumps(corpus_patterns, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    summary_meta = {
        "total_vpkgs": len(fits),
        "bucket_counts": bucket_counts,
        "top_n": args.top_n,
        "top_canonical_names": [t["canonical_name"] for t in top],
        "discovery_dossiers_count": len(discovery_dossiers),
        "corpus_pattern_count": len(corpus_patterns),
    }
    (out / "00_summary.json").write_text(
        json.dumps(summary_meta, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # Persist newly-discovered formal profile back into VPKGs.
    # We do this safely via upsert (B2-fixed) so the existing
    # subobjects survive.
    updated = 0
    for dossier in discovery_dossiers:
        fsp = dossier.get("formal_submission_profile")
        if not fsp or fsp.get("access_status") != "opened":
            continue
        vpkg = name_to_vpkg.get(dossier["canonical_name"])
        if not vpkg:
            continue
        vpkg.completeness["FormalSubmissionProfile"] = (
            "partial" if fsp.get("fields_present") else "missing"
        )
        if dossier.get("url_hop", {}).get("discovered", {}).get(
            "editorial_board"
        ):
            board_urls = dossier["url_hop"]["discovered"]["editorial_board"]
            note = (
                f"editorial board URL discovered: {board_urls[0]} "
                "(adapter scrape not yet wired in this pass)"
            )
            if note not in vpkg.warnings:
                vpkg.warnings.append(note)
        reg.upsert(vpkg)
        updated += 1
    log.info("VPKGs updated with new formal profile signal: %d", updated)

    # Final coverage snapshot AFTER deeplite + B2 restoration
    final = _coverage_snapshot(reg)
    (out / "coverage_final.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info(
        "FINAL:  total=%d openalex=%d hull=%d board=%d formal=%d homepage=%d",
        final["total_vpkgs"], final["with_openalex_id"],
        final["with_corpus_hull"], final["with_editorial_board"],
        final["with_formal_profile"], final["with_homepage_url"],
    )

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    print("\n=== BUCKETS (v2.1) ===")
    print(json.dumps(bucket_counts, ensure_ascii=False, indent=2))
    print("\n=== TOP (bucket-first) ===")
    for i, t in enumerate(top, 1):
        try:
            print(f"  {i}. [{t['bucket']}] {t['canonical_name']}")
        except UnicodeEncodeError:
            print(f"  {i}. [{t['bucket']}] {t['canonical_name'].encode('ascii','replace').decode()}")


if __name__ == "__main__":
    main()
