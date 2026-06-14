# Project Status — Kairoskopion

**Last updated:** 2026-06-14 (RC17 — Mavrinsky benchmark-backed baseline + Venue Funnel v1 doctrine)

## Latest release pass — RC17 (2026-06-14)

**Tag:** `v0.2.0-alpha-rc17` (pending push)

RC17 ships both halves of the Mavrinsky benchmark model in one
coherent release:

**Article-side stack (merged FF):**

- `feature/wire-fpm-pipeline` — FieldPositionModel wired into Case orchestrator.
- `feature/sprint-alpha-evidence-policy` — `SourceEvidencePacket` +
  `ProtectedCorePolicy` + `EvidencePolicy` substrate (PIM v1 B1+B3).
- `fix/llm-agent-tolerance-mavrinsky` — 9 LLM-output-shape bugs fixed;
  Mavrinsky golden-run baseline (4 PASS / 3 PARTIAL / 3 FAIL on 10 §14
  checks); 302.ai gateway reality doc; harness + scorer.

**Venue-side doctrine + baseline (merged with content-clean 3-way):**

- `feature/venue-funnel-v1-canon` — canonical reference
  `docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md` (8-layer funnel,
  `VenueProfilePackage` of 24 sub-models, source allowlist A–J,
  two-stage DB→network search with cache-miss taxonomy, mirror gold),
  ADR-16 supersession, VF-C1…C9 code-alignment backlog,
  `SPEC_COVERAGE_MATRIX` §6.7–§6.16 routing.
- `feature/venue-side-golden-baseline` — operational rubric
  `benchmarks/golden/venue_source_layer_map.md` (v2: 7 minimal
  subobjects, primary computation layer per axis, six caveats),
  five-cluster `mavrinsky_venue_side_gold.md` (continental /
  philtech / STS / HCI / RU), `source_acquisition_funnel.md`,
  deterministic `services/corpus_hull_builder.py` (15 tests),
  harness skeleton `scripts/run_venue_side_benchmark.py`,
  deterministic benchmark proof #001 (4 PASS / 1 PARTIAL / 0 FAIL,
  all 5 clusters covered).

The release fixes the rc16-vs-main drift the audit closed by bringing
all benchmark-relevant work into one coherent tag.

**Not in RC17:**

- Live `EditorialBoardCloud` adapter (next venue-side sprint).
- ВАК / РИНЦ / КиберЛенинка adapters (deferred).
- Shadow / full-text resolvers (deferred).
- 50–80 venue live discovery (deferred).
- `chore/state-audit-2026-06-14` doc-only branch: skipped from FF train
  because it would have prevented FF of the article-side stack. Lands
  as a follow-up doc patch.

## Repository

| Parameter | Value |
|-----------|-------|
| Branch | `main` (merge target: `feature/ui-cockpit-v0`) |
| Tag | `v0.2.0-alpha-rc15` (pending) |
| Remote | `origin` → `https://github.com/Stimurid/Kairoskopion.git` |
| Working tree | clean |
| Python | >=3.11 |
| Node.js | >=18 (for UI build) |

## UI Cockpit v0 (Operator/Staging Preview)

> **This is an internal operator/staging preview, NOT a public product release.**
> Deterministic backend fallbacks are still in use. Persistence is in-memory only.
> Auth, job queue, and production hardening are NOT implemented.
> Staging deployment must be protected (IP-restricted or auth-gated).
> No public prod claim.

- FastAPI backend: 19 REST endpoints covering full Case pipeline
- React + TypeScript frontend: 17 components, dark theme, responsive layout
- Pipeline continuity: select_venue triggers fit → mismatch → rewrite chain
- Quality gates populated after stage transitions
- Evidence badge system (FACT, CLAIM, CORPUS, INFERRED, USER, UNKNOWN, STALE, CONFLICT)
- API smoke test: 18/18 PASS, 1 SKIP (expected)
- Browser smoke: all views render, zero console errors, mobile responsive at 375px
- Frontend build: `tsc --noEmit` clean, `vite build` clean
- Backend on `fix/llm-agent-tolerance-mavrinsky` (after this pass): **1355 pytest tests passing**, 4 deselected = network. Main is still at 1307.

## Recent commit history (main)

