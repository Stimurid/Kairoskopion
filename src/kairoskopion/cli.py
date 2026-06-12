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


def _resolve_llm_provider(args: argparse.Namespace):
    """Build LLMProvider from CLI args or env, returns None if not configured."""
    model = getattr(args, "llm_model", None)
    base_url = getattr(args, "llm_base_url", None)
    api_key_env = getattr(args, "llm_api_key_env", None)

    if model and base_url:
        from .llm.config import LLMConfig
        from .llm.openai_compat import OpenAICompatProvider
        cfg = LLMConfig(
            model=model,
            base_url=base_url,
            api_key_env=api_key_env or "KAIROSKOPION_LLM_API_KEY",
        )
        return OpenAICompatProvider(cfg)

    from .llm.config import LLMConfig
    cfg = LLMConfig.from_env()
    if cfg is not None:
        from .llm.openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(cfg)

    return None


def cmd_status(args: argparse.Namespace) -> int:
    """Show environment status."""
    from .llm.config import is_llm_available, provider_status

    root = _resolve_storage_root(args)
    print(f"Kairoskopion v{__version__}")
    print(f"Working directory: {Path.cwd()}")
    print(f"Storage root:      {root.resolve()}")
    print(f"Registries exist:  {registries_exist(root)}")
    print(f"Vault exists:      {vault_exists(root)}")
    if registries_exist(root):
        regs = list_registries(root)
        print(f"Registries:        {', '.join(regs) if regs else '(empty)'}")
    # LLM status
    llm = provider_status()
    print(f"LLM available:     {llm['available']}")
    if llm["available"]:
        print(f"LLM provider:      {llm['provider']}")
        print(f"LLM model:         {llm['model']}")
        print(f"LLM base URL:      {llm['base_url']}")
        print(f"LLM has API key:   {llm['has_api_key']}")
    else:
        print(f"LLM reason:        {llm.get('reason', 'not configured')}")
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
    llm = _resolve_llm_provider(args)
    pipeline = ManuscriptVenueFitPipeline(llm_provider=llm)
    if llm:
        print(f"LLM provider: {getattr(llm, '_config', None) and llm._config.model or 'configured'}")
    else:
        print("LLM provider: none (deterministic mode)")
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
    llm = _resolve_llm_provider(args)
    pipeline = ManuscriptVenueFitPipeline(llm_provider=llm)
    if llm:
        print(f"LLM provider: {getattr(llm, '_config', None) and llm._config.model or 'configured'}")
    else:
        print("LLM provider: none (deterministic mode)")
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


def cmd_export_whitecrow_patches(args: argparse.Namespace) -> int:
    """Export WhiteCrow patch queue from latest pipeline artifacts."""
    from .integrations.whitecrow_bridge import build_whitecrow_patch_queue, write_whitecrow_patches
    from .schema import (
        ComplianceChecklist,
        MismatchMap,
        RewritePlan,
        RiskReport,
    )

    root = _resolve_storage_root(args)
    output_dir = Path(args.output_dir)
    target_doc = getattr(args, "target_doc", None)

    if not registries_exist(root):
        print("ERROR: no registries found. Run a pipeline first.", file=sys.stderr)
        return 1

    def _latest(name: str) -> dict | None:
        records = read_registry(name, storage_root=root)
        return records[-1] if records else None

    mm_d = _latest("mismatch_maps")
    rw_d = _latest("rewrite_plans")
    comp_d = _latest("compliance_checklists")
    risk_d = _latest("risk_reports")

    mismatch_map = MismatchMap.from_dict(mm_d) if mm_d else None
    rewrite_plan = RewritePlan.from_dict(rw_d) if rw_d else None
    compliance = ComplianceChecklist.from_dict(comp_d) if comp_d else None
    risk = RiskReport.from_dict(risk_d) if risk_d else None

    patches = build_whitecrow_patch_queue(
        mismatch_map=mismatch_map,
        rewrite_plan=rewrite_plan,
        compliance=compliance,
        risk=risk,
        target_document_ref=target_doc,
    )

    if not patches:
        print("No patches generated — no mismatches, rewrites, compliance gaps, or blocking risks found.")
        return 0

    path = write_whitecrow_patches(patches, output_dir)

    print("--- WhiteCrow Patch Export ---")
    print(f"Output:         {path.resolve()}")
    print(f"Total patches:  {len(patches)}")
    by_type: dict[str, int] = {}
    for p in patches:
        ct = p.get("change_type", "unknown")
        by_type[ct] = by_type.get(ct, 0) + 1
    for ct, count in sorted(by_type.items()):
        print(f"  {ct}: {count}")
    blocking = [p for p in patches if "[BLOCKING]" in p.get("change_summary", "")]
    if blocking:
        print(f"Blocking patches: {len(blocking)}")
    return 0


