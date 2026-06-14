"""Build real Mavrinsky venue pool v2 — with corpus mining, editorial
board scraping, CyberLeninka Russian-side adapter, and persistent
VenueProfilePackage registry.

Pipeline:
  1. Discovery — fan-out queries to DOAJ + OpenAlex + CyberLeninka
     across 15+ discipline-cluster queries.
  2. Dedupe by ISSN/name.
  3. Shortlist top-N by discovery breadth.
  4. For each top-15: build VenueProfilePackage via the real corpus
     miner (OpenAlex Works → reconstructed abstracts → corpus_analyzer
     → corpus_hull_builder). Persist to registry.
  5. For each top-5: also scrape editorial board (if homepage_url
     available) and produce EditorialBoardCloud.
  6. Cross-session reuse: on second run, existing entries are upserted
     (sub-IDs preserved, lists merged).

NO LLM. NO new architecture. NO paid sources.

Usage:
    python scripts/build_real_venue_pool_v2.py \\
        --output private_inputs/runs/mavrinsky_real_venue_pool_v2_001
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from kairoskopion.adapters.venue.cyberleninka import search_journals as cl_search  # noqa: E402
from kairoskopion.services.venue_profile_package_builder import (  # noqa: E402
    build_venue_profile_package,
)
from kairoskopion.services.venue_profile_registry import VenueProfileRegistry  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("realpool2")


DOAJ_BASE = "https://doaj.org/api/search/journals"
OPENALEX_BASE = "https://api.openalex.org/sources"
DEFAULT_UA = (
    "Kairoskopion/0.2 "
    "(https://github.com/Stimurid/Kairoskopion; "
    "mailto:kairoskopion@proton.me)"
)


QUERY_CLUSTERS_EN = [
    ("philosophy_of_technology", "philosophy of technology"),
    ("continental_philosophy", "continental philosophy"),
    ("media_philosophy", "media philosophy"),
    ("media_studies", "media theory"),
    ("interface_studies", "interface theory"),
    ("digital_culture", "digital culture"),
    ("STS", "science and technology studies"),
    ("STS_2", "social studies of science"),
    ("AI_ethics", "ethics of technology"),
    ("digital_humanities", "digital humanities"),
]

QUERY_CLUSTERS_RU = [
    ("ru_philosophy_techn", "философия техники"),
    ("ru_subjectivity", "субъект феноменология"),
    ("ru_methodology", "методология"),
    ("ru_continental", "континентальная философия"),
    ("ru_media", "медиафилософия"),
]


def fetch_json(url: str, timeout: int = 15) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        log.warning("HTTP %s on %s", type(e).__name__, url[:80])
        return None


def doaj_search(q: str, size: int = 15) -> list[dict[str, Any]]:
    url = f"{DOAJ_BASE}/{urllib.parse.quote(q)}?pageSize={size}"
    data = fetch_json(url)
    return data.get("results", []) or [] if data else []


def openalex_search(q: str, per_page: int = 15) -> list[dict[str, Any]]:
    url = f"{OPENALEX_BASE}?search={urllib.parse.quote(q)}&per_page={per_page}"
    data = fetch_json(url)
    return data.get("results", []) or [] if data else []


def normalize_doaj(rec: dict[str, Any], cluster_query: str) -> dict[str, Any]:
    bib = rec.get("bibjson", {}) or {}
    eissn = bib.get("eissn")
    pissn = bib.get("pissn")
    issns = sorted({x for x in (eissn, pissn) if x})
    publisher = (bib.get("publisher") or {}).get("name") if isinstance(
        bib.get("publisher"), dict
    ) else None
    languages = bib.get("language", []) or []
    return {
        "canonical_name": bib.get("title"),
        "issns": issns,
        "publisher": publisher,
        "homepage_url": next(
            (link.get("url") for link in (bib.get("link", []) or [])
             if link.get("type") == "homepage"),
            None,
        ),
        "languages": languages,
        "doaj_source_id": rec.get("id"),
        "openalex_source_id": None,
        "discovery_sources": ["DOAJ"],
        "discovery_clusters": [cluster_query],
        "venue_type": "journal",
    }


def normalize_openalex(rec: dict[str, Any], cluster_query: str) -> dict[str, Any]:
    issns = rec.get("issn", []) or []
    if rec.get("issn_l") and rec["issn_l"] not in issns:
        issns = [rec["issn_l"]] + list(issns)
    issns = sorted(set(issns))
    return {
        "canonical_name": rec.get("display_name"),
        "issns": issns,
        "publisher": rec.get("host_organization_name"),
        "homepage_url": rec.get("homepage_url"),
        "languages": [],
        "doaj_source_id": None,
        "openalex_source_id": rec.get("id"),
        "discovery_sources": ["OpenAlex"],
        "discovery_clusters": [cluster_query],
        "venue_type": "journal",
    }


def normalize_cyberleninka(rec: dict[str, Any], cluster_query: str) -> dict[str, Any]:
    return {
        "canonical_name": rec.get("canonical_name"),
        "issns": [],
        "publisher": None,
        "homepage_url": None,
        "languages": ["ru"],
        "doaj_source_id": None,
        "openalex_source_id": None,
        "cyberleninka_source_id": rec.get("canonical_name"),
        "discovery_sources": ["CyberLeninka"],
        "discovery_clusters": [cluster_query],
        "venue_type": "journal",
        "_article_sample_count": rec.get("article_sample_count", 0),
    }


def dedupe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedupe by (ISSN union name). Merge discovery_sources/clusters."""
    by_key: dict[str, dict[str, Any]] = {}
    for r in records:
        keys = []
        for issn in r.get("issns", []) or []:
            keys.append(("issn", issn.strip().upper()))
        keys.append(("name", (r.get("canonical_name") or "").strip().lower()))
        merged = False
        for key in keys:
            if key in by_key:
                existing = by_key[key]
                for fld in ("discovery_sources", "discovery_clusters", "languages"):
                    s = list(dict.fromkeys(
                        (existing.get(fld) or []) + (r.get(fld) or [])
                    ))
                    existing[fld] = s
                # propagate missing fields
                for fld in ("publisher", "homepage_url", "openalex_source_id",
                            "doaj_source_id", "cyberleninka_source_id"):
                    if not existing.get(fld) and r.get(fld):
                        existing[fld] = r[fld]
                # merge ISSNs
                existing["issns"] = sorted(set(
                    (existing.get("issns") or []) + (r.get("issns") or [])
                ))
                merged = True
                break
        if not merged:
            for key in keys:
                by_key.setdefault(key, r)
    seen_names = set()
    out = []
    for r in by_key.values():
        name = (r.get("canonical_name") or "").lower()
        if name in seen_names:
            continue
        seen_names.add(name)
        out.append(r)
    return out


