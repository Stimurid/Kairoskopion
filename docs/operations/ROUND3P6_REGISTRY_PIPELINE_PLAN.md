# Round III-P6: Registry Pipeline Plan

**Status:** PLAN ONLY — no implementation in this pass.
**Date:** 2026-06-26
**Branch:** feature/round3-six-phase-build-hardening

## Overview

P5C introduced 7 registry record types as dataclasses. P6 wires them
into a production pipeline: JSONL persistence, services, acquisition
flow, downstream consumption rules, and UI/API surface.

## Registry Record Types (from P5C)

| Record | ID prefix | Purpose |
|--------|-----------|---------|
| DisciplineRecord | `drec_` | Discipline taxonomy entry |
| EpistemicFrameworkRecord | `efrec_` | Epistemic framework (tradition, method family, theorem family, etc.) |
| VenueSectionRecord | `vsrec_` | Venue section/track/special issue |
| ClassificationSystemRecord | `csrec_` | Classification system (OECD, ASJC, VAK, etc.) |
| SubjectCategoryRecord | `screc_` | Subject category within a classification system |
| VenueClassificationRecord | `vcrec_` | Venue-to-category mapping (per year, per section) |
| VenueMetricRecord | `vmrec_` | Venue metric (quartile, IF, etc.) per database/year/category/section |

## JSONL Registries

Each record type gets an append-only JSONL file under `$KAIROSKOPION_DATA_DIR/registries/`:

- `disciplines.jsonl`
- `epistemic_frameworks.jsonl`
- `venue_sections.jsonl`
- `classification_systems.jsonl`
- `subject_categories.jsonl`
- `venue_classifications.jsonl`
- `venue_metrics.jsonl`

Standard pattern: `append(record)`, `load_all()`, `find_by_id()`,
`find_by(field, value)`. Same as existing VenueRecord/VenueSource/VenueClaim
registries.

## Services

### RegistryStore (generic)

Stateless service that reads/appends JSONL for any record type.
Parameterized by dataclass type + file path. No SQL, no ORM.

### DisciplineRegistryService

- `seed_from_adapter(adapter_result)` — creates provisional records
- `promote(record_id, evidence_refs)` — changes source_status to confirmed
- `find_by_name(name, language)` — fuzzy match across display_names/aliases
- `merge(source_id, target_id)` — dedup with provenance chain

### VenueMetricService

- `upsert_metric(venue_id, metric_type, value, source, year, category_id, section_id)`
- Invariant: never collapse across databases/years/categories/sections
- `get_metrics(venue_id)` → list, always multi-valued

## Acquisition Flow

```
1. User/pipeline provides discipline name + region hint
2. Check local DisciplineRecord registry (base-first)
3. If gap → DisciplineSourceAcquisitionAgent proposes search tasks
4. Adapters execute tasks (OpenAlex, DOAJ, VAK, etc.)
5. Results → provisional DisciplineRecords + SubjectCategoryRecords
6. Curator review → promote/reject/merge
```

No LLM-recalled codes at any step. Codes come from adapter results only.

## Downstream Rules

1. **FitAssessor** may read DisciplineRecords to validate discipline claims
2. **VenueProfiler** reads VenueClassificationRecords + VenueMetricRecords
3. **FieldPositionModel** uses framework_affiliation_vector (from EpistemicFrameworkRecords as seeds, not as axis values)
4. **Vault cards** render registry records as linked entities
5. **UI** shows per-database/year/category metric tables, never single-value

## UI/API Surface

- `GET /registries/{type}` — list records
- `GET /registries/{type}/{id}` — single record
- `POST /registries/{type}` — create provisional
- `PATCH /registries/{type}/{id}` — update status/evidence
- UI: registry browser with search, linked to venue/discipline views

## Non-goals for P6

- No automatic promotion (always curator-gated)
- No cross-repo sync (stays within Kairoskopion bounded context)
- No UI editing of record content (API + curator workflow only)
