# Changelog — Kairoskopion

All notable changes to this project will be documented in this file.

## [Unreleased] — Real Venue Pool Discovery v0

### Added
- **Venue discovery pipeline**: ArticleSemanticProfile + DisciplinaryPathways → VenueDiscoveryQuery plans → adapter queries → VenueCandidate objects → identity normalization + dedupe → VenueCandidatePool
- **Venue discovery enums** (`enums.py`): VenueDiscoverySource (7), VenueCandidateStatus (8), VenueCandidateReason (11)
- **5 new schema models** (`schema.py`): VenueDiscoveryQuery, VenueCandidate, VenueCandidatePool, VenueCandidateScreeningResult, CandidateEvidenceMatrix
- **5 new ID factories** (`ids.py`): venue_discovery_query_id, venue_candidate_id, venue_candidate_pool_id, venue_candidate_screening_id, candidate_evidence_matrix_id
- **Query planner service** (`services/venue_discovery_planner.py`): per-pathway query plan generation with scenario constraints
- **Pool discovery service** (`services/venue_pool_discovery.py`): fixture-based discovery with built-in DISCOVERY_FIXTURES for openalex (5), doaj (3), crossref (2)
- **Identity normalization service** (`services/venue_candidate_identity.py`): ISSN/name normalization, strong/weak merge, conflict detection (same-name-different-ISSN, publisher mismatch)
- **Candidate screening service** (`services/venue_candidate_screening.py`): 7-axis screening (discipline, article_type, language, publication_regime, indexing, corpus_evidence, authority_confidence), evidence matrix builder
- **VenueDiscoveryAgent rewrite** (`agents/venue/venue_discovery.py`): full pipeline integration, deterministic fallback
- **3 CLI commands**: `plan-venue-discovery`, `discover-venue-pool`, `screen-venue-candidates`
- **UC-1 workflow update**: step 3 now runs venue discovery with expanded input_keys
- 58 new tests (1068 total, was 1010)
- Documentation: REAL_VENUE_POOL_DISCOVERY_V0.md, VENUE_CANDIDATE_SCREENING_V0.md, UC1_DISCOVERY_MODE.md, REAL_VENUE_POOL_DISCOVERY_V0_IMPLEMENTATION_MAP.md

### Fixed
- `discover_venue_pool`: `fixtures={}` now correctly means "no fixtures" (was falling through to defaults)
- `cmd_inspect_agent`: restored correct import `get_agent_spec` (was broken by typo `instantiate_agent_spec` during CLI additions)

### Known limitations
- Deterministic pathway mapper produces weak/unknown pathways offline — fixture venues may not match
- Fixture discovery is synthetic (DISCOVERY_FIXTURES); live mode placeholder returns empty
- Live adapter mode not tested by default (no network required)
- No broad crawler, no all-journal database

## [Unreleased] — Source Authority and Integrity Model v0

### Added
- **Source authority model** (`source_authority.py`): SourceAuthorityClaim, SourceAuthorityAssessment, EvidenceConflict, EvidenceReconciliationResult, PublicationHistoryModel, PriorVersion, CitationIntegrityCheck, ReportingGuidelineSelection
- **Source authority enums** (`enums.py`): SourceAccessMode (12), SourceAuthorityScope (20), AuthorityStrength (4), ConflictType (4), ConflictSeverity (3), ConflictResolutionStatus (5), RetractionStatus (7), PriorVersionType (9)
- **Authority checker service** (`services/source_authority.py`): deterministic authority matrix, claim validation, conflict detection, evidence reconciliation
- **EvidenceAuditor integration**: optional authority_assessments and evidence_conflicts parameters for source authority and conflict checking
- **GPT-16 alignment matrix** (`docs/GPT16_ALIGNMENT_MATRIX.md`): canonical 16-point architectural critique coverage tracking
- **12 backlog sprint entries** (GP-1 through GP-12) for GPT-16 items
- 53 new tests (943 total, was 890)
- Documentation: SOURCE_AUTHORITY_MODEL_V0.md, EVIDENCE_CONFLICT_RECONCILIATION_V0.md, GPT16_ALIGNMENT_BACKLOG_PATCH.md

## [Unreleased] — UC-1 Demo Pack v0