def cmd_export_litops_pack(args: argparse.Namespace) -> int:
    """Export latest pipeline artifacts as Litops-compatible JSONL."""
    from .integrations.litops_bridge import build_litops_export_pack, write_litops_export
    from .schema import (
        ArticleModel,
        BibliographyProfile,
        FitAssessment,
        PublicationTrajectoryReport,
        RiskReport,
        SubmissionPack,
        VenueModel,
    )

    root = _resolve_storage_root(args)
    output_dir = Path(args.output_dir)

    if not registries_exist(root):
        print("ERROR: no registries found. Run a pipeline first.", file=sys.stderr)
        return 1

    def _latest(name: str) -> dict | None:
        records = read_registry(name, storage_root=root)
        return records[-1] if records else None

    art_d = _latest("article_models")
    ven_d = _latest("venue_models")

    if not art_d and not ven_d:
        print("ERROR: no article or venue models in storage.", file=sys.stderr)
        return 1

    article = ArticleModel.from_dict(art_d) if art_d else None
    venue = VenueModel.from_dict(ven_d) if ven_d else None

    fit_d = _latest("fit_assessments")
    risk_d = _latest("risk_reports")
    traj_d = _latest("trajectory_reports")
    pack_d = _latest("submission_packs")
    bib_d = _latest("bibliography_profiles")

    fit = FitAssessment.from_dict(fit_d) if fit_d else None
    risk = RiskReport.from_dict(risk_d) if risk_d else None
    trajectory = PublicationTrajectoryReport.from_dict(traj_d) if traj_d else None
    pack = SubmissionPack.from_dict(pack_d) if pack_d else None
    bibliography = BibliographyProfile.from_dict(bib_d) if bib_d else None

    export_pack = build_litops_export_pack(
        article=article,
        venue=venue,
        fit=fit,
        risk=risk,
        trajectory=trajectory,
        pack=pack,
        bibliography=bibliography,
    )

    written = write_litops_export(export_pack, output_dir)

    print("--- Litops Export ---")
    print(f"Output dir:     {output_dir.resolve()}")
    print(f"Sources:        {len(export_pack.get('sources', []))}")
    print(f"Artifacts:      {len(export_pack.get('artifacts', []))}")
    for name, path in sorted(written.items()):
        print(f"  {name}: {path}")
    return 0


def cmd_import_venue_seed(args: argparse.Namespace) -> int:
    """Import venue seed corpus into venue registries."""
    from .services.venue_registry import import_venue_seed_corpus, persist_import_result

    corpus_dir = Path(args.corpus)
    storage = _resolve_storage_root(args)

    print(f"Importing venue seed corpus from {corpus_dir.resolve()} ...")
    result = import_venue_seed_corpus(corpus_dir)

    if not result.success:
        print("FAILED — validation errors:", file=sys.stderr)
        for err in result.errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        return 1

    if result.warnings:
        for w in result.warnings:
            print(f"  WARNING: {w}")

    written = persist_import_result(result, storage)

    print(f"Venues:   {len(result.venues)}")
    print(f"Sources:  {len(result.sources)}")
    print(f"Claims:   {len(result.claims)}")
    print(f"Storage:  {storage.resolve()}")
    for name, path in sorted(written.items()):
        print(f"  {name}: {path}")
    return 0


