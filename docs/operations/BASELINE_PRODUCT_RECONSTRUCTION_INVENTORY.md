# Baseline Product Reconstruction Inventory

**Date:** 2026-07-11
**Branch:** `program/baseline-user-journey-reconstruction`
**Base commit:** `0e1dbf0` (main)

---

## User Journey: 12 Stages

```
Manuscript → ArticleModel → user-confirmed ArticleModel
→ Venue Discovery / Direct Venue → VenueModel
→ SubmissionScenario → FitAssessment → MismatchMap
→ RewritePlan → CitationPlan → RiskReport → SubmissionPack
```

---

## Stage-by-Stage Implementation Status

### 1. Manuscript Intake

| Aspect | Status | Detail |
|--------|--------|--------|
| Backend method | **REAL** | `Case.intake_text()` (L245-359): LLM InputClassifierAgent + deterministic fallback, routes to article or venue pipeline |
| File upload | **REAL** | `/cases/{id}/intake/file` (app.py L310-391): PDF/DOCX/MD/TXT/HTML extraction |
| API endpoints | **REAL** | `POST /intake/text`, `POST /intake/file`, `POST /intake/override` |
| UI component | **REAL** | `IntakeSurface.tsx` (text+file drag-drop, type selector, region, search depth, char count) + `InputTypeOverridePanel.tsx` |
| LLM integration | **REAL** | InputClassifierAgent with conservative UNKNOWN fallback |
| Tests | **STRONG** | ~106 tests across 10 files |

**Verdict: OPERATIONAL**

### 2. ArticleModel Creation

| Aspect | Status | Detail |
|--------|--------|--------|
| Backend method | **REAL** | `Case._build_article_model()` (L478-621): LLM ArticleModelerAgent + deterministic fallback, auto-names case, chains to discipline matcher + semantic profiler + article FPM |
| Schema | **REAL** | `ArticleModel` (schema.py L188): 30+ fields with to_dict/from_dict |
| API endpoints | **REAL** | `GET /article-model`, `POST /article-model/rerun`, `POST /article-model/confirm`, `POST /article-model/refine` |
| UI component | **REAL** | `ArticleCard.tsx` (technical view) + `HumanModelView.tsx` (human view with per-block accept/reject, refinement chat, genre/method rerun) |
| LLM integration | **REAL** | ArticleModelerAgent with JSON repair + structural fallback |
| Discipline matching | **REAL** | `DisciplineMatcherAgent` (L99-217): LLM+keyword fallback, max_tokens=8192, truncation detection |
| Semantic profiling | **REAL** | `ArticleSemanticProfilerAgent`: LLM+fallback |
| Tests | **ADEQUATE** | ~38 dedicated + 16 truncation regression + agent contract tests |

**Verdict: OPERATIONAL** — dual view (human/technical), refinement chat, discipline rerun all wired.

### 3. User-Confirmed ArticleModel

| Aspect | Status | Detail |
|--------|--------|--------|
| Backend method | **REAL** | `Case.confirm_article_model()` (L1416-1478): applies corrections, sets lifecycle_status=CONFIRMED, logs to CorrectionRegistry |
| API endpoint | **REAL** | `POST /article-model/confirm` |
| UI component | **REAL** | Confirm button in `ArticleCard.tsx`, corrections in `HumanModelView.tsx` |
| Protected core | **REAL** | Protected core zone with add/remove in ArticleCard |
| Tests | **ADEQUATE** | Tested via `test_api_cases.py`, `test_blocker_regression.py` |

**Verdict: OPERATIONAL**

### 4. Venue Discovery / Direct Venue

| Aspect | Status | Detail |
|--------|--------|--------|
| Direct venue investigation | **REAL** | `Case.investigate_venue()` (L904-1002): LLM VenueProfilerAgent + deterministic fallback, min 200 chars, stores in registry |
| Venue by URL | **REAL** | `Case.investigate_venue_by_url()` (L1058-1095): URL fetch + SSRF protection |
| Venue by reference | **REAL** | `Case.investigate_venue_by_reference()` (L1004-1028): resolves evidence pack |
| Venue discovery (pool) | **REAL** | `Case.discover_venues()` (L1742-1812): LLM VenueDiscoveryAgent + deterministic fallback |
| API endpoints | **REAL** | `POST /investigate-venue`, `POST /investigate-venue-by-url`, `POST /investigate-venue-by-reference`, `POST /discover-venues`, `GET /venue-pool`, `POST /select-venue/{id}` |
| UI component | **REAL** | `VenuePoolBoard.tsx` + `VenueCandidateCard.tsx` (sortable grid, confidence badges, selection) |
| Tests | **STRONG** | ~96 tests (venue pool discovery) + 39 tests (venue profiling) |

**Verdict: OPERATIONAL**

### 5. VenueModel

