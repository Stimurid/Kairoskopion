# P7.2 Source Authority Discovery — Acceptance Checklist

**Date:** 2026-06-27
**Branch:** `feature/round3-p7-llm-integration`

## Track-by-Track Acceptance

| track | description | status | evidence |
|-------|-------------|--------|----------|
| 0 | Preflight | PASS | `P7_2_SOURCE_AUTHORITY_PREFLIGHT.md` |
| 1 | Existing source audit | PASS | `P7_2_EXISTING_SOURCE_AUTHORITY_AUDIT.md` — 9 adapters found |
| 2 | SourceAuthorityRegistry | PASS | `source_authority_registry.py` — Record, Store, TaskStore, Evaluator |
| 3 | Sufficiency rules | PASS | `P7_2_SOURCE_AUTHORITY_SUFFICIENCY_RULES.md` — 7 minimum types, country hints |
| 4 | Populate from project | DEFERRED | No local authority records yet — by design (no Claude-memory facts) |
| 5 | Seed workflow integration | PASS | `seed_workflow.py` — Stage 0 authority evaluation, _has_authority, blocked_on_authority |
| 6 | External adapter registry | PASS | `external_source_adapters.py` — 14 adapters, suggest_for_authority_type |
| 7 | Authority-aware task generation | PASS | Acquisition tasks respect authority coverage; blocked tasks reported |
| 8 | Dogfood rerun | PASS | `P7_2_LUKSHA_AUTHORITY_AWARE_DOGFOOD_REPORT.md` — 7 tasks, 1 blocked |
| 9 | Validation hardening | PASS | 45 tests covering all new code |
| 10 | Reports | PASS | This checklist + 4 operation docs |
| 11 | Full test suite | PASS | 2859 passed, 0 failures |
| 12 | Commit | PENDING | Ready to commit |

## Doctrine Compliance

| rule | status | evidence |
|------|--------|----------|
| Two-registry doctrine | PASS | Source authority registry separate from factual registries |
| No Claude-memory facts | PASS | No ISSNs, quartiles, editors fabricated |
| No paid API calls | PASS | scopus/wos disabled by default |
| Argentina cross-check | PASS | test_argentina_no_russian_hints — VAK/РИНЦ excluded |
| Authority-first | PASS | Missing authorities → discovery tasks, not factual tasks |
| Provisional only | PASS | All store records provisional until accepted |

## Files Created

| file | type |
|------|------|
| `src/kairoskopion/services/source_authority_registry.py` | Service (SourceAuthorityRecord, Store, TaskStore, SufficiencyEvaluator) |
| `src/kairoskopion/services/external_source_adapters.py` | Service (ExternalAdapterRecord, ExternalAdapterRegistry, 14 adapters) |
| `src/kairoskopion/services/seed_workflow.py` | Modified (Stage 0 authority, blocked_on_authority, adapter awareness) |
| `tests/test_source_authority_registry.py` | 45 tests (8 classes) |
| `docs/operations/P7_2_SOURCE_AUTHORITY_PREFLIGHT.md` | Track 0 doc |
| `docs/operations/P7_2_EXISTING_SOURCE_AUTHORITY_AUDIT.md` | Track 1 doc |
| `docs/operations/P7_2_SOURCE_AUTHORITY_SUFFICIENCY_RULES.md` | Track 3 doc |
| `docs/operations/P7_2_EXTERNAL_SOURCE_ADAPTERS.md` | Track 6 doc |
| `docs/operations/P7_2_LUKSHA_AUTHORITY_AWARE_DOGFOOD_REPORT.md` | Track 8 doc |
| `docs/operations/P7_2_SOURCE_AUTHORITY_ACCEPTANCE_CHECKLIST.md` | This file |

## Test Count

- Before: 2814
- New: 45
- Total: 2859

## VERDICT

**ACCEPT** — all implementable tracks completed, doctrine compliant, 2859 tests pass. Track 4 (populate from project materials) deferred by design — requires human-provided source materials, not Claude-memory facts.
