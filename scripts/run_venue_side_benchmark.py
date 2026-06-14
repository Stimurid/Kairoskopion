"""Venue-side benchmark harness skeleton.

Mirrors `run_mavrinsky_benchmark.py` on the venue side. Defines the
future three-stage run shape (pool → shortlist → deep) and, in the
current baseline, accepts synthetic / fixture inputs.

Scope of THIS baseline:

- No live external calls by default. `--allow-live` flag opt-in only.
- Pool stage and shortlist stage operate on a fixture pool of venue
  records or on whatever is in the local venue registry.
- Deep stage demonstrates `corpus_hull_builder` on a fixture corpus
  for each picked venue.
- Outputs go under `private_inputs/runs/<id>/venue/` (gitignored).
- Scorecard is computed against
  `benchmarks/golden/mavrinsky_venue_side_gold.md` §2 envelope
  ranges. Score JSON shape mirrors the article-side scorecard.

This file is intentionally a **skeleton**. The shape, contract, and
allowlist policy are stable; live adapter integration lands in
follow-up sprints (EditorialBoardAdapter, ВАК/РИНЦ, full-text).

Usage:

    python scripts/run_venue_side_benchmark.py \\
        --article-fpm  private_inputs/runs/mavrinsky_006/03_article_field_position.json \\
        --output       private_inputs/runs/venue_001 \\
        --fixture-pool private_inputs/fixtures/venue_pool_synthetic.json

By default (no `--allow-live`), every adapter falls back to fixture
mode. The harness fails loudly if both the live flag and the fixture
are missing — no silent fake success.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from kairoskopion.schema import FieldPositionModel  # noqa: E402
from kairoskopion.services.corpus_analyzer import (  # noqa: E402
    CorpusAnalysisResult,
    CorpusPattern,
)
from kairoskopion.services.corpus_hull_builder import (  # noqa: E402
    build_venue_corpus_hull,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("venue-bench")


# ---------------------------------------------------------------------------
# Gold expectations (mirror of benchmarks/golden/mavrinsky_venue_side_gold.md §2)
# ---------------------------------------------------------------------------

CLUSTER_GOLD = {
    "continental_media_philosophy": {
        "school_envelope_required_dims": {
            "Deleuze_Guattari", "Foucault", "Agamben",
        },
        "school_envelope_forbidden_dominant": {
            "HCI_dark_patterns", "Latour_ANT",
        },
        "expected_method_accepted": "theoretical",
        "expected_label_set": {"possible", "possible_but_costly"},
    },
    "philosophy_of_technology": {
        "school_envelope_required_dims": {
            "Simondon", "Stiegler", "Yuk_Hui",
        },
        "school_envelope_forbidden_dominant": {"HCI_dark_patterns"},
        "expected_method_accepted": "theoretical",
        "expected_label_set": {"possible_but_costly", "adjacent_with_reframe"},
    },
    "STS_platform_studies": {
        "school_envelope_required_dims": {"Latour_ANT"},
        "school_envelope_forbidden_dominant": set(),
        "expected_method_accepted": "case_study",
        "expected_label_set": {"adjacent_with_reframe", "high_risk"},
    },
    "HCI_design_theory": {
        "school_envelope_required_dims": {"HCI_affordances"},
        "school_envelope_forbidden_dominant": {"Deleuze_Guattari", "Agamben"},
        "expected_method_accepted": "experimental",
        "expected_label_set": {"poor_fit", "high_core_risk"},
    },
    "RU_philosophy_regime": {
        "school_envelope_required_dims": set(),  # varies per journal
        "school_envelope_forbidden_dominant": set(),
        "expected_method_accepted": "theoretical",
        "expected_label_set": {"possible", "possible_but_costly",
                                "adjacent_with_reframe", "high_risk"},
    },
}


# ---------------------------------------------------------------------------
# Stage 1: Pool
# ---------------------------------------------------------------------------

def stage_pool(
    fixture_pool: Path | None,
    allow_live: bool,
) -> list[dict[str, Any]]:
    """Stage 1 — pool. 30–80 candidates at V1+V2 (identity + scope claim).

    Current baseline: read from fixture JSON if provided. Live discovery
    is deferred to follow-up sprints; --allow-live flag is accepted for
    forward-compat but currently treated the same as fixture mode with
    a warning.
    """
    if allow_live:
        log.warning(
            "--allow-live is set but live venue pool discovery is not "
            "implemented in this baseline. Falling back to fixture pool."
        )
    if fixture_pool is None or not fixture_pool.exists():
        log.error(
            "No fixture pool supplied and live discovery is not "
            "implemented yet. Set --fixture-pool or wait for the live "
            "adapter sprint."
        )
        raise SystemExit(2)
    log.info("Loading fixture pool from %s", fixture_pool)
    raw = json.loads(fixture_pool.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Fixture pool must be a JSON array of records")
    log.info("Pool stage: %d candidates", len(raw))
    return raw


# ---------------------------------------------------------------------------
# Stage 2: Shortlist
# ---------------------------------------------------------------------------

def stage_shortlist(
    pool: list[dict[str, Any]],
    article_fpm: dict[str, Any],
) -> list[dict[str, Any]]:
    """Stage 2 — shortlist. 8–12 candidates with pathway_decision.

    Current baseline: a candidate makes the shortlist iff its
    `disciplinary_cluster` field intersects the article's
    `discipline_vector` keys. This is intentionally coarse — the full
    pathway mapping is article_field_positioner work plus per-cluster
    light envelope check, deferred to a follow-up sprint.
    """
    article_dims = set(article_fpm.get("discipline_vector", {}).keys()) | \
                   set((article_fpm.get("subdiscipline_address") or {}).values())

    shortlist: list[dict[str, Any]] = []
    for cand in pool:
        clusters = set(cand.get("disciplinary_cluster", []) or [])
        if not clusters:
            cand["_shortlist_skipped"] = "no disciplinary_cluster annotation"
            continue
        # Coarse intersection on cluster name vs FPM dimension
        if any(
            any(token in d.lower() for token in (c.lower(),))
            for c in clusters
            for d in article_dims
        ) or any(c.lower() in str(article_fpm).lower() for c in clusters):
            cand["pathway_decision"] = sorted(clusters)
            shortlist.append(cand)
    log.info("Shortlist stage: %d candidates with pathway_decision", len(shortlist))
    return shortlist


# ---------------------------------------------------------------------------
# Stage 3: Deep
# ---------------------------------------------------------------------------

def stage_deep(
    shortlist: list[dict[str, Any]],
    max_deep: int = 3,
) -> list[dict[str, Any]]:
    """Stage 3 — deep. 3–5 candidates with PublishedCorpusHull built
    from a fixture or operator-supplied corpus."""
    deep: list[dict[str, Any]] = []
    for cand in shortlist[:max_deep]:
        synthetic = _synth_analysis_for(cand)
        fpm = build_venue_corpus_hull(synthetic, venue_model_id=cand.get("venue_id"))
        cand_out = {
            "venue_id": cand.get("venue_id"),
            "canonical_name": cand.get("canonical_name"),
            "pathway_decision": cand.get("pathway_decision", []),
            "venue_fpm": fpm.to_dict(),
        }
        deep.append(cand_out)
    log.info("Deep stage: %d dossiers built", len(deep))
    return deep


def _synth_analysis_for(cand: dict[str, Any]) -> CorpusAnalysisResult:
    """Synthesise a corpus analysis from fixture pool annotations.

    Baseline only: when we have no live corpus, the fixture pool may
    include `fixture_corpus_summary` field describing the venue's
    expected corpus topology; we materialise that into a
    CorpusAnalysisResult so the hull builder gets something to work
    with."""
    summary = cand.get("fixture_corpus_summary", {})
    n = summary.get("corpus_size", 0)
    return CorpusAnalysisResult(
        venue_model_id=cand.get("venue_id"),
        corpus_size=n,
        method_patterns=[
            CorpusPattern("method", k, float(v), "medium", [])
            for k, v in (summary.get("method_distribution") or {}).items()
        ],
        school_patterns=[
            CorpusPattern("school", k, float(v), "medium", [])
            for k, v in (summary.get("school_distribution") or {}).items()
        ],
        genre_summary=summary.get("genre_distribution", {}) or {},
        citation_stats=summary.get("citation_stats", {}) or {},
        abstract_patterns=[],
        warnings=summary.get("warnings", []) or [],
        confidence=summary.get("confidence", "low"),
        unknowns=summary.get("unknowns", []) or [],
    )


# ---------------------------------------------------------------------------
# Scoring vs gold
# ---------------------------------------------------------------------------

def score_against_gold(
    deep_dossiers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score the deep dossiers against
    benchmarks/golden/mavrinsky_venue_side_gold.md §2 envelope shapes.
    """
    results: list[dict[str, Any]] = []
    for d in deep_dossiers:
        pathway_set = set(d.get("pathway_decision", []))
        fpm = d.get("venue_fpm", {})
        cluster_findings = []
        for cluster, gold in CLUSTER_GOLD.items():
            if cluster not in pathway_set:
                continue
            check = _check_cluster(fpm, gold)
            cluster_findings.append({
                "cluster": cluster,
                "status": check["status"],
                "evidence": check["evidence"],
            })
        results.append({
            "venue_id": d.get("venue_id"),
            "pathway_decision": list(pathway_set),
            "cluster_findings": cluster_findings,
        })
    summary = {
        "deep_dossier_count": len(results),
        "clusters_covered": sorted({
            f["cluster"]
            for r in results
            for f in r["cluster_findings"]
        }),
    }
    return {"summary": summary, "results": results}


