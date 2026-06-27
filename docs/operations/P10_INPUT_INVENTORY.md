# P10 Input Inventory — Source Authorities, Adapters, and Existing Data

**Date:** 2026-06-27

## 1. Source Authority Records (17 total)

From `data/seed_registry/source_authorities/source_authority_records.jsonl`:

| authority_id | authority_type | access_mode | status | P10 class |
|-------------|---------------|-------------|--------|-----------|
| vak_journal_list | official_registry | public_web | accepted | use_now_local |
| elibrary_ru | bibliographic_database | api_key_required | accepted | blocked_needs_key |
| cyberleninka | open_repository | public_web | accepted | use_now_free_public |
| openalex | bibliographic_database | free_api | accepted | use_now_free_public |
| crossref | bibliographic_database | free_api | accepted | use_now_free_public |
| opencitations | bibliographic_database | free_api | accepted | use_now_free_public |
| doaj | directory | free_api | accepted | use_now_free_public |
| unpaywall | bibliographic_database | free_api | accepted | use_now_free_public |
| scimago_jr | ranking_system | public_web | accepted | task_only_no_adapter |
| issn_portal | official_registry | public_web | accepted | task_only_no_adapter |
| istina_msu | institutional_repository | public_web | accepted | task_only_no_adapter |
| rsci | bibliographic_database | api_key_required | provisional | blocked_needs_key |
| scopus | bibliographic_database | api_key_required | provisional | blocked_paid |
| wos | bibliographic_database | api_key_required | provisional | blocked_paid |
| semantic_scholar | bibliographic_database | free_api | provisional | use_now_free_public |
| sherpa_romeo | policy_registry | free_api | provisional | task_only_no_adapter |
| motto_distribution | publisher_catalog | public_web | provisional | task_only_no_adapter |

### Classification summary

| class | count | authorities |
|-------|-------|-------------|
| use_now_local | 1 | vak_journal_list |
| use_now_free_public | 7 | cyberleninka, openalex, crossref, opencitations, doaj, unpaywall, semantic_scholar |
| task_only_no_adapter | 4 | scimago_jr, issn_portal, istina_msu, sherpa_romeo, motto_distribution |
| blocked_needs_key | 2 | elibrary_ru, rsci |
| blocked_paid | 2 | scopus, wos |

## 2. External Adapters (14 total, 8 enabled free)

From `src/kairoskopion/services/external_source_adapters.py`:

| adapter_id | enabled | cost_class | can_search | can_extract_metadata | P10 usable |
|-----------|---------|-----------|------------|---------------------|------------|
| local_file | Yes | free | No | Yes | Yes (local evidence) |
| manual_url | Yes | free | No | Yes | Yes (manual) |
| repo_docs | Yes | free | No | Yes | Yes (local evidence) |
| openalex | Yes | free | Yes | Yes | Yes (LIVE mode) |
| crossref | Yes | free | Yes | Yes | Yes (LIVE mode) |
| doaj | Yes | free | Yes | Yes | Yes (LIVE mode) |
| unpaywall | Yes | free | No | Yes | Yes (LIVE mode) |
| opencitations | Yes | free | No | Yes | Yes (LIVE mode) |
| cyberleninka | Yes | free | Yes | Yes | Yes (LIVE mode) |
| semantic_scholar | No | free | Yes | Yes | No (disabled) |
| sherpa_romeo | No | free | No | Yes | No (disabled) |
| scopus | No | paid | Yes | Yes | No (paid) |
| wos | No | paid | Yes | Yes | No (paid) |
| elibrary_ru | No | key_required | Yes | Yes | No (needs key) |

### Venue adapters (search-capable, in `src/kairoskopion/adapters/venue/`)

| adapter | modes | default mode | LIVE available | search_venues() |
|---------|-------|-------------|----------------|----------------|
| OpenAlexVenueAdapter | OFFLINE_STUB, FIXTURE, CACHED, LIVE_API | OFFLINE_STUB | Yes | Yes (per_page) |
| CrossrefVenueAdapter | OFFLINE_STUB, FIXTURE, CACHED, LIVE_API | OFFLINE_STUB | Yes | Yes |
| DOAJVenueAdapter | OFFLINE_STUB, FIXTURE, CACHED, LIVE_API | OFFLINE_STUB | Yes | Yes |
| UnpaywallVenueAdapter | OFFLINE_STUB, FIXTURE, CACHED, LIVE_API | OFFLINE_STUB | Yes | No (DOI-only) |
| OpenCitationsVenueAdapter | OFFLINE_STUB, FIXTURE, CACHED, LIVE_API | OFFLINE_STUB | Yes | No (DOI-only) |
| SnapshotCrawlerAdapter | OFFLINE_STUB, FIXTURE | OFFLINE_STUB | No | No |