def cmd_build_venue_evidence_pack(args: argparse.Namespace) -> int:
    """Build venue evidence pack from registry data."""
    from .services.venue_registry import (
        build_venue_evidence_pack,
        evidence_pack_to_markdown,
        import_venue_seed_corpus,
    )

    storage = _resolve_storage_root(args)
    reg_root = storage / "registries"

    venues_path = reg_root / "venue_records.jsonl"
    sources_path = reg_root / "venue_sources.jsonl"
    claims_path = reg_root / "venue_claims.jsonl"

    missing = [p for p in [venues_path, sources_path, claims_path] if not p.exists()]
    if missing:
        print(
            "Venue registries not found. Run 'import-venue-seed' first.",
            file=sys.stderr,
        )
        for p in missing:
            print(f"  Missing: {p}", file=sys.stderr)
        return 1

    from .schema import VenueClaim, VenueRecord, VenueSource

    venues = []
    with venues_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                venues.append(VenueRecord.from_dict(json.loads(line)))

    sources = []
    with sources_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                sources.append(VenueSource.from_dict(json.loads(line)))

    claims = []
    with claims_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                claims.append(VenueClaim.from_dict(json.loads(line)))

    pack = build_venue_evidence_pack(args.venue_id, venues, sources, claims)
    if pack is None:
        print(f"Venue not found: {args.venue_id}", file=sys.stderr)
        print(f"Available venues ({len(venues)}):", file=sys.stderr)
        for v in venues:
            aliases = f" (aliases: {', '.join(v.aliases)})" if v.aliases else ""
            print(f"  {v.venue_record_id}: {v.canonical_name}{aliases}", file=sys.stderr)
        return 1

    md = evidence_pack_to_markdown(pack)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"Evidence pack written to {out.resolve()}")
        print(f"  Venue: {pack.profile.get('name', '?')}")
        print(f"  Official facts: {len(pack.official_facts)}")
        print(f"  Conflicts: {len(pack.conflicts)}")
        print(f"  Unknowns: {len(pack.unknowns)}")
    else:
        print(md)

    return 0


# ---------------------------------------------------------------------------
# Agent / workflow CLI commands (Agentic Contour v0.1)
# ---------------------------------------------------------------------------

def _safe_print(text: str) -> None:
    """Print text safely on Windows consoles (cp1251/cp1252)."""
    sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def _print_json(data: dict) -> None:
    """Print JSON safely on Windows consoles (cp1251/cp1252)."""
    text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def cmd_list_agents(args: argparse.Namespace) -> int:
    from .agents.registry import list_agent_specs
    specs = list_agent_specs()
    layer_filter = getattr(args, "layer", None)
    if layer_filter:
        specs = [s for s in specs if s.layer == layer_filter]
    for s in specs:
        status = s.implementation_status
        print(f"  {s.role_id:<40} [{s.layer:<12}] {status}")
    print(f"\n{len(specs)} agents")
    return 0


def cmd_inspect_agent(args: argparse.Namespace) -> int:
    from .agents.registry import get_agent_spec
    try:
        spec = get_agent_spec(args.role_id)
    except KeyError:
        print(f"Unknown agent: {args.role_id}", file=sys.stderr)
        return 1
    _print_json(spec.to_dict())
    return 0


def cmd_list_prompt_families(args: argparse.Namespace) -> int:
    from .agents.prompt_families.catalog import list_prompt_families
    families = list_prompt_families()
    for fid in families:
        print(f"  {fid}")
    print(f"\n{len(families)} prompt families")
    return 0


def cmd_inspect_prompt_family(args: argparse.Namespace) -> int:
    from .agents.prompt_families.catalog import get_prompt_family
    fam = get_prompt_family(args.family_id)
    if fam is None:
        print(f"Unknown prompt family: {args.family_id}", file=sys.stderr)
        return 1
    if getattr(args, "full", False):
        safe = {k: v for k, v in fam.items() if not callable(v)}
    else:
        safe = {k: v for k, v in fam.items() if k != "output_schema" and not callable(v)}
        safe["output_schema"] = "(omitted, use --full to include)"
    _print_json(safe)
    return 0