def _check_cluster(fpm: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    school_env = fpm.get("school_envelope") or {}
    evidence: list[str] = []

    required = gold["school_envelope_required_dims"]
    forbidden = gold["school_envelope_forbidden_dominant"]
    hits = required & set(school_env.keys())
    forbidden_dominant = [
        k for k in school_env
        if k in forbidden and school_env[k][1] >= 0.4
    ]

    method_accepted = (
        fpm.get("method_stance", {}).get("accepted_method_families") or []
    )
    method_ok = gold["expected_method_accepted"] in method_accepted

    if required and not hits:
        status = "FAIL"
        evidence.append(
            f"required school dims missing: {sorted(required)}; "
            f"got {sorted(school_env.keys())}"
        )
    elif forbidden_dominant:
        status = "FAIL"
        evidence.append(
            f"forbidden dominant schools in envelope: {forbidden_dominant}"
        )
    elif required and hits and method_ok:
        status = "PASS"
        evidence.append(
            f"school hits {sorted(hits)}; method '{gold['expected_method_accepted']}' "
            "accepted"
        )
    elif required and hits and not method_ok:
        status = "PARTIAL"
        evidence.append(
            f"school hits {sorted(hits)} but method "
            f"'{gold['expected_method_accepted']}' not in accepted"
        )
    else:
        status = "PARTIAL"
        evidence.append("required dims empty (e.g. cluster 5); manual review")
    return {"status": status, "evidence": evidence}


# ---------------------------------------------------------------------------
# Run report writer
# ---------------------------------------------------------------------------

def _save(out_dir: Path, name: str, obj: Any):
    p = out_dir / f"{name}.json"
    p.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info("wrote %s (%d bytes)", p.name, p.stat().st_size)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(
    article_fpm_path: Path,
    output_dir: Path,
    fixture_pool: Path | None,
    allow_live: bool,
) -> dict[str, Any]:
    venue_dir = output_dir / "venue"
    venue_dir.mkdir(parents=True, exist_ok=True)

    article_fpm = json.loads(article_fpm_path.read_text(encoding="utf-8"))
    log.info("Article FPM loaded: %s", article_fpm.get("entity_id"))

    pool = stage_pool(fixture_pool, allow_live)
    _save(venue_dir, "01_pool", pool)

    shortlist = stage_shortlist(pool, article_fpm)
    _save(venue_dir, "02_shortlist", shortlist)

    deep = stage_deep(shortlist)
    _save(venue_dir, "03_deep_dossiers", deep)

    scorecard = score_against_gold(deep)
    _save(venue_dir, "04_scorecard", scorecard)

    log.info(
        "Run complete. Clusters covered: %s",
        scorecard["summary"]["clusters_covered"],
    )
    return scorecard


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--article-fpm", type=Path, required=True,
                    help="Path to article FieldPositionModel JSON "
                         "(typically the 03_article_field_position.json "
                         "from a Mavrinsky run).")
    ap.add_argument("--output", type=Path, required=True,
                    help="Run output directory under private_inputs/runs/.")
    ap.add_argument("--fixture-pool", type=Path, default=None,
                    help="Path to a JSON fixture pool. Required while "
                         "live discovery is not implemented.")
    ap.add_argument("--allow-live", action="store_true",
                    help="Forward-compat flag for live discovery. "
                         "Currently warns and falls back to fixture.")
    args = ap.parse_args()
    scorecard = run(
        args.article_fpm,
        args.output,
        args.fixture_pool,
        args.allow_live,
    )
    print("\n=== SCORECARD ===")
    print(json.dumps(scorecard["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
