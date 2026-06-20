# Reachability & Reuse Audit

**Status:** documentation only. No production behavior changed.
**Authored:** 2026-06-20.
**Baseline commit:** `ada7fb6` (= main/prod).
**Sources:** 4 parallel read-only sub-audits over API + agents + UI +
deterministic services. All file:line references verified against
`ada7fb6`.

This audit is a precondition for the next 3 passes. Goal: know what
exists, what's wired, what's orphaned, before adding new agents.

---

## 1. Entrypoint map

### 1.1 FastAPI routes (35, grouped)

Source: [`src/kairoskopion/api/app.py`](../../src/kairoskopion/api/app.py).

| Domain | Routes |
|---|---|
| Health | `GET /health` |
| Auth (soft, staging) | `POST /auth/signup`, `POST /auth/continue`, `GET /auth/me`, `POST /auth/logout` |
| Cases CRUD | `GET /cases`, `POST /cases`, `GET /cases/{id}`, `DELETE /cases/{id}` |
| Intake | `POST /intake/text`, `POST /intake/override`, `POST /intake/file` |
| Article | `GET /article-model`, `POST /article-model/confirm`, `GET /article-model/human-view`, `GET /discipline-matches` |
| Venue | `POST /investigate-venue`, `GET /investigated-venue`, `GET /venues/{key}/human-view`, `POST /discover-venues`, `GET /venue-pool`, `POST /select-venue/{venue_id}` |
| Scenario | `POST /scenario`, `GET /scenario`, `GET /pathways` |
| Fit / adaptation | `GET /fit`, `GET /mismatch-map`, `GET /adaptation-plan`, `POST /decisions` |
| Evidence / dossier / log | `GET /evidence/{entity}/{field}` ⚠ **stub**, `GET /quality-gates`, `GET /dossier`, `GET /decision-log` |
| Agents introspection | `GET /agents/map` |
| SPA static | `GET /{path}` |

### 1.2 UI activeView keys (12)

Source: [`ui/src/components/CaseWorkspace.tsx`](../../ui/src/components/CaseWorkspace.tsx), [`ui/src/components/StatusBar.tsx`](../../ui/src/components/StatusBar.tsx).

| key | renders | data source | in StatusBar nav |
|---|---|---|---|
| `empty` / `intake` | IntakeSurface + OverridePanel | api.intakeText/intakeFile/overrideIntakeType | yes |
| `article_model` | HumanModelView / ArticleCard + DisciplineMatches | api.getArticleModel + api.getDisciplineMatches | yes |
| `venue_investigation` | HumanModelView / VenueProfile | api.getInvestigatedVenue | **NO** (reachable only via intake routing) |
| `scenario` | ScenarioBuilder | api.setScenario | yes |
| `pathways` | PathwayMap | api.getPathways | yes |
| `venue_pool` | VenuePoolBoard | api.discoverVenues / getVenuePool | yes |
| `fit_assessed` | MismatchMapView only | api.getMismatchMap (**not getFit**) | yes |
| `adapting` | AdaptationStudio | api.getAdaptationPlan | yes |
| `submission_pack` | placeholder + DecisionLog | — | yes |
| `dossier` | DossierView | api.getDossier | yes |
| `venue_selected` (StatusBar chip) | — falls into default placeholder | — | yes-but-unrendered |

### 1.3 LLM call-sites + role plumbing

Source: [`src/kairoskopion/llm/config.py`](../../src/kairoskopion/llm/config.py), [`src/kairoskopion/api/cases.py`](../../src/kairoskopion/api/cases.py).

`_get_llm_provider(role_id)` is called at 11 sites in `cases.py` with the following role_ids:

