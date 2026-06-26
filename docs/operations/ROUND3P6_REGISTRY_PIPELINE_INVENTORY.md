# Round III-P6: Registry Pipeline Inventory

> Generated 2026-06-26. Source: audit of `src/kairoskopion/` codebase.

## 1. Inventory Table

| Existing Component | Path | Usable for P6? | Notes |
|--------------------|------|----------------|-------|
| **Generic JSONL engine** (`registry.py`) | `src/kairoskopion/registry.py` | YES — foundation | `append()`, `read_all()`, `find_by_id()`, `list_ids()`. Flat JSONL, no indexing, no update. All registries build on this. |
| **Pipeline persistence** (`persistence.py`) | `src/kairoskopion/persistence.py` | YES — pattern to follow | `save_pipeline_result()` writes 14+ entity types. Layout: `.kairoskopion/registries/*.jsonl`. |
| **VenueProfileRegistry** | `src/kairoskopion/services/venue_profile_registry.py` | YES — best template | In-memory indexed registry for `VenueProfilePackage`. Triple-indexed (name, ISSN, OpenAlex ID). Sophisticated merge/upsert with completeness-downgrade protection. JSONL append-only, last-write-wins. |
| **VenueMemoryRegistry** | `src/kairoskopion/services/venue_memory.py` | YES — review_status pattern | `VenueMemoryRecord` with `review_status` lifecycle: provisional -> candidate -> accepted/rejected/superseded. Append-only JSONL. |
| **DisciplineRegistry** (loader) | `src/kairoskopion/services/discipline_registry/loader.py` | PARTIAL — read-only | Seeds from `data/disciplinary_landscape/seeds/*.jsonl`, live registry from `registry/disciplinary_landscape.jsonl`. In-memory `_by_id` dict. Has `add()` but NO JSONL write-back built in. Keyword matcher for pre-filtering. |
| **DisciplineModel** | `src/kairoskopion/services/discipline_registry/model.py` | YES — working-tool model | Full dataclass with `source_status` (9 values), `evidence_refs`, `EvidenceRef` sub-model, `KeyAuthor` sub-model. `to_dict`/`from_dict`. |
| **CorrectionRegistry** | `src/kairoskopion/api/cases.py:2567` | YES — pattern reference | Class-method singleton. Append-only JSONL. `analyze_signals()` detects recurring correction patterns. |
| **CaseStore** | `src/kairoskopion/api/cases.py:~2695` | NO — different paradigm | Single JSON file per case (not JSONL). Atomic tmp+replace writes. User-scoped paths. Not registry pattern. |
| **UserStore** | `src/kairoskopion/api/auth.py` | YES — pattern reference | JSONL append-only, in-memory `_by_id`/`_by_email` indexes. Last-write-wins. |
| **VenueRecord** | `src/kairoskopion/schema.py:698` | YES — existing model | `venue_record_id`, `canonical_name`, `aliases`, `issn`, `eissn`, `publisher`, `official_urls`. No `source_status`/`review_status`. |
| **VenueSource** | `src/kairoskopion/schema.py:711` | YES — existing model | `venue_source_id`, `venue_record_id`, `source_url`, `source_type`, `retrieved_at`, `freshness_window_days`, `extracted_by`. |
| **VenueClaim** | `src/kairoskopion/schema.py:726` | YES — existing model | `venue_claim_id`, `venue_record_id`, `venue_source_id`, `claim_path`, `claim_value`, `evidence_status`, `confidence`, `conflict_group`. |
| **VenueEvidencePack** | `src/kairoskopion/schema.py:740` | YES — existing model | `evidence_pack_id`, `venue_record_id`, `profile`, `official_facts`, `external_claims`, `inferences`, `unknowns`, `conflicts`, `stale_warnings`, `build_log`. |
| **Venue registry service** | `src/kairoskopion/services/venue_registry.py` | YES — seed import + pack build | `import_venue_seed_corpus()`, `persist_import_result()`, `build_venue_evidence_pack()` with claim conflict resolution (official_fact > external_claim > inference). Staleness detection. Markdown renderer. |
| **DisciplineRecord** (P5C) | `src/kairoskopion/schema.py:1808` | YES — model exists, NO persistence | `discipline_record_id`, `display_name`, `display_names`, `aliases`, `parent_discipline_id`, `source_status` (provisional/accepted/rejected), `review_status` (pending/reviewed/curator_confirmed), `evidence_refs`, `provenance`. |
| **EpistemicFrameworkRecord** (P5C) | `src/kairoskopion/schema.py:1828` | YES — model exists, NO persistence | `framework_record_id`, `framework_kind` (open label), `discipline_record_ids`, `source_status`, `review_status`, `evidence_refs`. |
| **VenueSectionRecord** (P5C) | `src/kairoskopion/schema.py:1854` | YES — model exists, NO persistence | `venue_section_record_id`, `parent_venue_id`, `section_type`, `target_disciplines`, `status` (active/closed/unknown), `evidence_refs`, `source_status`. No `review_status`. |
| **ClassificationSystemRecord** (P5C) | `src/kairoskopion/schema.py:1878` | YES — model exists, NO persistence | `classification_system_record_id`, `system_name`, `publisher`, `version`, `evidence_refs`, `source_status`. No `review_status`. |
| **SubjectCategoryRecord** (P5C) | `src/kairoskopion/schema.py:1898` | YES — model exists, NO persistence | `subject_category_record_id`, `classification_system_id`, `code`, `display_name`, `parent_category_id`, `evidence_refs`, `source_status`. |
| **VenueClassificationRecord** (P5C) | `src/kairoskopion/schema.py:1916` | YES — model exists, NO persistence | `venue_classification_record_id`, `venue_id`, `venue_section_id`, `classification_system_id`, `subject_category_id`, `year`, `evidence_refs`, `source_status`. |
| **VenueMetricRecord** (P5C) | `src/kairoskopion/schema.py:1938` | YES — model exists, NO persistence | `venue_metric_record_id`, `venue_id`, `venue_section_id`, `classification_system_id`, `subject_category_id`, `year`, `metric_type`, `metric_value`, `metric_source`, `evidence_refs`, `source_status`. |
| **VF-C3 subobject models** (13 models) | `src/kairoskopion/schema.py` | PARTIAL — embedded only | `JournalModel`, `SectionModel`, `SpecialIssueModel`, `EditorialBoardMember`, `EditorialBoardCloud`, `PublishedCorpusHull`, `MethodExpectationProfile`, `GenreMoveProfile`, `StyleRegisterProfile`, `AuthorEligibilityProfile`, `TimeReviewProfile`, `APCAccessProfile`, `TacitVenueSignal`. All have `evidence_refs`, `source_category`, `confidence`, `evidence_status`. Stored inside VenueProfilePackage by ID — no standalone persistence. |
| **Venue adapters** (13 adapters) | `src/kairoskopion/adapters/venue/` | YES — source acquisition | OpenAlex, Crossref, DOAJ, Unpaywall, OpenCitations, SemanticScholar, Sherpa, Cyberleninka, EditorialBoard, GuidelinesExtractor, OpenAlexWorks, VenueUrlHop, SnapshotCrawler. All use `VenueAdapterMode` (OFFLINE_STUB/FIXTURE/CACHED/LIVE_API). |
| **VenueAdapterMode / Config** | `src/kairoskopion/adapters/venue/base.py` | YES — mode infrastructure | `VenueAdapterMode` enum, `VenueAdapterConfig`, `SourceAcquisitionConfig` with `effective_mode()` degradation. |
| **Source evidence packet** | `src/kairoskopion/services/source_evidence_packet.py` | YES — aggregation pattern | `build_packet_from_case()` aggregates case inputs into `SourceEvidencePacket`. |
| **LocalFsVault** | `src/kairoskopion/storage/local_fs_vault.py` | YES — binary storage | Writes bytes + `.meta.json` sidecar. Content-hash, kind, size_bytes. |