def run(output_dir: Path, top_corpus: int, top_board: int) -> dict[str, Any]:
    venue_dir = output_dir / "venue"
    venue_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: discovery
    log.info("Stage 1 — discovery (DOAJ + OpenAlex + CyberLeninka)")
    raw: list[dict[str, Any]] = []
    for ckey, q in QUERY_CLUSTERS_EN:
        log.info("  EN '%s'", q)
        for r in doaj_search(q, size=15):
            raw.append(normalize_doaj(r, q))
        for r in openalex_search(q, per_page=15):
            raw.append(normalize_openalex(r, q))
        time.sleep(0.2)
    for ckey, q in QUERY_CLUSTERS_RU:
        log.info("  RU CyberLeninka '%s'", q)
        try:
            for r in cl_search(q, sample_articles=40, mode="live")[:8]:
                raw.append(normalize_cyberleninka(r, q))
        except Exception as e:  # noqa: BLE001
            log.warning("CyberLeninka query failed: %s", e)
        # OpenAlex Russian search
        for r in openalex_search(q, per_page=10):
            raw.append(normalize_openalex(r, q))
        time.sleep(0.2)
    log.info("Discovery raw: %d records", len(raw))

    # Stage 2: dedupe
    deduped = dedupe(raw)
    log.info("Stage 2 — dedupe: %d unique candidates", len(deduped))
    save(venue_dir, "01_pool_deduped", deduped)

    # Stage 3: shortlist
    def score(r):
        clusters = len(r.get("discovery_clusters") or [])
        sources = len(r.get("discovery_sources") or [])
        return clusters * 10 + sources * 3
    deduped.sort(key=score, reverse=True)
    shortlist = deduped[:top_corpus]
    log.info("Stage 3 — shortlist: top-%d by discovery breadth", len(shortlist))
    save(venue_dir, "02_shortlist", shortlist)

    # Stage 4: VPKG build with corpus mining for top-N
    log.info("Stage 4 — VenueProfilePackage build with real corpus mining "
             "(top-%d)", top_corpus)
    registry = VenueProfileRegistry(storage_root=str(REPO / ".kairoskopion"))
    log.info("Registry pre-run count: %d", registry.count())
    vpkgs: list[dict[str, Any]] = []
    for i, identity in enumerate(shortlist, 1):
        log.info("  [%d/%d] %s", i, len(shortlist),
                 identity.get("canonical_name", "?")[:60])
        do_board = (i <= top_board) and bool(identity.get("homepage_url"))
        try:
            vpkg = build_venue_profile_package(
                identity=identity,
                fetch_corpus=bool(identity.get("openalex_source_id")),
                fetch_editorial_board=do_board,
                max_works=30,
                board_page_url=(
                    identity.get("homepage_url") if do_board else None
                ),
                registry=registry,
            )
            vpkgs.append({
                "venue_profile_package_id": vpkg.venue_profile_package_id,
                "canonical_name": vpkg.canonical_name,
                "issns": vpkg.issns,
                "publisher": vpkg.publisher,
                "discovery_sources": vpkg.discovery_sources,
                "discovery_clusters": vpkg.discovery_clusters,
                "completeness": vpkg.completeness,
                "confidence": vpkg.confidence,
                "openalex_source_id": vpkg.openalex_source_id,
                "doaj_source_id": vpkg.doaj_source_id,
                "cyberleninka_source_id": vpkg.cyberleninka_source_id,
                "venue_field_position_id": vpkg.venue_field_position_id,
                "published_corpus_hull_id": vpkg.published_corpus_hull_id,
                "editorial_board_cloud_id": vpkg.editorial_board_cloud_id,
                "warnings": vpkg.warnings,
                "unknowns": vpkg.unknowns,
            })
        except Exception as e:  # noqa: BLE001
            log.warning("VPKG build failed for %s: %s",
                        identity.get("canonical_name"), e)
    save(venue_dir, "03_vpkg_summary", vpkgs)

    log.info("Registry post-run count: %d", registry.count())

    summary = {
        "discovery_raw": len(raw),
        "deduped_pool": len(deduped),
        "shortlist": len(shortlist),
        "vpkgs_built": len(vpkgs),
        "vpkgs_with_corpus": sum(
            1 for v in vpkgs
            if v["completeness"].get("PublishedCorpusHull") in ("present", "partial")
        ),
        "vpkgs_with_board": sum(
            1 for v in vpkgs
            if v["completeness"].get("EditorialBoardCloud") in ("present", "partial")
        ),
        "registry_total_after_run": registry.count(),
        "registry_path": str(registry.path),
        "sources_used": ["DOAJ search", "OpenAlex Sources + Works",
                          "CyberLeninka"],
        "sources_deliberately_skipped": [
            "Scopus / WoS / JCR (paid)",
            "eLibrary.ru / ВАК (auth required)",
            "Sci-Hub / Academia / ResearchGate / personal library",
            "Sherpa / Unpaywall (no DOI list at pool stage)",
        ],
    }
    save(venue_dir, "00_summary", summary)
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def save(out: Path, name: str, obj: Any):
    p = out / f"{name}.json"
    p.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info("wrote %s (%d bytes)", p.name, p.stat().st_size)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--top-corpus", type=int, default=15,
                    help="Number of shortlisted venues for full VPKG build "
                         "(default 15)")
    ap.add_argument("--top-board", type=int, default=5,
                    help="Number of top venues to also run EditorialBoardCloud "
                         "on (default 5)")
    args = ap.parse_args()
    run(args.output, args.top_corpus, args.top_board)


if __name__ == "__main__":
    main()
