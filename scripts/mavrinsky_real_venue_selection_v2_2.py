"""Mavrinsky venue selection v2.2 — editorial board glue (surgical).

Wires the existing `editorial_board.py` adapter onto board URLs
discovered in v2.1 for the top-5 candidates only.

Does NOT add venues. Does NOT broad-discover. Does NOT re-run
selection over the full pool unless --rerun-selection is passed.

Steps:

  1. Load durable VenueProfileRegistry.
  2. Identify top-5 by re-running selection v2.1 (cheap; same fits,
     same calibrated bucketer, same ranker — no new venues touched).
  3. For each top-5: rerun controlled homepage hop to recover board URLs
     (deterministic), then call `enrich_board_for_vpkg`.
  4. Safe upsert per VPKG. Empty/JS-only/INACCESSIBLE results do NOT
     attach a fake board id or downgrade existing data.
  5. Persist board dossiers + final coverage.

NO LLM. NO new architecture. NO broad discovery. NO secrets committed.
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
    mavrinsky_article_model,
    rank_top_candidates,
    select_shortlist,
)
from kairoskopion.services.venue_profile_registry import (  # noqa: E402
    VenueProfileRegistry,
)
from kairoskopion.services.venue_topcand_deeplite import (  # noqa: E402
    discover_for_vpkg,
    enrich_board_for_vpkg,
)
from kairoskopion.schema import VenueProfilePackage  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("selection-v2.2")


def _coverage_snapshot(reg) -> dict:
    out = {
        "total_vpkgs": 0, "with_openalex_id": 0, "with_corpus_hull": 0,
        "with_editorial_board": 0, "with_formal_profile": 0,
        "with_homepage_url": 0,
    }
    for v in reg.list_all():
        cd = v.completeness or {}
        out["total_vpkgs"] += 1
        if v.openalex_source_id: out["with_openalex_id"] += 1
        if cd.get("PublishedCorpusHull") in ("present", "partial"):
            out["with_corpus_hull"] += 1
        if cd.get("EditorialBoardCloud") in ("present", "partial"):
            out["with_editorial_board"] += 1
        if cd.get("FormalSubmissionProfile") in ("present", "partial"):
            out["with_formal_profile"] += 1
        if v.homepage_url: out["with_homepage_url"] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--storage-root", default=".kairoskopion")
    ap.add_argument("--top-n", type=int, default=5)
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
    log.info("BEFORE board=%d formal=%d", before["with_editorial_board"],
              before["with_formal_profile"])

    # Re-run selection to identify the same top-5 (deterministic — no
    # new venues touched).
    article = mavrinsky_article_model()
    fits = []
    for v in reg.list_all():
        vd = v.to_dict()
        is_ru = bool(vd.get("cyberleninka_source_id")) or "ru" in (
            vd.get("languages") or []
        )
        fits.append(assess_fit_for_vpkg(
            article, vd,
            corpus_titles=None, corpus_works_n=0,
            has_formal_profile=(
                vd.get("completeness", {}).get("FormalSubmissionProfile")
                in ("present", "partial")
            ),
            is_russian_venue=is_ru,
        ))
    buckets = select_shortlist(fits, calibrated=True)
    top = rank_top_candidates(fits, buckets, n=args.top_n)
    (out / "top_candidates.json").write_text(
        json.dumps(top, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info("Top-%d (bucket-first):", args.top_n)
    for i, t in enumerate(top, 1):
        log.info("  %d. [%s] %s", i, t["bucket"], t["canonical_name"])

    name_to_vpkg = {v.canonical_name: v for v in reg.list_all()}

    # Step 3 + 4: re-hop each top to recover board URL, then enrich
    board_dossiers = []
    status_counter: dict[str, int] = {}
    upsert_actions = []
    for entry in top:
        vpkg = name_to_vpkg.get(entry["canonical_name"])
        if vpkg is None:
            board_dossiers.append({
                "canonical_name": entry["canonical_name"],
                "extraction_status": "UNKNOWN",
                "notes": ["VPKG not found in registry — skipping"],
            })
            continue

        # Discover board URL (homepage hop; same as v2.1)
        try:
            hop = discover_for_vpkg(vpkg)
            url_hop = hop.get("url_hop") or {}
            board_urls = (url_hop.get("discovered") or {}).get(
                "editorial_board", []
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("hop failed for %s: %s", entry["canonical_name"], exc)
            board_urls = []
            url_hop = {"warnings": [f"hop error: {exc}"]}

        board_url = board_urls[0] if board_urls else None

        result = enrich_board_for_vpkg(vpkg, board_page_url=board_url)
        result["homepage_hop_status"] = url_hop.get("homepage_access_status")
        status_counter[result["extraction_status"]] = (
            status_counter.get(result["extraction_status"], 0) + 1
        )
        board_dossiers.append(result)

        # Safe upsert: only attach board cloud id + bump completeness
        # when extraction actually produced members.
        if result["members_sampled"] > 0 and result["editorial_board_cloud"]:
            cloud = result["editorial_board_cloud"]
            new_id = cloud.get("editorial_board_cloud_id")
            # Build a minimal patch VPKG — same canonical_name + issns
            # for matching — that only carries the board fields. The
            # B2-fixed registry.upsert preserves everything else.
            patch_completeness = {
                "EditorialBoardCloud": (
                    "partial" if result["members_sampled"] < 6 else "present"
                )
            }
            patch = VenueProfilePackage(
                canonical_name=vpkg.canonical_name,
                issns=list(vpkg.issns or []),
                editorial_board_cloud_id=new_id,
                completeness=patch_completeness,
            )
            patch.warnings.append(
                f"v2.2 board glue: status={result['extraction_status']} "
                f"members={result['members_sampled']} url={board_url}"
            )
            reg.upsert(patch)
            upsert_actions.append({
                "canonical_name": vpkg.canonical_name,
                "action": "board_cloud_attached",
                "members": result["members_sampled"],
                "status": result["extraction_status"],
            })
        else:
            # Honest: record the failure on the VPKG via a warning,
            # do NOT touch board_cloud_id or completeness.
            patch = VenueProfilePackage(
                canonical_name=vpkg.canonical_name,
                issns=list(vpkg.issns or []),
                # no editorial_board_cloud_id, no completeness change
            )
            patch.warnings.append(
                f"v2.2 board glue: status={result['extraction_status']} "
                f"members={result['members_sampled']} url={board_url}"
            )
            reg.upsert(patch)
            upsert_actions.append({
                "canonical_name": vpkg.canonical_name,
                "action": "board_failure_logged",
                "status": result["extraction_status"],
            })

    (out / "board_dossiers.json").write_text(
        json.dumps(board_dossiers, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (out / "upsert_actions.json").write_text(
        json.dumps(upsert_actions, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info("Status distribution: %s", status_counter)

    after = _coverage_snapshot(reg)
    (out / "coverage_after.json").write_text(
        json.dumps(after, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info("AFTER  board=%d formal=%d", after["with_editorial_board"],
              after["with_formal_profile"])

    summary = {
        "top_canonical_names": [t["canonical_name"] for t in top],
        "before_board_coverage": before["with_editorial_board"],
        "after_board_coverage": after["with_editorial_board"],
        "status_distribution": status_counter,
    }
    (out / "00_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
