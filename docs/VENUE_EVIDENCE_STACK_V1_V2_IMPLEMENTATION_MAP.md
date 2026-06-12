# Venue Evidence Stack V1–V2 Implementation Map

**Branch:** `feature/venue-evidence-stack-v1-v2`
**Architecture source:** `architecture/VENUE_EVIDENCE_STACK_CANONICAL_ARCHITECTURE.md`
**Date:** 2026-06-12

---

## Depth Levels (L0–L7)

| Level | Name | Implemented | Adapters | Agents |
|-------|------|-------------|----------|--------|
| L0 | Identity | V1 | OpenAlexVenueAdapter, CrossrefVenueAdapter | VenueIdentifierAgent |
| L1 | Official / Formal | V1 | VenueSnapshotCrawler (offline fixture) | VenueProfiler |
| L2 | Publication Model | V1 (partial) | Aggregator stub from L0 data | PublicationRegimeClassifier |
| L3 | Corpus Sample | V1 | CorpusSampler + CorpusAnalyzer (fixture) | corpus_sampler, corpus_analyzer |
| L4 | Editorial Intelligence | Stub | — | editorial_board_analyzer (planned) |
| L5 | Policy & Indexing | V1 (partial) | OpenCitationsVenueAdapter | — |
| L6 | External Graph | V1 (partial) | OpenCitationsVenueAdapter | — |
| L7 | User Memory & Outcomes | Stub | — | venue_memory_keeper (planned) |

## Purpose → Target Depth Policy Table

| Purpose | Min | Target | Max | Required Agents | Max API Calls |
|---------|-----|--------|-----|-----------------|---------------|
| `quick_look` | L0 | L2 | L2 | venue_identifier | 10 |
| `fit_assessment` | L0 | L4 | L4 | venue_identifier, venue_profiler, publication_regime_classifier, venue_publication_profile_builder | 30 |
| `venue_deep_profile` | L0 | L6 | L6 | + corpus_sampler, corpus_analyzer | 50 |
| `submission_ready` | L0 | L7 | L7 | + corpus_sampler, corpus_analyzer | 50 |

## VenueModel Field → Source → Evidence Status Map

### L0: Identity
| Field | Source | Evidence Status |
|-------|--------|-----------------|
| canonical_name | OpenAlex / Crossref | FACT_FROM_API_METADATA |
| ISSN / eISSN | Crossref / OpenAlex | FACT_FROM_API_METADATA |
| publisher_or_owner | Crossref / OpenAlex | FACT_FROM_API_METADATA |
| venue_type | OpenAlex | FACT_FROM_API_METADATA |
| official_urls | OpenAlex homepage | FACT_FROM_API_METADATA |

### L1: Formal Requirements
| Field | Source | Evidence Status |
|-------|--------|-----------------|
| scope_summary | Author guidelines snapshot | FACT_FROM_SOURCE |
| article_types_supported | Author guidelines | FACT_FROM_SOURCE |
| language_policy | Author guidelines | FACT_FROM_SOURCE |
| word_limits | Author guidelines | FACT_FROM_SOURCE |

### L3: Corpus-Derived
| Field | Source | Evidence Status |
|-------|--------|-----------------|
| genre_move_distribution | CorpusAnalyzer | CORPUS_OBSERVATION |
| method_expectations | CorpusAnalyzer | CORPUS_OBSERVATION |
| schools_and_traditions | CorpusAnalyzer | CORPUS_OBSERVATION |

### L5–L6: External
| Field | Source | Evidence Status |
|-------|--------|-----------------|
| citation_ecology | OpenCitations | FACT_FROM_API_METADATA |
| self_citation_rate | OpenCitations | FACT_FROM_API_METADATA |

## What Was Implemented in This Branch

### New modules
| Module | File | Lines |
|--------|------|-------|
| Depth model | `src/kairoskopion/venue_depth.py` | ~370 |
| Vault backend ABC | `src/kairoskopion/storage/vault_backend.py` | ~100 |
| Local FS vault | `src/kairoskopion/storage/local_fs_vault.py` | ~120 |
| Venue adapter base | `src/kairoskopion/adapters/venue/base.py` | ~95 |
| OpenAlex venue adapter | `src/kairoskopion/adapters/venue/openalex.py` | ~105 |
| Crossref venue adapter | `src/kairoskopion/adapters/venue/crossref.py` | ~90 |
| OpenCitations venue adapter | `src/kairoskopion/adapters/venue/opencitations.py` | ~100 |
| Snapshot crawler | `src/kairoskopion/adapters/venue/snapshot_crawler.py` | ~105 |
| Evidence stack service | `src/kairoskopion/services/venue_evidence_stack.py` | ~345 |
| Corpus sampler | `src/kairoskopion/services/corpus_sampler.py` | ~155 |
| Corpus analyzer | `src/kairoskopion/services/corpus_analyzer.py` | ~220 |