```
14d34d1 Add real source acquisition v0 with adapter authority enforcement
b34ddd7 Add source authority and integrity model
10164e5 Audit UC-1 demo pack
62ce29e Fix 3 agent attribute bugs: compliance_auditor, submission_pack_builder, evidence_auditor
4498a74 Implement UC-1 Demo Pack v0: offline reproducible pipeline demo
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
- Agentic Contour v0.1: 26 agents (7 layers), registry, executor, orchestrator, 4 workflows, 16 prompt families, 7 new CLI commands — full UC-1 orchestrated layer
- Venue Evidence Stack V1–V2: 8-level depth model, vault storage, 4 venue adapters, corpus profiler, 3 agent upgrades, workflow wiring, 4 new CLI commands
- UC-1 Demo Pack v0: offline reproducible demo of full UC-1 pipeline (12/12 steps), synthetic fixtures, 3 agent bugfixes (compliance_auditor, submission_pack_builder, evidence_auditor), 16 output artifacts, report generator
- Source Authority Model v0: SourceAccessMode/SourceAuthorityScope enums, SourceAuthorityClaim/SourceAuthorityAssessment models, authority checker service, EvidenceAuditor integration, 53 tests
- Real Source Acquisition v0: 6 venue adapters (OpenAlex, Crossref, DOAJ, Unpaywall, OpenCitations, Snapshot) with authority enforcement at adapter boundary, cross-adapter conflict detection, aggregation service, 3 new CLI commands, 67 tests
- Real Venue Pool Discovery v0: discovery pipeline (query planner, fixture pool discovery, identity normalization/dedupe, candidate screening), 3 new enums, 5 new schema models, 4 new services, VenueDiscoveryAgent rewrite, 3 new CLI commands, UC-1 workflow update, 58 tests
- UI Cockpit v0: FastAPI REST API (30 endpoints, audit-verified), React+TypeScript frontend (18 components), pipeline continuity (select_venue → fit chain), quality gates, evidence badges, responsive dark theme, API smoke test, 188 backend tests — operator/staging preview only, not public product
- **FPM wiring (`feature/wire-fpm-pipeline`)**: `Case` orchestrator integrates `ArticleFieldPositionerAgent` + `VenueFieldPositionerAgent`; FPM-based fit runs in parallel to the legacy 12-axis FitAssessment.
- **Sprint α (`feature/sprint-alpha-evidence-policy`)**: PIM v1 §2/§7 substrate — `SourceEvidencePacket` + `EvidenceGranularity` enum, `ProtectedCorePolicy` + `EvidencePolicy` dataclasses, deterministic builder, policy gate in `RewritePlanner` chain. +15 tests.
- **Mavrinsky golden-run baseline (`fix/llm-agent-tolerance-mavrinsky`)** (2026-06-14): LLM-driven end-to-end run on a real Russian philosophical draft. Provider `gpt-4o-mini` via 302.ai (`gpt-4.1-mini` + strict json_schema hangs through this gateway — documented). 9 agent/parser/protocol bugs fixed with 25 regression tests. Best run: 4 PASS / 3 PARTIAL / 3 FAIL on a 10-check rubric. Harness, rubric, sanitized report, and merge plan committed under `benchmarks/` and `docs/benchmarks/`. NOT yet merged to main.

## Modules implemented

### Core domain (`src/kairoskopion/`)

| Module | Contents |
|--------|----------|
| `ids.py` | UUID-based ID generation with 36 prefixes |
| `enums.py` | 40 domain enums (28 original + 9 source authority/integrity + 3 venue discovery) |
| `schema.py` | 34+ dataclass models with `to_dict`/`from_dict` |
| `source_authority.py` | Source authority domain models: SourceAuthorityClaim, SourceAuthorityAssessment, EvidenceConflict, EvidenceReconciliationResult, PublicationHistoryModel, PriorVersion, CitationIntegrityCheck, ReportingGuidelineSelection |
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
| `cli.py` | CLI: 34 commands (31 existing + plan-venue-discovery, discover-venue-pool, screen-venue-candidates) |
| `api/app.py` | FastAPI app: CORS, health, case CRUD, pipeline endpoints (operator/staging preview) |
| `api/cases.py` | Case orchestrator: in-memory pipeline state, 19 REST routes |

### Demo (`src/kairoskopion/demo/`)

| Module | Purpose |
|--------|---------|
| `uc1_demo_loader.py` | Load + validate UC-1 demo pack from fixture directory |
| `uc1_runner.py` | Run UC-1 workflow with loaded demo pack, write artifacts |
| `uc1_report.py` | Generate UC1_DEMO_REPORT.md from run results |

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
| `venue_evidence_stack.py` | Venue Evidence Stack orchestrator: depth-driven evidence collection across 8 levels |
| `corpus_sampler.py` | Corpus sampling: PublishedArticleCorpus from fixtures with distribution analysis |
| `corpus_analyzer.py` | Corpus analysis: method/school/citation pattern extraction |
| `source_authority.py` | Source authority checker: authority matrix, claim validation, conflict detection, evidence reconciliation |
| `real_source_acquisition.py` | Real source acquisition: orchestrates 6 adapters, cross-adapter conflict detection, AcquisitionResult |
| `venue_discovery_planner.py` | Query plan generation: per-pathway search terms + scenario constraints |
| `venue_pool_discovery.py` | Pool discovery: fixture + live adapters → VenueCandidatePool |
| `venue_candidate_identity.py` | Identity normalization, ISSN/name dedupe, conflict detection |
| `venue_candidate_screening.py` | 7-axis candidate screening, evidence matrix builder |

### Storage (`src/kairoskopion/storage/`)

| Module | Purpose |
|--------|---------|
| `vault_backend.py` | VaultBackend ABC, VaultObjectKind, VaultObjectRef, content hashing |
| `local_fs_vault.py` | LocalFsVault filesystem implementation with metadata sidecars |

### Venue depth (`src/kairoskopion/`)

| Module | Purpose |
|--------|---------|
| `venue_depth.py` | 8-level depth model, VenueDepthPolicy, VenueDepthCoverage, 4 default policies |

### Venue adapters (`src/kairoskopion/adapters/venue/`)

| Adapter | Status |
|---------|--------|
| `base.py` | VenueAdapter ABC, VenueAdapterMode (5 modes), VenueAdapterResult (with authority), SourceAcquisitionConfig |
| `openalex.py` | OpenAlex venue lookup (fixture + live + cached) |
| `crossref.py` | Crossref journal metadata (fixture + live + cached) |
| `doaj.py` | DOAJ journal OA/indexing (fixture + live + cached) |
| `unpaywall.py` | Unpaywall article OA by DOI (fixture + live) |
| `opencitations.py` | OpenCitations citation ecology (fixture + live) |
| `snapshot_crawler.py` | Official webpage HTML capture with vault integration (fixture + live) |

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

| Module | Role |
|--------|------|
| `contract.py` | AgentInput/AgentOutput/AgentRole ABC |
| `runtime_models.py` | AgentSpec, AgentTask, AgentRun, AgentResult, AgentTrace, WorkflowStepSpec, etc. |
| `base_shell.py` | service_output(), contract_only_output(), missing_input_output() |
| `registry.py` | 27 AgentSpec entries (7 layers), lookup, instantiation |
| `executor.py` | Single-agent execution with task/run/trace tracking |
| `orchestrator.py` | Sequential workflow execution with entity pool |
| `workflows.py` | 4 workflow specs + registry |
| `prompt_families/` | 16 prompt family modules + catalog |
| `control/` | 4 agents: IntentClassifier, ScenarioProber, ResearchPlanner, StatusJob |
| `article/` | 3 agents: ArticleModeler, SemanticProfiler, DisciplinaryMapper |
| `venue/` | 6 agents: VenueProfiler, VenueIdentifier, VenueDiscovery, PublicationRegimeClassifier, VenuePublicationProfileBuilder, CorpusSampler |
| `fit/` | 4 agents: FitAssessor, MismatchMapper, RewritePlanner, CitationPlanner |
| `submission/` | 3 agents: RiskOfficer, ComplianceAuditor, SubmissionPackBuilder |
| `review/` | 6 agents (contract-only): ReviewerSimulation, ReviewOutcomeAnalyst, RevisionPlanner, RebuttalArchitect, TacitSignalStructurer, VenueMemoryKeeper |
| `evidence/` | 1 agent: EvidenceAuditor |

### Prompt families (`src/kairoskopion/prompts/` + `src/kairoskopion/agents/prompt_families/`)

| Family | Agent |
|--------|-------|
| `article_modeling.py` | ArticleModelerAgent |
| `venue_fact_extraction.py` | VenueProfilerAgent |
| `fit_assessment.py` | FitAssessorAgent |
| `semantic_profiling.py` | ArticleSemanticProfilerAgent |
| `disciplinary_mapping.py` | DisciplinaryPathwayMapperAgent |
| `scenario_interview.py` | ScenarioProber |
| `publication_regime.py` | PublicationRegimeClassifier |
| `corpus_pattern_mining.py` | VenuePublicationProfileBuilder |
| `citation_ecology.py` | CitationPlanner |
| `mismatch_mapping.py` | MismatchMapper |
| `rewrite_planning.py` | RewritePlanner |
| `risk_reporting.py` | RiskOfficer |
| `compliance_checklist.py` | ComplianceAuditor |
| `submission_pack.py` | SubmissionPackBuilder |
| `review_outcome.py` | ReviewOutcomeAnalyst |
| `evidence_audit.py` | EvidenceAuditor |

### Adapters

| Adapter | Status |
|---------|--------|
| `base.py` | Adapter contracts: AdapterResult, AdapterRecord, AdapterConfig, AdapterError |
| `source_intake.py` | Local file/text registration with PDF/DOCX extraction, 14 source roles |
| `url_snapshot.py` | URL placeholder (no real fetch) |
| `http_client.py` | Shared HTTP client (stdlib urllib) with caching, rate limiting, HttpResult, fetch_json_safe/fetch_text_safe |
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
| `kairoskopion import-venue-seed --corpus DIR` | Import venue seed corpus into registries |
| `kairoskopion build-venue-evidence-pack --venue-id ID` | Build venue evidence pack from registry |
| `kairoskopion list-agents [--layer L]` | List all registered agents |
| `kairoskopion inspect-agent ROLE_ID` | Show agent spec as JSON |
| `kairoskopion list-prompt-families` | List all prompt families |
| `kairoskopion inspect-prompt-family FAMILY_ID` | Show prompt family details |
| `kairoskopion list-workflows` | List all workflow specs |
| `kairoskopion inspect-workflow WORKFLOW_ID` | Show workflow spec as JSON |
| `kairoskopion run-agent-workflow WORKFLOW_ID` | Run an agentic workflow |
| `kairoskopion inspect-venue-depth-policy --purpose PURPOSE` | Show depth policy for analysis purpose |
| `kairoskopion build-venue-evidence-stack --venue-name NAME --purpose PURPOSE` | Build venue evidence stack |
| `kairoskopion sample-venue-corpus --fixture FILE [--venue-id ID]` | Sample corpus from article fixtures |
| `kairoskopion analyze-venue-corpus --fixture FILE` | Analyze corpus for method/school patterns |
| `kairoskopion run-uc1-demo [--pack-dir DIR] [--output-dir DIR]` | Run UC-1 offline demo pack (synthetic, deterministic, no LLM) |
| `kairoskopion acquire-venue-sources --venue-name NAME [--issn ISSN] [--url URL] [--doi DOI] [--output FILE]` | Run all enabled source adapters for a venue |
| `kairoskopion list-source-adapters` | List available source adapters with access modes |
| `kairoskopion inspect-adapter ADAPTER_ID` | Show adapter details |

Global options: `--storage-root PATH` or env `KAIROSKOPION_STORAGE_ROOT`; `--adapter-mode mock|real`; `--llm-model`, `--llm-base-url`, `--llm-api-key-env` for LLM-backed commands.

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

- **1275 tests**, all passing (188 new in UI Cockpit v0, 58 in venue pool discovery v0, 67 in real source acquisition v0, 53 in source authority model v0, 35 in UC-1 Demo Pack v0)
- 50+ test files covering: schema, registry, evidence, quality, cards,
  invariants, fixtures, pipeline, article modeling, venue profiling,
  fit assessment, evidence audit, persistence, artifacts, CLI,
  source acquisition, bibliography parsing, citation ecology, adapters,
  vault indexes, exchange bundles, freshness tracking,
  document intake (PDF/DOCX), entity completeness (12 fit axes, 18 risk types),
  real adapters (HTTP cache, rate limiting), venue profile builder,
  bibliography & trajectory reports, submission pack, Litops bridge, WhiteCrow bridge,
  rewrite planning (conditional actions), language policy extraction,
  generalized venue-fit (language blocker, word limits, article types, discipline matching),
  arbitrary manuscript x venue validation matrix (6 behavioral cases, 28 tests),
  agentic runtime models, agent registry (26 agents), agent shells, executor,
  orchestrator/workflows, agentic CLI commands,
  UC-1 demo pack (loader, runner, report, CLI, 12/12 steps, agent bugfix coverage)

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
- ~~No real HTTP fetch for URL adapter (placeholder only)~~ → implemented in venue snapshot crawler
- Mock adapters do not verify references (verification_status stays "not_verified")
- Mock evidence is VENDOR_CLAIM, never FACT_FROM_SOURCE
- No Sherpa/RoMEO, Semantic Scholar, GROBID adapters (future)
- No retraction/PubPeer live lookup (prohibited by constraint)
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
11. Run a full UC-1 offline demo (12-step pipeline, 16 artifact files, reproducible report)

11. Expose all of the above through a REST API and operator-facing web cockpit (staging preview only)

All without network access, LLM calls, or external dependencies (UI requires Node.js for build).
