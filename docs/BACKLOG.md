# Engineering Backlog — Kairoskopion

**Last updated:** 2026-06-13

Each sprint package is a self-contained autonomous unit. An agent reads CLAUDE.md → PROJECT_STATUS → SPEC_COVERAGE_MATRIX → this BACKLOG, picks the next sprint, implements on a feature branch, updates docs/tests/status, commits, pushes. No manual micromanagement required.

---

## UI Cockpit v0 (Operator/Staging Preview) ✓ DONE (2026-06-13)

**Goal:** Build an operator-facing web cockpit exposing the full Case pipeline through a REST API + React frontend. Wire pipeline continuity (select_venue → fit → mismatch → rewrite chain). This is an internal staging preview, NOT a public product.

**Phases completed:**
1. ✓ Branch `feature/ui-cockpit-v0` from main at `33ca31a` (rc14)
2. ✓ FastAPI backend: app.py + cases.py (19 endpoints, in-memory Case orchestrator)
3. ✓ React+TypeScript frontend scaffold (Vite, 17 components, dark theme)
4. ✓ Phase 0: API layer + scaffold
5. ✓ Phase 1: IntakeSurface, ArticleCard, VenueProfile, EvidenceDrawer
6. ✓ Phase 2: ScenarioBuilder, MismatchMapView, QualityGateBar
7. ✓ Phase 3: PathwayMap, VenuePoolBoard, VenueCandidateCard
8. ✓ Phase 4: AdaptationStudio, RewriteTaskCard, decision flow
9. ✓ Phase 5-6: DecisionLog, DossierView
10. ✓ Phase 7: responsive breakpoints, Escape key, focus styles
11. ✓ Pipeline continuity: select_venue triggers fit/mismatch/rewrite chain
12. ✓ Quality gates populated after stage transitions
13. ✓ TypeScript build clean (tsc --noEmit + vite build)
14. ✓ API smoke test: 18/18 PASS, 1 SKIP (expected)
15. ✓ Browser smoke: all views render, zero console errors, mobile responsive
16. ✓ Backend tests: 188 new (1275 total)

**What this is NOT:** Public product, production deployment, database persistence, authentication, job queue, WebSocket progress, production CORS policy.

**What docs must state:**
- UI Cockpit v0 is operator/staging preview, not public product
- Deterministic backend fallbacks still exist
- Persistence/auth/job queue are not production-ready
- Staging deployment must be protected
- No public prod claim yet

**Branch:** `feature/ui-cockpit-v0`
**Tests added:** 188 new tests (1275 total, was 1068 + 19 from venue pool discovery on main)
**Files:** 35 files, ~9700 lines added

---

## Real Source Acquisition v0 + Adapter Authority Enforcement ✓ DONE (2026-06-13)

**Goal:** Make the venue evidence stack capable of using real external source adapters in opt-in live/cached mode, while enforcing the Source Authority Model at the adapter boundary.

**Phases completed:**
1. ✓ Branch `feature/real-source-acquisition-v0` from `b34ddd7` (v0.2.0-alpha-rc11)
2. ✓ Implementation map doc
3. ✓ Adapter config/mode model (5 modes, SourceAcquisitionConfig)
4. ✓ HTTP client extended (HttpResult, fetch_json_safe, fetch_text_safe)
5. ✓ OpenAlex adapter: fixture + live + cached + authority
6. ✓ Crossref adapter: fixture + live + cached + authority
7. ✓ DOAJ adapter (new): fixture + live + cached + authority
8. ✓ Unpaywall adapter (new): fixture + live (DOI-only) + authority
9. ✓ OpenCitations adapter: upgraded with authority
10. ✓ Snapshot crawler: upgraded with authority + content hash
11. ✓ Aggregation service: cross-adapter conflict detection
12. ✓ VenueEvidenceStack integration with authority/conflict pass-through
13. ✓ CLI: 3 new commands + --use-source-adapters flag
14. ✓ Fixtures: synthetic inline constants per adapter
15. ✓ Tests: 67 new (1010 total)
16. ✓ Documentation: 3 new docs, 5 updated

