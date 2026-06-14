"""Mavrinsky golden-run benchmark driver.

Loads .env, takes an article text file path, runs a full Case through
intake → article model → semantic profile → article FPM → scenario →
pathways → venue pool → venue FPM → fit chain (FitAssessment + FPM fit
+ mismatch + rewrite + policy gate) → dossier, and writes every stage
output to a run directory under private_inputs/runs/.

The runner records provider/model/timeout/temperature into the run
report so post-hoc analysis can tell which configuration produced
which result.

Usage:
    python scripts/run_mavrinsky_benchmark.py \\
        --article  private_inputs/mavrinsky_article.txt \\
        --scenario private_inputs/scenarios/mavrinsky.json \\
        --output   private_inputs/runs/mavrinsky_001 \\
        --require-llm

`--require-llm` exits with status 2 if no LLM is configured (no
silent fake success). Omit it for a deterministic-only sanity check.

See benchmarks/README.md for the full workflow.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import traceback
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Project src
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from kairoskopion.api.cases import Case, _case_to_snapshot  # noqa: E402
from kairoskopion.llm.config import LLMConfig  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("benchmark")


def _save(out_dir: Path, name: str, obj: Any):
    p = out_dir / f"{name}.json"
    p.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    log.info("wrote %s (%d bytes)", p.name, p.stat().st_size)


def _safe(stage: str, fn):
    try:
        result = fn()
        log.info("STAGE OK: %s", stage)
        return result, None
    except Exception as exc:
        tb = traceback.format_exc()
        log.error("STAGE FAILED: %s -- %s", stage, exc)
        return None, {"error": str(exc), "traceback": tb}


def run(
    article_path: Path,
    scenario_path: Path | None,
    output_dir: Path,
    require_llm: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = LLMConfig.from_env()
    llm_active = bool(cfg and cfg.api_key)
    log.info("LLM active: %s (model=%s base=%s timeout=%ss)",
             llm_active,
             cfg.model if cfg else None,
             cfg.base_url if cfg else None,
             cfg.timeout_seconds if cfg else None)

    if require_llm and not llm_active:
        log.error(
            "--require-llm was set but no LLM provider is configured. "
            "Set KAIROSKOPION_LLM_API_KEY (and optionally _MODEL, _BASE_URL, "
            "_TIMEOUT_MS) in .env. Refusing to score without LLM."
        )
        raise SystemExit(2)

    article_text = article_path.read_text(encoding="utf-8")
    log.info("Loaded article %s chars=%d", article_path.name, len(article_text))

    scenario_data: dict[str, Any] = {}
    if scenario_path and scenario_path.exists():
        scenario_data = json.loads(scenario_path.read_text(encoding="utf-8"))
        log.info("Loaded scenario %s", scenario_path.name)
    else:
        scenario_data = {
            "goal": "international_visibility",
            "target_indexing": "Scopus",
            "language": "ru",
            "rewrite_depth_allowed": "medium",
        }
        log.info("Using default scenario: %s", scenario_data)

    case = Case(title=f"E2E run: {article_path.stem}")
    log.info("created case_id=%s", case.case_id)

    run_report: dict[str, Any] = {
        "case_id": case.case_id,
        "article_path": str(article_path),
        "article_chars": len(article_text),
        "scenario_path": str(scenario_path) if scenario_path else None,
        "provider": {
            "active": llm_active,
            "model": cfg.model if cfg else None,
            "base_url": cfg.base_url if cfg else None,
            "timeout_seconds": cfg.timeout_seconds if cfg else None,
        },
        "deterministic_only": not llm_active,
        "stages": {},
        "errors": {},
    }

    # 1. Intake
    intake_result, err = _safe("intake_text", lambda: case.intake_text(article_text, input_type="manuscript"))
    if err:
        run_report["errors"]["intake"] = err
    else:
        run_report["stages"]["intake"] = intake_result
    if case.article_model:
        _save(output_dir, "01_article_model", case.article_model.to_dict())
    if case.semantic_profile:
        _save(output_dir, "02_semantic_profile", case.semantic_profile.to_dict())
    if case.article_field_position:
        _save(output_dir, "03_article_field_position", case.article_field_position.to_dict())

    # 2. SourceEvidencePacket (Sprint α B1)
    sep, err = _safe("source_evidence_packet", case.get_source_evidence_packet)
    if err:
        run_report["errors"]["source_evidence_packet"] = err
    else:
        _save(output_dir, "04_source_evidence_packet", sep)

    # 3. ProtectedCorePolicy (Sprint α B3)
    pcp, err = _safe("protected_core_policy_derive", case.get_protected_core_policy)
    if err:
        run_report["errors"]["protected_core_policy"] = err
    else:
        _save(output_dir, "05_protected_core_policy_derived", pcp)

    # 4. Scenario
    sc_result, err = _safe("set_scenario", lambda: case.set_scenario(scenario_data))
    if err:
        run_report["errors"]["scenario"] = err
    else:
        _save(output_dir, "06_scenario", sc_result)

    # 5. Pathways
    paths, err = _safe("get_pathways", case.get_pathways)
    if err:
        run_report["errors"]["pathways"] = err
    else:
        _save(output_dir, "07_pathways", paths)

    # 6. Venue discovery
    vp, err = _safe("discover_venues", case.discover_venues)
    if err:
        run_report["errors"]["discover_venues"] = err
    else:
        _save(output_dir, "08_venue_pool", vp)

    # 7. Pick first candidate and select
    candidates = []
    if case.venue_pool:
        candidates = (
            case.venue_pool.candidates
            if hasattr(case.venue_pool, "candidates") else []
        )
    if candidates:
        first = candidates[0]
        venue_id = (
            first.get("venue_candidate_id")
            if isinstance(first, dict)
            else getattr(first, "venue_candidate_id", "")
        )
        if venue_id:
            sel, err = _safe("select_venue", lambda: case.select_venue(venue_id))
            if err:
                run_report["errors"]["select_venue"] = err
            else:
                _save(output_dir, "09_select_venue_result", sel)
    else:
        log.warning("no venue candidates discovered — skipping select_venue")

    if case.venue_field_position:
        _save(output_dir, "10_venue_field_position", case.venue_field_position.to_dict())
    if case.fit_assessment:
        _save(output_dir, "11_fit_assessment", case.get_fit())
    if case.field_position_fit:
        _save(output_dir, "12_field_position_fit", case.field_position_fit)
    if case.mismatch_map:
        _save(output_dir, "13_mismatch_map", case.get_mismatch_map())
    if case.rewrite_plan:
        _save(output_dir, "14_rewrite_plan", case.rewrite_plan.to_dict())
    if case.policy_blocked_changes:
        _save(output_dir, "14b_policy_blocked", case.policy_blocked_changes)

    # 8. Adaptation aggregate + dossier
    adaptation, err = _safe("adaptation_plan", case.get_adaptation_plan)
    if err:
        run_report["errors"]["adaptation"] = err
    else:
        _save(output_dir, "15_adaptation_plan", adaptation)

    dossier, err = _safe("dossier", case.build_dossier)
    if err:
        run_report["errors"]["dossier"] = err
    else:
        _save(output_dir, "16_dossier", dossier)

    # Full snapshot for replay
    _save(output_dir, "99_full_snapshot", _case_to_snapshot(case))
    _save(output_dir, "00_run_report", run_report)

    log.info("run complete: %s", output_dir)
    return run_report


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--article", type=Path, required=True,
                    help="Path to article text (UTF-8). Kept private; not committed.")
    ap.add_argument("--scenario", type=Path, default=None,
                    help="Optional scenario JSON. Defaults to a reasonable shape.")
    ap.add_argument("--output", type=Path, required=True,
                    help="Run output directory (private_inputs/runs/...).")
    ap.add_argument("--require-llm", action="store_true",
                    help="Exit non-zero if no LLM provider is configured. "
                         "Use this for real benchmark runs; omit for deterministic "
                         "sanity checks.")
    args = ap.parse_args()
    report = run(args.article, args.scenario, args.output,
                 require_llm=args.require_llm)
    n_stages = len(report["stages"])
    n_errs = len(report["errors"])
    print(f"\nSTAGES OK: {n_stages}  ERRORS: {n_errs}")
    if report["errors"]:
        print("Failed:", list(report["errors"].keys()))


if __name__ == "__main__":
    main()
