# Venue Evidence Stack V1–V2 Foundation Report

**Branch:** `feature/venue-evidence-stack-v1-v2`
**Date:** 2026-06-12
**Base commit:** `babcbbc`

## Summary

Implemented the Venue Evidence Stack foundation: 8-level depth model, demand-driven depth policies, content-addressed vault storage, 4 venue adapters (OpenAlex, Crossref, OpenCitations, SnapshotCrawler), corpus sampling and analysis services, and full integration into the agentic workflow layer.

## What was built

### Depth model (`venue_depth.py`, ~370 lines)
- `VenueEvidenceDepthLevel` enum: L0_IDENTITY through L7_USER_MEMORY_AND_OUTCOMES
- `VenueAnalysisPurpose` enum: 6 analysis purposes
- `VenueDepthPolicy` dataclass: configurable depth routing with source roles, agents, stop conditions, degradation rules
- 4 default policies: QUICK_LOOK (→L2), FIT_ASSESSMENT (→L4), VENUE_DEEP_PROFILE (→L6), SUBMISSION_READY (→L7)
- `VenueDepthCoverage`: per-level status tracking (fresh/partial/stale/never_run)

### Vault storage (`storage/vault_backend.py`, `storage/local_fs_vault.py`)
- `VaultBackend` ABC: content-addressed storage with SHA-256[:16] hashing
- `VaultObjectKind` enum: 8 object types
- `LocalFsVault`: filesystem implementation with metadata sidecars

### Venue adapters (`adapters/venue/`)
- `VenueAdapter` ABC with `VenueAdapterMode` (offline_stub/live_api/cached_snapshot)
- `OpenAlexVenueAdapter`: ISSN-based venue lookup (fixture mode)
- `CrossrefVenueAdapter`: journal metadata (fixture mode)
- `OpenCitationsVenueAdapter`: citation link data (fixture mode)
- `VenueSnapshotCrawler`: homepage HTML capture with vault integration

### Services (`services/`)
- `venue_evidence_stack.py`: `build_venue_evidence_stack()` orchestrator — collects evidence level-by-level up to policy depth
- `corpus_sampler.py`: `sample_venue_corpus()` — builds PublishedArticleCorpus from fixtures with distribution analysis
- `corpus_analyzer.py`: `analyze_venue_corpus()` — extracts method/school/citation patterns from corpus

### Agent upgrades
- `VenueIdentifierAgent`: rewritten from stub to functional identity resolution with ISSN normalization, resolution_status, ambiguity tracking
- `VenuePublicationProfileBuilderAgent`: rewritten to consume depth_coverage, corpus, citation_profile, editorial_board with explicit unknowns per missing layer
- `CorpusSamplerAgent`: new thin wrapper around corpus_sampler service for workflow integration

### Workflow integration
- `direct_manuscript_venue_fit`: added `venue_identifier` step (step 1, 9 steps total)
- `venue_deep_profile`: added `corpus_sampler` step (step 1, 4 steps total)
- Registry updated: venue_identifier → operational_now, corpus_sampler registered

### Schema fix
- `topic_clusters` type corrected: `list[str]` → `list[dict[str, Any]]` to match sampler output

### CLI commands (4 new)
- `inspect-venue-depth-policy --purpose PURPOSE`
- `build-venue-evidence-stack --venue-name NAME --purpose PURPOSE`
- `sample-venue-corpus --fixture FILE [--venue-id ID]`
- `analyze-venue-corpus --fixture FILE`

### Tests
- 73 venue evidence stack tests covering: depth model, vault, adapters, evidence stack, corpus sampler, corpus analyzer, topic_clusters type, VenueIdentifier agent, ProfileBuilder agent, workflow integration
- 855 total tests, all passing (was 834)

## What is deferred

- L4 editorial board data collection (needs real API or curated fixtures)
- L5 policy/indexing integration (DOAJ, Sherpa/Romeo)
- L6 external citation graph (OpenCitations live mode)
- L7 user memory/outcomes tracking
- Live API mode for all adapters (currently offline_stub only)
- Vault persistence across CLI invocations (currently in-memory per run)

## Constraints honored

- No new infrastructure layers
- No mass crawling or real journal database collection
- No live network required in tests
- All fixtures synthetic
- No force-push, no destructive git operations
- No private_inputs or generated storage in git
