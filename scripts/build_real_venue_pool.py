"""Build a bounded real Mavrinsky venue pool from existing free public
adapters. NO new architecture, NO EditorialBoardCloud, NO ВАК/РИНЦ, NO
shadow/full-text resolvers, NO paid sources, NO LLM.

Sources actually queried:
  - DOAJ public search API (open access journals, free, no auth)
  - OpenAlex Sources API (works metadata venue endpoint, free, no auth)

Pool is built by fanning out subject queries across the Mavrinsky
article's likely discipline clusters and deduplicating by ISSN /
canonical name. The resulting pool is written to an ignored run
directory under `private_inputs/runs/<id>/venue/`. NOT committed.

Usage:
    python scripts/build_real_venue_pool.py \\
        --output private_inputs/runs/mavrinsky_real_venue_pool_001 \\
        [--no-network]
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("realpool")


DOAJ_BASE = "https://doaj.org/api/search/journals"
OPENALEX_BASE = "https://api.openalex.org/sources"


# Mavrinsky-side query clusters. Each is one subject query string that
# the source APIs can handle. Note: DOAJ search ranks by full-text
# relevance not by topic match — so these are pool-feeders, not
# claims of fit. Fit comes from the screening pass below.
QUERY_CLUSTERS = [
    # International / English
    ("philosophy_of_technology", "philosophy of technology"),
    ("philosophy_of_technology_2", "philosophy technology"),
    ("continental_philosophy", "continental philosophy"),
    ("media_philosophy", "media philosophy"),
    ("media_studies", "media theory"),
    ("interface_studies", "interface theory"),
    ("digital_culture", "digital culture"),
    ("STS", "science and technology studies"),
    ("STS_2", "social studies of science"),
    ("AI_ethics", "ethics of technology"),
    ("digital_humanities", "digital humanities"),
    ("HCI_theory", "human-computer interaction"),
    # Russian-language / regional
    ("ru_philosophy", "русская философия"),
    ("ru_phenomenology", "феноменология"),
    ("ru_methodology", "методология"),
]


def fetch_json(url: str, timeout: int = 15) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Kairoskopion/0.2 (research; contact via repo)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log.warning("HTTP %d on %s", e.code, url)
    except (urllib.error.URLError, TimeoutError) as e:
        log.warning("network error: %s on %s", type(e).__name__, url)
    except Exception as e:  # noqa: BLE001
        log.warning("unexpected: %s on %s", type(e).__name__, url)
    return None


def query_doaj(q: str, page_size: int = 25) -> list[dict[str, Any]]:
    url = f"{DOAJ_BASE}/{urllib.parse.quote(q)}?pageSize={page_size}"
    data = fetch_json(url)
    if not data:
        return []
    return data.get("results", []) or []


def query_openalex(q: str, per_page: int = 25) -> list[dict[str, Any]]:
    url = f"{OPENALEX_BASE}?search={urllib.parse.quote(q)}&per_page={per_page}"
    data = fetch_json(url)
    if not data:
        return []
    return data.get("results", []) or []


def normalize_doaj_record(rec: dict[str, Any], cluster_query: str) -> dict[str, Any]:
    bib = rec.get("bibjson", {}) or {}
    title = bib.get("title")
    eissn = bib.get("eissn")
    pissn = bib.get("pissn")
    issns = sorted({x for x in (eissn, pissn) if x})
    publisher = (bib.get("publisher") or {}).get("name") if isinstance(bib.get("publisher"), dict) else None
    keywords = bib.get("keywords", []) or []
    subjects = [s.get("term") for s in (bib.get("subject", []) or []) if isinstance(s, dict)]
    languages = bib.get("language", []) or []
    apc = bib.get("apc", {}) or {}
    apc_currency = (apc.get("max", [{}])[0].get("currency") if apc.get("max") else None) if isinstance(apc.get("max"), list) else None
    apc_amount = (apc.get("max", [{}])[0].get("price") if apc.get("max") else None) if isinstance(apc.get("max"), list) else None
    return {
        "source_id": rec.get("id"),
        "source": "DOAJ",
        "canonical_name": title,
        "issns": issns,
        "publisher": publisher,
        "homepage": next(
            (link.get("url") for link in (bib.get("link", []) or [])
             if link.get("type") == "homepage"),
            None,
        ),
        "subjects": subjects,
        "keywords": keywords,
        "languages": languages,
        "oa_status": "doaj_listed",
        "apc_required": bool(apc),
        "apc_amount": apc_amount,
        "apc_currency": apc_currency,
        "ranking_evidence_status": "external_claim_doaj",
        "discovery_cluster_query": cluster_query,
        "raw_keys_available": sorted(bib.keys()),
        "unknowns": [],
    }


def normalize_openalex_record(rec: dict[str, Any], cluster_query: str) -> dict[str, Any]:
    issns = rec.get("issn", []) or []
    if rec.get("issn_l") and rec["issn_l"] not in issns:
        issns = [rec["issn_l"]] + list(issns)
    issns = sorted(set(issns))
    return {
        "source_id": rec.get("id"),
        "source": "OpenAlex",
        "canonical_name": rec.get("display_name"),
        "issns": issns,
        "publisher": rec.get("host_organization_name"),
        "homepage": rec.get("homepage_url"),
        "subjects": [c.get("display_name") for c in (rec.get("concepts", []) or [])
                     if isinstance(c, dict)],
        "keywords": [],
        "languages": [],
        "oa_status": "yes" if rec.get("is_oa") else (
            "no" if rec.get("is_oa") is False else "unknown"
        ),
        "apc_required": rec.get("apc_usd") is not None,
        "apc_amount": rec.get("apc_usd"),
        "apc_currency": "USD" if rec.get("apc_usd") else None,
        "ranking_evidence_status": "metadata_api_openalex",
        "discovery_cluster_query": cluster_query,
        "works_count": rec.get("works_count"),
        "cited_by_count": rec.get("cited_by_count"),
        "raw_keys_available": sorted(k for k in rec.keys() if not k.startswith("_")),
        "unknowns": [],
    }


def dedupe_by_issn_or_name(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for r in records:
        keys = []
        for i in r.get("issns", []) or []:
            keys.append(("issn", i))
        keys.append(("name", (r.get("canonical_name") or "").strip().lower()))
        merged = False
        for key in keys:
            if key in by_key:
                existing = by_key[key]
                # merge: keep first, but record alt source
                alt = existing.setdefault("alt_sources", [])
                alt.append({"source": r["source"], "source_id": r["source_id"]})
                # collect discovery cluster fan-out
                clusters = existing.setdefault("discovery_clusters",
                                                [existing.get("discovery_cluster_query")])
                if r.get("discovery_cluster_query") not in clusters:
                    clusters.append(r["discovery_cluster_query"])
                # merge subjects / keywords
                for fld in ("subjects", "keywords", "languages"):
                    s = set(existing.get(fld) or [])
                    s.update(r.get(fld) or [])
                    existing[fld] = sorted(s)
                merged = True
                break
        if merged:
            continue
        # New record: index under all its keys
        for key in keys:
            by_key.setdefault(key, r)
        r.setdefault("discovery_clusters", [r.get("discovery_cluster_query")])
    seen_ids = set()
    out = []
    for r in by_key.values():
        sid = (r.get("source"), r.get("source_id"))
        if sid in seen_ids:
            continue
        seen_ids.add(sid)
        out.append(r)
    return out


def screen_to_shortlist(
    pool: list[dict[str, Any]], target: int = 12
) -> list[dict[str, Any]]:
    """Score candidates by discipline-cluster proximity ONLY.

    The score is *the count of distinct cluster queries* that pulled
    this candidate. No school fit, no method fit, no fabricated subject
    tags. Per source layer map §3.1: official scope is `official_claim`,
    not `corpus_observation`. We are screening on discovery breadth,
    not on content fit.
    """
    scored = []
    for r in pool:
        clusters = set(r.get("discovery_clusters") or [])
        clusters.discard(None)
        score = len(clusters)
        # very small bonus: relevant subject term in DOAJ subject list
        terms = {
            t.lower()
            for t in (r.get("subjects") or []) + (r.get("keywords") or [])
            if isinstance(t, str)
        }
        keywords_hit = sum(
            1 for w in (
                "philosophy", "technology", "media", "science",
                "studies", "humanities", "interface", "digital",
                "continental", "phenomenology", "методология",
                "философия",
            ) if any(w.lower() in t for t in terms)
        )
        scored.append((score * 10 + keywords_hit, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    short = [r for _, r in scored[:target]]
    log.info("Shortlist: %d candidates (out of %d pool)", len(short), len(pool))
    return short


def deep_lite(
    shortlist: list[dict[str, Any]], top_n: int = 5
) -> list[dict[str, Any]]:
    """Deep-lite expansion: for top-N from shortlist, try to fetch
    works metadata from OpenAlex (free, no auth) as a corpus-hint
    layer. NOT a full corpus hull. NOT EditorialBoardCloud."""
    deep: list[dict[str, Any]] = []
    for r in shortlist[:top_n]:
        out = dict(r)
        out["deep_lite_layer"] = {}
        # OpenAlex source ID is ideal; otherwise we have to skip
        oa_id = None
        if r.get("source") == "OpenAlex":
            oa_id = r["source_id"]
        elif r.get("alt_sources"):
            for alt in r["alt_sources"]:
                if alt.get("source") == "OpenAlex":
                    oa_id = alt["source_id"]
                    break
        if not oa_id:
            # Lookup by ISSN
            for issn in r.get("issns", []) or []:
                resp = fetch_json(f"{OPENALEX_BASE}/issn:{issn}")
                if resp and resp.get("id"):
                    oa_id = resp["id"]
                    break
        if not oa_id:
            out["deep_lite_layer"]["status"] = "no_openalex_id"
            out["deep_lite_layer"]["unknowns"] = [
                "no OpenAlex source id; corpus hint layer not built"
            ]
            deep.append(out)
            continue

        # Fetch latest 15 works (corpus hint only — titles + concepts +
        # authorships counts; NOT full text, NOT references, NOT
        # editor biographies, NOT abstracts beyond OpenAlex's free tier)
        works_url = (
            f"https://api.openalex.org/works?filter=primary_location.source.id:{oa_id}"
            f"&per_page=15&sort=publication_year:desc"
        )
        works_resp = fetch_json(works_url)
        if not works_resp:
            out["deep_lite_layer"]["status"] = "openalex_works_fetch_failed"
            deep.append(out)
            continue
        works = works_resp.get("results", []) or []
        titles = [w.get("title") for w in works if w.get("title")]
        years = [w.get("publication_year") for w in works
                 if w.get("publication_year")]
        concepts: dict[str, int] = {}
        for w in works:
            for c in (w.get("concepts") or []):
                name = c.get("display_name")
                if name:
                    concepts[name] = concepts.get(name, 0) + 1
        top_concepts = sorted(concepts.items(), key=lambda x: x[1],
                              reverse=True)[:15]
        out["deep_lite_layer"] = {
            "status": "openalex_corpus_hint",
            "works_fetched": len(works),
            "title_sample": titles[:5],
            "year_range": [min(years), max(years)] if years else None,
            "top_concepts": [{"name": n, "count": c} for n, c in top_concepts],
            "warnings": [
                "Corpus hint is metadata only (titles + concepts + years). "
                "Not full corpus mining. Not EditorialBoardCloud. Not "
                "PublishedCorpusHull. Concept frequencies are OpenAlex "
                "machine-tagged, not corpus-derived theory shoulders."
            ],
            "unknowns": [
                "no abstracts at this tier",
                "no references / citations",
                "no editorial board",
                "no formal author guidelines",
            ],
        }
        deep.append(out)
        time.sleep(0.3)  # be polite to OpenAlex
    log.info("Deep-lite: %d candidates expanded", len(deep))
    return deep


def run(output_dir: Path, no_network: bool) -> dict[str, Any]:
    venue_dir = output_dir / "venue"
    venue_dir.mkdir(parents=True, exist_ok=True)

    if no_network:
        log.error(
            "--no-network was set but this script's pool stage requires "
            "DOAJ and OpenAlex live access. Aborting."
        )
        raise SystemExit(2)

    log.info("Pool stage: fanning out %d cluster queries", len(QUERY_CLUSTERS))
    pool_raw: list[dict[str, Any]] = []
    for cluster_key, q in QUERY_CLUSTERS:
        log.info("  DOAJ '%s'", q)
        for r in query_doaj(q, page_size=15):
            pool_raw.append(normalize_doaj_record(r, q))
        log.info("  OpenAlex '%s'", q)
        for r in query_openalex(q, per_page=15):
            pool_raw.append(normalize_openalex_record(r, q))
        time.sleep(0.2)

    log.info("Pool raw: %d records before dedupe", len(pool_raw))
    pool = dedupe_by_issn_or_name(pool_raw)
    log.info("Pool deduped: %d candidates", len(pool))

    save(venue_dir, "01_pool_raw", pool_raw)
    save(venue_dir, "02_pool_deduped", pool)

    shortlist = screen_to_shortlist(pool, target=12)
    save(venue_dir, "03_shortlist", shortlist)

    deep = deep_lite(shortlist, top_n=5)
    save(venue_dir, "04_deep_lite", deep)

    summary = {
        "pool_raw_count": len(pool_raw),
        "pool_deduped_count": len(pool),
        "shortlist_count": len(shortlist),
        "deep_lite_count": len(deep),
        "sources_used": ["DOAJ search", "OpenAlex Sources", "OpenAlex Works (deep-lite only)"],
        "sources_deliberately_skipped": [
            "ВАК / РИНЦ / КиберЛенинка",
            "Scopus / WoS / JCR",
            "EditorialBoardCloud live scraping",
            "Sherpa / Unpaywall (no DOI list at pool stage)",
            "Crossref (covered by OpenAlex)",
            "Sci-Hub / Academia / ResearchGate / personal library",
        ],
        "policy_flags": {
            "no_LLM_calls": True,
            "no_fabricated_indexing": True,
            "no_fabricated_scope_to_fit_promotion": True,
            "official_scope_marked_official_claim_only": True,
            "OpenAlex_concept_tags_marked_machine_tagged": True,
        },
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
    ap.add_argument("--no-network", action="store_true",
                    help="Refuse to run if live access would be needed. "
                         "Currently this means the script refuses to run.")
    args = ap.parse_args()
    run(args.output, args.no_network)


if __name__ == "__main__":
    main()