## 2. Existing Persistence Patterns

### 2.1 Generic JSONL engine (`registry.py`)

Core functions: `append(name, record)`, `read_all(name)`, `find_by_id(name, entity_id)`, `list_ids(name)`.

- Files stored under a configurable `base_dir`, one JSON object per line.
- **Append-only.** No update-in-place, no delete.
- ID resolution tries: `id_field`, then `{name}_id`, then `entity_id`.
- No indexing, no in-memory caching at this level.

### 2.2 Pipeline result persistence (`persistence.py`)

- Layout: `.kairoskopion/registries/{name}.jsonl`
- `save_pipeline_result()` writes 14+ entity types (article_models, manuscripts, venue_models, fit_assessments, etc.)
- `save_adapter_result()` writes to `adapter_results.jsonl`
- `list_registries()`, `read_registry()` for discovery and read-back.

### 2.3 Indexed in-memory registries

Three implementations exist, each re-implementing the pattern:

| Registry | Index keys | Merge strategy | Write-back |
|----------|-----------|---------------|------------|
| `VenueProfileRegistry` | name, ISSN, OpenAlex ID | Identity-merge, list union, dict merge, completeness-downgrade protection | JSONL append, last-write-wins |
| `VenueMemoryRegistry` | name, ISSN (linear scan) | Fact list append | JSONL append, last-write-wins |
| `DisciplineRegistry` | discipline_id (dict) | Last-write-wins on load | **NO write-back** (read-only loader) |

