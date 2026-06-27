# P7 Bootstrap — Acceptance Checklist

**Date:** 2026-06-27

## Track-by-Track Acceptance

| track | description | status | evidence |
|-------|-------------|--------|----------|
| 0 | State/branch verified | PASS | Branch `feature/round3-p7-llm-integration`, HEAD `eec64c6` |
| 1 | Input archive located, protected | PASS | `.gitignore` covers `data/input/private/`, `data/private_work/` |
| 2 | Current system dogfood audit | PASS | `P7_BOOTSTRAP_CURRENT_ALGORITHM_AUDIT.md` created |
| 3 | SeedWorkflow contract defined | PASS | `P7_BOOTSTRAP_WORKFLOW_CONTRACT.md` — 11 stages documented |
| 4 | Article archetype from pipeline | PASS | `SeedRegistryWorkflow._build_article_archetype()` uses `ArticleModelerAgent.execute_deterministic()` |
| 5 | Zone/discipline/framework lookup | PASS | Registry-first search + SourceAcquisitionTask on miss |
| 6 | Source acquisition adapter layer | PASS | `ingest_local_file_as_packet()` for local files; tasks for missing |
| 7 | Venue universe generation | PASS | Registry search + fallback tasks; empty universe warning |
| 8 | Metrics/classification check | PASS | Checks VenueMetricRegistry; gaps reported when empty |
| 9 | Shortlist generation | PASS | Sorts accepted > provisional; shortage reported when < 5 |
| 10 | Deep VenueModel tasks | PASS | Created for each shortlisted venue |
| 11 | Run script | PASS | `scripts/run_education_ai_seed_workflow.py` with --no-live-llm, --validate-only, --zones |
| 12 | Dogfood run | PASS | Ran on Luksha article, all outputs in `data/seed_registry/education_ai_russia/` |
| 13 | Tests | PASS | 22 new tests (12 categories), 2814 total passed |
| 14 | Reports | PASS | This checklist + `P7_BOOTSTRAP_SELF_SEEDING_REPORT.md` |

## Doctrine Compliance

| rule | status | evidence |
|------|--------|----------|
| Registry-first | PASS | All lookups search existing registry before creating tasks |
| Source-backed | PASS | No invented data; all records are source-backed or marked unknown |
| Unknown is valid | PASS | 5 unknowns in archetype, gaps list in result |
| No LLM invention | PASS | Deterministic path marks `needs_llm_for` states |
| Provisional only | PASS | Workflow creates only provisional records |
| No fake references | PASS | No DOIs, ISSNs, editor names fabricated |
| Privacy protected | PASS | Raw article never in tracked output; `.gitignore` covers private dirs |

## Files Created

| file | type |
|------|------|
| `src/kairoskopion/services/seed_workflow.py` | Service (SeedRegistryWorkflow + SeedWorkflowConfig + SeedWorkflowResult + ingest_local_file_as_packet) |
| `scripts/run_education_ai_seed_workflow.py` | CLI runner (--input-file, --no-live-llm, --validate-only, --zones, --target, --output-dir) |
| `tests/test_seed_workflow.py` | 22 tests (12 categories) |
| `docs/operations/P7_BOOTSTRAP_PREFLIGHT.md` | Preflight report |
| `docs/operations/P7_BOOTSTRAP_INPUT_AUDIT.md` | Input audit |
| `docs/operations/P7_BOOTSTRAP_CURRENT_ALGORITHM_AUDIT.md` | Algorithm audit |
| `docs/operations/P7_BOOTSTRAP_WORKFLOW_CONTRACT.md` | Workflow contract |
| `docs/operations/P7_BOOTSTRAP_SELF_SEEDING_REPORT.md` | Dogfood run report |
| `docs/operations/P7_BOOTSTRAP_ACCEPTANCE_CHECKLIST.md` | This checklist |

## Test Count

- Before: 2792
- New: 22
- Total: 2814

## VERDICT

**ACCEPT** — all 16 tracks completed, doctrine compliant, 2814 tests pass.
