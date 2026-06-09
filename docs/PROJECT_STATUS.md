# Project Status — Kairoskopion

**Last updated:** 2026-06-09

## Repository

| Parameter | Value |
|-----------|-------|
| Branch | `feature/external-adapter-stubs` (from `main`) |
| Remote | `origin` → `https://github.com/Stimurid/Kairoskopion.git` |
| Working tree | clean |
| Python | >=3.11, installed in `.venv` |

## Commit history (main)

```
327c4ac Add citation ecology stub
299251e Add run-local pipeline for user files
9d04df7 Add repository operating layer and foundation docs
ca9c2fb Update documentation for first usable local build
beaf1bd Add source acquisition layer, inspect-storage, vault card expansion
5d3b048 Add persistence, vault output, and CLI smoke
91fa714 Add fixture manuscript-venue fit pipeline
24dab23 Audit Pass: add negative-case tests, fixtures, pipeline base
8e841f9 Bootstrap Kairoskopion MVP0 domain skeleton
```

## Modules implemented

### Core domain (`src/kairoskopion/`)

| Module | Contents |
|--------|----------|
| `ids.py` | UUID-based ID generation with 19 prefixes |
| `enums.py` | 23 domain enums |
| `schema.py` | 18+ dataclass models with `to_dict`/`from_dict` |
| `registry.py` | JSONL append/read/list/find |
| `persistence.py` | Storage root management, pipeline + adapter result persistence |
| `artifacts.py` | Vault markdown card filesystem output |
| `evidence.py` | Evidence layer helpers |
| `quality.py` | Quality gate evaluators (fit gate, submission gate) |
| `traces.py` | Operation trace recording |
| `decisions.py` | User decision tracking |
| `cards.py` | 7 markdown card generators |
| `cli.py` | CLI: status, run-fixture, run-local, adapters-smoke, inspect-storage |

### Services (`src/kairoskopion/services/`)

| Service | Purpose |
|---------|---------|
| `article_modeling.py` | ManuscriptModel + ArticleModel from text |
| `venue_profiling.py` | VenueModel + PublicationRegimeModel from guidelines |
| `scenario.py` | SubmissionScenario from user input |
| `fit_assessment.py` | Multi-axis fit comparison (8 axes) |
| `mismatch_mapping.py` | MismatchMap from weak/bad axes |
| `rewrite_planning.py` | RewritePlan action list |
| `risk_reporting.py` | RiskReport (7+ risk types) |
| `compliance.py` | ComplianceChecklist from guidelines |
| `evidence_audit.py` | Evidence coverage quality gate |
| `bibliography_parsing.py` | Reference extraction, year/DOI/kind detection, BibliographyProfile |
| `citation_ecology.py` | Citation gaps, tasks, bridge references, venue expectation matching |

### Pipelines

| Pipeline | Steps |
|----------|-------|
| `manuscript_venue_fit.py` | 18-step deterministic pipeline |

### Adapters

| Adapter | Status |
|---------|--------|
| `base.py` | Adapter contracts: AdapterResult, AdapterRecord, AdapterConfig, AdapterError |
| `source_intake.py` | Local file/text registration, 14 source roles |
| `url_snapshot.py` | URL placeholder (no real fetch) |
| `openalex.py` | Mock adapter — deterministic work search, no API calls |
| `crossref.py` | Mock adapter — DOI lookup + search, no API calls |
| `opencitations.py` | Mock adapter — citation link query, no API calls |
| `bridge.py` | Adapter → SourceSnapshot / EvidenceItem conversion |

### Integration stubs

| Module | Types |
|--------|-------|
| `litops.py` | 5 stub dataclasses (SourceRef, ContextPackRef, ArtifactRef, VaultProjection, WorksetRef) |
| `whitecrow.py` | 6 stub dataclasses (FieldModelRef, ProtectedCore, PatchCandidate, ExternalDocAction, ManuscriptRef, ArticleTrajectoryRef) |

## CLI commands

| Command | Description |
|---------|-------------|
| `kairoskopion status` | Version, cwd, storage root, registry/vault existence |
| `kairoskopion run-fixture` | Full fixture pipeline → persist registries + vault cards |
| `kairoskopion run-local` | Pipeline on user-provided manuscript + venue + scenario files |
| `kairoskopion adapters-smoke` | Run mock adapters, bridge to source/evidence, persist results |
| `kairoskopion inspect-storage` | Registry record counts, entity IDs, vault card listing |

Global option: `--storage-root PATH` or env `KAIROSKOPION_STORAGE_ROOT`.

## Storage layout

```
.kairoskopion/
  registries/
    article_models.jsonl        manuscripts.jsonl
    venue_models.jsonl          publication_regimes.jsonl
    submission_scenarios.jsonl   fit_assessments.jsonl
    mismatch_maps.jsonl         rewrite_plans.jsonl
    risk_reports.jsonl          compliance_checklists.jsonl
    pipeline_runs.jsonl         operation_traces.jsonl
    quality_gates.jsonl
    bibliography_profiles.jsonl  citation_ecology_reports.jsonl
    adapter_results.jsonl        source_snapshots.jsonl
    evidence_items.jsonl
  vault/
    articles/    venues/    fits/      risks/
    compliance/  mismatches/ citations/ submissions/ traces/
```

## Tests

- **308 tests**, all passing
- 17 test files covering: schema, registry, evidence, quality, cards,
  invariants, fixtures, pipeline, article modeling, venue profiling,
  fit assessment, evidence audit, persistence, artifacts, CLI,
  source acquisition, bibliography parsing, citation ecology, adapters

## Fixture pipeline output

Running `kairoskopion run-fixture` produces:
- FitAssessment: `possible_but_costly`
- 5 mismatches, 6 risk items, 9 compliance items (3 missing)
- 13 JSONL registries, 7 vault markdown cards

## Known omissions

- No real HTTP fetch (URL adapter is placeholder only)
- No PDF/DOCX text extraction (binary files: `not_extracted`)
- No LLM-assisted extraction (all heuristic regex)
- ~~No OpenAlex/Crossref/OpenCitations adapters~~ → implemented as mock stubs (no real API calls)
- ~~No `--manuscript`/`--venue` CLI args~~ → implemented as `run-local`
- ~~No citation ecology profiling~~ → implemented as heuristic stub (no external API)
- Mock adapters do not verify references (verification_status stays "not_verified")
- Mock evidence is VENDOR_CLAIM, never FACT_FROM_SOURCE
- No title-based fuzzy matching for reference linking (DOI only)
- No Telegram, web UI, reviewer simulation
- No submission portal automation
- No real Litops/WhiteCrow API connection (stubs only)

## What "usable local build" means

The system can:
1. Take synthetic fixture files (manuscript, venue guidelines, scenario)
2. Run an 18-step deterministic pipeline
3. Produce multi-axis fit assessment, mismatch map, rewrite plan, risk report, compliance checklist
4. Persist all results to JSONL registries
5. Write human-readable vault markdown cards
6. Run mock external adapters and bridge results to evidence layer
7. Display results via CLI

All without network access, LLM calls, or external dependencies.
