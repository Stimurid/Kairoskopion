# Changelog — Kairoskopion

All notable changes to this project will be documented in this file.

## [0.7.0-logos-evidence-pack] — 2026-06-10

### Fixed
- **D11:** Language policy extraction no longer confuses metadata language with article body language. New `_extract_language_policy()` checks dedicated Language Policy section, scope signals, and Submission Requirements with proper disambiguation. Journals requiring bilingual metadata but Russian-only articles are now correctly identified.

### Added
- Logos venue evidence pack: 10 source notes from official/external sources
- Full pipeline rerun with evidence pack (poor_fit, 1 blocking mismatch)
- 5 new language policy extraction tests (`TestLanguagePolicyExtraction`)
- Comparison report: `docs/TRIAL_LOGOS_EVIDENCE_RERUN_REPORT.md`

### Changed
- Fit assessment: possible_but_costly → **poor_fit** (language barrier surfaced)
- Mismatch map: 0 blocking → **1 blocking** (language_register)
- Risk report: 0 blocking → **1 blocking** (desk_reject_risk)
- Submission pack: needs_file_update → **not_ready** (2 blocking items)
- Rewrite plan: 3 proposed + 10 conditional → **4 proposed + 8 conditional**

### Stats
- 597 tests passing (was 592)
- D10 closed: UNKNOWN seed replaced with real evidence pack
- D11 closed: language policy extraction bug

---

## [0.6.1-logos-trial-quality] — 2026-06-10

### Fixed (Logos Target Trial — D1-D9)
- **D1:** Venue name extraction from seed files (multi-format heading/field parsing)
- **D2:** Venue model no longer hallucinates structured fields from UNKNOWN seeds (UNKNOWN-section-aware extraction)
- **D3:** Venue unknowns propagated from explicit UNKNOWN sections in seed files
- **D4:** Genre classification handles philosophical/theoretical articles (multi-marker scoring)
- **D5:** Method classification handles conceptual/philosophical articles
- **D6:** RewritePlan generates conditional trajectory actions under venue uncertainty (evidence collection, guideline verification, language/citation bridge preparation)
- **D7:** AI disclosure detection no longer false-positives on AI-as-topic articles
- **D8:** Bibliography parser extracts title_fragment from Chicago/APA/author-date/quoted references
- **D9:** source_kind classification improved: report detection (UNESCO, OECD, working papers), DOI-based journal inference, tightened chapter markers

### Added
- `tests/test_rewrite_planning.py` — 10 tests for conditional rewrite behavior
- 6 title_fragment extraction tests, 9 source_kind classification tests
- Trial report: `docs/TRIAL_LOGOS_REPORT.md` with full 10-section audit

### Stats
- 592 tests passing (was 556)
- RewritePlan: 13 actions under venue uncertainty (was 0)
- Bibliography: 42/42 titles extracted (was 0/42)

---

## [0.6.0-whitecrow-bridge] — 2026-06-09

### Added (Sprints 1–8)
- **Sprint 1: Document intake** — PDF extraction (pypdf), DOCX extraction (python-docx), improved text intake with extraction status taxonomy (9 statuses), CLI `intake-file`
- **Sprint 2: Entity completeness** — FitAssessment expanded to 12 axes (topic, discipline, genre, argument_structure, method, citation_ecology, novelty_positioning, language_register, audience, formal_compliance, author_eligibility, publication_regime), RiskReport expanded to 18 risk types, ArticleModel practical fields (word_count, section_count, etc.), VenueModel enrichment fields (ai_policy, data_policy, etc.)
- **Sprint 3: Real adapters** — HTTP client with stdlib urllib, per-host rate limiting, file-based JSON cache, Crossref/OpenAlex/OpenCitations real mode (mock default), CLI `--adapter-mode` flag
- **Sprint 4: Venue profile builder** — Multi-source venue profiling from local files, role guessing, merge log, CLI `build-venue-profile`
- **Sprint 5: Bibliography & trajectory** — Multi-style reference parsing (APA, numbered, Vancouver, Chicago), reference style detection, PublicationTrajectoryReport combining fit+risk+bibliography
- **Sprint 6: Submission pack** — SubmissionPack preparation with readiness assessment (5 statuses), cover letter template, required statements, blocking issue detection, CLI `build-submission-pack`
- **Sprint 7: Litops bridge** — Litops-compatible JSONL export (sources + artifacts), entity mapping with bridge version tags, CLI `export-litops-pack`
- **Sprint 8: WhiteCrow bridge** — Patch queue generation from mismatches, rewrite plans, compliance gaps, blocking risks; FieldCoreImpact mapping, CLI `export-whitecrow-patches`

### Stats
- 556 tests passing (was 351)
- 14 CLI commands (was 9)
- 13 domain services (was 11)
- 12 fit axes (was 8)
- 18 risk types (was 7)

## [0.1.0-alpha] — 2026-06-09

### Added
- Enhanced vault: cross-linked markdown cards, per-section indexes, root index, machine-readable manifest, link validation
- Export/import storage bundles as zip archives with metadata
- Freshness/staleness tracking for sources and adapter results (6 statuses: fresh, possibly_stale, stale, expired, mock, unknown_freshness)
- CLI commands: `vault-index`, `export-bundle`, `import-bundle`, `validate-bundle`
- Alpha demo: `examples/` directory with sample manuscript, venue guidelines, scenario
- Spec coverage matrix: `docs/SPEC_COVERAGE_MATRIX.md`
- Engineering backlog: `docs/BACKLOG.md` (9 sprint packages)
- Milestones: `docs/MILESTONES.md` (v0.1.0 through v0.6.0)
- CI: GitHub Actions workflow for pytest on push/PR
- LICENSE (MIT)
- CONTRIBUTING.md

### Previous (pre-changelog)
- External adapter stubs: OpenAlex, Crossref, OpenCitations mock adapters with evidence bridge
- Citation ecology stub: bibliography parsing, citation gaps, bridge references
- Real-file pipeline: `run-local` CLI command
- Source acquisition: local file registration with content hash
- Persistence + vault + CLI: JSONL registries, markdown cards, 5 CLI commands
- Fixture pipeline: 18-step manuscript × venue fit pipeline
- Domain skeleton: 18+ dataclasses, 23 enums, evidence layer, quality gates
