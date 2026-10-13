"""Run explicit local P06/P07 input bundles; never submit or synthesize evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from kairoskopion.kairon_provider.publication_runner import run_import, save_json


def run_controls(input_root: Path, output_root: Path, catalog_root: Path,
                 *, resume: bool = False, allow_fixtures: bool = False) -> dict:
    results = []
    for article in ("P06", "P07"):
        root = input_root / article
        try:
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            if manifest["spec"]["article_id"] != article:
                raise ValueError("control_article_identity_mismatch")
            result = run_import(manifest_path=root / "manifest.json",
                                approval_path=root / "approval.json", input_root=root,
                                output_root=output_root / article, catalog_root=catalog_root,
                                resume=resume, allow_fixtures=allow_fixtures)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result = {"status": "BLOCKED_NEEDS_ADAPTER", "blockers": [str(exc)],
                      "finalization_request": None, "fixture_gate_request": None,
                      "live_acceptance": "NOT_CLAIMED", "external_submit_events": []}
            save_json(output_root / article / "current.json", result)
        results.append({"article": article, "stage": result.get("factory_phase", "INPUT_IMPORT"),
                        "status": result["status"], "blockers": result["blockers"],
                        "execution_id": result.get("execution_id"),
                        "evidence": str(output_root / article / result["execution_id"] / "result.json")
                        if result.get("execution_id") else None})
    receipt = {"schema_version": "publication-controls-v1", "controls": results,
               "live_acceptance": "NOT_CLAIMED", "external_submit_events": []}
    save_json(output_root / "controls-receipt.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("input-root", "output-root", "catalog-root"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-fixtures", action="store_true")
    args = parser.parse_args(argv)
    receipt = run_controls(args.input_root, args.output_root, args.catalog_root,
                           resume=args.resume, allow_fixtures=args.allow_fixtures)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if all(r["status"] in {"DRY_RUN_COMPLETE", "FIXTURE_DRY_RUN_COMPLETE"}
                    for r in receipt["controls"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
