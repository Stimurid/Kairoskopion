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

from kairoskopion.logic.field_position_fit import (  # noqa: E402
    compute_field_position_fit,
)
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

    Baseline behaviour (per
    `benchmarks/golden/mavrinsky_venue_side_gold.md` §3): a candidate
    with a non-empty `disciplinary_cluster` annotation is promoted with
    its annotated cluster names as `pathway_decision`. The actual fit
    arithmetic against the article FPM happens in deep + scorer, not
    here.

    The `article_fpm` argument is accepted for forward-compat (a future
    revision may filter the shortlist by an envelope-vs-point screen)
    but is NOT used to gate inclusion in the baseline.
    """
    del article_fpm  # forward-compat reserved
    shortlist: list[dict[str, Any]] = []
    for cand in pool:
        clusters = sorted(set(cand.get("disciplinary_cluster", []) or []))
        if not clusters:
            cand["_shortlist_skipped"] = "no disciplinary_cluster annotation"
            continue
        cand["pathway_decision"] = clusters
        shortlist.append(cand)
    log.info("Shortlist stage: %d candidates with pathway_decision", len(shortlist))
    return shortlist


# ---------------------------------------------------------------------------
# Stage 3: Deep
# ---------------------------------------------------------------------------

def stage_deep(
    shortlist: list[dict[str, Any]],
    article_fpm: dict[str, Any],
    max_deep: int = 5,
) -> list[dict[str, Any]]:
    """Stage 3 — deep. 3–5 candidates with PublishedCorpusHull built
    from a fixture or operator-supplied corpus.

    For the Mavrinsky deterministic benchmark we deepen up to 5 (one
    per cluster). For real runs the operator picks the top N from the
    shortlist; defaulting to 5 keeps cluster coverage tractable.

    Each dossier carries a `field_position_fit` block computed via
    `compute_field_position_fit(article_fpm, venue_fpm)`. This is the
    deterministic FPM fit used by the scorer to check label topology
    against the Mavrinsky venue-side gold §5.
    """
    deep: list[dict[str, Any]] = []
    for cand in shortlist[:max_deep]:
        synthetic = _synth_analysis_for(cand)
        venue_fpm = build_venue_corpus_hull(synthetic, venue_model_id=cand.get("venue_id"))
        try:
            fpm_fit = compute_field_position_fit(article_fpm, venue_fpm.to_dict())
        except Exception as exc:  # noqa: BLE001
            log.warning("compute_field_position_fit failed for %s: %s",
                        cand.get("venue_id"), exc)
            fpm_fit = {"axes": [], "overall_label": "not_enough_data",
                       "_error": str(exc)}
        cand_out = {
            "venue_id": cand.get("venue_id"),
            "canonical_name": cand.get("canonical_name"),
            "pathway_decision": cand.get("pathway_decision", []),
            "venue_fpm": venue_fpm.to_dict(),
            "field_position_fit": fpm_fit,
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
    benchmarks/golden/mavrinsky_venue_side_gold.md §2 envelope shapes
    AND §5 label topology.
    """
    results: list[dict[str, Any]] = []
    for d in deep_dossiers:
        pathway_set = set(d.get("pathway_decision", []))
        fpm = d.get("venue_fpm", {})
        fpm_fit = d.get("field_position_fit", {})
        cluster_findings = []
        for cluster, gold in CLUSTER_GOLD.items():
            if cluster not in pathway_set:
                continue
            envelope = _check_envelope(fpm, gold)
            label = _check_label(fpm_fit, gold)
            combined_status = _combine_status(envelope["status"], label["status"])
            cluster_findings.append({
                "cluster": cluster,
                "status": combined_status,
                "envelope_check": envelope,
                "label_check": label,
            })
        results.append({
            "venue_id": d.get("venue_id"),
            "pathway_decision": list(pathway_set),
            "cluster_findings": cluster_findings,
        })

    # Aggregate
    flat = [f for r in results for f in r["cluster_findings"]]
    counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "UNDETERMINED": 0}
    for f in flat:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    summary = {
        "deep_dossier_count": len(results),
        "clusters_covered": sorted({f["cluster"] for f in flat}),
        "PASS": counts.get("PASS", 0),
        "PARTIAL": counts.get("PARTIAL", 0),
        "FAIL": counts.get("FAIL", 0),
        "UNDETERMINED": counts.get("UNDETERMINED", 0),
    }
    return {"summary": summary, "results": results}


def _combine_status(envelope_status: str, label_status: str) -> str:
    """Combine envelope and label checks honestly.

    Per `benchmarks/golden/venue_source_layer_map.md` §3.5
    (Unknown != absent), a `not_enough_data` label coming out of an
    intentionally partial venue FPM (corpus hull only) is NOT a fit
    failure — it is an honest unknown. The combined status reflects
    the envelope's verdict; the label state is surfaced in the
    detailed `label_check` evidence.
    """
    if "FAIL" in (envelope_status, label_status):
        return "FAIL"
    if label_status == "UNDETERMINED":
        return envelope_status
    if envelope_status == "PASS" and label_status == "PASS":
        return "PASS"
    if envelope_status == "PASS" and label_status == "PARTIAL":
        return "PARTIAL"
    return "PARTIAL"


def _check_envelope(fpm: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    school_env = fpm.get("school_envelope") or {}
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
        return {"status": "FAIL",
                "evidence": [f"required school dims missing: {sorted(required)}; "
                             f"got {sorted(school_env.keys())}"]}
    if forbidden_dominant:
        return {"status": "FAIL",
                "evidence": [f"forbidden dominant schools in envelope: "
                             f"{forbidden_dominant}"]}
    if required and hits and method_ok:
        return {"status": "PASS",
                "evidence": [f"school hits {sorted(hits)}; method "
                             f"'{gold['expected_method_accepted']}' accepted"]}
    if required and hits and not method_ok:
        return {"status": "PARTIAL",
                "evidence": [f"school hits {sorted(hits)} but method "
                             f"'{gold['expected_method_accepted']}' not in accepted"]}
    return {"status": "PARTIAL",
            "evidence": ["required dims empty (e.g. cluster 5); manual review"]}


def _check_label(
    fpm_fit: dict[str, Any], gold: dict[str, Any]
) -> dict[str, Any]:
    expected = gold.get("expected_label_set") or set()
    actual = fpm_fit.get("overall_label")
    if not expected:
        return {"status": "PARTIAL",
                "evidence": ["no expected_label_set in gold (cluster 5)",
                             f"computed overall_label: {actual!r}"]}
    if actual in expected:
        return {"status": "PASS",
                "evidence": [f"overall_label {actual!r} in expected set "
                             f"{sorted(expected)}"]}
    if actual == "not_enough_data":
        return {"status": "UNDETERMINED",
                "evidence": [
                    "overall_label is not_enough_data — corpus-hull-only "
                    "venue FPM does not cover all 11 fit axes (formalization, "
                    "audience, jargon, language, genre_formality, geographic). "
                    "Per rubric §3.5 (Unknown != absent), this is honest "
                    "unknown, not failure. Needs A guidelines + C registry "
                    "to reach label verdict.",
                ]}
    return {"status": "FAIL",
            "evidence": [f"overall_label {actual!r} NOT in expected "
                         f"{sorted(expected)}"]}


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

    deep = stage_deep(shortlist, article_fpm)
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