### 2.4 CaseStore (different paradigm)

- One JSON file per case: `{data_dir}/users/{user_id}/cases/{case_id}.json`
- Atomic tmp+replace writes.
- NOT JSONL, NOT append-only. Full-state snapshots.
- Not usable as registry pattern.


## 3. Existing Venue Evidence Infrastructure

### 3.1 Core models (schema.py)

`VenueRecord` -> `VenueSource` -> `VenueClaim` -> `VenueEvidencePack`

- One VenueRecord has many VenueSources (linked by `venue_record_id`).
- One VenueSource has many VenueClaims (linked by `venue_source_id`).
- VenueClaim has `claim_path` (field name), `claim_value`, `evidence_status` (official_fact/external_claim/inference/unknown), `confidence`, `conflict_group`.
- VenueEvidencePack is a resolved view: profile dict + provenance lists + conflicts + stale_warnings.

### 3.2 Venue registry service (`venue_registry.py`)

- **Seed import:** `import_venue_seed_corpus(corpus_dir)` reads `venues.jsonl`, `sources.jsonl`, `claims.jsonl`. Validates referential integrity (venue_record_id, venue_source_id).
- **Persist:** `persist_import_result()` writes to JSONL registries via `registry.py`.
- **Evidence pack build:** `build_venue_evidence_pack()` resolves claims with:
  - Official fact wins over external claim wins over inference.
  - Conflict detection via `conflict_group` markers or differing values.
  - Staleness detection via `freshness_window_days` per source type.
- **Markdown render:** `evidence_pack_to_markdown()` for human-readable output.

### 3.3 Venue adapters (13 adapters)

All return `VenueAdapterResult` with `claims: list[VenueAdapterClaim]`, `authority_assessment`, `evidence_status`, `raw_data`, `vault_ref`, `cache_ref`, `unknowns`, `provenance`.

Mode infrastructure via `SourceAcquisitionConfig`:
- Global `live_enabled` kill switch.
- Per-adapter `VenueAdapterConfig` with mode, timeout, retry, cache settings.
- `effective_mode()` degrades LIVE_API to OFFLINE_STUB when live is disabled.


## 4. Existing Discipline Registry

### 4.1 DisciplineModel (`services/discipline_registry/model.py`)

Full working-tool dataclass with 30+ fields:
- Identity: `discipline_id`, `display_names` (lang dict), `aliases`, `region`
- Status: `source_status` (9 values: llm_draft, needs_review, user_confirmed, auto_enriched, disputed, merged, deprecated, rejected, candidate)
- Provenance: `evidence_refs: list[EvidenceRef]`, `confidence_by_section`, `unknowns`, `disputed_fields`
- Body: paradigm, epistemic_regime, forms_of_evidence, canonical_questions, legitimate/illegitimate_objects, argument_styles, publication_genres, methods, instruments, ontologies, key_authors, boundaries, adjacent, typical_venues
- Stats: `first_seen_in_case`, `times_seen`, `last_enriched`

### 4.2 DisciplineRegistry loader (`services/discipline_registry/loader.py`)

- Seeds: `data/disciplinary_landscape/seeds/*.jsonl` (immutable, ship-with-repo)
- Live: `data/disciplinary_landscape/registry/disciplinary_landscape.jsonl` (mutable)
- Load order: seeds first, then live overlay (last-write-wins by `discipline_id`)
- Methods: `get(id)`, `all()`, `by_region(region)`, `candidates_keyword(text, region, limit)`, `adjacent_of(id)`, `add(discipline)`
- **No JSONL write-back.** `add()` only mutates in-memory dict.

### 4.3 P5C DisciplineRecord vs DisciplineModel — two parallel models

