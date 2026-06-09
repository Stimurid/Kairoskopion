# Roadmap — Kairoskopion

Engineering queue. Each item is a concrete deliverable, not an aspiration.

## Foundation (complete)

### MVP-0 Domain skeleton
- [x] 18+ dataclass models, 22 enums, JSONL registry
- [x] Evidence layer, quality gates, operation traces, user decisions
- [x] 7 markdown card generators
- [x] Litops/WhiteCrow integration stubs
- [x] Pipeline base class

### Fixture pipeline
- [x] Synthetic fixtures: manuscript, venue guidelines, submission scenario
- [x] 9 domain services (deterministic, no LLM)
- [x] ManuscriptVenueFitPipeline (16 steps)
- [x] Markdown artifact generation

### Persistence + vault + CLI
- [x] JSONL persistence (13 registries)
- [x] Vault filesystem (8 subdirs, markdown cards)
- [x] CLI: status, run-fixture, inspect-storage
- [x] Storage root via flag/env

### Source acquisition skeleton
- [x] Local file registration with content hash
- [x] Text input registration
- [x] URL snapshot placeholder (no fetch)
- [x] 14 source roles
- [x] Evidence creation from source

### Repository operating layer
- [x] CLAUDE.md with agent instructions
- [x] PROJECT_STATUS.md, ROADMAP.md, DECISIONS.md, OPERATOR_MANUAL.md
- [x] Remote-safe push to GitHub

### Real-file pipeline (complete)

**Goal:** `kairoskopion run-local --manuscript FILE --venue-guidelines FILE --scenario FILE`

- [x] CLI command `run-local` accepting local file paths
- [x] Source registration wired into pipeline steps
- [x] SourceSnapshot created per input file, persisted to source_snapshots registry
- [x] Pipeline runs on arbitrary user-provided files
- [x] Vault artifacts and JSONL registries from real files
- [x] Tests: local files, missing file errors, unsupported extensions, invalid JSON
- [x] OPERATOR_MANUAL update

### Citation ecology stub (complete)

- [x] Bibliography parsing from manuscript text (references section extraction, year/DOI/kind detection)
- [x] BibliographyProfile model with year distribution, source kind distribution, recency profile
- [x] CitationEcologyReport: gaps, tasks, bridge references, warning signals
- [x] Reference count / recency / diversity / DOI coverage analysis
- [x] Venue expectation matching (reference limits, recency requirements)
- [x] Pipeline integration (steps 3b + 14)
- [x] JSONL registries (bibliography_profiles, citation_ecology_reports)
- [x] Vault card (citations/)
- [x] Artifact includes citation ecology section
- [x] 40 tests (bibliography parsing + citation ecology + pipeline + persistence integration)

### External adapter stubs (complete)

- [x] Adapter contracts: AdapterResult, AdapterRecord, AdapterConfig, AdapterError, AdapterStatus enum
- [x] OpenAlex mock adapter with deterministic work search
- [x] Crossref mock adapter with DOI lookup + search
- [x] OpenCitations mock adapter with citation link query
- [x] Evidence bridge: adapter result → SourceSnapshot, adapter record → EvidenceItem
- [x] Reference linking stub (DOI-based matching, no fuzzy title matching)
- [x] Mock evidence marked VENDOR_CLAIM, never FACT_FROM_SOURCE
- [x] References never marked verified by mock data
- [x] JSONL persistence: adapter_results, source_snapshots, evidence_items registries
- [x] CLI `adapters-smoke` command
- [x] 35 tests (serialization, mock adapters, bridge, evidence safety, persistence, no-network)

### Enhanced vault / exchange / freshness (complete)

- [x] Vault indexes: articles, venues, fits, citations, traces, adapters (per-section INDEX.md with tables)
- [x] Root vault index (INDEX.md) with section counts and links
- [x] Vault cross-linking: fit→article+venue, mismatch→fit, risk/compliance→article+venue, citation→article+venue
- [x] Machine-readable vault manifest (manifest.json with card paths, counts, entity IDs)
- [x] Link validation: detect broken internal markdown links, report as warnings
- [x] Export storage bundle: zip archive with registries, vault, metadata.json
- [x] Import storage bundle: append (default) or replace mode
- [x] Bundle validation: metadata presence, structure checks
- [x] Freshness tracking: FreshnessPolicy with fresh/aging/stale/expired thresholds
- [x] Source freshness: detect mock sources by parser_used field
- [x] Adapter result freshness: is_mock flag → always "mock" status
- [x] Batch freshness assessment
- [x] CLI: vault-index, export-bundle, import-bundle, validate-bundle
- [x] 43 tests (vault indexes, cross-linking, manifest, link validation, export/import, freshness)

## Document intake & entity completeness (complete)

- [x] PDF text extraction (pypdf), DOCX text extraction (python-docx)
- [x] Extraction status taxonomy (9 statuses)
- [x] FitAssessment expanded to 12 axes
- [x] RiskReport expanded to 18 risk types
- [x] ArticleModel practical fields, VenueModel enrichment fields
- [x] CLI: `intake-file`

## Real external adapters (complete)

- [x] HTTP client with stdlib urllib, caching, rate limiting
- [x] OpenAlex real adapter (work search)
- [x] Crossref real adapter (DOI lookup + search)
- [x] OpenCitations real adapter (citation links)
- [x] Adapter result caching with TTL
- [x] Per-host rate limiting (1s interval)
- [x] CLI: `--adapter-mode mock|real`

## Venue profiling & bibliography (complete)

- [x] Multi-source venue profiling from local files
- [x] Multi-style bibliography parsing (APA, numbered, Vancouver, Chicago)
- [x] PublicationTrajectoryReport synthesis
- [x] CLI: `build-venue-profile`

## Reports & submission (complete)

- [x] SubmissionPack with readiness assessment
- [x] Cover letter template generation
- [x] Required statements detection
- [x] CLI: `build-submission-pack`

## Integration bridges (complete)

- [x] Litops compatibility bridge (JSONL export, source/artifact mapping)
- [x] WhiteCrow patch queue bridge (mismatch/rewrite/compliance/risk → patches)
- [x] CLI: `export-litops-pack`, `export-whitecrow-patches`
- [ ] Vault sync with Litops Vault (Obsidian)
- [ ] Fuzzy title matching for reference linking

## Later (only when explicitly requested)

- [ ] LLM-assisted article modeling
- [ ] LLM-assisted venue profiling
- [ ] Telegram intake layer
- [ ] Web UI
- [ ] Reviewer risk simulation (controlled, labeled)
- [ ] Venue pool discovery
- [ ] Submission portal profiles
- [ ] Multi-venue comparison pipeline