| Aspect | Status | Detail |
|--------|--------|--------|
| Schema | **REAL** | `VenueModel` (schema.py L256): 25+ fields. **No ISSN field** (by design — ISSN in VenueRegistryRecord) |
| Venue profiling | **REAL** | LLM VenueProfilerAgent + deterministic regex extraction |
| Venue FPM | **REAL** | VenueFieldPositionerAgent, LLM or deterministic |
| Venue family context | **REAL** | VenueFamilyContextBuilderAgent, LLM (Organ #3) |
| API endpoints | **REAL** | `GET /investigated-venue`, `POST /enrich-venue`, `GET /venue-profile-package` |
| UI component | **REAL** | `VenueProfile.tsx` (technical) + `HumanModelView.tsx` (human view) |
| Tests | **STRONG** | ~39 dedicated + 93 evidence-pack tests |

**Verdict: OPERATIONAL**

### 6. SubmissionScenario

| Aspect | Status | Detail |
|--------|--------|--------|
| Schema | **REAL** | `SubmissionScenario` (schema.py L310): goal, priorities, APC, deadline, rewrite/reframe depth, risk tolerance |
| Backend method | **REAL** | `Case.set_scenario()` (L1648-1676) |
| Preliminary scenario | **REAL** | Auto-created in `_run_fit_chain()` if operator hasn't filled one |
| API endpoints | **REAL** | `POST /scenario`, `GET /scenario` |
| UI component | **REAL** | `ScenarioBuilder.tsx` (full form: goal, prestige/speed, APC, deadline, language, rewrite depth, risk, indexing) |
| Tests | **THIN** | No dedicated test file — tested only as side effect of SubmissionPack tests |

**Verdict: OPERATIONAL but thin test coverage**

### 7. FitAssessment

| Aspect | Status | Detail |
|--------|--------|--------|
| Schema | **REAL** | `FitAssessment` (schema.py L352): 12-axis assessment with FitAxis sub-model |
| Backend method | **REAL** | In `_run_fit_chain()` (L1923-1961): LLM FitAssessorAgent + deterministic `assess_fit` |
| Field position fit | **REAL** | `compute_field_position_fit()` when both FPMs present |
| API endpoints | **REAL** | `GET /fit` |
| UI component | **REAL** | Fit matrix in `DossierView.tsx` (12 axes with unknowns/evidence) |
| Tests | **STRONG** | ~88 tests across 4 files |

**Verdict: OPERATIONAL**

### 8. MismatchMap

| Aspect | Status | Detail |
|--------|--------|--------|
| Schema | **REAL** | `MismatchMap` (schema.py L387): list of MismatchItem (axis, article_side, venue_side, severity, possible_actions, field_core_risk) |
| Backend method | **REAL** | In `_run_fit_chain()` (L1985-2234): deterministic `build_mismatch_map()` + LLM MismatchNarratorAgent with per-axis rescue |
| API endpoints | **REAL** | `GET /mismatch-map` |
| UI component | **REAL** | `MismatchMapView.tsx` (sorted by severity, article/venue sides, actions, core risk badges) |
| Tests | **MODERATE** | ~18 dedicated + heavy indirect coverage |

**Verdict: OPERATIONAL** — narrator enrichment with rescue is production-quality.

### 9. RewritePlan

| Aspect | Status | Detail |
|--------|--------|--------|
| Schema | **REAL** | `RewritePlan` (schema.py L404): changes list, effort, field_core_risk, semantic_status, attempt_diagnostics |
| Backend method | **REAL** | In `_run_fit_chain()` (L2269-2310): LLM `try_llm_rewrite_planner` + needs_llm placeholder. Protected core policy gate. |
| User decisions | **REAL** | `Case.apply_decisions()` (L2563-2599) via review_loop service |
| API endpoints | **REAL** | `GET /adaptation-plan`, `POST /decisions` |
| UI component | **REAL** | `AdaptationStudio.tsx` + `RewriteTaskCard.tsx` (filterable changes, accept/reject/defer, core gate) |
| Tests | **THIN** | ~10 dedicated + indirect via test_review_loop (20), test_protected_core (19) |

**Verdict: OPERATIONAL** — LLM wired with needs_llm fallback; policy gate live.

### 10. CitationPlan

| Aspect | Status | Detail |
|--------|--------|--------|
| Schema | **REAL** | `CitationPlan` (schema.py L427): gap categories, search tasks, padding warnings, semantic_status |
| Backend method | **REAL** | In `_run_fit_chain()` (L2339-2385): structural `build_minimal_citation_plan` + LLM upgrade via `upgrade_citation_plan_with_llm` |
| BibliographyProfile | **REAL** | `build_minimal_bibliography_profile` from raw article text |
| API endpoints | **REAL** | Part of `GET /adaptation-plan` response |
| UI component | **REAL** | Section in `DossierView.tsx` |
| Tests | **MODERATE** | ~24 tests (citation ecology) |

**Verdict: OPERATIONAL**

### 11. RiskReport

| Aspect | Status | Detail |
|--------|--------|--------|
| Schema | **REAL** | `RiskReport` (schema.py L570): risk_items (18-type taxonomy), overall_risk_label, semantic_status |
| Backend method | **REAL** | In `_run_fit_chain()` (L2246-2267): LLM `try_llm_risk_officer` + needs_llm placeholder |
| API endpoints | **REAL** | Part of `GET /adaptation-plan` response |
| UI component | **REAL** | Section in `DossierView.tsx` (semantic status, risk items, mitigations) |
| Tests | **ADEQUATE** | ~35 tests across 2 files |

**Verdict: OPERATIONAL**

### 12. SubmissionPack

| Aspect | Status | Detail |
|--------|--------|--------|
| Schema | **REAL** | `SubmissionPack` (schema.py L617): files, statements, missing_items, blocking_issues, ready_status |
| Backend method | **REAL** | In `_run_fit_chain()` (L2459-2481): `build_minimal_submission_pack` from all upstream |
| Also: standalone | **REAL** | `Case.build_submission_pack_api()` (L1181-1200) |
| ComplianceChecklist | **REAL** | `build_minimal_compliance_checklist` with error placeholder fallback |
| API endpoints | **REAL** | `POST /build-submission-pack`, `GET /compliance` |
| UI component | **PARTIAL** | CaseWorkspace shows placeholder with `DepthModePanel.tsx` + `DecisionLog.tsx`, no dedicated submission pack viewer |
| Tests | **ADEQUATE** | ~32 tests |

**Verdict: OPERATIONAL** — but UI is the weakest link (no dedicated pack builder/viewer).

---

## Cross-Cutting Infrastructure

### LLM Runtime (Current State)

| Aspect | Status | Detail |
|--------|--------|--------|
| Provider | **REAL** | `openai_compat.py`: OpenAI-compatible, 302.ai proxy |
| Config | **REAL** | `LLMConfig.for_role(role_id)`: per-role model override via env vars |
| Structured output | **REAL** | `response_format.json_schema.strict: true` |
| JSON repair | **REAL** | `repair_and_parse()`: ```json fences, balanced brace extraction |
| Retry/fallback | **REAL** | Model fallback chain in provider |
| Truncation detection | **REAL** | `finish_reason == "length"` check (discipline_matcher) |
| Default max_tokens | **FRAGMENTED** | Global default 4096, discipline_matcher 8192, each agent hardcodes independently |
| Token budget tracking | **MISSING** | No unified token budget across agents |
| Attempt metadata | **PARTIAL** | `LLMAttemptMetadata` exists but only discipline_matcher fully uses it |

**Problem: LLM runtime is fragmented.** Each agent constructs its own provider call with hardcoded parameters. No unified orchestration, no cross-agent budget, no centralized attempt tracking.

### Persistence (CaseStore)

| Aspect | Status | Detail |
|--------|--------|--------|
| Format | **REAL** | JSON-per-case files |
| User scoping | **REAL** | `users/<user_id>/cases/<case_id>.json` |
| Serialization | **REAL** | Full roundtrip of all 20+ domain models via `_case_to_snapshot`/`_case_from_snapshot` |
| Atomic write | **REAL** | tmp + rename |
| Path traversal defense | **REAL** | Rejects `/`, `\`, `..` |
| Auto-save on mutation | **MISSING** | No auto-save after pipeline steps — explicit `store.save(case)` required |

### API Layer

| Aspect | Status | Detail |
|--------|--------|--------|
| Endpoints | **58+** | Full coverage of all journey stages |
| Auth | **REAL** | Staging soft-auth (display name + optional email) |
| Error handling | **REAL** | 401 for unauthorized, 404 for missing case |
| **BUG** | **3 endpoints** | `set-depth-mode`, `set-budget`, `cost-estimate` use undefined `_get_case` (will crash at runtime) |

### UI Layer

| Aspect | Status | Detail |
|--------|--------|--------|
| Components | **29** | All functional, dark theme |
| 10-step StatusBar | **REAL** | Horizontal progress bar with stage chips |
| Dual view | **REAL** | Technical (ArticleCard/VenueProfile) + Human (HumanModelView) |
| Dossier | **REAL** | Comprehensive with all pipeline stages (DossierView + HumanDossierView) |
| Unused API methods | **19** | `buildSubmissionPack`, `getCompliance`, `investigateVenueByUrl`, `enrichVenue`, `setDisciplineIntent`, `setBudget`, etc. |

---

## Agent Inventory (32 Total)

| Layer | Count | Operational | Contract-only stubs |
|-------|-------|-------------|---------------------|
| Article | 7 | 7 | 0 |
| Control | 5 | 5 | 0 |
| Venue | 10 | 9 | 1 (PublicationRegimeClassifier) |
| Fit | 5 | 5 | 0 |
| Submission | 3 | 3 | 0 |
| Review | 6 | 0 | 6 |
| Evidence | 2 | 2 | 0 |
| **Total** | **38** | **31** | **7** |

Review layer stubs: ReviewerSimulation, ReviewOutcomeAnalyst, RevisionPlanner, RebuttalArchitect, TacitSignalStructurer, VenueMemoryKeeper.

---

## Known Bugs Found During Audit

1. **`app.py` L1071-1093**: Three endpoints use undefined `_get_case()` instead of `_user_case` dependency — will crash with NameError.
2. **`Case.get_evidence()` L2603**: Always returns UNKNOWN stub — evidence drill-down not connected.
3. **19 API client methods unused by UI** — wired backend, no frontend caller.

---

## Gaps for Reconstruction (What Scopes A-G Need)

### A. Canonical persisted case runtime
- **State:** CaseStore exists and works. Missing: auto-save after pipeline steps; no stage machine enforcement (stages can be skipped); no case version history.
- **Work:** Add auto-persist hooks on stage transitions. Add state machine guards.

### B. Unified semantic hypothesis mechanism
- **State:** Discipline matches have rerun+user-comment. Genre/method have rerun via `rerun_article_model`. ArticleModel confirmation exists. Missing: no unified hypothesis model across all semantic axes; no ranked alternatives UI for genre/method/contribution/regime; no contradiction tracking; no version history.
- **Work:** Define `SemanticHypothesis` model. Unify discipline/genre/method/contribution/regime under it. Wire accept/dispute/comment/rerun + version history per axis.

### C. Unified LLM runtime
- **State:** Provider exists, per-role config works. Missing: each agent hardcodes max_tokens; no cross-agent budget; no centralized attempt tracking; no unified retry/truncation policy.
- **Work:** Extract unified `AgentExecutionContext` with model, max_tokens, budget, truncation policy. All agents delegate to it.

### D. Real pipeline graph
- **State:** ManuscriptVenueFitPipeline exists (18 stages, 11 executed). Case._run_fit_chain() does 10 sub-steps inline. Workflows exist (4 specs). Agent map exists. Missing: no unified executable graph; pipeline and Case orchestrator are separate systems; UI Agent Map reads from registry, not from runtime graph.
- **Work:** Merge pipeline and Case orchestrator into one executable graph with 17+ nodes. Agent Map reads from runtime graph.

### E. Full user journey (10-step UI flow without terminal)
- **State:** 29 components, all functional. StatusBar has 10 steps. Full intake→dossier flow exists. Missing: SubmissionPack has no dedicated viewer; 19 API methods unwired in UI; evidence drill-down stub.
- **Work:** Wire unused API methods. Build SubmissionPack viewer. Connect evidence drill-down.

### F. Migration
- **State:** CaseStore loads old cases. Snapshot serialization roundtrips all fields. Missing: no schema migration; no honest provenance markers on old deterministic results; no rerun button for stale results.
- **Work:** Add provenance markers. Add per-section rerun buttons with honest "deterministic/unknown" labels.

### G. Non-SSH deployment
- **State:** SSH disabled. No CI/CD. No GitHub Actions. No webhook.
- **Work:** Either implement GitHub Actions deploy or provide minimal owner bootstrap action.

---

## Test Coverage Summary

| Stage | Dedicated Tests | Verdict |
|-------|----------------|---------|
| Manuscript Intake | ~106 | STRONG |
| ArticleModel | ~38 | ADEQUATE |
| Venue Discovery | ~96 | STRONG |
| VenueModel/Profile | ~39 (+93 evidence) | STRONG |
| SubmissionScenario | ~0 dedicated | THIN |
| FitAssessment | ~88 | STRONG |
| MismatchMap | ~18 | MODERATE |
| RewritePlan | ~10 | THIN |
| CitationPlan | ~24 | MODERATE |
| RiskReport | ~35 | ADEQUATE |
| SubmissionPack | ~32 | ADEQUATE |
| Pipeline integration | ~89 | STRONG |
| **Total** | **3110+** | — |

---

## Priority Order for Phase 1

1. Fix 3 broken endpoints (`_get_case` → `_user_case`)
2. Add auto-persist on stage transitions
3. Define unified `LLMExecutionContext` (model, max_tokens, budget, truncation policy)
4. Migrate all agents to use `LLMExecutionContext`
5. Define `SemanticHypothesis` model for discipline/genre/method/contribution/regime
6. Wire hypothesis accept/dispute/rerun per axis
7. Add schema migration for old cases (provenance markers)
