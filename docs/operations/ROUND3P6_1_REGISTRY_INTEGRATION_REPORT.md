# Round III-P6.1 — Registry Integration Report

**Date:** 2026-06-27
**Branch:** `feature/round3-six-phase-build-hardening`
**Base:** `8368c77` (P6-0 infrastructure)

## Summary

P6.1 wires the P6-0 registry infrastructure into actual Case/API product paths.
The `RegistryIntegrationService` class is the single product-path entry point.
All Case methods that touch discipline/venue data delegate to it.

## Product paths now calling registry integration

| Product path | Method | Registry integration | Track |
|---|---|---|---|
| Discipline matching | `Case._run_discipline_matcher()` | Registry-first lookup via `_registry.discipline_lookup()`. Accepted → canonical, skip agent. Provisional → use with warning. Miss → fall through to DisciplineMatcherAgent. | 3 |
| Venue investigation | `Case.investigate_venue()` | Post-extraction: `_registry.store_venue_extraction()` stores venue/sections/metrics as provisional records. Status propagation via `_registry.propagate_status()`. | 7, 8 |
| Venue family context | `Case._build_venue_family_from_venue()` | Registry-first family: `_registry.build_family_context()` builds from registry evidence (sections, parent/child neighbors). Falls back to BLOCKED_NEEDS_LLM if no registry record. | 5 |
| Venue matrix | `Case.get_venue_matrix()` | Provenance enrichment via `_registry.enrich_candidates_with_provenance()`. Candidates without provenance warned. Status propagation via `_registry.propagate_status()`. | 6, 8 |

## Bypass audit: direct agent call sites

| Direct call site | Path | Product path? | Goes through integration? | Action |
|---|---|---|---|---|
| InputClassifierAgent | `cases.py:443` | Yes — intake classification | No bypass — classification is not a registry operation | Safe — no registry concern |
| ArticleModelerAgent | `cases.py:495` | Yes — article extraction | No bypass — article modeling is not a registry operation | Safe — no registry concern |
| ArticleSemanticProfilerAgent | `cases.py:594` | Yes — semantic profile | No bypass — profiling is not a registry operation | Safe — no registry concern |
| DisciplineMatcherAgent | `cases.py:698` | Yes — discipline matching | **Yes** — only reached after registry-first lookup misses | Wired (Track 3) |
| ArticleFieldPositionerAgent | `cases.py:767` | Yes — article FPM | No bypass — field positioning is not a registry operation | Safe — no registry concern |
| VenueProfilerAgent | `cases.py:872` | Yes — venue investigation | **Yes** — output stored as provisional records post-extraction | Wired (Track 7) |
| VenueFieldPositionerAgent | `cases.py:1329` | Yes — venue FPM | No bypass — field positioning is not a registry operation | Safe — no registry concern |
| DisciplinaryPathwayMapperAgent | `cases.py:1593` | Yes — pathway mapping | No bypass — pathway uses confirmed article model | Safe — consumes confirmed data |
| VenueDiscoveryAgent | `cases.py:1652` | Yes — venue discovery | Documented bypass — discovery creates candidates for future registry ingest | P6.2 wiring candidate |
| FitAssessorAgent | `cases.py:1812` | Yes — fit assessment | No bypass — assesses confirmed article vs confirmed venue | Safe — consumes confirmed data |
| MismatchNarratorAgent | `cases.py:1891` | Yes — mismatch narration | No bypass — narrates confirmed fit assessment | Safe — consumes confirmed data |
| VenueProfilerAgent | `pipeline:87` | Yes — pipeline venue profiling | Documented bypass — pipeline is the batch/CLI path, not interactive case path | Legacy/batch path |
| agents/executor.py | `executor.py:69,72` | Internal — generic agent executor | Not a direct bypass — internal dispatch mechanism | Internal |

## Direct agent calls that bypass registry — assessment

