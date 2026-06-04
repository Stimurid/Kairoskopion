"""CLI for Kairoskopion.

Commands:
    kairoskopion status           — show environment info
    kairoskopion run-fixture      — run fixture pipeline, persist results
    kairoskopion inspect-storage  — show registry and vault contents
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .artifacts import write_pipeline_result_cards
from .persistence import (
    ensure_storage_root,
    list_registries,
    read_registry,
    registries_exist,
    save_pipeline_result,
    storage_root_from_env,
    vault_exists,
)


def _resolve_storage_root(args: argparse.Namespace) -> Path:
    if args.storage_root:
        return Path(args.storage_root)
    return storage_root_from_env()


def cmd_status(args: argparse.Namespace) -> int:
    """Show environment status."""
    root = _resolve_storage_root(args)
    print(f"Kairoskopion v{__version__}")
    print(f"Working directory: {Path.cwd()}")
    print(f"Storage root:      {root.resolve()}")
    print(f"Registries exist:  {registries_exist(root)}")
    print(f"Vault exists:      {vault_exists(root)}")
    if registries_exist(root):
        regs = list_registries(root)
        print(f"Registries:        {', '.join(regs) if regs else '(empty)'}")
    return 0


def cmd_inspect_storage(args: argparse.Namespace) -> int:
    """Show detailed storage contents."""
    root = _resolve_storage_root(args)
    print(f"Kairoskopion storage: {root.resolve()}\n")

    if not registries_exist(root):
        print("No registries found. Run 'kairoskopion run-fixture' first.")
        return 0

    regs = list_registries(root)
    print(f"=== Registries ({len(regs)}) ===\n")
    for name in regs:
        records = read_registry(name, storage_root=root)
        print(f"  {name}: {len(records)} record(s)")
        for r in records[:3]:
            # Show first ID-like field
            for key in (f"{name.rstrip('s')}_id", f"{name}_id", "id",
                        "operation_id", "gate_id", "pipeline_run_id"):
                if key in r:
                    label = r.get("overall_label") or r.get("status") or r.get("lifecycle_status") or ""
                    print(f"    {r[key]}{f'  ({label})' if label else ''}")
                    break

    vault_root = root / "vault"
    if vault_root.exists():
        md_files = sorted(vault_root.rglob("*.md"))
        print(f"\n=== Vault ({len(md_files)} card(s)) ===\n")
        for f in md_files:
            rel = f.relative_to(vault_root)
            print(f"  {rel}")
    else:
        print("\nNo vault found.")

    return 0


def cmd_run_fixture(args: argparse.Namespace) -> int:
    """Run fixture pipeline and persist results."""
    from .pipelines.manuscript_venue_fit import ManuscriptVenueFitPipeline

    root = _resolve_storage_root(args)

    # Locate fixtures
    fixtures_dir = _find_fixtures_dir()
    if not fixtures_dir:
        print("ERROR: Cannot find tests/fixtures/ directory", file=sys.stderr)
        return 1

    ms_path = fixtures_dir / "manuscript_sample.md"
    gl_path = fixtures_dir / "venue_guidelines_sample.md"
    sc_path = fixtures_dir / "submission_scenario_sample.json"

    for p in (ms_path, gl_path, sc_path):
        if not p.exists():
            print(f"ERROR: Fixture not found: {p}", file=sys.stderr)
            return 1

    ms_text = ms_path.read_text(encoding="utf-8")
    gl_text = gl_path.read_text(encoding="utf-8")
    sc_data = json.loads(sc_path.read_text(encoding="utf-8"))

    # Run pipeline
    pipeline = ManuscriptVenueFitPipeline()
    result = pipeline.execute(
        manuscript_text=ms_text,
        venue_guidelines_text=gl_text,
        scenario_data=sc_data,
    )

    # Persist
    reg_paths = save_pipeline_result(result, pipeline, storage_root=root)
    card_paths = write_pipeline_result_cards(result, pipeline, storage_root=root)

    # Summary
    print("--- Pipeline complete ---")
    print(f"ArticleModel:   {result.article.article_model_id if result.article else '?'}")
    print(f"VenueModel:     {result.venue.venue_model_id if result.venue else '?'}")
    print(f"FitAssessment:  {result.fit.fit_assessment_id if result.fit else '?'}")
    print(f"Overall label:  {result.fit.overall_label if result.fit else '?'}")
    print(f"Mismatches:     {len(result.mismatch_map.mismatches) if result.mismatch_map else 0}")
    print(f"Risk items:     {len(result.risk_report.risk_items) if result.risk_report else 0}")
    print(f"Compliance:     {len(result.compliance.checklist_items) if result.compliance else 0} items"
          f" ({len(result.compliance.missing_items) if result.compliance else 0} missing)")
    print(f"Pipeline run:   {pipeline.run.pipeline_run_id}")
    print(f"Pipeline status:{pipeline.run.status}")
    print(f"Registry root:  {(root / 'registries').resolve()}")
    print(f"Vault root:     {(root / 'vault').resolve()}")
    print(f"Registries written: {', '.join(sorted(reg_paths.keys()))}")
    print(f"Cards written:      {', '.join(sorted(card_paths.keys()))}")
    for name, p in sorted(card_paths.items()):
        print(f"  {name}: {p}")
    return 0


def _find_fixtures_dir() -> Path | None:
    """Search for tests/fixtures/ relative to cwd or package location."""
    cwd_fixtures = Path.cwd() / "tests" / "fixtures"
    if cwd_fixtures.is_dir():
        return cwd_fixtures
    pkg_dir = Path(__file__).resolve().parent.parent.parent
    pkg_fixtures = pkg_dir / "tests" / "fixtures"
    if pkg_fixtures.is_dir():
        return pkg_fixtures
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kairoskopion",
        description="Kairoskopion — evidence-first publication-positioning system",
    )
    parser.add_argument(
        "--storage-root",
        default=None,
        help="Override storage root (default: $KAIROSKOPION_STORAGE_ROOT or .kairoskopion/)",
    )

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="Show environment status")
    sub.add_parser("run-fixture", help="Run fixture pipeline and persist results")
    sub.add_parser("inspect-storage", help="Show registry and vault contents")

    args = parser.parse_args(argv)

    commands = {
        "status": cmd_status,
        "run-fixture": cmd_run_fixture,
        "inspect-storage": cmd_inspect_storage,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