**What this is NOT:** UI, broad crawling, real all-journal database, live network tests required, retraction/PubPeer lookup.

**Branch:** `feature/real-source-acquisition-v0`
**Tests added:** 67 new tests (1010 total, was 943)
**Report:** `docs/REAL_SOURCE_ACQUISITION_V0.md`

---

## Source Authority Model v0 ✓ DONE (2026-06-13)

**Goal:** Implement Source Authority Model: access modes, authority scopes, authority matrix, claim validation, conflict detection, evidence reconciliation, EvidenceAuditor integration.

**Branch:** `feature/source-authority-integrity-v0`
**Tests added:** 53 new tests (943 total, was 890)
**Report:** `docs/SOURCE_AUTHORITY_MODEL_V0.md`

---

## UC-1 Demo Pack v0 ✓ DONE (2026-06-13)

**Goal:** Create a fully reproducible offline UC-1 demo: synthetic fixtures, demo loader, workflow runner, report generator, CLI command, 16 output artifacts. Fix 3 agent attribute bugs exposed by the demo.

**Phases completed:**
1. ✓ Branch `feature/uc1-demo-pack-v0` from main at `d20ff8f`
2. ✓ Synthetic demo dataset: draft article (Simondon/STS, ~1200 words), 5 venue seeds, 3 venue guidelines, 3 corpus files (9 articles), scenario.json
3. ✓ Demo loader module: `src/kairoskopion/demo/uc1_demo_loader.py` with validation
4. ✓ CLI command: `run-uc1-demo` with `--pack-dir` and `--output-dir` flags
5. ✓ Artifact output: 16 files (workflow_trace.json, entity JSONs, UC1_DEMO_REPORT.md)
6. ✓ Report generator: `src/kairoskopion/demo/uc1_report.py`
7. ✓ Agent bugfixes: compliance_auditor (title/abstract/keywords), submission_pack_builder (readiness), evidence_auditor (status.value, findings)
8. ✓ Tests: 35 new (890 total, was 855)
9. ✓ Documentation: `docs/UC1_DEMO_PACK_V0.md`
10. ✓ Commit, push, release audit

**What this is NOT:** New architecture, live APIs, real venue DB, real corpus, LLM inference.

**Branch:** `feature/uc1-demo-pack-v0`
**Tests added:** 35 new tests (890 total, was 855)
**Report:** `docs/UC1_DEMO_PACK_V0.md`

---

## Venue Evidence Stack V1–V2 Foundation ✓ DONE (2026-06-12)

**Goal:** Implement the Venue Evidence Stack foundation: 8-level depth model, demand-driven depth policies, content-addressed vault storage, 4 venue adapters, corpus profiler, agent upgrades (VenueIdentifier, ProfileBuilder, CorpusSampler), workflow wiring, CLI commands, documentation.

**Phases completed:**
1. ✓ Verify state: branch `feature/venue-evidence-stack-v1-v2` at `babcbbc`, 834 tests passing
2. ✓ Implementation map: `docs/VENUE_EVIDENCE_STACK_V1_V2_IMPLEMENTATION_MAP.md`
3. ✓ topic_clusters type fix: `list[str]` → `list[dict[str, Any]]` in schema.py
4. ✓ VenueIdentifierAgent upgrade: stub → functional identity resolution with ISSN normalization
5. ✓ VenuePublicationProfileBuilderAgent rewrite: depth-aware, corpus/citation/editorial consumption
6. ✓ Workflow wiring: venue_identifier in direct_fit (9 steps), corpus_sampler in venue_deep_profile (4 steps)
7. ✓ CLI smoke: all 4 new commands produce valid output
8. ✓ Documentation: 4 new docs (REPORT, VENUE_DEPTH_POLICY, VAULT_BACKEND_ARCHITECTURE, VENUE_CORPUS_PROFILER_V2), 5 updated (CHANGELOG, PROJECT_STATUS, BACKLOG, SPEC_COVERAGE_MATRIX)
9. ✓ Full validation: 855 tests passing, 0 failures
10. ✓ Commit and push