1. **VenueDiscoveryAgent** (`cases.py:1652`): creates venue candidates for the funnel. These candidates should flow through registry in P6.2 when the discovery→registry ingest pipeline is wired. **P6.2 candidate, not a P6.1 blocker** — discovery output is new candidate generation, not fact consumption.

2. **ManuscriptVenueFitPipeline** (`pipeline:87`): the batch/CLI pipeline path. This is the legacy deterministic path used by `kairoskopion run-fixture` and `kairoskopion run-local`. It does not participate in the Case/API interactive flow. **Documented legacy bypass** — pipeline refactoring is outside P6.1 scope.

All other direct agent calls (InputClassifier, ArticleModeler, SemanticProfiler, FieldPositioners, PathwayMapper, FitAssessor, MismatchNarrator) operate on non-registry domains (article extraction, semantic analysis, fit assessment) and do not need registry-first gating.

## Tracks completed

| Track | Status | Evidence |
|---|---|---|
| 0 — Preflight | DONE | `ROUND3P6_1_PREFLIGHT.md` |
| 2 — Integration contract | DONE | `ROUND3P6_1_INTEGRATION_CONTRACT.md` |
| 3 — Discipline registry-first | DONE | `Case._run_discipline_matcher()` → `_registry.discipline_lookup()` → canonical/provisional/miss. 4 standalone + 2 Case product-path tests. |
| 4 — VenueFunnel registry candidates | DONE | `RegistryIntegrationService.build_registry_candidates_for_funnel()`. 4 standalone tests (accepted/rejected/provisional/ISSN). |
| 5 — VenueFamilyContext from registry | DONE | `Case._build_venue_family_from_venue(registry_venue_id=...)` → `_registry.build_family_context()`. 5 standalone + 1 Case product-path test. |
| 6 — VenueMatrix provenance enrichment | DONE | `Case.get_venue_matrix()` → `_registry.enrich_candidates_with_provenance()`. 3 standalone + 1 Case product-path test. |
| 7 — VenueFactExtraction → registry | DONE | `Case.investigate_venue()` → `_registry.store_venue_extraction()`. 6 standalone + 2 Case product-path tests. |
| 8 — Downstream status propagation | DONE | `_registry.propagate_status()` called in `investigate_venue()` and `get_venue_matrix()`. 3 standalone tests. |
| 9 — API integration | DONE | Registry router at `/api/registry/` (from P6-0). Case constructor accepts `registry_service`. |
| 10 — UI review surface | DEFERRED to P6.2 | API status visibility exists via `_registry_status` annotations. UI panel not yet built. |
| 11 — E2E smoke tests | DONE | 3 Case-level integration tests prove end-to-end flow. |
| 12 — Full test run | DONE | 2719 passed, 0 failed, 0 regressions. Frontend typecheck + build pass. |
| 14 — Prompt export policy | N/A | No prompt changes in P6.1. |

## Test count

| Suite | Count |
|---|---|
| Existing P6-0 tests | 100 |
| New P6.1 integration tests | 37 |
| Total P6.x tests | 137 |
| Full suite (before P6.1) | 2682 |
| Full suite (after P6.1) | 2719 |
| Frontend typecheck | PASS |
| Frontend build | PASS |

## Files changed

| File | Change |
|---|---|
| `src/kairoskopion/registry/integration.py` | Rewritten as `RegistryIntegrationService` class |
| `src/kairoskopion/registry/__init__.py` | Export `RegistryIntegrationService` |
| `src/kairoskopion/api/cases.py` | Wire `_registry` service into `__init__`, `_run_discipline_matcher`, `investigate_venue`, `_build_venue_family_from_venue`, `get_venue_matrix` |
| `tests/test_round3p6_1_integration.py` | 37 product-path integration tests |
| `docs/operations/ROUND3P6_1_REGISTRY_INTEGRATION_REPORT.md` | This report |
| `docs/operations/ROUND3P6_1_ACCEPTANCE_CHECKLIST.md` | Acceptance checklist |
