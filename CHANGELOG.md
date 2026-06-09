# Changelog — Kairoskopion

All notable changes to this project will be documented in this file.

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