| role | cases.py line | in routed_roles tuple? |
|---|---|---|
| `input_classifier` | 403 | ✅ |
| `article_modeler` | 445 | ✅ |
| `article_semantic_profiler` | 501 | ✅ |
| `discipline_matcher` | 575 | ✅ |
| `disciplinary_pathway_mapper` | 912 | ✅ |
| `venue_profiler` | 736 | ✅ |
| `fit_assessor` | 1114 | ✅ |
| `mismatch_narrator` | 1198 | ✅ |
| `article_field_positioner` | 644 | ❌ **gap** |
| `venue_field_positioner` | 809 | ❌ **gap** |
| `venue_discovery` | 973 | ❌ **gap** |
| (bare, no role) | 675 | n/a |

`provider_status().model_per_role` exposes 10 roles. Three production-live roles (article/venue field positioner, venue_discovery) are absent — they still work via global fallback but their override env vars aren't surfaced in `/health`. **Tuple is stale.**

### 1.4 Case lifecycle

CaseStage enum has 11 values. Stage assignments traced:

| Stage | Assigned at | Status |
|---|---|---|
| EMPTY | `__init__` (cases.py:88) | live |
| INTAKE | intake_text (241), apply_input_override (355) | live |
| ARTICLE_MODEL | _build_article_model (488) | live |
| SCENARIO | set_scenario (879) | live |
| PATHWAYS | get_pathways (942) | live (lazy) |
| VENUE_POOL | discover_venues (995) | live |
| VENUE_SELECTED | select_venue (1030) | live |
| FIT_ASSESSED | _run_fit_chain (1147) | live |
| ADAPTING | _run_fit_chain (1265), apply_decisions (1396) | live |
| **SUBMISSION_PACK** | **never assigned** | ⚠ orphan stage |
| **DOSSIER** | **never assigned** (build_dossier doesn't advance stage) | ⚠ orphan stage |

---

## 2. Entity reachability table

| Entity | Created at | In snapshot | API route | Case attr | UI component | Classification |
|---|---|---|---|---|---|---|
| ArticleModel | cases.py:458, 478 | ✅ | `/article-model`, `/dossier` | `article_model` | ArticleCard, HumanModelView | **ACTIVE_PROD_PATH** |
| ManuscriptModel | cases.py:477 (transient) | ❌ | none | none | none | **BACKEND_ONLY / transient** |
| ArticleSemanticProfile | cases.py:518, 525 | ✅ | embedded in `/dossier`, `/article-model/human-view` | `semantic_profile` | none direct | **ACTIVE_BUT_UI_HIDDEN** |
| DisciplinaryPathway | cases.py:938 | ✅ | `/pathways`, `/dossier` | `pathways` | PathwayMap | **ACTIVE_PROD_PATH** |
| VenueModel (investigated) | cases.py:755, 765 | ✅ | `/investigated-venue` | `investigated_venue` | VenueProfile | **ACTIVE_PROD_PATH** |
| VenueModel (selected) | cases.py:1024, 1029 | ✅ | `/dossier` | `selected_venue` | VenueProfile / VenueCandidateCard | **ACTIVE_PROD_PATH** |
| PublicationRegimeModel | cases.py:757, 765 | ✅ | embedded | `publication_regime` | none direct | **ACTIVE_BUT_UI_HIDDEN** |
| SubmissionScenario | cases.py:872, 1102 | ✅ | `/scenario`, `/dossier` | `scenario` | ScenarioBuilder, DossierView | **ACTIVE_PROD_PATH** |
| FitAssessment | cases.py:1133, 1141 | ✅ | `/fit`, `/dossier` | `fit_assessment` | none dedicated (consumed in DossierView/MismatchMapView only) | **ACTIVE_BUT_UI_HIDDEN** — `api.getFit` has **zero callers** |
| MismatchMap | cases.py:1176 | ✅ | `/mismatch-map`, `/dossier` | `mismatch_map` | MismatchMapView | **ACTIVE_PROD_PATH** |
| RewritePlan | cases.py:1254, 1393 | ✅ | `/adaptation-plan` | `rewrite_plan` | AdaptationStudio, RewriteTaskCard | **ACTIVE_PROD_PATH** |
| **CitationPlan** | **never instantiated** | ✅ (slot) | `/adaptation-plan` (dead branch) | `citation_plan` | none | **ORPHAN_UNUSED in Case** |
| RiskReport | cases.py:1235 | ✅ | `/adaptation-plan`, `/dossier` | `risk_report` | none in UI | **ACTIVE_BUT_UI_HIDDEN** |
| **ComplianceChecklist** | not on Case | ❌ | none | not on Case | none | **ORPHAN_UNUSED in Case** (CLI/test-only) |
| **SubmissionPack** | not on Case | ❌ | none | not on Case | placeholder view | **ORPHAN_UNUSED in Case** |
| **"VenueMemory"** | **no schema class** | ❌ | none | none | none | **ORPHAN_UNUSED — no schema class** (only stub agent) |
| VenueCandidatePool | cases.py:991 | ✅ | `/venue-pool`, `/dossier` | `venue_pool` | VenuePoolBoard | **ACTIVE_PROD_PATH** |
| FieldPositionModel (article) | cases.py:655 | ✅ | embedded | `article_field_position` | IntakeSurface unknowns only | **ACTIVE_BUT_UI_HIDDEN** |
| FieldPositionModel (venue) | cases.py:820 | ✅ | embedded | `venue_field_position` | IntakeSurface unknowns only | **ACTIVE_BUT_UI_HIDDEN** |
| SourceEvidencePacket | cases.py:1305 | ✅ | none | `source_evidence_packet` | none | **BACKEND_ONLY** |
| ProtectedCorePolicy | cases.py:1314, 1328 | ✅ | none (method exists, no HTTP) | `protected_core_policy` | none | **BACKEND_ONLY** |
| EvidencePolicy | cases.py:1333 | ✅ | none | `evidence_policy` | none | **BACKEND_ONLY** |

**Persistence symmetry:** every snapshot key has a matching restore. Two write-only `__init__` fields (`_llm_input_text`, `_llm_input_truncation`) are intentionally transient. No drift.

---

## 3. Agent / prompt / schema reachability

### 3.1 Top-level prompt families (12)

All 12 prompts in `prompts/` are exported from `prompts/__init__.py`, all have validators, all resolve to a consumer agent that calls `provider.complete`. **Zero orphaned top-level prompts.**

### 3.2 Secondary prompt catalog (`agents/prompt_families/catalog.py`)

| Family | Consumer | Status |
|---|---|---|
| `citation_ecology` | `fit/citation_planner.py:30` | wired, agent never invoked from cases.py |
| `compliance_checklist` | `submission/compliance_auditor.py:27` | wired, agent never invoked |
| `evidence_audit` | `evidence/evidence_auditor.py:35` | wired, agent never invoked |
| `mismatch_mapping` | `fit/mismatch_mapper.py:23` | wired, agent **bypassed** by narrator |
| `publication_regime` | `venue/publication_regime_classifier.py:24` | executable_stub |
| `rewrite_planning` | `fit/rewrite_planner.py:27` | wired, agent never invoked |
| `risk_reporting` | `submission/risk_officer.py:30` | wired, agent never invoked |
| `scenario_interview` | `control/scenario_prober.py:28` | mode mismatch (spec=deterministic, code=LLM) |
| `submission_pack` | `submission/submission_pack_builder.py:26` | wired, agent never invoked |
| `corpus_pattern_mining` | **no consumer** | **ORPHAN_PROMPT** |
| `review_outcome` | only by contract_only review stubs | **ORPHAN_PROMPT (effectively)** |

### 3.3 Agent classes (34) — disposition summary

| Classification | Count | Names |
|---|---:|---|
| **ACTIVE_PROD_PATH** | 11 | input_classifier, article_modeler, article_semantic_profiler, article_field_positioner, disciplinary_pathway_mapper, discipline_matcher, venue_profiler, venue_field_positioner, venue_discovery, fit_assessor, mismatch_narrator |
| **BACKEND_ONLY / test-only** | 3 | venue_identifier, venue_publication_profile_builder, reference_verifier |
| **DEFERRED_BACKLOG** (documented in [VENUE_FIT_BACKLOG.md](VENUE_FIT_BACKLOG.md)) | 7 | rewrite_planner, citation_planner, risk_officer, compliance_auditor, submission_pack_builder, discipline_source_acquisition, discipline_seeder |
| **ORPHAN_UNUSED** (registered, never called outside tests/registry) | 7 | intent_classifier, scenario_prober, research_planner, status_job, corpus_sampler, publication_regime_classifier, **mismatch_mapper** ⚠, **evidence_auditor** ⚠ |
| **INTENTIONAL_STUB** (contract_only review/) | 6 | reviewer_simulation, review_outcome_analyst, revision_planner, rebuttal_architect, tacit_signal_structurer, venue_memory_keeper |

**Spec ↔ class map**: perfect 1:1 (34 / 34). No registry drift.

### 3.4 Cross-cutting agent gaps

1. **`mismatch_mapper` bypassed by `mismatch_narrator`.** Narrator works on `entities.mismatches`, but no upstream agent populates that key from a *structured* MismatchMap LLM pass — currently the deterministic `build_mismatch_map` produces them. The mapper was intended as the LLM-driven structured layer; the narrator was added on top. They should be chained, not alternatives.
2. **`evidence_auditor`** — full quality-gate agent class exists but no caller. The quality-gate concept exists in [`quality_gates`](../../src/kairoskopion/api/cases.py) endpoint but is not LLM-evaluated.
3. **`scenario_prober`** — spec says `execution_mode=deterministic`, code attempts LLM call when provider present. Mode label or code must change.
4. **Two orphaned secondary prompts** (`corpus_pattern_mining`, `review_outcome`) — keep or delete consciously.

---

## 4. Zombie fallback table — top 5 remaining

All 5 are guarded by paired LLM agents that override them when LLM is enabled. Risk materialises only when fallback runs.

| # | File:line | Function | Sev | Symptom | LLM guard | Fix size |
|---|---|---|---|---|---|---|
| 1 | [`fit_assessment.py:96-112`](../../src/kairoskopion/services/fit_assessment.py) | topic-fit axis | **HIGH** | Hardcoded keyword list `["science","technology","social","sts","ethics"]` → false-positive "strong topic fit" between unrelated venues sharing 3 common English words. Flows into `overall_label`. | FitAssessorAgent (when LLM on) | medium (rewrite axis) |
| 2 | [`article_enrichment.py:118-126`](../../src/kairoskopion/services/article_enrichment.py) | `_detect_argument_move` | **MED** | Single keyword hit wins (e.g. one "limitation" mention → `critique`). Flows to UI chip + `article_field_positioner` deterministic FPM as `argument_move_vector={"critique":1.0}`. | ArticleSemanticProfilerAgent | tiny (raise threshold) |
| 3 | [`compliance.py:141-144`](../../src/kairoskopion/services/compliance.py) | AI-disclosure check | **MED** | `"ai" in gl` substring fires on "available", "domain", "explain", etc. → false "missing AI disclosure" warning. | none (no compliance LLM agent yet) | tiny (`\bai\b` word boundary) |
| 4 | [`venue_profiling.py:287-329`](../../src/kairoskopion/services/venue_profiling.py) | `_extract_language_policy` bilingual case | **MED** | Bilingual journal with "metadata in English" gets classified as Russian-only body. Flows into VenueModel.language_policy + language fit axis. | none (deterministic only) | small |
| 5 | [`fit_assessment.py:257-263`](../../src/kairoskopion/services/fit_assessment.py) | publication_regime axis | **LOW-MED** | Always says `"Classic journal regime -- standard submission path"` even for special-issue / conference venues (when regime_type != classic). Cosmetic-but-misleading. | FitAssessorAgent | tiny (branch on regime_type or downgrade to "unknown") |

**Five smaller wins** (DLC → HF with tiny fixes): see audit 4 table rows #15, #32, #52, #67, #80.

---

## 5. Reuse candidates before next agents

Per [`VENUE_FIT_BACKLOG.md`](VENUE_FIT_BACKLOG.md), 5 LLM agents are queued. For each, this audit identifies what already exists and can be reused:

### Before `RewritePlanAgent`
- ✅ `agents/fit/rewrite_planner.py` (ORPHAN_UNUSED) — agent class + spec + prompt family `rewrite_planning` already wired but never invoked. **Reuse: instantiate this in `_run_fit_chain` after the narrator, do not create new file.**
- ✅ `services/rewrite_planning.py` `build_rewrite_plan` — deterministic backbone produces ordered `RewriteChange` objects from MismatchMap. **Reuse as fallback.**
- ✅ `RewritePlan` schema + persistence + `AdaptationStudio` UI already render it. **No new domain model needed.**
- Gap: `RewriteTaskCard` UI assumes deterministic placeholder text — verify rendering of LLM-authored `desired_state`/`current_state` quotes.

### Before `CitationBridgeAgent`
- ✅ `agents/fit/citation_planner.py` (ORPHAN_UNUSED) — class + prompt family `citation_ecology` wired. **Reuse.**
- ✅ `services/citation_ecology.py` `build_citation_ecology_report` — deterministic gap detection. **Reuse as fallback.**
- ✅ `CitationPlan` schema slot + snapshot persistence exist; Case attribute exists. **But Case.citation_plan is never assigned today.** Wire-up needed at fit chain.
- Gap: `BibliographyProfile` is not built in standard pipeline — citation chain requires it. Either build on demand (already in `/adaptation-plan` lazy build) or add to fit chain.

### Before `VenuePolicyExtractorAgent`
- ✅ `agents/venue_profiler.py` already calls VENUE_FACT_EXTRACTION_FAMILY for full venue profile. **Could extend prompt with policies block instead of separate agent.**
- ✅ `services/venue_profiling.py` `_extract_*_policy` family with negation guards (D1) — usable as fallback.
- ✅ `VenueModel.open_access_status` / `apc_policy` / `anonymization_policy` / `ai_policy` / `data_policy` / `ethics_policy` / `indexing_claims` fields already exist on dataclass.
- Gap: `_extract_language_policy` bilingual bug (Zombie #4) should be fixed before LLM extends the same field.

### Before `SubmissionPack` lane
- ✅ `agents/submission/risk_officer.py`, `compliance_auditor.py`, `submission_pack_builder.py` — all ORPHAN_UNUSED but classes + prompts exist. **Reuse.**
- ✅ `RiskReport` already built by `_run_fit_chain` (commit 25166f3). UI gap: not rendered.
- ❌ `SubmissionPack` and `ComplianceChecklist` not on Case attributes — needs adding.
- ❌ `CaseStage.SUBMISSION_PACK` orphan — wire it.
- ❌ `submission_pack` UI view is placeholder.

### Before `MismatchMapperAgent` chain (separate from existing narrator)
- ✅ Narrator works on already-built mismatches. **Chain mapper → narrator** — narrator continues to enrich; mapper provides LLM-driven structured backbone instead of deterministic.

---

## 6. UI-hidden backend fields

### 6.1 Backend → UI (collected, not shown)

| Field | Backend source | UI status | Severity |
|---|---|---|---|
| **`FitAssessment.axes[]`** (12 axes) | `_run_fit_chain` writes it; `/fit` returns it | `api.getFit` has **zero callers** in UI | **HIGH** — fit_assessed view shows only mismatch, half the picture |
| `investigated-venue.venue_field_position` + `used_llm` | exposed in `/investigated-venue` response (F5) | not in `VenueInvestigationResult` TS type, never read | **HIGH** — flagged in VENUE_FIT_BACKLOG.md UI2/UI3 |
| `cases/{id}.discipline_matches_count`, `region_hint` | set by Case.to_dict() at cases.py:193 | absent from `CaseDetail` interface | MED |
| Override response: `classifier_input_type`, `user_selected_input_type`, `override_source`, `override_at` | typed in client.ts:163–167 | **never consumed** | MED — provenance of routing override invisible |
| `dossier.risk_report` | built by fit chain; in case.to_dict() via build_dossier | not in `Dossier` TS interface; **zero grep hits** | **HIGH** — risk report invisible |
| `dossier.citation_plan` | slot exists but never populated | n/a (orphan) | n/a |
| `dossier.rewrite_plan` individual changes | DossierView renders only effort/count/summary | individual `changes[]` not rendered in dossier (AdaptationStudio is separate view) | MED |

### 6.2 UI → Backend (rendered, missing/shallow)

| Route | Symptom |
|---|---|
| `venue_selected` (StatusBar chip) | falls into "will be implemented" placeholder |
| `submission_pack` view | pure placeholder + DecisionLog; no actual pack rendering |
| `fit_assessed` view | shows MismatchMap only, never fetches FitAssessment axes |
| `venue_investigation` view | not in StatusBar nav; reachable only from intake routing — operator can't navigate back |
| `RewriteChange._blocked_reason`, `_matched_core_elements` | underscore-prefixed UI fields — verify backend sets them |

---

## 7. Recommended next 3 passes

Based ONLY on this audit's evidence. Each is small/focused.

### Pass A — Close FitAssessment axes UI gap (UI-only)
**Why:** the single highest-leverage gap. `api.getFit` returns 12 axes per pairing but UI never fetches it. Operator sees half the verdict.

**Scope:**
- New `FitAxesView.tsx` component rendering 12 axes table (axis, value, notes, evidence_refs, unknowns).
- Wire `getFit` into `CaseWorkspace` `fit_assessed` view alongside existing MismatchMapView.
- Also expose `risk_report` in `DossierView` (likely already in backend payload — verify and add to TS interface).
- ~200 LOC, UI only, no backend.

### Pass B — Wire mismatch_mapper → mismatch_narrator chain
**Why:** the narrator was added on top of deterministic build_mismatch_map; the registered `mismatch_mapper` LLM agent never runs. Chaining gives a real LLM-driven structured pass before the prose pass.

**Scope:**
- Modify `_run_fit_chain` to optionally invoke `MismatchMapperAgent` (already registered) before the narrator.
- Honest fallback to deterministic `build_mismatch_map` when LLM off.
- Add `mismatch_mapper` to `routed_roles` tuple in `llm/config.py`.
- Also fix the three other `routed_roles` gaps (article_field_positioner, venue_field_positioner, venue_discovery) — 4-line fix.
- ~150 LOC backend + tests.

### Pass C — Wire `evidence_auditor` into quality_gates
**Why:** quality-gate agent class exists fully built; `/quality-gates` endpoint returns deterministic results. Audit gate is effectively absent in user-facing path.

**Scope:**
- Invoke EvidenceAuditorAgent after fit chain completes; write result into Case.quality_gates with provenance.
- Add to `routed_roles`.
- UI: render LLM gate verdicts in QualityGateBar (already rendered structurally).
- ~150 LOC.

**Explicitly NOT recommended for next pass** (still backlog):
- `RewritePlanAgent`, `CitationBridgeAgent`, `VenuePolicyExtractorAgent`, `SubmissionPack` lane — bigger work, lower immediate visibility than passes A/B/C.

**Explicitly NOT recommended for any pass**:
- Deleting orphan agents (intent_classifier, status_job, etc.) — they cost nothing as scaffolding and may be wired in future passes.
- Deleting orphan secondary prompts (corpus_pattern_mining, review_outcome) — same.
- Removing `CaseStage.SUBMISSION_PACK` / `DOSSIER` orphan values — they belong in the eventual submission-pack lane.

---

## 8. Confirmations

- **No production behavior changed.** This commit adds only this document to `docs/operations/`.
- **No code edits.** No agent created, no prompt edited, no route added, no model routing changed.
- **All file:line citations verified** at commit `ada7fb6`.
- **No env, no model, no temperature, no timeout, no API key changes.**
- **No deletions.** Orphan classifications are advisory, not action items.
