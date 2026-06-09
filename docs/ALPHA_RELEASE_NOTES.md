# Alpha Release Notes — Kairoskopion v0.1.0-alpha

**Date:** 2026-06-09

## What is Kairoskopion?

Kairoskopion is an evidence-first publication-positioning system. It matches
manuscripts and articles against academic publication containers (journals,
sections, special issues) and produces traceable fit assessments, mismatch maps,
adaptation plans, and risk reports.

It is a bounded context within the Litops-WhiteCrow ecosystem.

## What works in this alpha

### Core pipeline
- Provide a manuscript (.md/.txt), venue guidelines, and submission scenario
- Get a multi-axis fit assessment (8 axes: topic, discipline, genre, method, citation ecology, language register, formal compliance, publication regime)
- Get a mismatch map showing where and why fit fails
- Get a rewrite plan with actionable changes
- Get a risk report with severity levels
- Get a compliance checklist against venue requirements
- Get a bibliography profile and citation ecology report

### Data management
- All results persisted to JSONL registries (append-only, auditable)
- Human-readable markdown vault cards with cross-links
- Vault indexes and machine-readable manifest
- Export/import storage bundles as zip archives
- Freshness/staleness tracking for sources

### External adapters (mock)
- OpenAlex, Crossref, OpenCitations — typed contracts with deterministic mock data
- Evidence bridge: adapter results become SourceSnapshots and EvidenceItems
- Mock evidence is always VENDOR_CLAIM (never FACT_FROM_SOURCE)

### CLI
9 commands: `status`, `run-fixture`, `run-local`, `inspect-storage`, `adapters-smoke`, `vault-index`, `export-bundle`, `import-bundle`, `validate-bundle`

### Quality
- 351 passing tests
- No external dependencies at runtime
- No network calls
- No LLM calls
- Fully deterministic pipeline

## What does NOT work yet

- **No PDF/DOCX extraction** — only .md/.txt/.json/.html accepted
- **No real API calls** — adapters are mock only
- **No LLM-assisted extraction** — all heuristic/regex
- **No venue deep profiling** — single guidelines file only
- **No SubmissionPack** entity
- **No review loop** (ReviewOutcome, RevisionPlan, VenueMemory)
- **No UI beyond CLI**
- **No Litops/WhiteCrow live integration** (stubs only)

## How to try it

```bash
pip install -e ".[dev]"

kairoskopion --storage-root .kairoskopion_demo run-local \
  --manuscript examples/sample_manuscript.md \
  --venue-guidelines examples/sample_venue_guidelines.md \
  --scenario examples/sample_scenario.json

kairoskopion --storage-root .kairoskopion_demo vault-index
kairoskopion --storage-root .kairoskopion_demo export-bundle --output demo.zip
```

## Architecture

See `docs/SPEC_COVERAGE_MATRIX.md` for how the implementation maps to the full technical specification (10 waves, 12665 lines).

See `docs/BACKLOG.md` for the next planned sprints.

See `docs/MILESTONES.md` for the roadmap to v1.0.