**What this is NOT:** Live API adapters, L4-L7 data collection, cross-session vault persistence, mass crawling.

**Branch:** `feature/venue-evidence-stack-v1-v2`
**Tests added:** 73 new tests (855 total, was 782)
**Report:** `docs/VENUE_EVIDENCE_STACK_V1_V2_REPORT.md`

---

## Agentic Contour v0.1 (UC-1 Orchestrated Layer) ✓ DONE (2026-06-12)

**Goal:** Implement the full UC-1 orchestrated agent layer: runtime models, 26 agent shells (7 layers), registry, executor, orchestrator, 4 workflow specs, 16 prompt families, 7 CLI commands. All operational agents wrap existing deterministic services. Review layer is contract-only (6 stubs). No fabrication.

**Phases completed:**
1. ✓ Runtime models: 13 dataclasses (AgentSpec, AgentTask, AgentRun, AgentResult, AgentTrace, AgentFailure, AgentToolCall, WorkflowStepSpec, AgenticWorkflowSpec, WorkflowRun, WorkflowResult, WorkflowTrace)
2. ✓ 7 new enums + 7 new ID factories
3. ✓ 11 new prompt families + catalog (16 total)
4. ✓ 21 new agent shells (4 control, 4 venue, 3 fit, 3 submission, 6 review, 1 evidence) + base_shell utilities
5. ✓ Agent registry: 26 AgentSpec entries, layer filtering, class instantiation
6. ✓ Executor: single-agent execution with task/run/trace tracking
7. ✓ Orchestrator: sequential workflow with shared entity pool, skip_if_missing
8. ✓ 4 workflow specs: direct_manuscript_venue_fit (8), uc1_draft_to_venue_pool (12), venue_deep_profile (3), review_loop (6, skeleton)
9. ✓ 7 CLI commands: list-agents, inspect-agent, list-prompt-families, inspect-prompt-family, list-workflows, inspect-workflow, run-agent-workflow
10. ✓ 76 new tests (782 total, was 706)
11. ✓ Architecture + report docs

**What this is NOT:** LLM execution exercised, review-layer functional, parallel orchestration.

**Branch:** `feature/agentic-contour-uc1-v01`
**Tests added:** 76 new tests (782 total)
**Report:** `docs/AGENTIC_CONTOUR_V0_REPORT.md`

---

## UC-1 Semantic Profiling Agents + LLM Config ✓ DONE (2026-06-12)

**Goal:** Implement UC-1 "Draft-to-Venue-Pool Positioning" substrate: LLM config aligned with litops/quint, agent contract, 5 agents (3 pipeline + 2 UC-1 profiling), 5 prompt families, 7 new schema entities, 3 new enums. Production LLM config supported but deterministic fallback always available.

**Phases completed:**
1. ✓ LLM subsystem: config, OpenAI-compatible provider, error taxonomy, diagnostics
2. ✓ Agent contract: AgentInput/AgentOutput/AgentRole with dual execution paths
3. ✓ 3 pipeline agents: ArticleModeler, VenueProfiler, FitAssessor
4. ✓ 2 UC-1 agents: ArticleSemanticProfiler, DisciplinaryPathwayMapper
5. ✓ 5 prompt families with system prompts, user templates, JSON schemas, validators
6. ✓ 7 new entities: ArticleSemanticProfile, DisciplinaryPathway, ArticleVariant, VenuePublicationProfile, EditorialBoardProfile, PublishedArticleCorpus, CitationExpectationProfile
7. ✓ 3 new enums: DisciplinaryFitStrength, ArgumentMoveType, VariantRelation
8. ✓ Pipeline rewrite to use agent contract
9. ✓ CLI LLM options: --llm-model, --llm-base-url, --llm-api-key-env
10. ✓ 33 new tests, 706 total

