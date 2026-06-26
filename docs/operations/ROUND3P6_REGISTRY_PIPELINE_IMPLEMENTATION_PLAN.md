# Round III-P6 — Registry Pipeline Implementation Plan

## 1. Storage design

Reuse existing JSONL append-only pattern from discipline_registry.
Each registry type gets its own JSONL file under `data/registry/`.
In-memory registries loaded on startup, mutations appended to JSONL.

Directory structure:
```
data/registry/
  disciplines.jsonl          (existing, move reference)
  epistemic_frameworks.jsonl
  venues.jsonl
  venue_sections.jsonl
  classification_systems.jsonl
  subject_categories.jsonl
  venue_classifications.jsonl
  venue_metrics.jsonl
  source_packets.jsonl
  acquisition_tasks.jsonl
```

## 2. Registry models

All models follow `DisciplineModel` pattern:
- Dataclass with `to_dict()`/`from_dict()`
- `source_status` + `review_status` fields
- `evidence_refs: list[EvidenceRef]`
- ID generator from `ids.py`

New shared `EvidenceRef` in registry base (generalized from discipline_registry).

Record types: EvidenceRef, SourcePacket, DisciplineRecord (exists as DisciplineModel),
EpistemicFrameworkRecord, VenueRegistryRecord, VenueSectionRecord,
ClassificationSystemRecord, SubjectCategoryRecord, VenueClassificationRecord,
VenueMetricRecord, SourceAcquisitionTask.

## 3. Registry services

Generic `BaseRegistry` class with:
- list, get, search, add_provisional, accept, reject, update_review_status
- dedupe/find_duplicate, append_evidence_ref, export_snapshot
- JSONL persistence (append on write, full load on init)

Concrete registries inherit and add type-specific search.

## 4. Review lifecycle

source_status: provisional | accepted | rejected | unknown
review_status: pending | reviewed | curator_confirmed | rejected

New records default to provisional + pending.
Accept/reject requires explicit action.
No auto-promotion.

## 5. Acquisition tasks

SourceAcquisitionTask model with lifecycle:
open → in_progress → completed | blocked | cancelled

LLM agents may create tasks. Tasks are NOT facts.

## 6. Source packets

Generalize DisciplineSourcePacket to universal SourcePacket.
Bridge between adapters/search and provisional records.

## 7. Downstream usage rules

`record_usage_status()` utility:
- accepted + curator_confirmed → canonical
- provisional/pending → usable with warning
- rejected → not usable
- unknown → unknown

## 8. API endpoints

Follow existing FastAPI patterns in api/cases.py.
New router: `/registry/` with CRUD + search + accept/reject.

## 9. UI minimal surface

Add registry types to domain.ts. Mark as P6.1 if UI work is too wide.

## 10. Tests

Registry model serialization, storage CRUD, acquisition flow,
venue section independence, metric per-db/year/category,
downstream provisional markers, API endpoints.

## 11. Non-goals

- No live external adapter implementation
- No production deployment
- No main merge
- No full schema/dataclass rename migration
- No fake external search
