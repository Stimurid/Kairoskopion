# Round III — Merge Candidate Report

**Date:** 2026-06-27
**Branch:** `feature/round3-six-phase-build-hardening`
**Base:** `main`

## Summary

Round III P6 (Phase 6) implements registry-first acquisition pipeline and wires it into
all interactive product paths. The branch is merge-candidate ready.

## What changed

### P6-0: Registry infrastructure (commit `8368c77`)
- 10 record types with source/review lifecycle
- Generic JSONL-backed registry store
- `record_usage_status()` for canonical/provisional/rejected/unknown
- RegistryHub service with lazy-loaded registries
- API router at `/api/registry/` (CRUD + accept/reject + tasks)
- 100 tests

### P6.1: Product-path integration (commit `51e0494`)
- `RegistryIntegrationService` class — single entry point
- Discipline matching: registry-first lookup before DisciplineMatcherAgent
- Venue investigation: extraction output → provisional registry records
- Venue family context: from registry evidence (sections, parent/child)
- Venue matrix: provenance enrichment with usage_status warnings
- Status propagation: `_registry_status` on all registry-relevant outputs
- 37 tests

### P6.2: Closure and hardening (this commit)
- VenueDiscoveryAgent closure: discovered candidates → provisional records
- ManuscriptVenueFitPipeline documented as legacy/CLI-only bypass
- `GET /api/registry/review-queue` endpoint for pending records
- Bypass audit structural guard (test_no_new_agent_calls)
- 5 E2E acceptance scenarios
- 20 tests

## Test evidence

| Metric | Value |
|---|---|
| Total tests | 2739 |
| P6.x tests | 157 (100 + 37 + 20) |
| Failures | 0 |
| TypeScript typecheck | PASS |
| Frontend build | PASS |
| Regressions | 0 |

## Files changed (branch total)

| Area | Files | Lines |
|---|---|---|
| Registry infrastructure | 8 | ~2200 |
| API wiring (cases.py) | 1 | ~100 |
| Registry router | 1 | ~180 |
| Tests | 3 | ~1600 |
| Documentation | 10 | ~450 |

## Risk assessment

| Risk | Mitigation |
|---|---|
| Registry-first changes break existing flows | All 2739 tests pass, zero regressions |
| Discovery candidates stored without validation | All stored as provisional, require curator acceptance |
| Review-queue endpoint performance | Limited to 500 records max, simple list scan |
| Legacy pipeline not wired | Documented, CLI-only, not API-reachable |

## Merge readiness

- [ ] Owner review of P6.1 + P6.2 acceptance checklists
- [ ] Owner decision on 5 untracked legacy docs (stage or .gitignore)
- [ ] Owner merge command

**Branch does NOT auto-merge. Awaiting explicit owner command.**