**What this is NOT:** Full Agent Runtime (spec Wave 6). This is the agent contract + concrete agents. Agent orchestration, runtime loop, operation journal are future work.

**Branch:** `main` (direct commit by user request)
**Tests added:** 33 new tests (706 total, was 673)

---

## Venue Registry / Source Collector Architecture v0 ✓ DONE (2026-06-12)

**Goal:** Design and implement a general venue evidence registry with data model, provenance discipline, import path, seed corpus format, CLI integration, and report integration.

**Phases completed:**
1. ✓ Architecture spec: `docs/VENUE_REGISTRY_ARCHITECTURE.md`
2. ✓ Seed corpus: 5 synthetic venues in `examples/venue_seed_corpus/`
3. ✓ Enums: VenueClaimStatus (7), VenueSourceType (10)
4. ✓ Domain model: VenueRecord, VenueSource, VenueClaim, VenueEvidencePack
5. ✓ Service module: import, persist, build, conflict resolution, Markdown rendering
6. ✓ CLI: `import-venue-seed`, `build-venue-evidence-pack`
7. ✓ Synthetic trial: evidence pack → run-local pipeline
8. ✓ Bug fix: conflict_group detection
9. ✓ Docs update: CHANGELOG, BACKLOG, PROJECT_STATUS, README, CLAUDE.md
10. ✓ 32 tests, 673 total

**Branch:** `feature/venue-registry-source-collector-v0`
**Report:** `docs/VENUE_REGISTRY_V0_REPORT.md`

---

## Arbitrary Manuscript x Venue Validation Matrix ✓ DONE (2026-06-11)

**Goal:** Prove Kairoskopion behaves as a general evidence-first article-to-venue trajectory engine for arbitrary manuscripts and venues, not just the Logos trial.

**Phases completed:**
1. ✓ Validation matrix spec: 6 behavioral cases defined
2. ✓ Synthetic fixtures: 3 manuscripts + 5 venues (all non-private)
3. ✓ Behavioral tests: 28 tests across 6 test classes
4. ✓ CLI smoke script: 6/6 pass via `kairoskopion run-local`
5. ✓ Bounded repairs: D16 (method detection), D17 (citation ecology thresholds + risk)
6. ✓ Validation matrix report: `docs/VALIDATION_MATRIX_REPORT.md`

**Defects closed:**
- D16: Method detection missed normative/theoretical/argumentative markers
- D17: Citation ecology threshold too coarse (20 refs); citation_gap risk missing for weak bibliography

**Branch:** `feature/arbitrary-manuscript-venue-validation-matrix`
**Tests added:** 28 new tests (641 total, was 613)
**Report:** `docs/VALIDATION_MATRIX_REPORT.md`

---

## Logos Venue Evidence Pack + Rerun ✓ DONE (2026-06-10)

**Goal:** Close D10 — replace conservative UNKNOWN venue seed with real evidence pack collected from official Logos journal sources. Close D11 — fix language policy extraction bug found during evidence-pack rerun.

**Phases completed:**
1. ✓ Audit existing seed (10 UNKNOWN items, 22 unknowns)
2. ✓ Identify official sources (logosjournal.ru pages, RCSI portal, external indexers)
3. ✓ Collect evidence (10 source notes under private_inputs/)
4. ✓ Build venue evidence pack (synthesized with evidence status categories)
5. ✓ Rerun pipeline (poor_fit, 1 blocking mismatch — language)
6. ✓ Comparison report (docs/TRIAL_LOGOS_EVIDENCE_RERUN_REPORT.md)
7. ✓ Bounded repair (D11 — language policy extraction)
8. ✓ Tests, safety check, commit, push

**Defects closed:**
- D10: UNKNOWN seed replaced with real evidence pack
- D11: Language policy extraction confused metadata language with article body language

