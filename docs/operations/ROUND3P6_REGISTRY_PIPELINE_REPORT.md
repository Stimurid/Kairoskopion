# Round III-P6 — Registry-First Acquisition Pipeline: Implementation Report

**Date:** 2026-06-26
**Branch:** `feature/round3-six-phase-build-hardening`
**Tests before:** 2582 passed
**Tests after:** 2682 passed (+100 new P6 tests)

---

## Executive summary

P6 delivers the **registry-first acquisition pipeline** — a local evidence
base that all downstream agents, services, and UI must consult before
creating acquisition tasks for missing data. No agent may invent source
facts; unknown data creates tasks, not records.

## What was built

### Package: `src/kairoskopion/registry/`

| File | Purpose | LOC |
|------|---------|-----|
| `__init__.py` | Package exports (P6 models + stores + legacy compat) | ~60 |
| `models.py` | 10 record type dataclasses + EvidenceRef + SourcePacket + SourceAcquisitionTask | ~543 |
| `store.py` | BaseRegistry (generic JSONL-backed), SourcePacketStore, AcquisitionTaskStore, load_registry | ~361 |
| `status.py` | `record_usage_status()` — canonical/provisional_with_warning/rejected_unusable/unknown | ~30 |
| `services.py` | RegistryHub — registry-first lookup wrappers with auto-task creation | ~170 |
| `legacy.py` | Old `registry.py` moved here — append/read_all/list_ids/find_by_id (backward compat) | ~74 |

### API: `src/kairoskopion/api/registry_router.py`

FastAPI router at `/api/registry/` with:
- `GET /types` — list available registry types
- `GET /{record_type}` — list/search records
- `GET /{record_type}/{record_id}` — get single record
- `POST /{record_type}` — add provisional (with dedup check)
- `POST /{record_type}/{record_id}/accept` — curator accept
- `POST /{record_type}/{record_id}/reject` — curator reject
- `GET /tasks/open` — list open acquisition tasks
- `GET /tasks/all` — list all acquisition tasks

### Tests: `tests/test_round3p6_registry.py`

100 tests covering:
- EvidenceRef, SourcePacket, SourceAcquisitionTask serialization (9 tests)
- All 8 registry record types round-trip (16 tests)
- Constants validation (3 tests)
- `record_usage_status()` — all 7 combinations (7 tests)
- JSONL I/O helpers (5 tests)
- BaseRegistry in-memory CRUD (20 tests)
- BaseRegistry JSONL persistence (3 tests)
- Parametrized all-record-types (6 tests)
- SourcePacketStore (3 tests)
- AcquisitionTaskStore (4 tests)
- load_registry convenience (2 tests)
- Search by code/label (2 tests)
- VenueMetricRecord no-collapse invariant (2 tests)
- Edge cases (4 tests)
- RegistryHub service layer (7 tests)
- Registry API router (6 tests)

## Record types implemented

| Record | ID field | ID prefix | Status fields |
|--------|----------|-----------|---------------|
| DisciplineRecord | discipline_id | `disc_` | source_status + review_status |
| EpistemicFrameworkRecord | framework_id | `epfr_` | source_status + review_status |
| VenueRegistryRecord | venue_id | `vrec_` | source_status + review_status |
| VenueSectionRecord | section_id | `vsec_` | source_status + review_status |
| ClassificationSystemRecord | system_id | `csys_` | source_status + review_status |
| SubjectCategoryRecord | category_id | `scat_` | source_status + review_status |
| VenueClassificationRecord | record_id | `vclf_` | evidence_status + review_status |
| VenueMetricRecord | metric_id | `vmet_` | evidence_status + review_status |

## Review lifecycle

```
NEW RECORD → provisional + pending
    ↓ curator reviews
provisional + reviewed
    ↓ curator confirms
accepted + curator_confirmed → CANONICAL (downstream: safe to use)
    OR
rejected + rejected → REJECTED (downstream: unusable)
```

`record_usage_status()` maps these to downstream-usable labels:
- `canonical` — accepted + curator_confirmed
- `provisional_with_warning` — provisional (any review status)
- `rejected_unusable` — either field is rejected
- `unknown` — everything else

## Key design decisions

1. **Legacy compatibility:** Old `registry.py` moved to `registry/legacy.py`
   and re-exported from `__init__.py`. All 2582 existing tests pass without
   any import changes elsewhere.

2. **VenueClassificationRecord/VenueMetricRecord** use `evidence_status`
   instead of `source_status` — these are link/measurement records, not
   entity records; their lifecycle is about evidence quality, not entity
   acceptance.

3. **VenueMetricRecord is per-database/year/category** — never collapse to
   `journal.quartile = Q1`. Each metric is its own record.

4. **VenueSectionRecord is independent** — section scope != parent venue
   scope. Sections are first-class records.

5. **RegistryHub creates acquisition tasks automatically** when a lookup
   finds nothing — agents get tasks, not fabricated data.

## Track completion matrix

| Track | Description | Status |
|-------|-------------|--------|
| 1 | Branch footprint audit | DONE |
| 2 | Registry code inventory | DONE |
| 3 | Implementation plan | DONE |
| 4 | Registry record models (10 types) | DONE |
| 5 | JSONL storage (BaseRegistry) | DONE |
| 6 | Service layer (RegistryHub) | DONE |
| 7 | Acquisition task integration | DONE |
| 8 | DisciplineSourceAcquisition wiring | DEFERRED (P6.1) |
| 9 | VenueFunnel wiring | DEFERRED (P6.1) |
| 10 | VenueFamilyContext wiring | DEFERRED (P6.1) |
| 11 | VenueMatrix wiring | DEFERRED (P6.1) |
| 12 | VenueFactExtraction wiring | DEFERRED (P6.1) |
| 13 | Downstream canonical/provisional utility | DONE |
| 14 | API endpoints | DONE |
| 15 | UI minimal review surface | DEFERRED (P6.1) |
| 16 | Comprehensive tests (100 tests) | DONE |
| 17 | Implementation report | THIS FILE |
| 18 | Prompt export policy | N/A (no prompt changes) |
| 19 | Commit | PENDING |
| 20 | Final response | PENDING |

## Deferred to P6.1

Tracks 8-12 (wiring existing agents to registry-first flow) and Track 15
(UI review surface) are deferred. They require modifying working agent code
to add registry lookups before LLM calls — the infrastructure is ready but
the integration is better done as a focused pass after the base layer is
stable and tested.

## Files changed

### New files
- `src/kairoskopion/registry/__init__.py`
- `src/kairoskopion/registry/models.py`
- `src/kairoskopion/registry/store.py`
- `src/kairoskopion/registry/status.py`
- `src/kairoskopion/registry/services.py`
- `src/kairoskopion/registry/legacy.py` (moved from `src/kairoskopion/registry.py`)
- `src/kairoskopion/api/registry_router.py`
- `tests/test_round3p6_registry.py`
- `docs/operations/ROUND3P6_BRANCH_FOOTPRINT_AUDIT.md`
- `docs/operations/ROUND3P6_REGISTRY_PIPELINE_INVENTORY.md`
- `docs/operations/ROUND3P6_REGISTRY_PIPELINE_IMPLEMENTATION_PLAN.md`

### Modified files
- `src/kairoskopion/api/app.py` (include registry router)

### Deleted files
- `src/kairoskopion/registry.py` (moved to `registry/legacy.py`)