| Aspect | DisciplineModel (disc. registry) | DisciplineRecord (schema.py P5C) |
|--------|----------------------------------|----------------------------------|
| Location | `services/discipline_registry/model.py` | `schema.py:1808` |
| Base class | Custom dataclass | `_DictMixin` dataclass |
| ID field | `discipline_id` | `discipline_record_id` |
| Status | `source_status` (9 values) | `source_status` (3) + `review_status` (3) |
| Evidence | `evidence_refs: list[EvidenceRef]` (typed) | `evidence_refs: list[str]` (IDs only) |
| Body | 30+ working-tool fields | Minimal: display_name, aliases, parent_discipline_id |
| Persistence | Seeds + live JSONL (loader) | **None** |
| Write-back | In-memory only | **None** |

**These are NOT the same model.** DisciplineModel is the rich working-tool card; DisciplineRecord is the lightweight registry stub created in P5C. P6 must decide which to use or how to bridge them.


## 5. Gaps — What P6 Needs That Does Not Exist

### 5.1 Missing persistence for P5C registry record types

Seven schema.py models have NO persistence layer:

| Model | Has `to_dict`/`from_dict` | Has JSONL store | Has in-memory index | Has service class |
|-------|--------------------------|-----------------|--------------------|--------------------|
| `DisciplineRecord` | YES | NO | NO | NO |
| `EpistemicFrameworkRecord` | YES | NO | NO | NO |
| `VenueSectionRecord` | YES | NO | NO | NO |
| `ClassificationSystemRecord` | YES | NO | NO | NO |
| `SubjectCategoryRecord` | YES | NO | NO | NO |
| `VenueClassificationRecord` | YES | NO | NO | NO |
| `VenueMetricRecord` | YES | NO | NO | NO |

### 5.2 No generic indexed registry class

Each existing registry (VenueProfileRegistry, VenueMemoryRegistry, DisciplineRegistry, UserStore) re-implements the JSONL load/append/index pattern independently. There is no shared `IndexedJSONLRegistry[T]` base class.

P6 could:
- (a) Continue the pattern — one class per record type (7 new classes).
- (b) Build a generic `TypedJSONLRegistry[T]` with configurable index keys, then instantiate for each P5C type.

### 5.3 No unified review/source status enum

Three different status vocabularies coexist:

| Component | Field | Values |
|-----------|-------|--------|
| DisciplineModel | `source_status` | llm_draft, needs_review, user_confirmed, auto_enriched, disputed, merged, deprecated, rejected, candidate |
| P5C records | `source_status` | provisional, accepted, rejected |
| P5C records | `review_status` | pending, reviewed, curator_confirmed |
| VenueMemoryRecord | `review_status` | provisional, candidate, accepted, rejected, superseded |

P6 must either unify these or document why they differ.

### 5.4 No `evidence_refs` referential integrity

`evidence_refs` is `list[str]` everywhere — plain IDs with no typed reference resolution, no existence checks, no registry that validates the referenced evidence items exist. The DisciplineModel uses typed `list[EvidenceRef]` (richer), but schema.py P5C records use `list[str]`.

### 5.5 No DisciplineRegistry write-back

The existing `DisciplineRegistry.add()` only mutates the in-memory dict. There is no method to append a new or updated discipline to the live JSONL file. P6 needs write-back for pipeline-created discipline records.

### 5.6 No classification/metric pipeline

The models exist (`ClassificationSystemRecord`, `SubjectCategoryRecord`, `VenueClassificationRecord`, `VenueMetricRecord`) but there is:
- No service to import classification data from adapters (Scopus ASJC, WoS categories, VAK specialties)
- No service to build/resolve metric records from adapter results
- No quartile/rank pipeline that connects adapter results to these models

### 5.7 No VenueSectionRecord population pipeline

`VenueSectionRecord` exists as a model but there is:
- No service to discover/create sections from venue investigation results
- No link from `SectionModel` (VF-C3 subobject inside VenueProfilePackage) to `VenueSectionRecord` (standalone registry record)
- No pipeline step that extracts sections from adapter results

### 5.8 No cross-registry linkage service

No service that:
- Links a `VenueClassificationRecord` to both a `VenueRecord` and a `SubjectCategoryRecord`
- Links a `VenueSectionRecord` to its parent `VenueRecord`
- Links a `DisciplineRecord` to related `EpistemicFrameworkRecord`s
- Validates referential integrity across registries

### 5.9 DisciplineRecord vs DisciplineModel bridge

No mapping between the lightweight P5C `DisciplineRecord` and the rich `DisciplineModel`. They have different ID fields (`discipline_record_id` vs `discipline_id`), different status vocabularies, and different evidence_refs types. P6 must decide:
- Use DisciplineModel as the canonical store and DisciplineRecord as a lightweight reference?
- Merge them into one model?
- Keep both with an explicit bridge?