**Branch:** `feature/logos-venue-evidence-pack-rerun`
**Tests added:** 5 new tests (597 total, was 592)
**Report:** `docs/TRIAL_LOGOS_EVIDENCE_RERUN_REPORT.md`

---

## Generalized Venue-Fit Anti-Overfitting Repairs ✓ DONE (2026-06-10)

**Goal:** Extract reusable product logic from the Logos trial so Kairoskopion improves for arbitrary manuscripts and venues. No Logos-specific hardcoding.

**Phases completed:**
1. ✓ Reality audit: identified 7 generalized invariants from trial experience
2. ✓ Anti-overfitting code review: confirmed no Logos-specific hardcoding in pipeline
3. ✓ Doc updates: CHANGELOG, README, CLAUDE.md, PROJECT_STATUS version alignment
4. ✓ Code fixes: D12 (word limit distinction), D13 (article type extraction), D14 (discipline matching), D15 (citation ecology + audience axes)
5. ✓ Generalized regression tests: 3 synthetic fixtures + 16 tests proving generic behavior
6. ✓ Full test suite green (613 tests)

**Defects closed:**
- D12: Word limit extraction confused abstract limits with article body limits
- D13: Article type extraction only recognized bold format (missed numbered/bullet lists)
- D14: Discipline matching was STS-only — replaced with generic 13-discipline keyword taxonomy + adjacency graph
- D15: Citation ecology always returned unknown — now uses bibliography reference count; audience axis uses discipline overlap

**Branch:** `feature/generalized-venue-fit-anti-overfit-repairs`
**Tests added:** 16 new tests (613 total, was 597)
**Invariants doc:** `docs/GENERALIZED_VENUE_FIT_INVARIANTS.md`

---

## Logos Target Trial Quality Audit ✓ DONE (2026-06-10)

**Goal:** Fix 9 product defects found during first real-use-case trial (philosophical article targeting Logos journal with conservative UNKNOWN venue seed).

**Defects closed:**
- D1: Venue name extraction from seed files
- D2: Venue model hallucination from UNKNOWN seeds
- D3: Venue unknowns propagation
- D4: Genre misclassification for philosophical articles
- D5: Method misclassification for conceptual articles
- D6: Empty RewritePlan under venue uncertainty → conditional trajectory actions
- D7: AI disclosure false positive on AI-as-topic
- D8: title_fragment null for all references → multi-style extraction
- D9: source_kind misclassification → report detection, DOI inference, tightened chapter markers

**Branch:** `feature/logos-target-trial-quality-audit`
**Tests added:** 25 new tests (592 total, was 567 after D1-D5/D7, was 556 before trial)
**Report:** `docs/TRIAL_LOGOS_REPORT.md`

---

## Sprint 1: Real Document Intake ✓ DONE

**Goal:** Accept PDF, DOCX, TXT, MD, HTML files and extract text content for pipeline processing.

**Scope:**
- PDF text extraction using `pypdf` or `pdfplumber` (MIT-licensed)
- DOCX text extraction using `python-docx`
- Improved MD/TXT/HTML intake (section detection, bibliography extraction)
- Extraction statuses: extracted, partially_extracted, unsupported, failed, binary_not_extracted, needs_ocr, encrypted_or_unreadable, unknown
- File metadata: path, filename, extension, size_bytes, modified_at, content_hash, extraction_method, extraction_status, extraction_warnings, text_length, source_role
- CLI: `kairoskopion intake-file --file FILE --role ROLE --storage-root PATH`
- `run-local` uses improved intake layer
- Support DOCX and PDF for manuscript/venue guidelines

**Non-goals:**
- No OCR (scanned PDFs remain `needs_ocr`)
- No image/figure extraction
- No GROBID integration
- No layout analysis

