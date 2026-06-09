"""CLI for Kairoskopion.

Commands:
    kairoskopion status           — show environment info
    kairoskopion run-fixture      — run fixture pipeline, persist results
    kairoskopion run-local        — run pipeline on user-provided files
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


_SUPPORTED_TEXT_EXTENSIONS = {".md", ".txt", ".json", ".html"}


def _validate_input_file(path: Path, label: str) -> str | None:
    """Validate an input file exists and has a supported extension.

    Returns an error message string, or None if valid.
    """
    if not path.exists():
        return f"{label}: file not found: {path}"
    if not path.is_file():
        return f"{label}: not a file: {path}"
    if path.suffix.lower() not in _SUPPORTED_TEXT_EXTENSIONS:
        return (
            f"{label}: unsupported extension '{path.suffix}'. "
            f"Supported: {', '.join(sorted(_SUPPORTED_TEXT_EXTENSIONS))}"
        )
    return None


def cmd_run_local(args: argparse.Namespace) -> int:
    """Run pipeline on user-provided local files."""
    from .adapters.source_intake import SourceRole, register_local_source
    from .pipelines.manuscript_venue_fit import ManuscriptVenueFitPipeline

    root = _resolve_storage_root(args)

    ms_path = Path(args.manuscript)
    vg_path = Path(args.venue_guidelines)
    sc_path = Path(args.scenario)

    # Validate all files before doing any work
    errors = []
    for path, label in [
        (ms_path, "manuscript"),
        (vg_path, "venue-guidelines"),
        (sc_path, "scenario"),
    ]:
        err = _validate_input_file(path, label)
        if err:
            errors.append(err)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Register sources
    ms_snapshot, ms_text = register_local_source(
        ms_path, role=SourceRole.ARTICLE_INPUT,
    )
    if not ms_text:
        print(f"ERROR: manuscript: could not read text from {ms_path}", file=sys.stderr)
        return 1

    vg_snapshot, vg_text = register_local_source(
        vg_path, role=SourceRole.VENUE_GUIDELINES,
    )
    if not vg_text:
        print(f"ERROR: venue-guidelines: could not read text from {vg_path}", file=sys.stderr)
        return 1

    sc_snapshot, sc_raw = register_local_source(
        sc_path, role=SourceRole.SUBMISSION_INFO,
    )
    if not sc_raw:
        print(f"ERROR: scenario: could not read text from {sc_path}", file=sys.stderr)
        return 1

    try:
        sc_data = json.loads(sc_raw)
    except json.JSONDecodeError as exc:
        print(f"ERROR: scenario: invalid JSON in {sc_path}: {exc}", file=sys.stderr)
        return 1

    # Run pipeline with real source refs
    pipeline = ManuscriptVenueFitPipeline()
    result = pipeline.execute(
        manuscript_text=ms_text,
        venue_guidelines_text=vg_text,
        scenario_data=sc_data,
        manuscript_source_ref=ms_snapshot.source_id,
        venue_source_ref=vg_snapshot.source_id,
    )

    # Persist
    reg_paths = save_pipeline_result(result, pipeline, storage_root=root)

    # Persist source snapshots to registries
    from . import registry as reg
    from .persistence import ensure_registry_root

    reg_root = ensure_registry_root(root)
    for snapshot in (ms_snapshot, vg_snapshot, sc_snapshot):
        reg.append("source_snapshots", snapshot.to_dict(), base_dir=reg_root)

    card_paths = write_pipeline_result_cards(result, pipeline, storage_root=root)

    # Summary
    print("--- Pipeline complete (local files) ---")
    print(f"Manuscript:     {ms_path}")
    print(f"Venue:          {vg_path}")
    print(f"Scenario:       {sc_path}")
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
    print(f"Sources:        {ms_snapshot.snapshot_id}, {vg_snapshot.snapshot_id}, {sc_snapshot.snapshot_id}")
    print(f"Registry root:  {(root / 'registries').resolve()}")
    print(f"Vault root:     {(root / 'vault').resolve()}")
    print(f"Registries written: {', '.join(sorted(reg_paths.keys()))}")
    print(f"Cards written:      {', '.join(sorted(card_paths.keys()))}")
    for name, p in sorted(card_paths.items()):
        print(f"  {name}: {p}")
    return 0


def cmd_adapters_smoke(args: argparse.Namespace) -> int:
    """Run mock adapters, save results, print summary."""
    from .adapters.bridge import (
        convert_adapter_record_to_evidence_item,
        convert_adapter_result_to_source_snapshot,
    )
    from .adapters.crossref import lookup_doi_mock, search_works_mock as crossref_search
    from .adapters.openalex import search_works_mock as openalex_search
    from .adapters.opencitations import get_citations_mock
    from .persistence import save_adapter_result

    root = _resolve_storage_root(args)

    results = []
    oalex = openalex_search("consciousness hard problem")
    results.append(("openalex:search", oalex))

    cref_search = crossref_search("consciousness philosophy")
    results.append(("crossref:search", cref_search))

    cref_doi = lookup_doi_mock("10.2307/2183914")
    results.append(("crossref:doi", cref_doi))

    ocit = get_citations_mock("10.1126/science.1234567", direction="references")
    results.append(("opencitations:refs", ocit))

    # Persist and bridge
    from . import registry as reg
    from .persistence import ensure_registry_root

    reg_root = ensure_registry_root(root)
    total_records = 0
    total_evidence = 0

    print("--- Adapter smoke test ---\n")
    for label, result in results:
        save_adapter_result(result.to_dict(), storage_root=root)
        snapshot = convert_adapter_result_to_source_snapshot(result)
        reg.append("source_snapshots", snapshot.to_dict(), base_dir=reg_root)

        n = len(result.records)
        total_records += n
        print(f"  {label}: {result.status}, {n} record(s), mock={result.is_mock}")

        for rec in result.records:
            evi = convert_adapter_record_to_evidence_item(
                rec,
                adapter_name=result.adapter_name,
                is_mock=result.is_mock,
                source_id=snapshot.source_id,
            )
            reg.append("evidence_items", evi.to_dict(), base_dir=reg_root)
            total_evidence += 1

    print(f"\nTotal adapter results: {len(results)}")
    print(f"Total records: {total_records}")
    print(f"Total evidence items: {total_evidence}")
    print(f"Registry root: {(root / 'registries').resolve()}")
    print(f"\nAll results are MOCK. No external API calls were made.")
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

    sub.add_parser("adapters-smoke", help="Run mock adapters, save results, print summary")

    run_local_parser = sub.add_parser(
        "run-local", help="Run pipeline on user-provided local files",
    )
    run_local_parser.add_argument(
        "--manuscript", required=True,
        help="Path to manuscript file (.md or .txt)",
    )
    run_local_parser.add_argument(
        "--venue-guidelines", required=True,
        help="Path to venue guidelines file (.md or .txt)",
    )
    run_local_parser.add_argument(
        "--scenario", required=True,
        help="Path to submission scenario JSON file (.json)",
    )

    args = parser.parse_args(argv)

    commands = {
        "status": cmd_status,
        "run-fixture": cmd_run_fixture,
        "run-local": cmd_run_local,
        "inspect-storage": cmd_inspect_storage,
        "adapters-smoke": cmd_adapters_smoke,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