### Modified modules
| Module | Change |
|--------|--------|
| `enums.py` | Added FACT_FROM_API_METADATA |
| `cli.py` | 4 new CLI commands |
| `agents/venue/venue_identifier.py` | Upgraded: identity resolution from input fields |
| `agents/venue/venue_publication_profile_builder.py` | Upgraded: consumes depth coverage + corpus |
| `agents/workflows.py` | venue_deep_profile expanded with evidence stack steps |
| `agents/registry.py` | VenueIdentifier status updated |

### New test files
| File | Tests |
|------|-------|
| `tests/test_venue_evidence_stack.py` | 52+ tests |
| `tests/fixtures/venue_evidence/synthetic_corpus.json` | 6 synthetic articles |
| `tests/fixtures/venue_evidence/synthetic_venue_identity.json` | 1 synthetic venue |

### New CLI commands
| Command | Purpose |
|---------|---------|
| `inspect-venue-depth-policy` | Show depth policy for a purpose |
| `build-venue-evidence-stack` | Build evidence to depth required by purpose |
| `sample-venue-corpus` | Build corpus from fixture articles |
| `analyze-venue-corpus` | Extract method/school patterns from corpus |

## What Is Deferred to V3–V6

| Feature | Reason | Earliest Phase |
|---------|--------|----------------|
| Live OpenAlex / Crossref / OpenCitations API calls | Needs API keys + rate limiting | V3 |
| Editorial board analysis (L4) | Needs board page crawler + OpenAlex author lookups | V4 |
| Community signal collection (L4) | PhilPapers/H-Net/PhilEvents integration | V4 |
| YandexDiskVault backend | Needs Yandex API + credential management | V3 |
| Freshness orchestrator | Level-aware staleness refresh | V3 |
| Full corpus download (50 articles) | Needs OpenAlex works API | V3 |
| User memory layer (L7) | Needs persistent user outcome storage | V5 |
| Review loop integration | Post-submission, review-cycle workflow | V6 |
| Mass journal database | Explicitly excluded from scope | Never in this branch |
| Mass crawling | Explicitly excluded from scope | Never in this branch |

## Affected Agents / Services

| Agent/Service | Change | Status |
|---------------|--------|--------|
| VenueIdentifierAgent | Upgraded: normalizes name/ISSN/URL input, produces identity candidate | operational |
| VenuePublicationProfileBuilderAgent | Upgraded: consumes VenueDepthCoverage, corpus, citation, editorial data | operational |
| VenueEvidenceStack service | NEW: orchestrates depth-driven collection | operational |
| CorpusSampler service | NEW: builds PublishedArticleCorpus from fixtures | operational |
| CorpusAnalyzer service | NEW: extracts method/school patterns from text | operational |
| VenueSnapshotCrawler | NEW: stores HTML into vault (no live crawl) | offline_stub |

## Affected Workflows

| Workflow | Change |
|----------|--------|
| `venue_deep_profile` | Added venue_evidence_stack step before profile builder |
| `direct_manuscript_venue_fit` | VenueIdentifier now resolves input fields before fit |
| `uc1_draft_to_venue_pool_positioning` | Unchanged (venue_pool discovery remains seed-based) |

## Acceptance Criteria

- [x] 8-level depth model with typed enums
- [x] 4 default depth policies (quick_look, fit_assessment, venue_deep_profile, submission_ready)
- [x] VaultBackend ABC + LocalFsVault with content-addressed storage
- [x] 4 venue adapters with offline fixtures
- [x] VenueEvidenceStack orchestrator
- [x] CorpusSampler + CorpusAnalyzer with synthetic fixtures
- [x] VenueIdentifier upgraded from stub
- [x] VenuePublicationProfileBuilder consumes evidence stack
- [x] 4 CLI commands operational
- [x] All tests pass (no regression)
- [x] FACT_FROM_API_METADATA added to EvidenceStatus enum
- [x] No mass crawler, no all-journal database
- [x] All fixtures synthetic only
- [x] Offline-safe — no live network required for tests or fixtures