**Tests required:**
- Markdown, txt, html, json extraction
- DOCX extraction (if dependency implemented)
- PDF extraction (if dependency implemented)
- Unsupported extension → explicit status
- Missing file → clean error
- Binary file → explicit status
- Content hash stable
- Metadata recorded
- Source snapshot persisted
- Evidence item created
- `run-local` still works on examples
- No network calls

**Acceptance criteria:**
- `kairoskopion run-local --manuscript paper.pdf` works
- Extracted text feeds into pipeline normally
- SourceSnapshot records extraction method and status
- All previous tests remain green

**Depends on:** None.

---

## Sprint 2: Entity Completeness ✓ DONE

**Goal:** Bring core entities closer to spec before adding more external intelligence.

**Scope:**

### 2.1 FitAssessment axes (expand from 8 to 12):
- topic (existing)
- discipline (existing)
- genre (existing)
- argument_structure (new)
- method (existing)
- citation_ecology (existing)
- novelty_positioning (new)
- language_register (existing)
- audience (new)
- formal_compliance (existing)
- author_eligibility (new)
- publication_regime (existing)

No numeric aggregate score.

### 2.2 Risk taxonomy (expand from 7 to 18):
- desk_reject_risk
- scope_mismatch
- methodology_mismatch
- citation_gap
- language_quality
- ethical_concern
- formatting_violation
- predatory_venue
- author_eligibility
- duplicate_submission
- copyright_conflict
- data_availability
- reviewer_pool_mismatch
- timeline_risk
- cost_risk
- reputational_risk
- ai_policy_risk
- core_transformation_risk

### 2.3 ArticleModel practical fields:
- word_count
- section_count
- reference_count
- abstract_length
- has_references_section
- has_methods_section
- has_data_availability_statement
- has_ai_disclosure
- language
- manuscript_stage
- protected_core_status
- extraction_status / source_text_status

### 2.4 VenueModel enrichment:
- official_urls
- aims_scope_summary
- indexing_claims
- metrics_claims
- open_access_status
- apc_policy
- review_process_claims
- article_types
- word_limits
- anonymization_policy
- ai_policy
- data_policy
- ethics_policy
- freshness_status

Claims must be claims, not facts, unless source/evidence supports them.

**Tests required:**
- All new fit axes created, no single score
- Missing data yields unknown axes
- New risk types can be created
- ArticleModel fields populate from markdown/doc intake where possible
- VenueModel fields populate from guidelines where possible
- Serialization roundtrip preserves new fields
- Backward compatibility with existing fixtures
- All previous tests remain green

**Depends on:** None (can run in parallel with Sprint 1).

---

## Sprint 3: Real Optional Adapters ✓ DONE

**Goal:** Connect OpenAlex, Crossref, OpenCitations APIs with real HTTP calls, disabled by default.

**Scope:**
- Adapter mode: disabled / mock / real
- network_allowed false by default
- Timeout, max_results, rate_limit, cache path configuration
- Optional polite email for OpenAlex
- Crossref real adapter first (no auth required)
- OpenAlex/OpenCitations real mode if safe
- CLI: `kairoskopion adapters-smoke --adapter crossref --mode real --network-allowed`
- Default remains mock/offline

**Evidence rules:**
- Adapter metadata is not absolute truth
- DOI match may be externally_matched, not blindly verified
- Mock data never verifies

**Tests required:**
- Real mode disabled by default
- Real mode requires explicit network flag
- Mock mode still works
- Cache works
- Rate-limit config present
- Error handling (timeout, 404, 429, 500)
- No network calls in normal tests
- Evidence statuses correct

**Depends on:** None.

---

## Sprint 4: Venue Profile Builder ✓ DONE

**Goal:** Turn venue guidelines and saved local pages into a rich VenueProfile.