def cmd_list_workflows(args: argparse.Namespace) -> int:
    from .agents.workflows import list_workflow_specs
    for wf in list_workflow_specs():
        n_steps = len(wf.steps)
        print(f"  {wf.workflow_id:<45} [{wf.implementation_status:<15}] {n_steps} steps")
    return 0


def cmd_inspect_workflow(args: argparse.Namespace) -> int:
    from .agents.workflows import get_workflow_spec
    try:
        wf = get_workflow_spec(args.workflow_id)
    except KeyError:
        print(f"Unknown workflow: {args.workflow_id}", file=sys.stderr)
        return 1
    _print_json(wf.to_dict())
    return 0


def cmd_run_agent_workflow(args: argparse.Namespace) -> int:
    from .agents.workflows import get_workflow_spec
    from .agents.orchestrator import run_workflow

    try:
        spec = get_workflow_spec(args.workflow_id)
    except KeyError:
        print(f"Unknown workflow: {args.workflow_id}", file=sys.stderr)
        return 1

    initial_entities: dict = {}
    if args.manuscript:
        text = Path(args.manuscript).read_text(encoding="utf-8")
        initial_entities["raw_text"] = text

    if args.venue_json:
        venue_data = json.loads(Path(args.venue_json).read_text(encoding="utf-8"))
        initial_entities["venue"] = venue_data

    if getattr(args, "venue_guidelines", None):
        guidelines_text = Path(args.venue_guidelines).read_text(encoding="utf-8")
        initial_entities["venue_guidelines_text"] = guidelines_text

    provider = _resolve_llm_provider(args)

    stop_on_fail = getattr(args, "stop_on_failure", False)

    _safe_print(f"Running workflow: {spec.display_name}")
    _safe_print(f"Steps: {len(spec.steps)}")
    _safe_print(f"LLM provider: {'configured' if provider else 'none (deterministic only)'}")
    _safe_print(f"Stop on failure: {stop_on_fail}")
    _safe_print("")

    result = run_workflow(
        spec,
        initial_entities=initial_entities,
        raw_text=initial_entities.get("raw_text"),
        provider=provider,
        prefer_deterministic=not getattr(args, "use_llm", False),
        stop_on_failure=stop_on_fail,
    )

    _safe_print(f"Status: {result.status}")
    _safe_print(f"Steps completed: {len([s for s in result.step_results if s.get('status') == 'completed'])}/{len(spec.steps)}")
    _safe_print("")
    for sr in result.step_results:
        status_mark = "OK" if sr.get("status") == "completed" else sr.get("status", "?").upper()
        _safe_print(f"  [{status_mark}] step[{sr['step_index']}] {sr['agent_role_id']}")

    trace = getattr(result, "_trace", None)
    if getattr(args, "show_trace", False) and trace:
        _safe_print("")
        _safe_print("--- Workflow Trace ---")
        trace_dict = trace.to_dict() if hasattr(trace, "to_dict") else {}
        for entry in trace_dict.get("steps_log", []):
            _safe_print(f"  {entry}")

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nFull result written to {out.resolve()}")

    return 0 if result.status == "completed" else 1


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

    run_fixture_parser = sub.add_parser("run-fixture", help="Run fixture pipeline and persist results")
    run_fixture_parser.add_argument("--llm-model", default=None, help="LLM model name (e.g. gpt-4o)")
    run_fixture_parser.add_argument("--llm-base-url", default=None, help="LLM API base URL")
    run_fixture_parser.add_argument("--llm-api-key-env", default=None, help="Env var name for API key (default: KAIROSKOPION_LLM_API_KEY)")

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
    run_local_parser.add_argument("--llm-model", default=None, help="LLM model name (e.g. gpt-4o)")
    run_local_parser.add_argument("--llm-base-url", default=None, help="LLM API base URL")
    run_local_parser.add_argument("--llm-api-key-env", default=None, help="Env var name for API key (default: KAIROSKOPION_LLM_API_KEY)")

    sub.add_parser(
        "build-submission-pack",
        help="Build submission pack from latest pipeline run",
    )

    litops_parser = sub.add_parser(
        "export-litops-pack",
        help="Export pipeline artifacts as Litops-compatible JSONL",
    )
    litops_parser.add_argument(
        "--output-dir", required=True,
        help="Directory to write Litops JSONL files into",
    )

    whitecrow_parser = sub.add_parser(
        "export-whitecrow-patches",
        help="Export patch queue for WhiteCrow from pipeline artifacts",
    )
    whitecrow_parser.add_argument(
        "--output-dir", required=True,
        help="Directory to write WhiteCrow patch queue JSONL into",
    )
    whitecrow_parser.add_argument(
        "--target-doc", default=None,
        help="Target document reference for patches (optional)",
    )

    # --- Agent / workflow subparsers ---
    list_agents_parser = sub.add_parser("list-agents", help="List all registered agents")
    list_agents_parser.add_argument("--layer", default=None, help="Filter by layer (control, article, venue, fit, submission, review, evidence)")

    inspect_agent_parser = sub.add_parser("inspect-agent", help="Show agent spec as JSON")
    inspect_agent_parser.add_argument("role_id", help="Agent role_id")

    sub.add_parser("list-prompt-families", help="List all prompt families")

    inspect_pf_parser = sub.add_parser("inspect-prompt-family", help="Show prompt family details")
    inspect_pf_parser.add_argument("family_id", help="Prompt family ID")
    inspect_pf_parser.add_argument("--full", action="store_true", help="Include output schema")

    sub.add_parser("list-workflows", help="List all workflow specs")

    inspect_wf_parser = sub.add_parser("inspect-workflow", help="Show workflow spec as JSON")
    inspect_wf_parser.add_argument("workflow_id", help="Workflow ID")

    run_wf_parser = sub.add_parser("run-agent-workflow", help="Run an agentic workflow")
    run_wf_parser.add_argument("workflow_id", help="Workflow ID to run")
    run_wf_parser.add_argument("--manuscript", default=None, help="Path to manuscript file")
    run_wf_parser.add_argument("--venue-json", default=None, help="Path to venue JSON file")
    run_wf_parser.add_argument("--output", default=None, help="Output JSON file for full result")
    run_wf_parser.add_argument("--use-llm", action="store_true", help="Prefer LLM execution over deterministic")
    run_wf_parser.add_argument("--stop-on-failure", action="store_true", default=False, help="Stop workflow on first step failure")
    run_wf_parser.add_argument("--venue-guidelines", default=None, help="Path to venue guidelines text file")
    run_wf_parser.add_argument("--show-trace", action="store_true", default=False, help="Show workflow trace log after run")
    run_wf_parser.add_argument("--llm-model", default=None, help="LLM model name")
    run_wf_parser.add_argument("--llm-base-url", default=None, help="LLM API base URL")
    run_wf_parser.add_argument("--llm-api-key-env", default=None, help="Env var for API key")

    import_seed_parser = sub.add_parser(
        "import-venue-seed",
        help="Import venue seed corpus (JSONL) into venue registries",
    )
    import_seed_parser.add_argument(
        "--corpus", required=True,
        help="Path to seed corpus directory containing venues.jsonl, sources.jsonl, claims.jsonl",
    )

    build_epack_parser = sub.add_parser(
        "build-venue-evidence-pack",
        help="Build venue evidence pack from registry data",
    )
    build_epack_parser.add_argument(
        "--venue-id", required=True,
        help="Venue record ID, alias, or canonical name",
    )
    build_epack_parser.add_argument(
        "--output", default=None,
        help="Output Markdown file path (default: stdout)",
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
        "export-litops-pack": cmd_export_litops_pack,
        "export-whitecrow-patches": cmd_export_whitecrow_patches,
        "import-venue-seed": cmd_import_venue_seed,
        "build-venue-evidence-pack": cmd_build_venue_evidence_pack,
        "list-agents": cmd_list_agents,
        "inspect-agent": cmd_inspect_agent,
        "list-prompt-families": cmd_list_prompt_families,
        "inspect-prompt-family": cmd_inspect_prompt_family,
        "list-workflows": cmd_list_workflows,
        "inspect-workflow": cmd_inspect_workflow,
        "run-agent-workflow": cmd_run_agent_workflow,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
