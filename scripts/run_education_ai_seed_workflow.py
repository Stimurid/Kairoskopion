#!/usr/bin/env python3
"""Run the self-seeding registry workflow for education/AI domain.

Usage:
    python scripts/run_education_ai_seed_workflow.py --input-file path/to/article.md
    python scripts/run_education_ai_seed_workflow.py --validate-only
    python scripts/run_education_ai_seed_workflow.py --no-live-llm --input-file data/private_work/luksha_article_intermediate_versions/08_cited_clean_current_base.md

Flags:
    --input-file FILE     Article text file (required unless --validate-only)
    --no-live-llm         Disable live LLM calls (deterministic only)
    --no-paid-api         Disable paid external API calls
    --validate-only       Validate registry state without running workflow
    --target DOMAIN       Domain target (default: education_ai_russia)
    --zones ZONE [ZONE..] Target zones for discipline search
    --output-dir DIR      Output directory (default: data/seed_registry/<target>/)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kairoskopion.registry.services import RegistryHub
from kairoskopion.services.seed_workflow import (
    SeedRegistryWorkflow,
    SeedWorkflowConfig,
    ingest_local_file_as_packet,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Education/AI seed workflow")
    parser.add_argument("--input-file", type=Path)
    parser.add_argument("--no-live-llm", action="store_true", default=True)
    parser.add_argument("--no-paid-api", action="store_true", default=True)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--target", default="education_ai_russia")
    parser.add_argument("--zones", nargs="*", default=[])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    hub = RegistryHub(data_dir=root / "data" / "registry")

    if args.validate_only:
        return _validate(hub)

    if not args.input_file:
        print("ERROR: --input-file required (unless --validate-only)")
        return 1

    if not args.input_file.exists():
        print(f"ERROR: file not found: {args.input_file}")
        return 1

    text = args.input_file.read_text(encoding="utf-8")
    if len(text) < 200:
        print(f"WARNING: article text is very short ({len(text)} chars)")

    output_dir = args.output_dir or (
        root / "data" / "seed_registry" / args.target
    )

    packet = ingest_local_file_as_packet(hub, args.input_file)
    print(f"Source packet created: {packet.packet_id}")

    cfg = SeedWorkflowConfig(
        article_text=text,
        article_source_ref=str(args.input_file),
        domain_target=args.target,
        target_zones=args.zones or [],
        no_live_llm=args.no_live_llm,
        no_paid_api=args.no_paid_api,
        output_dir=output_dir,
    )

    wf = SeedRegistryWorkflow(hub)
    result = wf.run(cfg)

    print(f"\n=== Seed Workflow Complete ===")
    print(f"Run ID: {result.run_id}")
    print(f"Archetype: {'yes' if result.article_archetype else 'no'}")
    print(f"Discipline lookups: {len(result.discipline_lookups)}")
    print(f"Acquisition tasks: {len(result.acquisition_tasks_created)}")
    print(f"Venue universe: {len(result.venue_universe)}")
    print(f"Shortlist: {len(result.shortlist)}")
    print(f"Deep venue tasks: {len(result.deep_venue_tasks)}")
    print(f"Gaps: {len(result.gaps)}")
    print(f"Warnings: {len(result.warnings)}")

    if result.gaps:
        print(f"\n--- Gaps ---")
        for g in result.gaps:
            print(f"  - {g}")

    if result.warnings:
        print(f"\n--- Warnings ---")
        for w in result.warnings:
            print(f"  - {w}")

    print(f"\nOutputs written to: {output_dir}")
    return 0


def _validate(hub: RegistryHub) -> int:
    print("=== Registry Validation ===")
    counts = {
        "disciplines": len(hub.disciplines().list_all()),
        "venues": len(hub.venues().list_all()),
        "venue_sections": len(hub.venue_sections().list_all()),
        "venue_metrics": len(hub.venue_metrics().list_all()),
        "venue_classifications": len(hub.venue_classifications().list_all()),
        "epistemic_frameworks": len(hub.epistemic_frameworks().list_all()),
        "classification_systems": len(hub.classification_systems().list_all()),
        "subject_categories": len(hub.subject_categories().list_all()),
        "acquisition_tasks": len(hub.tasks.list_all()),
        "source_packets": len(hub.packets.list_all()),
    }
    for name, count in counts.items():
        status = "OK" if count > 0 else "EMPTY"
        print(f"  {name}: {count} [{status}]")

    open_tasks = hub.tasks.list_open()
    if open_tasks:
        print(f"\n--- Open Acquisition Tasks ({len(open_tasks)}) ---")
        for t in open_tasks[:10]:
            print(f"  [{t.task_type}] {t.query}")
        if len(open_tasks) > 10:
            print(f"  ... and {len(open_tasks) - 10} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