**Scope:**
- Multiple source files per venue (aims/scope, guidelines, editorial board, policy pages)
- Local files only, no web fetch required, no LLM
- Models: VenueProfile, VenuePolicyProfile, AuthorGuidelinesProfile, ReviewModelProfile, PublicationRequirementsProfile, AimsScopeProfile, IndexingClaimsProfile, APCPolicyProfile, AIUsePolicyProfile, DataPolicyProfile, EthicsPolicyProfile
- Service: `src/kairoskopion/services/venue_profile_builder.py`
- CLI: `kairoskopion build-venue-profile --sources PATH_OR_DIR --storage-root PATH`

**Tests required:**
- Aims/scope extraction
- Article types detection
- Word limits extraction
- Anonymization/double-blind detection
- AI policy unknown/present
- APC/indexing claims as claims
- Evidence/source refs
- Freshness
- Vault output
- No network

**Depends on:** Sprint 1 recommended but not required.

---

## Sprint 5: Bibliography Robustness + Report Quality ✓ DONE

**Goal:** Make citation ecology and reports useful for real article positioning.

**Scope:**
- Multiple reference styles: APA, Chicago, Vancouver, numbered
- DOI URL forms
- Duplicate detection
- Old/new distribution
- Bridge references
- Warnings: too few, old, missing DOI, weak venue bridge
- Reference linking to adapter results
- Consolidated `PublicationTrajectoryReport`
- CLI: `kairoskopion report --storage-root PATH --latest`

**Depends on:** None.

---

## Sprint 6: SubmissionPack + Reports ✓ DONE

**Goal:** Create structured SubmissionPack preparation layer.

**Scope:**
- SubmissionPack entity: target venue, article, scenario, required/missing files, statements, compliance checklist, citation tasks, risk summary, readiness status, blockers, human decision points
- Cannot be ready if gates fail
- Cannot mark missing info complete
- No fake declarations
- No auto-submit
- CLI: `kairoskopion build-submission-pack --storage-root PATH --latest`

**Depends on:** Sprint 5 (report quality) recommended.

---

## Sprint 7: Litops Compatibility Bridge ✓ DONE

**Goal:** Create local Litops-compatible export without coupling repos.

**Scope:**
- `src/kairoskopion/integrations/litops_bridge.py`
- CLI: `kairoskopion export-litops-pack --storage-root PATH --output PATH`
- Pack contains registries, vault, manifest, metadata
- Source refs mapped
- No Litops installation required

**Depends on:** Sprint 6.

---

## Sprint 8: WhiteCrow Patch Queue Bridge ✓ DONE

**Goal:** Create first protected-core-aware patch queue export.

**Scope:**
- Models: ProtectedCoreImport, PatchCandidate, PatchQueueExport, CoreImpactAssessment, RewriteTrajectoryStep
- `src/kairoskopion/integrations/whitecrow_bridge.py`
- CLI: `kairoskopion export-whitecrow-patches --storage-root PATH --protected-core FILE --output PATH`
- Core-touching actions require human acceptance flag
- No auto rewrite

**Depends on:** Sprint 7.

---

## Sprint 9: LLM-Assisted Extraction (when requested)

**Goal:** Optional LLM-powered article modeling and venue profiling.

**Scope:**
- LLM provider interface (OpenAI-compatible)
- LLM-assisted ArticleModel + VenueModel extraction
- Deterministic fallback preserved
- Evidence status: LLM outputs marked as INFERENCE

**Depends on:** Sprint 1-4 (stable extraction layer).

---

## GPT-16 Alignment Sprints (added 2026-06-13)

See `docs/GPT16_ALIGNMENT_MATRIX.md` for full matrix. These sprints cover items
that are in the spec but were missing from the backlog.

### Sprint GP-1: Source Authority and Access Separation (P0)

**Status:** v0 DONE (2026-06-13, `feature/source-authority-integrity-v0`)
- SourceAccessMode / SourceAuthorityScope enums
- SourceAuthorityClaim, SourceAuthorityAssessment models
- Authority checker service with deterministic matrix
- EvidenceAuditor integration (optional authority/conflict params)
- 53 tests
- **Adapter-level enforcement:** DONE in Real Source Acquisition v0 — all 6 venue adapters call `_attach_authority()` at parse time