### Added
- **UC-1 demo pack** (`src/kairoskopion/demo/`): offline reproducible demonstration of the full UC-1 pipeline with synthetic fixtures
- **Demo loader** (`demo/uc1_demo_loader.py`): loads and validates demo pack from fixture directory (draft article, 5 venue seeds, guidelines, corpus)
- **Demo runner** (`demo/uc1_runner.py`): runs UC-1 workflow with loaded pack, writes 16 artifact files to output directory
- **Report generator** (`demo/uc1_report.py`): generates UC1_DEMO_REPORT.md with step table, entity summary, evidence gaps, trace log
- **Synthetic demo dataset** (`tests/fixtures/uc1_demo_pack/`): Simondon/STS article on AI publication positioning, 5 venue seeds, 3 venue guidelines, 3 corpus files (9 synthetic articles)
- **CLI command** `run-uc1-demo` with `--pack-dir` and `--output-dir` flags (28 total CLI commands)
- 35 new tests (890 total, was 855)
- Documentation: `docs/UC1_DEMO_PACK_V0.md`

### Fixed
- `compliance_auditor`: `article.title` → `title_current`, `article.abstract` → `abstract_current`, `article.keywords` → `core_claims`
- `submission_pack_builder`: `pack.readiness` → `pack.ready_status`
- `evidence_auditor`: removed `.value` on already-string status, replaced nonexistent `findings` with `warnings`/`blocking_issues`

## [Unreleased] — Venue Evidence Stack V1–V2 Foundation

### Added
- **8-level Venue Evidence Depth Model** (`venue_depth.py`): L0_IDENTITY through L7_USER_MEMORY_AND_OUTCOMES, VenueDepthPolicy, VenueDepthCoverage, 4 default policies (QUICK_LOOK, FIT_ASSESSMENT, VENUE_DEEP_PROFILE, SUBMISSION_READY)
- **Vault storage** (`storage/vault_backend.py`, `storage/local_fs_vault.py`): VaultBackend ABC with content-addressed SHA-256[:16] hashing, LocalFsVault filesystem implementation, VaultObjectKind enum (8 types), metadata sidecars
- **4 venue adapters** (`adapters/venue/`): OpenAlexVenueAdapter, CrossrefVenueAdapter, OpenCitationsVenueAdapter, VenueSnapshotCrawler — all with offline_stub mode and synthetic fixtures
- **Venue Evidence Stack orchestrator** (`services/venue_evidence_stack.py`): `build_venue_evidence_stack()` collects evidence level-by-level up to depth policy
- **Corpus profiler** (`services/corpus_sampler.py`, `services/corpus_analyzer.py`): `sample_venue_corpus()` builds PublishedArticleCorpus from fixtures; `analyze_venue_corpus()` extracts method/school/citation patterns
- **VenueIdentifierAgent** upgraded from stub to functional identity resolution: ISSN normalization, resolution_status (identity_partial/identity_minimal/needs_sources), ambiguity tracking
- **VenuePublicationProfileBuilderAgent** rewritten to consume depth_coverage, corpus, citation_profile, editorial_board with explicit L3/L4/L6/L7 unknowns
- **CorpusSamplerAgent** — thin wrapper around corpus_sampler service for workflow integration
- **Workflow wiring**: venue_identifier step in direct_manuscript_venue_fit (9 steps), corpus_sampler step in venue_deep_profile (4 steps)
- **4 new CLI commands**: inspect-venue-depth-policy, build-venue-evidence-stack, sample-venue-corpus, analyze-venue-corpus
- **New enum value**: FACT_FROM_API_METADATA in EvidenceStatus
- 73 new tests (855 total, was 782)
- 4 new docs: REPORT, VENUE_DEPTH_POLICY, VAULT_BACKEND_ARCHITECTURE, VENUE_CORPUS_PROFILER_V2

### Fixed
- `topic_clusters` type drift: `list[str]` → `list[dict[str, Any]]` to match corpus sampler output

## [Unreleased] — Agentic Contour v0.1 (UC-1 Orchestrated Layer)

