# Project Status — Kairoskopion

**Last updated:** 2026-06-12

## Repository

| Parameter | Value |
|-----------|-------|
| Branch | `main` at `88ad9b1` |
| Tag | `v0.2.0-alpha-rc6` |
| Remote | `origin` → `https://github.com/Stimurid/Kairoskopion.git` |
| Working tree | dirty (UC-1 agents + LLM config batch) |
| Python | >=3.11 |

## Recent commit history (main)

```
88ad9b1 Fix stale test/CLI counts in docs (641->673 tests, 14->16 commands)
32a2a2e Add venue evidence registry v0
3934f94 Prep v0.2.0-alpha-rc5 release
f726e8e Add arbitrary manuscript x venue validation matrix
b8a94bb Prep v0.2.0-alpha-rc4 release
33769ad Close D12-D15: generalized venue-fit anti-overfitting repairs
83f4028 Fix language policy extraction, close D10/D11 with evidence-pack rerun
```

## Trial history

Logos (Логос) was used as a **target-known trial case** to validate the pipeline
with a real venue. It is NOT the product target. Kairoskopion is a general
evidence-first article-to-venue trajectory engine.

- Logos seed trial: exposed D1-D9 (venue extraction, genre, method, rewrite plan, bibliography)
- Logos evidence-pack rerun: exposed D10-D11 (evidence upgrade, language policy extraction)
- Generalized venue-fit anti-overfitting pass: D12-D15 (word limit distinction, article type extraction, discipline matching, unassessed axes)
- All repairs were generalized — no Logos-specific hardcoding
- 16 generalized venue-fit regression tests with 3 synthetic fixtures prove no Logos overfitting
- Arbitrary manuscript x venue validation matrix: 8 fixture combinations, 28 behavioral tests, 6 CLI smoke cases
- D16-D17 closed: method detection broadened, citation ecology thresholds refined
- UC-1 semantic profiling substrate: 5 agents, 5 prompt families, 7 new entities, 3 new enums, LLM config — not full Agent Runtime, but agent contract + deterministic fallback + LLM path operational

## Modules implemented

### Core domain (`src/kairoskopion/`)

| Module | Contents |
|--------|----------|
| `ids.py` | UUID-based ID generation with 31 prefixes |
| `enums.py` | 28 domain enums |
| `schema.py` | 29+ dataclass models with `to_dict`/`from_dict` |
| `registry.py` | JSONL append/read/list/find |
| `persistence.py` | Storage root management, pipeline + adapter result persistence |
| `artifacts.py` | Vault markdown card filesystem output with cross-links |
| `vault.py` | Vault indexes, manifest, cross-linking, link validation |
| `exchange.py` | Export/import storage bundles (zip) |
| `freshness.py` | Freshness/staleness tracking for sources and adapter results |
| `evidence.py` | Evidence layer helpers |
| `quality.py` | Quality gate evaluators (fit gate, submission gate) |
| `traces.py` | Operation trace recording |
| `decisions.py` | User decision tracking |
| `cards.py` | 8 markdown card generators |
| `cli.py` | CLI: 16 commands (status, run-fixture, run-local, inspect-storage, adapters-smoke, vault-index, export-bundle, import-bundle, validate-bundle, intake-file, build-venue-profile, build-submission-pack, export-litops-pack, export-whitecrow-patches, import-venue-seed, build-venue-evidence-pack) |

### Services (`src/kairoskopion/services/`)

| Service | Purpose |
|---------|---------|
| `article_modeling.py` | ManuscriptModel + ArticleModel from text |
| `venue_profiling.py` | VenueModel + PublicationRegimeModel from guidelines |
| `scenario.py` | SubmissionScenario from user input |
| `fit_assessment.py` | Multi-axis fit comparison (12 axes) |
| `mismatch_mapping.py` | MismatchMap from weak/bad axes |
| `rewrite_planning.py` | RewritePlan action list |
| `risk_reporting.py` | RiskReport (18 risk types) |
| `compliance.py` | ComplianceChecklist from guidelines |
| `evidence_audit.py` | Evidence coverage quality gate |
| `bibliography_parsing.py` | Reference extraction, multi-style parsing (APA/numbered/Vancouver/Chicago), BibliographyProfile |
| `citation_ecology.py` | Citation gaps, tasks, bridge references, venue expectation matching |
| `venue_profile_builder.py` | Multi-source venue profiling from local files |
| `trajectory_report.py` | PublicationTrajectoryReport synthesizing fit+risk+bibliography |
| `submission_pack.py` | SubmissionPack preparation with readiness assessment |
| `venue_registry.py` | Venue evidence registry: seed import, evidence pack build, conflict resolution, Markdown rendering |