### Sprint GP-2: Evidence Conflict and Reconciliation (P0)

**Status:** v0 DONE (foundation models in source_authority.py)
- EvidenceConflict model with conflict_type, severity, resolution_status
- EvidenceReconciliationResult model
- detect_conflicts() and reconcile_evidence() in service
- Future: agent-driven reconciliation, user confirmation flow

### Sprint GP-3: Citation Integrity Gate (P1)

**Status:** Model DONE, service FUTURE
- CitationIntegrityCheck model (retraction, PubPeer, expression of concern, DOI resolution)
- RetractionStatus enum
- Future: live Crossref Retraction Watch integration, PubPeer API

### Sprint GP-4: Publication History Model (P1)

**Status:** Model DONE, population FUTURE
- PublicationHistoryModel with prior_versions, preprint/thesis/conference overlap
- PriorVersion model, PriorVersionType enum
- Future: user input flow, preprint server lookup, thesis repository check

### Sprint GP-5: Corpus Representativeness Hardening (P1)

**Status:** Field exists (selection_strategy), enforcement FUTURE
- PublishedArticleCorpus already has selection_strategy field
- Future: bias_notes enforcement, representativeness warnings in FitAssessment

### Sprint GP-6: Reporting Guideline Selector (P2)

**Status:** Model DONE, selector logic FUTURE
- ReportingGuidelineSelection model
- Future: EQUATOR database mapping, article-type → guideline selection rules

### Sprint GP-7: Author/Affiliation/Funder Identity (P2)

**Status:** FUTURE
- AuthorSubmissionProfile model (ORCID, ROR affiliation, CRediT roles, funder IDs)
- Future: ORCID API integration, ROR affiliation normalization

### Sprint GP-8: AI Disclosure and Prompt-Injection Scanner (P2)

**Status:** FUTURE (risk_officer checks AI disclosure flag)
- AIUseDisclosureScanner agent
- Future: ICMJE compliance checker, manuscript prompt-injection scanner

### Sprint GP-9: Submission-System Readiness (P2)

**Status:** FUTURE
- OJS/Editorial Manager/ScholarOne field mapping
- SubmissionPack portal alignment checks

### Sprint GP-10: OpportunityModel for Special Issues/CFPs (P2)

**Status:** FUTURE
- OpportunityModel (CFP, special issue, symposium, guest editors, deadline)
- Future: CFP channel watcher, association website scraper

### Sprint GP-11: Evaluation Suite Expansion (P3)

**Status:** PARTIAL (UC-1 demo pack + 6 validation cases)
- Future: adversarial fixtures (bad journal, corpus contradicts aims, sparse bibliography)
- Scenario-specific evaluation metrics from spec

### Sprint GP-12: Failure-as-State Enforcement (P0)

**Status:** Partially DONE in Real Source Acquisition v0
- All 6 venue adapters return structured VenueAdapterResult on any error (never exceptions)
- Aggregation service catches unexpected exceptions at adapter boundary
- VenueAdapterStatus enum: success, partial, no_results, unavailable, error, rate_limited
- Future: integration test that inaccessible source → INACCESSIBLE status preserved end-to-end through pipeline

## Later (only when explicitly requested)

- Telegram intake bot
- Web UI
- Reviewer simulation (controlled, labeled)
- Venue pool discovery
- Submission portal profiles
- Multi-venue comparison pipeline

---

## Sprint selection rules

1. Agent reads BACKLOG.md and SPEC_COVERAGE_MATRIX.md
2. Picks the lowest-numbered sprint whose dependencies are met
3. User can override by naming a specific sprint
4. Each sprint = one feature branch, one commit message, one push
5. No sprint may silently skip tests or docs
6. No sprint may break existing tests
7. After sprint: update PROJECT_STATUS, ROADMAP, SPEC_COVERAGE_MATRIX, CLAUDE.md