**Key finding:** OpenAlex, Crossref, and DOAJ adapters support `search_venues()` in LIVE_API mode and can be used for free venue discovery. Unpaywall/OpenCitations are DOI-only — useful for known-DOI metadata enrichment, not discovery.

## 3. Discipline Seeds (15 records, all `llm_draft`)

From `data/disciplinary_landscape/seeds/ru_seed.jsonl`:

| discipline_id | display_name (ru) | source_status | education/AI relevant |
|--------------|-------------------|---------------|----------------------|
| ru-vak-pedagogy | Педагогика (5.8.1) | llm_draft | Yes — core |
| ru-pedagogical-psychology | Педагогическая психология (5.3.4) | llm_draft | Yes — core |
| ru-developing-learning-theory | Теория развивающего обучения | llm_draft | Yes — adjacent |
| ru-cultural-historical-psychology | Культурно-историческая психология | llm_draft | Yes — adjacent |
| ru-activity-theory | Теория деятельности | llm_draft | Yes — adjacent |
| ru-smd-methodology | СМД-методология | llm_draft | Yes — adjacent |
| ru-organizational-activity-pedagogy | Оргдеятельностная педагогика | llm_draft | Yes — adjacent |
| ru-vak-philosophy | Философия (5.7.x) | llm_draft | No |
| ru-vak-sociology | Социология (5.4.x) | llm_draft | No |
| ru-vak-culturology | Культурология (5.10.x) | llm_draft | No |
| ru-vak-political-science | Политология (5.5.x) | llm_draft | No |
| ru-vak-psychology-general | Общая психология (5.3.1) | llm_draft | Marginal |
| ru-vak-economics | Экономика (5.2.x) | llm_draft | No |
| ru-vak-philology | Филология (5.9.x) | llm_draft | No |
| ru-vak-law | Юриспруденция (5.1.x) | llm_draft | No |

**All seeds are `llm_draft` with `llm_pretraining` evidence — none corroborated by authoritative sources yet.**

## 4. Existing Education/AI Data

### Open acquisition tasks (6)

From `data/seed_registry/education_ai_russia/acquisition_tasks/open_tasks.json`:

| task_type | query | status |
|----------|-------|--------|
| discipline_lookup | Higher Education (Russian journals) | open |
| discipline_lookup | AI in Education (Russian journals) | open |
| discipline_lookup | Educational Technology (Russian journals) | open |
| venue_discovery | Higher Education (Russian journals) | open |
| venue_discovery | AI in Education (Russian journals) | open |
| venue_discovery | Educational Technology (Russian journals) | open |

### Venue registry for education/AI domain

**EMPTY.** No VenueRegistryRecords, no VenueMetricRecords, no VenueSectionRecords for education/AI journals.

### Existing venue evidence packs (5 — all philosophy, NOT education/AI)

| venue | ISSN | Scopus | WoS | VAK | AI/Ed fit |
|-------|------|--------|-----|-----|-----------|
| Вопросы философии | 0042-8744 | Q1 | AHCI | Yes (K1 probable) | Individual articles only |
| Философский журнал | 2072-0726 | Yes | ESCI | Yes | Minimal |
| Цифровой ученый | 2618-9267 | No | No | Yes (2022) | **Core mission — highest fit** |
| Эпистемология и фил. науки | 1811-833X | Q1-Q2 | ESCI | K1 | Active AI epistemology thread |
| Логос | 0869-5377 | Q1 | ESCI | Yes | Thematic issues only |

**Note:** Цифровой ученый has the highest alignment with AI + higher education topics (core STS/digital transformation of education focus), despite weaker indexing (no Scopus, no WoS).

## 5. P10 Execution Strategy

### What can be done NOW (no API keys, no paid services)

1. **Free adapter LIVE queries** — OpenAlex, Crossref, DOAJ can search for education/AI journals
2. **Local evidence** — existing evidence packs (philosophy) can be cross-referenced for overlap
3. **Discipline corroboration** — VAK passport data can corroborate `ru-vak-pedagogy` and `ru-pedagogical-psychology` seeds
4. **Acquisition task generation** — structured tasks for manual resolution via CyberLeninka, ScimagoJR, ISSN Portal

### What CANNOT be done (blocked)

- eLibrary.ru API queries (needs key)
- RSCI data extraction (needs key)
- Scopus/WoS queries (paid)
- Semantic Scholar adapter (disabled in code)
- Auto-promotion of any records

### Expected P10 outputs

- Provisional venue records from free API queries
- Acquisition tasks for blocked/manual sources
- Verification gate run on all records
- Review packet for owner inspection
- Gap analysis showing what remains unresolved
