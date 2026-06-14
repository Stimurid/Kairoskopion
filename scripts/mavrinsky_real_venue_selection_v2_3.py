"""Mavrinsky venue selection v2.3 — closure + golden top-5 freeze.

Tiny pass on top of 72aa3b1:

  1. Run the Springer-pattern board fallback ONLY for Philosophy &
     Technology (the one top-5 VPKG still missing a board).
  2. Verify board completeness uses the codified threshold
     (`board_completeness_from_status`) for any new attach this run.
  3. Build a frozen, machine-readable + human-readable golden top-5
     dataset for manual methodological analysis. Marked
     GOLDEN_ANALYSIS_INPUT, NOT submission recommendation.

NO new venues. NO new seed list. NO broad discovery. NO LLM.
NO final submission recommendation.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from kairoskopion.schema import VenueProfilePackage  # noqa: E402
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
from kairoskopion.services.venue_profile_registry import (  # noqa: E402
    VenueProfileRegistry,
)
from kairoskopion.services.venue_topcand_deeplite import (  # noqa: E402
    board_completeness_from_status,
    corpus_pattern_light_summary,
    discover_for_vpkg,
    enrich_board_for_vpkg,
    enrich_board_with_springer_fallback,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("selection-v2.3")


TOP5_CANONICAL_NAMES = [
    "Memory, Mind & Media",
    "Foucault Studies",
    "Techné: Research in Philosophy and Technology",
    "Philosophy & Technology",
    "Le foucaldien",
]


def _safe_get(d: dict, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default if k == keys[-1] else {})
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--storage-root", default=".kairoskopion")
    ap.add_argument("--skip-springer-fallback", action="store_true")
    args = ap.parse_args()

    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    reg = VenueProfileRegistry(storage_root=args.storage_root)
    log.info("Registry: %d VPKGs", reg.count())

    # ----- 1. Springer fallback for P&T -----
    name_to_vpkg = {v.canonical_name: v for v in reg.list_all()}
    pt = name_to_vpkg.get("Philosophy & Technology")
    fallback_result = None
    if pt is None:
        log.warning("P&T VPKG not found; fallback skipped")
    elif args.skip_springer_fallback:
        log.info("Springer fallback skipped by flag")
    else:
        log.info("Running Springer board fallback for P&T "
                 "(homepage=%s)", pt.homepage_url)
        fallback_result = enrich_board_with_springer_fallback(pt)
        log.info("Fallback status: %s, members=%s, board_page_url=%s",
                  fallback_result["extraction_status"],
                  fallback_result["members_sampled"],
                  fallback_result.get("board_page_url"))
        # Persist the audit
        (out / "pt_springer_fallback.json").write_text(
            json.dumps(fallback_result, ensure_ascii=False, indent=2,
                       default=str),
            encoding="utf-8",
        )
        # If success: safe upsert with codified threshold
        if fallback_result["members_sampled"] > 0 \
                and fallback_result["editorial_board_cloud"]:
            cloud = fallback_result["editorial_board_cloud"]
            completeness_value = board_completeness_from_status(
                fallback_result["extraction_status"],
                fallback_result["members_sampled"],
            )
            patch = VenueProfilePackage(
                canonical_name=pt.canonical_name,
                issns=list(pt.issns or []),
                editorial_board_cloud_id=cloud.get("editorial_board_cloud_id"),
                completeness={"EditorialBoardCloud": completeness_value},
            )
            patch.warnings.append(
                f"v2.3 Springer fallback: status="
                f"{fallback_result['extraction_status']} "
                f"members={fallback_result['members_sampled']} "
                f"url={fallback_result.get('board_page_url')}"
            )
            reg.upsert(patch)
            log.info("P&T board attached with completeness=%s",
                      completeness_value)
        else:
            # Honest stable failure recorded on VPKG.
            patch = VenueProfilePackage(
                canonical_name=pt.canonical_name,
                issns=list(pt.issns or []),
            )
            patch.warnings.append(
                f"v2.3 Springer fallback: "
                f"{fallback_result['extraction_status']} — "
                f"tried {len(fallback_result.get('candidates_tried') or [])} "
                "URL patterns; no editor names fabricated"
            )
            reg.upsert(patch)

    # ----- 2. Selection + dossier re-derivation for the top-5 freeze -----
    log.info("=== Re-derive top-5 selection for freeze ===")
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
    top = rank_top_candidates(fits, buckets, n=5)
    fits_by_id = {f["venue_profile_package_id"]: f for f in fits}

    # Defensive: ensure the actual top-5 still matches the expected canon.
    top_names = [t["canonical_name"] for t in top]
    if top_names != TOP5_CANONICAL_NAMES:
        log.warning("Top-5 ordering differs from expected:\n  got: %s\n  expected: %s",
                     top_names, TOP5_CANONICAL_NAMES)

    # ----- 3. Build the golden freeze -----
    log.info("=== Build golden top-5 freeze ===")
    fresh_name_to_vpkg = {v.canonical_name: v for v in reg.list_all()}
    frozen_records = []
    for entry in top:
        vpkg = fresh_name_to_vpkg.get(entry["canonical_name"])
        fit = fits_by_id[entry["venue_profile_package_id"]]
        if vpkg is None:
            frozen_records.append({
                "canonical_name": entry["canonical_name"],
                "error": "VPKG not found in registry",
            })
            continue

        # Re-run lightweight discovery + corpus pattern for this snapshot
        try:
            discovery = discover_for_vpkg(vpkg)
        except Exception as exc:  # noqa: BLE001
            log.warning("discover failed for %s: %s",
                        entry["canonical_name"], exc)
            discovery = {"error": str(exc)}
        try:
            pattern = corpus_pattern_light_summary(vpkg, max_works=25)
        except Exception as exc:  # noqa: BLE001
            log.warning("pattern failed for %s: %s",
                        entry["canonical_name"], exc)
            pattern = {"error": str(exc)}

        # Re-run board lookup using the most recent discovered URL
        board_url = (discovery.get("url_hop") or {}).get("discovered", {}).get(
            "editorial_board", []
        )
        board_url = board_url[0] if board_url else None
        try:
            board_result = enrich_board_for_vpkg(vpkg, board_page_url=board_url)
        except Exception as exc:  # noqa: BLE001
            log.warning("board for %s: %s", entry["canonical_name"], exc)
            board_result = {"error": str(exc)}

        # Pull existing axes from the fit
        axes = fit["axes"]
        sig = fit["_signals_used"]

        frozen = {
            "_lifecycle_status": "GOLDEN_ANALYSIS_INPUT",
            "_not_a_submission_recommendation": True,
            "freeze_date": "2026-06-14",
            "freeze_run_id": str(out.name),
            "canonical_name": vpkg.canonical_name,
            "venue_profile_package_id": vpkg.venue_profile_package_id,
            "aliases": [],
            "publisher": vpkg.publisher,
            "issns": list(vpkg.issns or []),
            "homepage_url": vpkg.homepage_url,
            "languages": list(vpkg.languages or []),
            "openalex_source_id": vpkg.openalex_source_id,
            "cyberleninka_source_id": vpkg.cyberleninka_source_id,
            "discovery_sources": list(vpkg.discovery_sources or []),
            "bucket": entry["bucket"],
            "label_reasons": entry.get("label_reasons") or [],
            "fit_axes_summary": {
                k: ax["value"] for k, ax in axes.items()
            },
            "fit_axes_full": axes,
            "fit_signals": sig,
            "corpus_hull_summary": {
                "published_corpus_hull_id": vpkg.published_corpus_hull_id,
                "completeness": vpkg.completeness.get("PublishedCorpusHull"),
            },
            "corpus_pattern": pattern,
            "formal_submission_profile": discovery.get(
                "formal_submission_profile"
            ) if isinstance(discovery, dict) else None,
            "board_cloud_summary": {
                "editorial_board_cloud_id": vpkg.editorial_board_cloud_id,
                "completeness": vpkg.completeness.get("EditorialBoardCloud"),
                "extraction_status": (
                    board_result.get("extraction_status")
                    if isinstance(board_result, dict) else "UNKNOWN"
                ),
                "members_sampled": (
                    board_result.get("members_sampled", 0)
                    if isinstance(board_result, dict) else 0
                ),
                "board_page_url": (
                    board_result.get("board_page_url")
                    if isinstance(board_result, dict) else None
                ),
            },
            "mismatch_map": build_mismatch_map(article, fit),
            "rewrite_plan_stub": stub_rewrite_plan(article, fit),
            "citation_plan_stub": stub_citation_plan(article, fit),
            "risk_report_stub": stub_risk_report(article, fit),
            "completeness": dict(vpkg.completeness or {}),
            "unknowns": list(vpkg.unknowns or []),
            "warnings": list(vpkg.warnings or [])[-10:],
            "evidence_status_summary": {
                "VenueIdentity": "metadata_api_openalex" if vpkg.openalex_source_id else "unknown",
                "PublishedCorpusHull": (
                    "openalex_corpus_observation"
                    if vpkg.completeness.get("PublishedCorpusHull") in ("present", "partial")
                    else "unknown"
                ),
                "EditorialBoardCloud": (
                    board_result.get("extraction_status")
                    if isinstance(board_result, dict) and board_result.get("extraction_status")
                    else "unknown"
                ),
                "FormalSubmissionProfile": (
                    (discovery.get("formal_submission_profile") or {}).get(
                        "evidence_status"
                    ) if isinstance(discovery, dict) else "unknown"
                ) or "unknown",
            },
        }
        frozen_records.append(frozen)

    freeze = {
        "_lifecycle_status": "GOLDEN_ANALYSIS_INPUT",
        "_not_a_submission_recommendation": True,
        "_intended_use": (
            "Manual methodological golden analysis. NOT a submission "
            "recommendation. NOT a ranking that should be acted on without "
            "human review."
        ),
        "freeze_date": "2026-06-14",
        "freeze_branch": "feature/venue-blockers-vfc2-corpus-board-ru",
        "freeze_commit_baseline": "72aa3b1",
        "registry_total_vpkgs": reg.count(),
        "top5": frozen_records,
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
    }
    json_path = out / "GOLDEN_TOP5_FREEZE_V2_3.json"
    json_path.write_text(
        json.dumps(freeze, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info("Golden freeze written: %s", json_path)

    # ----- Coverage after -----
    after = {
        "with_editorial_board": sum(
            1 for v in reg.list_all()
            if (v.completeness or {}).get("EditorialBoardCloud") in (
                "present", "partial"
            )
        ),
        "top5_with_board": sum(
            1 for v in reg.list_all()
            if v.canonical_name in TOP5_CANONICAL_NAMES
            and (v.completeness or {}).get("EditorialBoardCloud") in (
                "present", "partial"
            )
        ),
        "top5_with_corpus_hull": sum(
            1 for v in reg.list_all()
            if v.canonical_name in TOP5_CANONICAL_NAMES
            and (v.completeness or {}).get("PublishedCorpusHull") in (
                "present", "partial"
            )
        ),
        "top5_with_formal_profile": sum(
            1 for v in reg.list_all()
            if v.canonical_name in TOP5_CANONICAL_NAMES
            and (v.completeness or {}).get("FormalSubmissionProfile") in (
                "present", "partial"
            )
        ),
    }
    (out / "coverage_after.json").write_text(
        json.dumps(after, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info("Coverage: %s", after)


if __name__ == "__main__":
    main()
