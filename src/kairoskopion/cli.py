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


_SUPPORTED_EXTENSIONS = {".md", ".txt", ".json", ".html", ".htm", ".pdf", ".docx"}


def _validate_input_file(path: Path, label: str) -> str | None:
    """Validate an input file exists and has a supported extension.

    Returns an error message string, or None if valid.
    """
    if not path.exists():
        return f"{label}: file not found: {path}"
    if not path.is_file():
        return f"{label}: not a file: {path}"
    if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
        return (
            f"{label}: unsupported extension '{path.suffix}'. "
            f"Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
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


def cmd_vault_index(args: argparse.Namespace) -> int:
    """Generate vault indexes and manifest."""
    from .vault import write_vault_indexes

    root = _resolve_storage_root(args)
    written = write_vault_indexes(root)
    print(f"Vault indexes generated ({len(written)} files):")
    for name, path in sorted(written.items()):
        print(f"  {name}: {path}")
    return 0


def cmd_export_bundle(args: argparse.Namespace) -> int:
    """Export storage as a zip bundle."""
    from .exchange import export_storage_bundle

    root = _resolve_storage_root(args)
    output = Path(args.output)
    export_storage_bundle(root, output)
    print(f"Bundle exported: {output.resolve()}")
    return 0


def cmd_import_bundle(args: argparse.Namespace) -> int:
    """Import a storage bundle."""
    from .exchange import import_storage_bundle

    root = _resolve_storage_root(args)
    bundle = Path(args.bundle)
    mode = getattr(args, "mode", "append")
    result = import_storage_bundle(bundle, root, mode=mode)
    if result["success"]:
        print(f"Bundle imported ({mode}):")
        print(f"  Registries: {result['imported_registries']}")
        print(f"  Records: {result['imported_records']}")
        print(f"  Vault files: {result['imported_vault_files']}")
        return 0
    else:
        for e in result.get("errors", []):
            print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_validate_bundle(args: argparse.Namespace) -> int:
    """Validate a storage bundle."""
    from .exchange import validate_bundle

    bundle = Path(args.bundle)
    result = validate_bundle(bundle)
    if result["valid"]:
        print(f"Bundle valid: {bundle}")
        meta = result.get("metadata", {})
        print(f"  Version: {meta.get('kairoskopion_version', '?')}")
        print(f"  Created: {meta.get('created_at', '?')}")
        print(f"  Registries: {result.get('registry_count', 0)}")
        print(f"  Vault files: {result.get('vault_file_count', 0)}")
        return 0
    else:
        for e in result.get("errors", []):
            print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_intake_file(args: argparse.Namespace) -> int:
    """Register a single file as a source with extraction."""
    from .adapters.source_intake import SourceRole, register_local_source

    root = _resolve_storage_root(args)
    file_path = Path(args.file)

    role_str = getattr(args, "role", "unknown")
    try:
        role = SourceRole(role_str)
    except ValueError:
        role = SourceRole.UNKNOWN

    snapshot, text = register_local_source(file_path, role=role)

    # Persist snapshot
    from . import registry as reg
    from .persistence import ensure_registry_root

    reg_root = ensure_registry_root(root)
    reg.append("source_snapshots", snapshot.to_dict(), base_dir=reg_root)

    print(f"--- File intake ---")
    print(f"File:              {file_path}")
    print(f"Role:              {role.value}")
    print(f"Content type:      {snapshot.content_type}")
    print(f"Extraction status: {snapshot.extraction_status}")
    print(f"Extraction method: {snapshot.parser_used}")
    print(f"Text length:       {len(text)} chars")
    if snapshot.content_hash:
        print(f"Content hash:      {snapshot.content_hash}")
    print(f"Snapshot ID:       {snapshot.snapshot_id}")
    print(f"Source ID:         {snapshot.source_id}")
    if snapshot.extraction_errors:
        for err in snapshot.extraction_errors:
            print(f"  Warning: {err}")
    return 0


def cmd_build_venue_profile(args: argparse.Namespace) -> int:
    """Build venue profile from multiple source files."""
    from .services.venue_profile_builder import build_venue_profile

    root = _resolve_storage_root(args)
    paths = [Path(p) for p in args.files]

    # Validate files exist
    errors = []
    for p in paths:
        if not p.exists():
            errors.append(f"file not found: {p}")
        elif p.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            errors.append(f"unsupported extension: {p}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    result = build_venue_profile(paths)

    # Persist
    from . import registry as reg
    from .persistence import ensure_registry_root

    reg_root = ensure_registry_root(root)
    reg.append("venue_models", result.venue.to_dict(), base_dir=reg_root)
    reg.append("publication_regimes", result.regime.to_dict(), base_dir=reg_root)
    for src in result.sources:
        reg.append("source_snapshots", src.snapshot.to_dict(), base_dir=reg_root)

    print(f"--- Venue Profile Built ---")
    print(f"Sources:        {result.source_count} files, {result.extracted_count} extracted")
    print(f"Venue:          {result.venue.canonical_name or '(unnamed)'}")
    print(f"Venue ID:       {result.venue.venue_model_id}")
    print(f"Publisher:      {result.venue.publisher_or_owner or 'unknown'}")
    print(f"Scope:          {(result.venue.scope_summary or '')[:80]}...")
    print(f"Confidence:     {result.venue.confidence}")
    print(f"Indexing:       {', '.join(result.venue.indexing_claims) if result.venue.indexing_claims else 'unknown'}")
    print(f"AI policy:      {result.venue.ai_policy or 'unknown'}")
    print(f"Data policy:    {result.venue.data_policy or 'unknown'}")
    print(f"Ethics policy:  {result.venue.ethics_policy or 'unknown'}")
    print(f"Open access:    {result.venue.open_access_status or 'unknown'}")
    print(f"Review model:   {result.regime.review_model or 'unknown'}")
    print(f"Unknowns:       {len(result.venue.unknowns)}")
    if result.merge_log:
        print(f"\nMerge log:")
        for entry in result.merge_log:
            print(f"  {entry}")
    return 0


def cmd_build_submission_pack(args: argparse.Namespace) -> int:
    """Build submission pack from latest pipeline run artifacts in storage."""
    from .services.submission_pack import build_submission_pack
    from .schema import (
        ArticleModel,
        ComplianceChecklist,
        FitAssessment,
        RiskReport,
        SubmissionScenario,
        VenueModel,
        PublicationTrajectoryReport,
    )

    root = _resolve_storage_root(args)

    if not registries_exist(root):
        print("ERROR: no registries found. Run a pipeline first.", file=sys.stderr)
        return 1

    def _latest(name: str) -> dict | None:
        records = read_registry(name, storage_root=root)
        return records[-1] if records else None

    art_d = _latest("article_models")
    ven_d = _latest("venue_models")
    sc_d = _latest("submission_scenarios")

    if not art_d:
        print("ERROR: no article_models in storage. Run pipeline first.", file=sys.stderr)
        return 1
    if not ven_d:
        print("ERROR: no venue_models in storage. Run pipeline first.", file=sys.stderr)
        return 1
    if not sc_d:
        print("ERROR: no submission_scenarios in storage. Run pipeline first.", file=sys.stderr)
        return 1

    article = ArticleModel.from_dict(art_d)
    venue = VenueModel.from_dict(ven_d)
    scenario = SubmissionScenario.from_dict(sc_d)

    fit_d = _latest("fit_assessments")
    risk_d = _latest("risk_reports")
    comp_d = _latest("compliance_checklists")
    traj_d = _latest("trajectory_reports")

    fit = FitAssessment.from_dict(fit_d) if fit_d else None
    risk = RiskReport.from_dict(risk_d) if risk_d else None
    compliance = ComplianceChecklist.from_dict(comp_d) if comp_d else None
    trajectory = PublicationTrajectoryReport.from_dict(traj_d) if traj_d else None

    pack = build_submission_pack(
        article=article,
        venue=venue,
        scenario=scenario,
        fit=fit,
        risk=risk,
        compliance=compliance,
        trajectory=trajectory,
    )

    # Persist
    from . import registry as reg
    from .persistence import ensure_registry_root

    reg_root = ensure_registry_root(root)
    reg.append("submission_packs", pack.to_dict(), base_dir=reg_root)

    print("--- Submission Pack ---")
    print(f"Pack ID:        {pack.submission_pack_id}")
    print(f"Article:        {pack.article_model_id}")
    print(f"Venue:          {pack.venue_model_id}")
    print(f"Ready status:   {pack.ready_status}")
    print(f"Files:          {', '.join(pack.files)}")
    print(f"Statements:     {len(pack.statements)}")
    for s in pack.statements:
        print(f"  - {s}")
    if pack.missing_items:
        print(f"Missing items:  {len(pack.missing_items)}")
        for m in pack.missing_items:
            print(f"  ! {m}")
    if pack.blocking_issues:
        print(f"Blocking:       {len(pack.blocking_issues)}")
        for b in pack.blocking_issues:
            print(f"  X {b}")
    if pack.warnings:
        print(f"Warnings:       {len(pack.warnings)}")
        for w in pack.warnings:
            print(f"  ~ {w}")
    print(f"\nCover letter template:\n{pack.cover_letter}")
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
    parser.add_argument(
        "--adapter-mode",
        default="mock",
        choices=["mock", "real"],
        help="Adapter mode: 'mock' (deterministic, no network) or 'real' (HTTP API calls with caching). Default: mock.",
    )

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="Show environment status")
    sub.add_parser("run-fixture", help="Run fixture pipeline and persist results")
    sub.add_parser("inspect-storage", help="Show registry and vault contents")

    sub.add_parser("adapters-smoke", help="Run mock adapters, save results, print summary")
    sub.add_parser("vault-index", help="Generate vault indexes and manifest")

    export_parser = sub.add_parser("export-bundle", help="Export storage as zip bundle")
    export_parser.add_argument("--output", required=True, help="Output zip file path")

    import_parser = sub.add_parser("import-bundle", help="Import a storage bundle")
    import_parser.add_argument("--bundle", required=True, help="Path to bundle zip")
    import_parser.add_argument("--mode", default="append", choices=["append", "replace"],
                               help="Import mode: append (default) or replace")

    validate_parser = sub.add_parser("validate-bundle", help="Validate a storage bundle")
    validate_parser.add_argument("--bundle", required=True, help="Path to bundle zip")

    intake_parser = sub.add_parser(
        "intake-file", help="Register a file as a source with text extraction",
    )
    intake_parser.add_argument(
        "--file", required=True,
        help="Path to file (.md, .txt, .html, .json, .pdf, .docx)",
    )
    intake_parser.add_argument(
        "--role", default="unknown",
        help="Source role (article_input, venue_guidelines, etc.)",
    )

    venue_profile_parser = sub.add_parser(
        "build-venue-profile",
        help="Build venue profile from multiple source files",
    )
    venue_profile_parser.add_argument(
        "--files", nargs="+", required=True,
        help="Paths to venue source files (guidelines, aims, policies, etc.)",
    )

    run_local_parser = sub.add_parser(
        "run-local", help="Run pipeline on user-provided local files",
    )
    run_local_parser.add_argument(
        "--manuscript", required=True,
        help="Path to manuscript file (.md, .txt, .pdf, .docx)",
    )
    run_local_parser.add_argument(
        "--venue-guidelines", required=True,
        help="Path to venue guidelines file (.md, .txt, .pdf, .docx)",
    )
    run_local_parser.add_argument(
        "--scenario", required=True,
        help="Path to submission scenario JSON file (.json)",
    )

    sub.add_parser(
        "build-submission-pack",
        help="Build submission pack from latest pipeline run",
    )

    args = parser.parse_args(argv)

    commands = {
        "status": cmd_status,
        "run-fixture": cmd_run_fixture,
        "run-local": cmd_run_local,
        "inspect-storage": cmd_inspect_storage,
        "adapters-smoke": cmd_adapters_smoke,
        "vault-index": cmd_vault_index,
        "export-bundle": cmd_export_bundle,
        "import-bundle": cmd_import_bundle,
        "validate-bundle": cmd_validate_bundle,
        "intake-file": cmd_intake_file,
        "build-venue-profile": cmd_build_venue_profile,
        "build-submission-pack": cmd_build_submission_pack,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