### Added
- **Agentic runtime models** (`agents/runtime_models.py`): AgentSpec, AgentTask, AgentRun, AgentResult, AgentTrace, AgentFailure, AgentToolCall, WorkflowStepSpec, AgenticWorkflowSpec, WorkflowRun, WorkflowResult, WorkflowTrace — all with `_DictMixin` serialization
- **Agent registry** (`agents/registry.py`): 26 AgentSpec entries across 7 layers (control, article, venue, fit, submission, review, evidence) with lookup, instantiation, and class map
- **Agent executor** (`agents/executor.py`): single-agent execution with task/run/trace tracking, deterministic/LLM dispatch, failure capture
- **Workflow orchestrator** (`agents/orchestrator.py`): sequential workflow execution with shared entity pool, skip_if_missing, stop_on_failure
- **4 workflow specs** (`agents/workflows.py`): direct_manuscript_venue_fit (8 steps), uc1_draft_to_venue_pool_positioning (12 steps), venue_deep_profile (3 steps), review_loop (6 steps, skeleton)
- **21 new agent shells**: 4 control (IntentClassifier, ScenarioProber, ResearchPlanner, StatusJob), 4 venue (VenueIdentifier, VenueDiscovery, PublicationRegimeClassifier, VenuePublicationProfileBuilder), 3 fit (MismatchMapper, RewritePlanner, CitationPlanner), 3 submission (RiskOfficer, ComplianceAuditor, SubmissionPackBuilder), 6 review (all contract-only stubs), 1 evidence (EvidenceAuditor)
- **Base shell utilities** (`agents/base_shell.py`): service_output(), contract_only_output(), missing_input_output()
- **11 new prompt families** (`agents/prompt_families/`): scenario_interview, publication_regime, corpus_pattern_mining, citation_ecology, mismatch_mapping, rewrite_planning, risk_reporting, compliance_checklist, submission_pack, review_outcome, evidence_audit
- **Prompt family catalog** (`agents/prompt_families/catalog.py`): all 16 families aggregated (5 existing + 11 new)
- **7 new CLI commands**: list-agents, inspect-agent, list-prompt-families, inspect-prompt-family, list-workflows, inspect-workflow, run-agent-workflow
- **7 new enums**: AgentLayer, AgentExecutionMode, AgentImplementationStatus, AgentRunStatus, WorkflowRunStatus, WorkflowImplementationStatus
- **7 new ID factories**: atask_, arun_, ares_, atrc_, wfrun_, wfres_, wftrc_
- 76 new tests (782 total, was 706)

## [v0.2.0-alpha-rc7] — UC-1 Semantic Profiling Agents + LLM Config

### Added
- **LLM subsystem** (`src/kairoskopion/llm/`): OpenAI-compatible provider with litops-aligned config
  - Two-level env fallback: `KAIROSKOPION_LLM_*` → `LLM_*` (litops pattern)
  - 5 model presets (302.ai×3, OpenAI×2), `is_llm_available()`, `provider_status()` diagnostics
  - Error taxonomy: PROVIDER_HTTP_ERROR, PROVIDER_TIMEOUT, NETWORK_ERROR, INVALID_JSON, EMPTY_RESPONSE_TEXT, RETRIES_EXHAUSTED
  - `reasoning_content` support for Qwen models
- **Agent contract** (`src/kairoskopion/agents/contract.py`): AgentInput/AgentOutput, AgentRole ABC with `execute()` (LLM) + `execute_deterministic()` (fallback) + `run()` dispatch
- **5 agents** (`src/kairoskopion/agents/`):
  - ArticleModelerAgent — article modeling from text
  - VenueProfilerAgent — venue fact extraction
  - FitAssessorAgent — article×venue fit assessment
  - ArticleSemanticProfilerAgent — disciplinary registers, schools/traditions, argument move, protected core (UC-1 step 3)
  - DisciplinaryPathwayMapperAgent — ranked disciplinary pathways with fit strength, adaptations, field core risk (UC-1 step 4)
- **5 prompt families** (`src/kairoskopion/prompts/`): article_modeling, venue_fact_extraction, fit_assessment, semantic_profiling, disciplinary_mapping — each with system prompt, user template, JSON output schema, validator
- **7 new schema entities**: ArticleSemanticProfile, DisciplinaryPathway, ArticleVariant, VenuePublicationProfile, EditorialBoardProfile, PublishedArticleCorpus, CitationExpectationProfile
- **3 new enums**: DisciplinaryFitStrength (5 values), ArgumentMoveType (12 values), VariantRelation (6 values)
- **7 new ID factories**: `asp_`, `dpath_`, `avar_`, `vpp_`, `ebp_`, `pac_`, `cexp_`
- CLI: `--llm-model`, `--llm-base-url`, `--llm-api-key-env` on `run-fixture`/`run-local`; `status` shows LLM availability
- ManuscriptVenueFitPipeline now accepts `llm_provider` and runs agents through contract
- 33 new tests (706 total, was 673)