### Pipelines

| Pipeline | Steps |
|----------|-------|
| `manuscript_venue_fit.py` | 18-step pipeline (deterministic or LLM-backed via agent contract) |

### LLM subsystem (`src/kairoskopion/llm/`)

| Module | Purpose |
|--------|---------|
| `config.py` | LLMConfig with two-level env fallback, 5 model presets, diagnostics |
| `openai_compat.py` | OpenAI-compatible provider with error taxonomy, retry, structured output |
| `provider.py` | LLMProvider Protocol |
| `response.py` | LLMResponse dataclass |

### Agents (`src/kairoskopion/agents/`)

| Agent | Role |
|-------|------|
| `contract.py` | AgentInput/AgentOutput/AgentRole ABC |
| `article_modeler.py` | ArticleModelerAgent — article modeling |
| `venue_profiler.py` | VenueProfilerAgent — venue fact extraction |
| `fit_assessor.py` | FitAssessorAgent — fit assessment |
| `semantic_profiler.py` | ArticleSemanticProfilerAgent — UC-1 semantic profiling |
| `disciplinary_mapper.py` | DisciplinaryPathwayMapperAgent — UC-1 disciplinary pathways |

### Prompt families (`src/kairoskopion/prompts/`)

| Family | Agent |
|--------|-------|
| `article_modeling.py` | ArticleModelerAgent |
| `venue_fact_extraction.py` | VenueProfilerAgent |
| `fit_assessment.py` | FitAssessorAgent |
| `semantic_profiling.py` | ArticleSemanticProfilerAgent |
| `disciplinary_mapping.py` | DisciplinaryPathwayMapperAgent |

### Adapters

| Adapter | Status |
|---------|--------|
| `base.py` | Adapter contracts: AdapterResult, AdapterRecord, AdapterConfig, AdapterError |
| `source_intake.py` | Local file/text registration with PDF/DOCX extraction, 14 source roles |
| `url_snapshot.py` | URL placeholder (no real fetch) |
| `http_client.py` | Shared HTTP client (stdlib urllib) with caching and rate limiting |
| `openalex.py` | Mock + real adapter — work search |
| `crossref.py` | Mock + real adapter — DOI lookup + search |
| `opencitations.py` | Mock + real adapter — citation link query |
| `bridge.py` | Adapter → SourceSnapshot / EvidenceItem conversion |

### Integration stubs

| Module | Types |
|--------|-------|
| `litops.py` | 5 stub dataclasses (SourceRef, ContextPackRef, ArtifactRef, VaultProjection, WorksetRef) |
| `litops_bridge.py` | Litops-compatible JSONL export (sources + artifacts) |
| `whitecrow.py` | 6 stub dataclasses (FieldModelRef, ProtectedCore, PatchCandidate, ExternalDocAction, ManuscriptRef, ArticleTrajectoryRef) |
| `whitecrow_bridge.py` | WhiteCrow patch queue export (mismatch/rewrite/compliance/risk → patches) |

## CLI commands

