# P7.3 Authority-Driven Source Harvest — Acceptance & Merge

**Date:** 2026-06-27
**Branch:** `feature/round3-p7-llm-integration`
**Commit:** `2a6b23c`

## What is accepted

1. **EvidencePackHarvester** (`services/evidence_pack_harvester.py`) — regex-based
   parser for venue evidence pack markdown → SourcePackets + provisional
   VenueRegistryRecord, VenueSectionRecord, VenueMetricRecord,
   VenueClassificationRecord.

2. **HarvestPlan builder** (`services/harvest_plan.py`) — HarvestTask model,
   `build_authority_harvest_plan()` mapping 17 SourceAuthorityRecords → 26 tasks
   with free/blocked adapter classification.

3. **SeedRegistryWorkflow stages 5-6** (`services/seed_workflow.py`) —
   `_ingest_evidence_packs()` and `_ingest_discipline_seeds()` wired into
   `run()` pipeline. Config extended with `evidence_pack_dir` and
   `discipline_seed_path`.

4. **Source list import template** (`data/seed_registry/templates/source_list_import_template.csv`).

5. **Audit docs** — preflight, source authority input audit, adapter capability audit, harvest report.

6. **53 new tests** (33 harvester + 20 harvest plan), all passing.

## Dogfood counts (Luksha article + 5 evidence packs)

| record type | count |
|------------|-------|
| venues | 5 |
| venue_sections | 38 |
| venue_metrics | 15 |
| venue_classifications | 6 |
| disciplines | 15 |
| source_packets | 62 |
| harvest_tasks | 26 (12 ready, 6 blocked, 8 planned) |
| acquisition_gaps | 8 |

## What is NOT proven

- Education/AI venue universe (evidence packs cover philosophy, not education).
- Shortlist matching (empty — expected, domain mismatch).
- LLM-based article modeling (deterministic fallback only).
- Live external API harvest (no_paid_api=True throughout).
- CSV import CLI command (template exists, CLI not wired).

## Runtime outputs NOT committed

- `data/seed_registry/p73_harvest_output/` — harvest plan JSONL, result JSON,
  registry JSONL files. These are runtime dogfood outputs, not fixtures.

## Constraints verified

| constraint | status |
|-----------|--------|
| No main merge (until now) | PASS |
| No prod deploy | PASS |
| No force push | PASS |
| No paid 302.ai calls | PASS |
| No model-memory facts | PASS |
| No fabricated data | PASS |
| Every record has evidence refs | PASS |
| All tests use tmp_path | PASS |
| No secrets committed | PASS |

## Why P7.3 is ready to merge

- All 2934 tests pass (0 failures).
- Core harvest pipeline is functional end-to-end.
- Real data dogfood (Luksha article + 5 venue evidence packs) produces
  correct provisional records with full provenance.
- No regressions in existing functionality.
- Remaining tracks (CSV CLI, education venue universe) are incremental
  and depend on additional data, not on P7.3 code changes.

## VERDICT: ACCEPT AND MERGE
