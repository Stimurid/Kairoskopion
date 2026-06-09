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
- Provide a manuscript (.md/.txt/.pdf/.docx), venue guidelines, and submission scenario
- Get a multi-axis fit assessment (12 axes: topic, discipline, genre, argument_structure, method, citation_ecology, novelty_positioning, language_register, audience, formal_compliance, author_eligibility, publication_regime)
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

### External adapters (mock + real)
- OpenAlex, Crossref, OpenCitations — mock (default) and real modes with HTTP caching and rate limiting
- Evidence bridge: adapter results become SourceSnapshots and EvidenceItems
- Mock evidence is always VENDOR_CLAIM (never FACT_FROM_SOURCE)

### Integration bridges
- Litops-compatible JSONL export (sources + artifacts)
- WhiteCrow patch queue export (mismatches, rewrites, compliance, risks → patches)

### CLI
14 commands: `status`, `run-fixture`, `run-local`, `inspect-storage`, `adapters-smoke`, `vault-index`, `export-bundle`, `import-bundle`, `validate-bundle`, `intake-file`, `build-venue-profile`, `build-submission-pack`, `export-litops-pack`, `export-whitecrow-patches`

### Quality
- 556 passing tests
- No external dependencies at runtime
- No network calls
- No LLM calls
- Fully deterministic pipeline

## What does NOT work yet

- **No LLM-assisted extraction** — all heuristic/regex
- **No OCR** — scanned PDFs remain `needs_ocr`
- **No review loop** (ReviewOutcome, RevisionPlan, VenueMemory)
- **No UI beyond CLI**
- **No live Litops/WhiteCrow API** — export bridges only
- **No submission portal automation**

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