| Command | Description |
|---------|-------------|
| `kairoskopion status` | Version, cwd, storage root, registry/vault existence |
| `kairoskopion run-fixture` | Full fixture pipeline → persist registries + vault cards |
| `kairoskopion run-local` | Pipeline on user-provided manuscript + venue + scenario files |
| `kairoskopion adapters-smoke` | Run mock adapters, bridge to source/evidence, persist results |
| `kairoskopion vault-index` | Generate vault indexes, manifest, and cross-links |
| `kairoskopion export-bundle --output FILE` | Export storage as zip bundle |
| `kairoskopion import-bundle --bundle FILE` | Import a storage bundle (append or replace) |
| `kairoskopion validate-bundle --bundle FILE` | Validate a storage bundle |
| `kairoskopion inspect-storage` | Registry record counts, entity IDs, vault card listing |
| `kairoskopion intake-file --file FILE --role ROLE` | Register a file with text extraction (PDF/DOCX/MD/TXT/HTML) |
| `kairoskopion build-venue-profile --files FILE [FILE ...]` | Build venue profile from multiple source files |
| `kairoskopion build-submission-pack` | Build submission pack from latest pipeline run |
| `kairoskopion export-litops-pack --output-dir DIR` | Export pipeline artifacts as Litops-compatible JSONL |
| `kairoskopion export-whitecrow-patches --output-dir DIR` | Export patch queue for WhiteCrow from pipeline artifacts |

Global options: `--storage-root PATH` or env `KAIROSKOPION_STORAGE_ROOT`; `--adapter-mode mock|real`.

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
    INDEX.md             — root index with section counts
    manifest.json        — machine-readable vault manifest
    articles/    INDEX.md + {article_model_id}.md
    venues/      INDEX.md + {venue_model_id}.md
    fits/        INDEX.md + {fit_assessment_id}.md (cross-linked to article/venue)
    risks/       {risk_report_id}.md (cross-linked to article/venue)
    compliance/  {compliance_checklist_id}.md (cross-linked)
    mismatches/  {mismatch_map_id}.md (cross-linked to fit)
    citations/   INDEX.md + {citation_ecology_report_id}.md (cross-linked)
    adapters/    INDEX.md
    submissions/
    traces/      INDEX.md + {pipeline_run_id}.md
```

## Tests

- **673 tests**, all passing
- 28+ test files covering: schema, registry, evidence, quality, cards,
  invariants, fixtures, pipeline, article modeling, venue profiling,
  fit assessment, evidence audit, persistence, artifacts, CLI,
  source acquisition, bibliography parsing, citation ecology, adapters,
  vault indexes, exchange bundles, freshness tracking,
  document intake (PDF/DOCX), entity completeness (12 fit axes, 18 risk types),
  real adapters (HTTP cache, rate limiting), venue profile builder,
  bibliography & trajectory reports, submission pack, Litops bridge, WhiteCrow bridge,
  rewrite planning (conditional actions), language policy extraction,
  generalized venue-fit (language blocker, word limits, article types, discipline matching),
  arbitrary manuscript x venue validation matrix (6 behavioral cases, 28 tests)

## Fixture pipeline output

Running `kairoskopion run-fixture` produces:
- FitAssessment: `possible_but_costly`
- 8 mismatches, 10 risk items, 9 compliance items (3 missing)
- 15 JSONL registries, 8 vault markdown cards (with cross-links)

## Known omissions

- ~~No PDF/DOCX text extraction~~ → implemented (pypdf, python-docx)
- ~~No real API calls~~ → implemented as optional real mode (mock default)
- ~~No SubmissionPack~~ → implemented with readiness assessment
- ~~No Litops/WhiteCrow integration~~ → implemented as JSONL export bridges
- No LLM-assisted extraction (all heuristic regex)
- No real HTTP fetch for URL adapter (placeholder only)
- Mock adapters do not verify references (verification_status stays "not_verified")
- Mock evidence is VENDOR_CLAIM, never FACT_FROM_SOURCE
- No title-based fuzzy matching for reference linking (DOI only)
- Freshness is local metadata only — no real source refresh
- No OCR for scanned PDFs
- No Telegram, web UI, reviewer simulation
- No submission portal automation
- No live Litops/WhiteCrow API connection (export bridges only)

## What "usable local build" means

The system can:
1. Take synthetic fixture files (manuscript, venue guidelines, scenario)
2. Run an 18-step deterministic pipeline
3. Produce multi-axis fit assessment, mismatch map, rewrite plan, risk report, compliance checklist
4. Persist all results to JSONL registries
5. Write human-readable vault markdown cards with cross-links
6. Run mock external adapters and bridge results to evidence layer
7. Generate vault indexes, manifest, and validate internal links
8. Export/import storage bundles as zip archives
9. Track freshness/staleness of sources and adapter results
10. Display results via CLI

All without network access, LLM calls, or external dependencies.