### Changed
- Pipeline uses AgentInput/AgentOutput through agent contract instead of direct service calls for article/venue/fit steps

---

## [Unreleased-prior] — Venue Registry v0

### Added
- Venue evidence registry: VenueRecord, VenueSource, VenueClaim, VenueEvidencePack data model
- VenueClaimStatus enum (7 statuses), VenueSourceType enum (10 types)
- Venue registry service module (`services/venue_registry.py`): import, persist, build, conflict resolution, Markdown rendering
- Seed corpus: 5 synthetic venues (34 claims, 12 sources) in `examples/venue_seed_corpus/`
- CLI: `import-venue-seed`, `build-venue-evidence-pack` (16 total, was 14)
- Architecture spec: `docs/VENUE_REGISTRY_ARCHITECTURE.md`
- 32 venue registry tests (673 total, was 641)

### Fixed
- Conflict group detection: claims with `conflict_group` marker now correctly trigger conflict reporting even when only one claim in the pair is marked

---

## [0.2.0-alpha-rc5] — 2026-06-11

> Tag: `v0.2.0-alpha-rc5`. Arbitrary manuscript x venue validation matrix proving general-purpose behavior.

### Fixed
- **D16:** Method detection expanded with broader conceptual markers (`normative framework`, `we argue that`, `theoretical framework`, etc.) and empirical markers (`mixed-methods`, `quantitative`, `thematic analysis`, etc.). Fixes false `unknown` for non-philosophical conceptual articles.
- **D17:** Citation ecology thresholds refined (8-14 refs = `medium`, was `weak` below 20). Risk report now generates `citation_gap` risk for `weak` citation ecology, not only `unknown`.

### Added
- Validation matrix spec: 6 behavioral cases covering good fit, language blocker, method/genre blocker, missing evidence, formal compliance, citation ecology
- 3 synthetic manuscript fixtures + 5 synthetic venue fixtures (all non-private)
- 28 validation matrix behavioral tests (`test_validation_matrix_behavior.py`)
- CLI smoke script (`scripts/run_validation_matrix.ps1`) running all 6 cases
- Validation matrix report: `docs/VALIDATION_MATRIX_REPORT.md`

### Stats
- 641 tests passing (was 613)
- D16-D17 closed: method detection + citation ecology improvements

---

## [0.2.0-alpha-rc4] — 2026-06-10

> Tag: `v0.2.0-alpha-rc4`. Generalized venue-fit anti-overfitting repairs (D12-D15).

### Fixed
- **D12:** Word limit extraction now distinguishes abstract limits (200-250 words) from article body limits (5000-12000 words). `_extract_article_word_limit()` skips abstract-line matches and requires hi >= 1000.
- **D13:** Article type extraction supports numbered lists (`1. Research articles`) and plain bullet lists (`- Research Article`) in addition to bold format (`- **Research Article**`). Keyword filtering prevents false positives.
- **D14:** Discipline matching is no longer STS-only. Generic keyword taxonomy (13 disciplines) with adjacency graph detects overlap between manuscript and venue disciplines.
- **D15:** Citation ecology now returns weak/medium based on bibliography reference count instead of always unknown. Audience axis uses discipline overlap data.

### Added
- `docs/GENERALIZED_VENUE_FIT_INVARIANTS.md` — 7 generalized invariants extracted from trial experience
- 3 synthetic test fixtures: English philosophy venue, Russian-only venue, separated word limits venue
- 16 generalized venue-fit regression tests (`test_generalized_venue_fit.py`) proving language blocker, word limit distinction, article type extraction, discipline matching, audience axis, citation ecology, and genre assessment all work for arbitrary venues

### Stats
- 613 tests passing (was 597)
- D12-D15 closed: anti-overfitting generalization pass

---

## [0.2.0-alpha-rc3] — 2026-06-10

> Tag: `v0.2.0-alpha-rc3`. Logos evidence-pack rerun (target-known trial case, not product target).

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
