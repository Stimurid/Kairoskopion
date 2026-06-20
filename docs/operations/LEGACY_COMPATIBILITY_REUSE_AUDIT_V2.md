# Legacy / Duplicate / Spec-Compatibility Reuse Audit — V2

**Status:** documentation only. No code, env, model, prompt, or deploy change.
**Authored:** 2026-06-20.
**Baseline commit:** `542256d` (= main/prod head; Pass A UI shipped).
**Predecessor:** [`REACHABILITY_REUSE_AUDIT.md`](REACHABILITY_REUSE_AUDIT.md) at `ada7fb6`.
**Production route:** global `claude-sonnet-4-5-20250929`, `input_classifier=gpt-4o-mini`, `mismatch_narrator=claude-sonnet-4-5-20250929`, timeout 90 s, retries 3.

V1 was a reachability map (what exists, what's wired). V2 is an
architectural-compatibility map (what duplicates what, what was
forgotten, what drifted from the original Kairon/Journal-Yuga spec, and
in what order we should reuse before we rebuild). All file:line refs
verified at `542256d`.

---

## 1. Executive summary

**Scope of pass.** 24 spec-required entities, 11 deterministic-service
modules, 34 agent classes, 12 prompt families, 35 API routes, 17 UI
components, 6 integration bridges. Cross-checked against
`docs/KAIRON_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md` (sampled) and the
predecessor audit. No code touched.

**State after Pass A (`542256d`).** Two high-leverage UI gaps from v1
are closed: `FitAssessment.axes` and `RiskReport` now render in
`DossierView` with honest unknowns and severity-coded risk items. The
backend already exposed both — Pass A was pure UI. **Therefore the v1
"axes invisible" and "risk_report invisible" gaps are no longer open.**
This audit only flags those areas where a *new* defect exists.

**Top findings.**

1. **Six fully-coded LLM agents are registered but never invoked in
   the production fit chain.** `mismatch_mapper`, `rewrite_planner`,
   `citation_planner`, `risk_officer`, `compliance_auditor`,
   `evidence_auditor` all have agent class + prompt family + service
   fallback ready. Wiring cost is small; rebuilding from scratch would
   be a serious anti-pattern. See §3 and §6.
2. **Four spec-required domain objects are orphan slots.** `CitationPlan`
   (slot on Case, never assigned), `ComplianceChecklist` (not on Case
   at all), `SubmissionPack` (not on Case), `VenueMemory` (no schema
   class). Each has either a deterministic service or a stub agent
   already on disk. See §4 and §9.
3. **Three architectural drifts deserve naming, not silent treatment.**
   (a) `ManuscriptModel` is built transiently inside the article-modeler
   path and immediately discarded — `RewritePlan.manuscript_id` is
   never populated, so rewrite changes refer to axes, not manuscript
   blocks. (b) `EvidenceStatus` enum is fully defined and unused by
   fallback writers — fit axes carry no `evidence_status`, so the
   spec's fact / vendor-claim / inference / unknown distinction
   collapses on the deterministic path. (c) `SubmissionScenario` is
   spec-required, but the fit chain auto-synthesises a *preliminary*
   one when missing (commit b48698e). The synthesis is flagged
   (`scenario_preliminary=true`) and the UI renders a banner, so the
   drift is honest, not silent — but it remains a spec deviation. See §8.
4. **Two confirmed `ZOMBIE_CAN_CORRUPT_OUTPUT` fallbacks survive into
   prod without an LLM guard.** `compliance.py` AI-disclosure substring
   bug (`"ai" in gl`) has no `ComplianceAuditorAgent` invocation
   anywhere — there is literally no LLM that can override it. And
   `venue_profiling.py` bilingual language extraction has no LLM guard
   either (the venue profiler agent uses the same deterministic
   `_extract_language_policy`). Both are inert today because nothing
   calls compliance and venue profiler runs at LLM-first level — but
   the moment LLM is off, they fire. See §5.
5. **Three `routed_roles` gaps from v1 are still open.**
   `article_field_positioner`, `venue_field_positioner`, `venue_discovery`
   are called in `cases.py` but absent from `provider_status().model_per_role`
   tuple in `llm/config.py`. 4-line fix, not done yet. See §5.

**What this audit does NOT recommend.** Deletion of any agent class,
prompt family, schema slot, or stage enum. The orphaned scaffolding is
*cheap to keep* and *exactly what the next 5 passes need to consume*.

---

## 2. Duplicate map

Each cluster: files + line refs → overlapping responsibility →
classification → decision.

### 2.1 Fit-assessment cluster

| Files | Responsibility | Active path | Better semantics |
|---|---|---|---|
| `services/fit_assessment.py:86–323` (12-axis deterministic) | Produce `FitAssessment(overall_label, axes[])` | Fallback only when LLM off | Service is the structural backbone (12-axis taxonomy); agent adds semantic judgement |
| `agents/fit_assessor.py:1–100` (LLM + service fallback) | Same output, LLM-driven | **Active in prod** (`cases.py:1114`) | — |

**Classification:** `DUPLICATE_KEEP_BOTH`.
**Decision:** Keep both — fallback is load-bearing, agent delegates to
service on `LLMUnavailable` (line ~32). Removing service would crash
the offline path used by tests and `KAIROSKOPION_LLM_PROVIDER=none`.

### 2.2 Article-semantic-profile cluster

| Files | Responsibility | Active path |
|---|---|---|
| `services/article_enrichment.py:1–197` (registry-backed discipline/school detection, argument-move keywords) | Build `ArticleSemanticProfile` | Fallback only |
| `agents/article_semantic_profiler.py` | Same output, LLM | **Active** (`cases.py:501`) |

**Classification:** `DUPLICATE_KEEP_BOTH`. Same reasoning as §2.1.

### 2.3 Venue-profiling cluster

| Files | Responsibility | Active path |
|---|---|---|
| `services/venue_profiling.py:169–440` (regex + negation guards for APC, OA, language, AI, ethics, data policies) | Build `VenueModel` + `PublicationRegimeModel` | Fallback only |
| `agents/venue_profiler.py` | Same output, LLM | **Active** (`cases.py:736`) |

**Classification:** `DUPLICATE_KEEP_BOTH`. Note: language-policy
bilingual bug (Z#4) lives in the *service*. Agent delegates to it on
fallback — and on the LLM path may also re-use parts of it. Bug-fix
location is the service.

### 2.4 Mismatch chain — **architectural debt**

| Files | Responsibility | Active path |
|---|---|---|
| `services/mismatch_mapping.py:17–91` (deterministic axis→mismatch translation; `venue_side` deliberately empty per Track D) | Structured mismatches | **Always runs** (`cases.py:1176`) |
| `agents/fit/mismatch_mapper.py:1–50` (LLM structured analysis) | Same output, LLM-enriched | **NEVER invoked** outside tests |
| `agents/mismatch_narrator.py` | Add `venue_side`, prose `description`, surgical `possible_actions` | **Active** (`cases.py:1198`) |

**Classification:** `DUPLICATE_MERGE_REQUIRED` — the mapper was
designed as the LLM-structured layer *between* deterministic build and
narrator prose; today the narrator runs directly on deterministic
output. Mapper is fully coded and orphaned.

**Decision:** Wire mapper into `_run_fit_chain` between deterministic
build and narrator. Don't delete it. Don't rebuild narrator. See §6
("Reuse-before-build") and §10 Pass B.
**Risk of removal:** medium — schema alignment between mapper output
and narrator input must be verified before activation; both operate on
`MismatchMap` but mapper may add new fields the narrator must tolerate.

### 2.5 Rewrite-plan cluster

| Files | Responsibility | Active path |
|---|---|---|
| `services/rewrite_planning.py:53–158` (deterministic ordered `RewriteChange[]` from MismatchMap; structural axis→change_type dict) | Build `RewritePlan` | **Always runs** (`cases.py:1254`) |
| `agents/fit/rewrite_planner.py:1–88` (LLM + service fallback; protected-core gate at 55–59) | Same output, LLM-enriched | **NEVER invoked** outside tests |
| `services/protected_core.py` (validates `RewriteChange` vs protected core, applies user-consent gate) | Gate rewrite plan | Active only via rewrite_planner agent → currently unreached |

**Classification:** `DUPLICATE_NEW_REPLACES_OLD` (but the "new" path
is not yet wired). Pure agent activation; no rebuild.
**Decision:** Wire agent in fit chain post-narrator. Protected-core
gating activates automatically. See §10 Pass C.

### 2.6 Risk-reporting cluster

| Files | Responsibility | Active path |
|---|---|---|
| `services/risk_reporting.py:50–242` (deterministic 18-type taxonomy from FitAssessment + MismatchMap + VenueModel; honest "unknown" inference) | Build `RiskReport` | **Active** (`cases.py:1233`) |
| `agents/submission/risk_officer.py:1–70` (LLM + service fallback) | Same output, LLM-enriched | **NEVER invoked** |

**Classification:** `DUPLICATE_NEW_REPLACES_OLD` (agent not active).
**Decision:** Service path is stable and now UI-visible (Pass A).
Agent activation is optional enrichment — defer until after the
mapper/rewrite chain is wired (§10 Pass D).

### 2.7 Citation-ecology cluster

| Files | Responsibility | Active path |
|---|---|---|
| `services/citation_ecology.py:24–313` (gap detection, recency, bridges with Track D ≥2-token requirement, DOI coverage, venue-expectation regex) | Build `CitationEcologyReport` / `CitationPlan` | Built lazily in `/adaptation-plan` only; **`Case.citation_plan` never assigned** |
| `agents/fit/citation_planner.py:1–70` (LLM + service fallback) | Same output, LLM-enriched | **NEVER invoked** |
| `schema.py` `CitationPlan` slot | Persistence slot | Slot only — orphan |

**Classification:** `DUPLICATE_UNCLEAR_NEEDS_TEST` — both exist; neither
writes to `Case.citation_plan`. Architectural decision needed:
fit-chain (requires BibliographyProfile to be available before fit) vs
adaptation-plan lane (BibliographyProfile already built there).
**Decision:** See §10 Pass D; do not rebuild.

### 2.8 Compliance cluster

| Files | Responsibility | Active path |
|---|---|---|
| `services/compliance.py:50–175` (13-item venue/regime checklist; contains Z#3 AI-disclosure substring bug) | Build `ComplianceChecklist` | **No call site in `cases.py`** |
| `agents/submission/compliance_auditor.py:1–77` (LLM + service fallback) | Same output, LLM-enriched | **NEVER invoked** |
| `Case` model | — | **`compliance_checklist` not even an attribute** |

**Classification:** `DUPLICATE_MERGE_REQUIRED`. Both exist; schema slot
on `Case` does not. Adding the slot + activating one path (preferably
the agent) is the next step.
**Decision:** Fix Z#3 bug first (one regex), then add Case slot, then
wire agent (§10 Pass E). Do not rebuild.

### 2.9 Submission-pack cluster

| Files | Responsibility | Active path |
|---|---|---|
| `services/submission_pack.py` | Deterministic pack build | No call site in `cases.py` |
| `agents/submission/submission_pack_builder.py:1–63` | LLM + service fallback | **NEVER invoked** |
| `CaseStage.SUBMISSION_PACK` (`enums.py`) | Stage marker | **Stage never assigned** |
| `submission_pack` UI view (`ui/src/components/CaseWorkspace.tsx`) | Placeholder | No data binding |

**Classification:** `DUPLICATE_UNCLEAR_NEEDS_TEST`. Full lane absent;
all pieces exist on disk. **Decision:** Defer to dedicated submission-
pack lane (not in next 5 passes).

### 2.10 Evidence-audit cluster

| Files | Responsibility | Active path |
|---|---|---|
| `services/evidence_audit.py` (if present) / deterministic gate logic on `Case.quality_gates` | Build quality-gate result | Active deterministic |
| `agents/evidence/evidence_auditor.py:1–74` (LLM + fallback) | Same output, LLM-driven | **NEVER invoked** |

**Classification:** `DUPLICATE_NEW_REPLACES_OLD` (agent dormant).
**Decision:** Wire as final pass after all other agents are wired —
v1 Pass C suggestion still stands. See §10 Pass D / E.

### 2.11 Prompt-family duplicates / drift

| Cluster | Status |
|---|---|
| `prompts/` (top-level, 12 families) — all consumed | No duplicates. Zero orphan. |
| `agents/prompt_families/catalog.py` (secondary, 11 families) — 2 orphan (`corpus_pattern_mining`, `review_outcome`) | `DUPLICATE_KEEP_BOTH` (top-level vs secondary catalog are different layers — keep, do not merge). |
| `agents/prompt_families/catalog.py` `scenario_interview` marked `execution_mode=deterministic` but code attempts LLM (`agents/control/scenario_prober.py:28`) | `DUPLICATE_MERGE_REQUIRED` for the spec doc — fix `execution_mode=llm_optional`, no code change needed. |

### 2.12 UI-component duplicates

None of substance. `DossierView` consolidates `FitAxes` + `RiskReport`
+ `MismatchNarrative` + `RewriteSummary` since Pass A. `MismatchMapView`
(standalone, `fit_assessed` stage) and `DossierView`'s mismatch section
overlap in *display* but read the same underlying `MismatchMap` — keep
both, do not merge.

---

## 3. Forgotten-good modules

Modules that exist, are spec-aligned, and are not active.

### 3.1 `agents/fit/rewrite_planner.py` — `REUSE_AS_IS`

**Useful idea:** LLM-planned rewrite changes with `protected-core` gate
already wired (`rewrite_planner.py:55–59` calls
`validate_rewrite_plan` + `apply_core_gate`). Honest service fallback.
**Why forgotten:** Never wired into `_run_fit_chain`. Service path was
wired directly first; agent was queued for a later pass.
**Still needed?** Yes — spec §15.5 makes RewritePlan a first-class
output. Service path is structural; LLM adds rationale.
**What must change:** ~5 lines in `cases.py` to swap direct service
call for agent. `rewrite_planner` added to `routed_roles`.
**Nearest pass:** §10 Pass C.

### 3.2 `agents/fit/citation_planner.py` — `REUSE_AFTER_ADAPTER`

**Useful idea:** LLM-driven citation-ecology gap detection (bridges,
padding warnings, missing-tradition flags). Service fallback via
`services/citation_ecology.py`.
**Why forgotten:** `CitationPlan` slot exists on `Case`, but no
upstream writer. `/adaptation-plan` endpoint lazy-builds
`BibliographyProfile`; fit chain does not.
**What must change:** Either (a) add `BibliographyProfile` build to
fit chain (heavier), or (b) wire agent into adaptation-plan handler
(lighter, BibliographyProfile already there).
**Nearest pass:** §10 Pass D.

### 3.3 `agents/submission/risk_officer.py` — `REUSE_AS_IS`

**Useful idea:** LLM risk reasoning across 18-type taxonomy beyond
rule-based service.
**Why forgotten:** Service path is stable and now UI-visible (Pass A),
so urgency dropped. Agent never invoked.
**What must change:** Single agent call after rewrite planner; falls
back to service.
**Nearest pass:** §10 Pass D (after the chain has structure to reason on).

### 3.4 `agents/submission/compliance_auditor.py` — `REUSE_AFTER_SCHEMA_UPDATE`

**Useful idea:** Venue/regime-aware compliance check with LLM
contextual reasoning.
**Why forgotten:** `ComplianceChecklist` is not on `Case` at all. The
service has a known bug (Z#3). Nobody wired either.
**What must change:** (1) Fix Z#3 regex (one line, deferred), (2) add
`Case.compliance_checklist` attribute + snapshot persistence,
(3) invoke agent in fit chain or submission-pack lane.
**Nearest pass:** §10 Pass E.

### 3.5 `agents/evidence/evidence_auditor.py` — `REUSE_AS_IS`

**Useful idea:** LLM cross-checks evidence coherence across the whole
chain — unsupported claims, circular reasoning, conflicting sources.
**Why forgotten:** v1 Pass C never executed. `quality_gates` endpoint
still returns deterministic-only.
**What must change:** Invoke once after all upstream agents complete.
Result writes to `Case.quality_gates` with provenance.
**Nearest pass:** §10 Pass E (must come after risk/compliance to have
material to audit).

### 3.6 `agents/fit/mismatch_mapper.py` — `REUSE_AS_IS` (with schema check)

**Useful idea:** Structured LLM mismatch analysis layer between
deterministic build and narrator prose.
**Why forgotten:** Narrator was added directly on top of deterministic
output; the mapper layer was skipped.
**What must change:** Wire between `build_mismatch_map` and narrator.
**Schema gate:** verify mapper-enriched `MismatchMap` is a superset
the narrator can still consume.
**Nearest pass:** §10 Pass B.

### 3.7 `agents/control/scenario_prober.py` — `REUSE_AS_SPEC_REFERENCE`

**Useful idea:** LLM-assisted scenario building from operator
constraints. Agent code already correct.
**Why forgotten:** Mode-label mismatch in
`agents/prompt_families/catalog.py` (`deterministic` vs the code's
`llm_optional`). No bug; doc out of sync.
**What must change:** One-line catalog fix (deferred — doc-only audit
does not patch).

### 3.8 `agents/venue/publication_regime_classifier.py` — `REUSE_AS_IS`

**Useful idea:** Optional LLM regime refinement on top of deterministic
classification.
**Why forgotten:** Marked `executable_stub`; intentionally optional.
**Nearest pass:** Not on next-5; opportunistic.

### 3.9 `agents/prompt_families/corpus_pattern_mining.py` — `REUSE_AFTER_ADAPTER`

**Useful idea:** LLM extraction of implicit publication norms from a
published-corpus sample (genre, method, citation patterns).
**Why forgotten:** Prompt family exists; no consumer agent class.
`CorpusSamplerAgent` is deterministic-only and does not invoke it.
**What must change:** Thin consumer agent (~50 LOC) — out of scope
for next-5.

### 3.10 `services/human_readable_card.py` (~874 LOC) — `REUSE_AS_IS`

**Already active** (`/article-model/human-view`, `/venues/{key}/human-view`).
Listed here for completeness: this is the canonical projection layer
for any future "human-review-before-trust" UI surface — reuse pattern,
not module.

### 3.11 `agents/review/*` (6 contract-only stubs: `reviewer_simulation`,
`review_outcome_analyst`, `revision_planner`, `rebuttal_architect`,
`tacit_signal_structurer`, `venue_memory_keeper`) — `REUSE_AS_SPEC_REFERENCE`

**Useful idea:** Spec §6.27–§6.29 + §8.1 — the post-submission
learning loop (review outcome → revision plan → venue memory).
**Why forgotten:** Wave 7+ on roadmap; not implementation-ready.
**What must change:** Schema classes (`RevisionPlan`, `VenueMemory`)
must be added; agents stay stub until then.
**Nearest pass:** Not in next-5. Keep stubs as canonical contracts.

### 3.12 `services/source_evidence_packet.py` — `REUSE_AS_IS` (UI gap)

**Useful idea:** Cross-pipeline evidence-source bundle with staleness
and chain-of-custody.
**Why forgotten:** Built and assigned to `Case.source_evidence_packet`
(`cases.py:1305`); never rendered in UI.
**What must change:** UI render only — schema is load-bearing for the
evidence auditor wiring (§3.5).

---

## 4. Spec compatibility matrix

Cross-checked against `docs/KAIRON_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md`
(sampled by grep, not whole-file read).

| # | Spec concept | Classification | Evidence (file:line) | Current behaviour | Missing link | Smallest safe next step |
|---|---|---|---|---|---|---|
| 1 | ArticleModel | `PROD_PATH_ACTIVE` | `schema.py:181–225`, `cases.py:458–478`, `ArticleCard.tsx` | Full LLM/fallback construction, UI visible | None | — |
| 2 | ManuscriptModel | `STUB_ONLY` | `schema.py:226–248`, built transiently `cases.py:477` then dropped | Schema exists; no Case attribute, no UI, no `manuscript_id` flowing into RewritePlan | Persist on Case; thread `manuscript_id` through rewrite chain | Schema is sufficient; wiring deferred |
| 3 | FieldModelReference / WhiteCrow field ref | `ABSENT` | grep finds no class | No back-reference from Article to WhiteCrow Field state | Two-way bridge | Defer (Wave 5+ WhiteCrow lane) |
| 4 | VenueModel | `PROD_PATH_ACTIVE` | `schema.py:249–284`, `agents/venue_profiler.py`, `VenueProfile.tsx` | Active, multi-policy | Citation-ecology not nested | OK as-is |
| 5 | JournalModel | `BACKEND_PRESENT` | `schema.py:1614–1655` | Full fields incl. sections[], special_issues[] (string refs) | Not promoted into UI; sections[] not nested as SectionModel[] | Defer |
| 6 | SectionModel | `BACKEND_PRESENT` | `schema.py:1656+` | Exists but referenced by name string from JournalModel | Promote to nested | Defer |
| 7 | IssueModel | `ABSENT` | grep negative | Spec wants standard issue (vol/no/date) separate from SpecialIssueModel | Add dataclass | Defer (5 fields, low cost) |
| 8 | SpecialIssueModel | `BACKEND_PRESENT` | `schema.py:~1700` | Present, not in UI | Render under VenueProfile when present | Defer |
| 9 | ResearchTopicModel | `ABSENT` | grep negative | CFP-driven topic absent | Add dataclass | Defer |
| 10 | PublicationRegimeModel | `BACKEND_PRESENT` | `schema.py:285–302`, embedded in venue investigation | Built by venue profiler; UI hidden | UI surface | Optional |
| 11 | SubmissionScenario | `PROD_PATH_ACTIVE` (with drift) | `schema.py:303–334`, `cases.py:872`, `ScenarioBuilder.tsx` | Active, but auto-synthesised when missing (`scenario_preliminary` flag) | Spec calls it required; honest banner shown | See §8 drift #5 |
| 12 | FitAssessment | `PROD_PATH_ACTIVE` (axes UI-visible since Pass A) | `schema.py:345–365`, `cases.py:1133`, `DossierView.tsx:146–211` | 12 axes, overall_label, multi-axis preserved, UI table | Per-axis `evidence_status` absent (§8 drift #3) | Defer |
| 13 | MismatchMap | `PROD_PATH_ACTIVE` | `schema.py:380–390`, `cases.py:1176`, `DossierView.tsx`, `MismatchMapView.tsx` | Active, narratives via mismatch_narrator | LLM-structured layer skipped (mapper bypassed) | §10 Pass B |
| 14 | RewritePlan | `BACKEND_PRESENT` (deterministic only) | `schema.py:391–406`, `cases.py:1254`, `AdaptationStudio.tsx` | Built by service; agent never invoked; `manuscript_id` null | Wire agent + manuscript linkage | §10 Pass C |
| 15 | ReframePlan | `ABSENT` | grep negative | Spec's core-preserving alternative to rewrite missing | Add dataclass + agent | Defer |
| 16 | CitationPlan | `STUB_ONLY` (slot exists, never written) | `schema.py:407–419`, `Case.citation_plan` slot, `services/citation_ecology.py:24–313`, `agents/fit/citation_planner.py:1–70` | Slot + service + agent all present, no writer | Wire one writer | §10 Pass D |
| 17 | RiskReport | `PROD_PATH_ACTIVE` (UI-visible since Pass A) | `schema.py:512–527`, `cases.py:1233`, `DossierView.tsx:224–280` | Built deterministically, severity/likelihood/mitigation rendered, blocking-vs-warnings split | Agent never invoked (optional enrichment) | §10 Pass D |
| 18 | ComplianceChecklist | `STUB_ONLY` (no Case slot, no call site) | `schema.py:528–543`, `services/compliance.py`, `agents/submission/compliance_auditor.py` | All three pieces on disk; not wired | Add Case slot + writer + fix Z#3 | §10 Pass E |
| 19 | SubmissionPack | `STUB_ONLY` (orphan stage) | `schema.py:544–567`, `services/submission_pack.py`, `agents/submission/submission_pack_builder.py`, `CaseStage.SUBMISSION_PACK` | All pieces present; orphan view in UI | Dedicated lane | Defer |
| 20 | ReviewerSimulation | `STUB_ONLY` | `agents/review/reviewer_simulation.py:10–24` | Contract-only stub | Wait for post-review lane | Defer |
| 21 | ReviewOutcome | `STUB_ONLY` | `agents/review/review_outcome_analyst.py` | Stub | Wait | Defer |
| 22 | RevisionPlan | `ABSENT` (schema), `STUB_ONLY` (agent) | `agents/review/revision_planner.py` | Agent stub; no dataclass | Add dataclass | Defer |
| 23 | VenueMemory | `ABSENT` (schema), `STUB_ONLY` (agent) | `agents/review/venue_memory_keeper.py` | Agent stub; no dataclass; no learning loop | Add dataclass + post-submission integration | Defer |
| 24 | EvidenceItem / SourceSnapshot / ContextPack | `PARTIALLY_COMPATIBLE` | `schema.py:139–178`, `enums.py:10–22` (EvidenceStatus 12 values) | Classes exist; enum complete; **but rarely populated by fallback writers; no `context_pack_id` on entities** | See §8 drift #3, #4 | Defer |
| 25 | Litops outputs (artifacts/vault cards) | `DEFERRED_BY_DESIGN` | `integrations/litops_bridge.py` (export-only) | Export-side OK; import-side absent | Two-way bridge | Defer |
| 26 | WhiteCrow patch candidates / protected core | `PARTIALLY_COMPATIBLE` | `integrations/whitecrow_bridge.py:40–78`, `services/protected_core.py` | Export-side OK; protected-core service load-bearing but only via dormant rewrite_planner agent | Wire rewrite_planner | §10 Pass C |
| 27 | UI formula: Article × Venue × Scenario → Fit → Mismatch → Action → Pack | `PARTIALLY_COMPATIBLE` | `cases.py:_run_fit_chain`, `DossierView.tsx` | Path complete through Risk; Rewrite rendered in `AdaptationStudio` but only structural; CitationPlan / Compliance / Pack invisible | See passes B–E | — |

---

## 5. Zombie fallback audit v2

Expanded from v1 §4 (top 5) to a sweep across `services/`. Each row
classifies the deterministic claim, the LLM guard (if any), and the
production risk.

| # | File:line | Service / axis | Classification | LLM guard | Active in prod today? |
|---|---|---|---|---|---|
| 1 | `fit_assessment.py:102–112` | topic-fit keyword list `["science","technology","social","sts","ethics"]` | `ZOMBIE_CAN_CORRUPT_OUTPUT` | FitAssessorAgent (active) | Only on offline path |
| 2 | `article_enrichment.py:118–126` | `_detect_argument_move` single-keyword | `ZOMBIE_CAN_CORRUPT_OUTPUT` | ArticleSemanticProfilerAgent (active) | Only offline |
| 3 | `compliance.py:141–144` | AI-disclosure substring `"ai" in gl` | `ZOMBIE_CAN_CORRUPT_OUTPUT` | **NONE** — compliance has no LLM agent invocation anywhere | **Currently inert: service has zero call sites. Will fire if anyone wires it without fix.** |
| 4 | `venue_profiling.py:287–329` | Bilingual language-policy mis-classification | `ZOMBIE_CAN_CORRUPT_OUTPUT` | VenueProfilerAgent shares this code on fallback path; LLM path may or may not re-extract | Currently active — extraction may use this even on LLM path for some sub-fields |
| 5 | `fit_assessment.py:257–263` | publication_regime axis hardcoded "Classic journal regime" | `ZOMBIE_CAN_CORRUPT_OUTPUT` (cosmetic-but-misleading) | FitAssessorAgent (active) | Only offline |
| 6 | `fit_assessment.py:153–167` | argument_structure axis — `unknown` if fields missing, `strong` if populated (no validity check) | `LOW_CONFIDENCE_HINT_OK` | FitAssessorAgent | OK |
| 7 | `fit_assessment.py:169–185` | method axis — heuristic empirical-keyword match | `LOW_CONFIDENCE_HINT_OK` | FitAssessorAgent | OK |
| 8 | `fit_assessment.py:187–206` | citation_ecology axis — regex ref count | `LOW_CONFIDENCE_HINT_OK` | (no dedicated agent; depends on upstream article modeler) | OK (honest unknowns) |
| 9 | `fit_assessment.py:208–217` | novelty_positioning — `medium` if `novelty_mode` populated | `LOW_CONFIDENCE_HINT_OK` | FitAssessorAgent | OK |
| 10 | `fit_assessment.py:219–227` | language_register — `article.language ∈ venue.language_policy` | `FORMAL_DETERMINISTIC_OK` | FitAssessorAgent | OK |
| 11 | `fit_assessment.py:229–244` | audience axis — discipline overlap | `LOW_CONFIDENCE_HINT_OK` | FitAssessorAgent | OK |
| 12 | `fit_assessment.py:246–249` | formal_compliance axis — always `unknown` | `SHOULD_RETURN_UNKNOWN` (and does) | — | OK |
| 13 | `fit_assessment.py:251–255` | author_eligibility axis — always `unknown` | `SHOULD_RETURN_UNKNOWN` (and does) | — | OK |
| 14 | `article_enrichment.py:87–115` | School detection via registry author-name match | `LOW_CONFIDENCE_HINT_OK` | ArticleSemanticProfilerAgent | OK |
| 15 | `compliance.py:101–114` | word_count check | `FORMAL_DETERMINISTIC_OK` | — | OK (when wired) |
| 16 | `compliance.py:63–80` | abstract length | `FORMAL_DETERMINISTIC_OK` | — | OK |
| 17 | `compliance.py:82–99` | keyword count | `FORMAL_DETERMINISTIC_OK` | — | OK |
| 18 | `compliance.py:126–139` | data-availability + ethics substring | `LOW_CONFIDENCE_HINT_OK` | none | inert |
| 19 | `compliance.py:150–162` | COI / anonymization / cover-letter substrings | `LOW_CONFIDENCE_HINT_OK` | none | inert |
| 20 | `venue_profiling.py:138–156` | publication_regime substring ("special issue", "conference", "mega-journal") | `FORMAL_DETERMINISTIC_OK` (honest None fallback) | VenueProfilerAgent | OK |
| 21 | `venue_profiling.py:332–339` | indexing_claims substring ("scopus", "doaj", ...) — metadata list only | `FORMAL_DETERMINISTIC_OK` | none needed | OK |
| 22 | `venue_profiling.py:388–439` | open_access / apc / anonymization / ai_policy / data / ethics policy regex with negation guards | `LOW_CONFIDENCE_HINT_OK` | VenueProfilerAgent | OK |
| 23 | `venue_profiling.py:102–125` | article_types regex extraction | `FORMAL_DETERMINISTIC_OK` | VenueProfilerAgent | OK |
| 24 | `venue_profiling.py:246–252` | venue confidence label (medium iff scope ≥200 chars + name present) | `LOW_CONFIDENCE_HINT_OK` | — | OK |
| 25 | `mismatch_mapping.py:14` | `core_sensitive_axes` hardcoded list | `FORMAL_DETERMINISTIC_OK` | — | OK (structural taxonomy) |
| 26 | `mismatch_mapping.py:23–48` | axis-severity classification | `FORMAL_DETERMINISTIC_OK` | mismatch_mapper (dormant) | OK |
| 27 | `mismatch_mapping.py:57–72` | `venue_side` deliberately empty (Track D) | `SAFE_BECAUSE_LLM_OVERRIDES` | MismatchNarratorAgent (active) | OK |
| 28 | `rewrite_planning.py:13–21` | axis→change_type dict mapping | `FORMAL_DETERMINISTIC_OK` | rewrite_planner (dormant) | OK |
| 29 | `rewrite_planning.py:136–158` | template conditional actions (`status=conditional`) | `FORMAL_DETERMINISTIC_OK` | — | OK |
| 30 | `risk_reporting.py:90–103` | desk_reject_risk from axis histogram | `LOW_CONFIDENCE_HINT_OK` | risk_officer (dormant) | OK |
| 31 | `risk_reporting.py:105–139` | scope / methodology / citation / language risks | `LOW_CONFIDENCE_HINT_OK` | dormant | OK |
| 32 | `risk_reporting.py:148–169` | formatting / predatory / author_eligibility | `LOW_CONFIDENCE_HINT_OK` (honest "unknown") | — | OK |
| 33 | `risk_reporting.py:171–193` | ai_policy + data_availability risks | `LOW_CONFIDENCE_HINT_OK` | — | OK |
| 34 | `risk_reporting.py:194–204` | core_transformation_risk count | `FORMAL_DETERMINISTIC_OK` | — | OK |
| 35 | `citation_ecology.py:86–115` | ref count vs guideline limit | `FORMAL_DETERMINISTIC_OK` | citation_planner (dormant) | OK (when wired) |
| 36 | `citation_ecology.py:117–147` | recency profile | `FORMAL_DETERMINISTIC_OK` (depends on upstream) | dormant | OK |
| 37 | `citation_ecology.py:150–177` | source-diversity kind distribution | `LOW_CONFIDENCE_HINT_OK` | dormant | OK |
| 38 | `citation_ecology.py:179–196` | DOI coverage ratio | `LOW_CONFIDENCE_HINT_OK` | dormant | OK |
| 39 | `citation_ecology.py:199–246` | bridge refs (Track D: ≥2 distinct discipline tokens + venue token) | `LOW_CONFIDENCE_HINT_OK` | dormant | OK (Track D fix landed) |
| 40 | `citation_ecology.py:249–279` | venue-expectation regex | `LOW_CONFIDENCE_HINT_OK` | dormant | OK |

**Top zombies still requiring attention** (priority order):

1. **Z#4 bilingual language-policy** — shared between fallback and LLM
   path; can still leak through `_extract_*_policy` family even when
   LLM enabled. Single function fix.
2. **Z#3 AI-disclosure substring** — inert today (no caller) but the
   first time someone wires compliance, false-positives ship.
3. **Z#1 topic-fit keyword list** — guarded in prod (FitAssessor
   active) but offline tests will pass spurious "strong" fit.
4. **Z#5 publication_regime axis label** — cosmetic but contradicts
   regime_type. Tiny fix.
5. **Z#2 single-keyword argument-move** — guarded in prod.

**Aggregate counts.**

| Classification | Count |
|---|---:|
| `FORMAL_DETERMINISTIC_OK` | 14 |
| `LOW_CONFIDENCE_HINT_OK` | 19 |
| `ZOMBIE_CAN_CORRUPT_OUTPUT` | 5 |
| `SAFE_BECAUSE_LLM_OVERRIDES` | 1 |
| `SHOULD_RETURN_UNKNOWN` (and does) | 2 |

**Routed-roles gap (still open from v1).** `article_field_positioner`,
`venue_field_positioner`, `venue_discovery` are invoked at
`cases.py:644`, `cases.py:809`, `cases.py:973` but absent from the
`routed_roles` tuple in `llm/config.py`. They fall back to the global
model, so the env override `KAIROSKOPION_LLM_MODEL_*` is silently
ignored for these three. Production safe (global model is current
Sonnet) but operator can't pin them independently. 4-line fix; see
§10 Pass A.

---

## 6. Reuse-before-build map

For each agent the backlog plans, what already exists on disk that
must be inspected/reused before any new file is created.

### 6.1 `RewritePlanAgent` (=`agents/fit/rewrite_planner.py`)

| Asset | Status |
|---|---|
| Agent class | ✅ exists, 1–88 LOC, LLM + fallback + protected-core gate |
| Prompt family | ✅ `rewrite_planning` wired |
| Schema | ✅ `RewritePlan`, `RewriteChange`, `manuscript_id` slot |
| Service fallback | ✅ `services/rewrite_planning.py` |
| Protected-core gate | ✅ `services/protected_core.py` |
| UI | ⚠ `AdaptationStudio` + `RewriteTaskCard` render structural changes; verify LLM-authored `desired_state` text renders cleanly |
| Tests | ✅ unit tests for both deterministic and agent path |
| Missing wiring | `_run_fit_chain` direct service call → agent call; add to `routed_roles`; verify `_blocked_reason`, `_matched_core_elements` UI fields |

**Danger if built from scratch:** would duplicate protected-core gate
logic, ignore existing `_blocked_reason` UI affordance, lose the
`manuscript_id` slot.

### 6.2 `CitationBridgeAgent` / `CitationPlannerAgent` (=`agents/fit/citation_planner.py`)

| Asset | Status |
|---|---|
| Agent class | ✅ exists, 1–70 LOC |
| Prompt family | ✅ `citation_ecology` |
| Schema | ✅ `CitationPlan` slot on `Case`, persisted/restored |
| Service fallback | ✅ `services/citation_ecology.py` (Track D bridge fix landed) |
| Adapter needed | ⚠ `BibliographyProfile` must be available before invocation. Today: only built in `/adaptation-plan`. Fit chain would need a builder. |
| UI | ❌ no `CitationPlanView`; absent from DossierView |
| Tests | ✅ for service path |

**Danger if built from scratch:** would duplicate gap-detection logic
and the Track D fix; would drop existing dangerous-padding-warnings
schema.

### 6.3 `VenuePolicyExtractorAgent`

| Asset | Status |
|---|---|
| Agent class | ⚠ no dedicated agent; `VenueProfilerAgent` already extracts policies as part of `VENUE_FACT_EXTRACTION_FAMILY` |
| Schema | ✅ `VenueModel` has `open_access_status`, `apc_policy`, `anonymization_policy`, `ai_policy`, `data_policy`, `ethics_policy`, `indexing_claims` |
| Service fallback | ✅ `venue_profiling.py:388–439` with negation guards |
| Wiring | ✅ active |

**Decision:** *Don't* build a separate agent. Extend
`VenueProfilerAgent`'s prompt with explicit policies block if richer
extraction needed. Fix Z#4 bilingual bug first.

### 6.4 `ComplianceChecklistBuilder` (=`agents/submission/compliance_auditor.py`)

| Asset | Status |
|---|---|
| Agent class | ✅ exists, 1–77 LOC |
| Prompt family | ✅ `compliance_checklist` |
| Schema | ✅ `ComplianceChecklist` dataclass |
| Case slot | ❌ no `Case.compliance_checklist` attribute |
| Service fallback | ⚠ exists but contains Z#3 bug |
| UI | ❌ no rendering |
| Tests | ✅ unit |

**Danger if built from scratch:** duplicates 13-item taxonomy;
re-introduces or misses Z#3 fix opportunity; doesn't reuse already-
wired venue/regime-awareness.

### 6.5 `SubmissionPackBuilder` (=`agents/submission/submission_pack_builder.py`)

| Asset | Status |
|---|---|
| Agent class | ✅ exists, 1–63 LOC |
| Prompt family | ✅ `submission_pack` |
| Schema | ✅ `SubmissionPack` |
| Service fallback | ✅ `services/submission_pack.py` |
| Case slot | ❌ no attribute |
| Stage | ✅ `CaseStage.SUBMISSION_PACK` enum exists but never assigned |
| UI | ⚠ placeholder view only |
| Tests | ✅ unit |

**Danger if built from scratch:** wastes the existing stage enum +
schema + placeholder view; duplicates pack-readiness logic.

### 6.6 `SubmissionScenarioBuilder` (=`agents/control/scenario_prober.py`)

| Asset | Status |
|---|---|
| Agent class | ✅ exists, 1–52 LOC; LLM + deterministic fallback correct |
| Prompt family | ✅ `scenario_interview` (catalog says deterministic, code says llm_optional — doc mismatch) |
| Schema | ✅ `SubmissionScenario` + `scenario_preliminary` flag |
| UI | ✅ `ScenarioBuilder` |
| Tests | ✅ |
| Missing | Only the catalog mode-label fix |

**Danger if built from scratch:** duplicates already-correct agent;
loses honest fallback to deterministic mapping.

### 6.7 `EvidenceAuditor` / `QualityGates`

| Asset | Status |
|---|---|
| Agent class | ✅ `agents/evidence/evidence_auditor.py:1–74` |
| Prompt family | ✅ `evidence_audit` |
| Schema | ✅ `Case.quality_gates: dict[str, QualityGateResult]` |
| Service fallback | ✅ deterministic gates (`audit_pipeline_evidence` or similar) |
| API | ✅ `/quality-gates` endpoint |
| UI | ✅ `QualityGateBar` |
| Tests | ✅ |
| Missing wiring | invoke after fit chain completes; surface LLM-judged gates with provenance |

**Danger if built from scratch:** duplicates gate taxonomy; loses
`QualityGateBar`'s existing structural rendering.

### 6.8 `VenueMemory`

| Asset | Status |
|---|---|
| Agent class | ✅ `agents/review/venue_memory_keeper.py` (contract stub) |
| Schema | ❌ no `VenueMemory` dataclass |
| Required upstream | `ReviewOutcome` (also stub-only) → `RevisionPlan` (no schema) → `VenueMemory` |

**Danger if built from scratch:** the post-submission loop is one
coherent design. Bolt-on `VenueMemory` without `ReviewOutcome` first
leaves it unfed.

### 6.9 `WhiteCrow PatchQueue export`

| Asset | Status |
|---|---|
| Bridge | ✅ `integrations/whitecrow_bridge.py:40–78`, one-way Kairon→WhiteCrow |
| Protected core | ✅ service exists |
| CLI | ✅ `kairoskopion export-whitecrow-patches` |
| Missing | Reverse direction (WhiteCrow → Kairon variant candidates), `FieldModelReference` |

### 6.10 `Litops / Vault artifact export`

| Asset | Status |
|---|---|
| Bridge | ✅ `integrations/litops_bridge.py` (JSONL export) |
| CLI | ✅ `kairoskopion export-litops-pack` |
| Vault | ✅ markdown cards + manifest |
| Missing | Import-side adapter |

---

## 7. Deletion candidates — advisory only

**No deletions performed. No deletions recommended this pass.** Each
row is "could be retired *if* the named successor proves itself in
prod, *after* the named tests are added." All currently `KEEP`.

| Candidate | Why it looks obsolete | What replaced it / will replace it | Proof required | Tests required before delete | Phase | Classification |
|---|---|---|---|---|---|---|
| `services/fit_assessment.py` deterministic keyword lists (Z#1, Z#5) | Replaced by FitAssessorAgent in prod | LLM agent | LLM-on path covers offline tests too (or offline tests get separate fixtures) | offline-mode test that doesn't depend on keyword zombies | After §10 Pass D | `KEEP_FOR_BACKCOMPAT` |
| `services/mismatch_mapping.py` deterministic build | Will be wrapped by mismatch_mapper agent | agent + service fallback chain | mapper agent in prod | mapper integration test | After §10 Pass B | `KEEP_UNTIL_NEW_AGENT` |
| `services/compliance.py` Z#3 substring branch | Bug + no LLM guard | ComplianceAuditorAgent (when wired) | agent in prod | regression for AI-disclosure detection | After §10 Pass E | `KEEP_UNTIL_NEW_AGENT` |
| `agents/prompt_families/corpus_pattern_mining.py` | No consumer agent | Future `CorpusPatternMinerAgent` (not planned in next-5) | — | — | Future | `KEEP_FOR_BACKCOMPAT` |
| `agents/prompt_families/review_outcome` | No consumer outside `review/` stubs | Future post-review lane | — | — | Future | `KEEP_FOR_BACKCOMPAT` |
| `CaseStage.SUBMISSION_PACK` enum | Orphan stage (never assigned) | Future submission-pack lane | — | — | Future | `KEEP_UNTIL_NEW_AGENT` |
| `CaseStage.DOSSIER` enum | Orphan stage | `build_dossier` does not currently advance stage | — | — | Future | `KEEP_UNTIL_NEW_AGENT` |
| `agents/review/*` 6 contract-only stubs | Stubs, never invoked | Post-review lane (Wave 7+) | — | — | Future | `KEEP_AS_FIXTURE` |
| `agents/intent_classifier`, `agents/status_job`, `agents/research_planner` | Registered, no caller | Various future passes | — | — | Future | `KEEP_FOR_BACKCOMPAT` |
| `_llm_input_text`, `_llm_input_truncation` transient fields | Write-only debug | — | — | — | — | `UNKNOWN_DO_NOT_DELETE` (intentionally transient) |

---

## 8. Architecture drift ledger

Places where current code diverged from the original spec because of
incremental prompt-driven development.

### Drift 1 — `ManuscriptModel` built transiently, never persisted

- **Original intent (spec §6.3, §6.4):** Separate semantic
  `ArticleModel` from structural `ManuscriptModel` (sections, blocks,
  word counts). Both persist on Case. `RewritePlan.changes[]` target
  manuscript blocks, not abstract axes.
- **Current:** `ManuscriptModel` is constructed at `cases.py:477` and
  discarded — not stored on `Case`. `RewritePlan.manuscript_id` is
  always `None`. Rewrite changes refer to axes / target_blocks
  semantically, not to manuscript block IDs.
- **Why:** v0 pipeline prioritised semantic model; manuscript was
  scaffolded but no consumer was added.
- **Acceptable?** For MVP yes — operator sees readable rewrite
  guidance. For long-term submission-pack lane no — pack output needs
  block-level edits.
- **Correction path:** Add `Case.manuscript_model` attribute + snapshot
  + thread `manuscript_id` through RewritePlan. ~200 LOC. **Defer until
  the rewrite agent is wired (§10 Pass C).**

### Drift 2 — Single `overall_label` accessible without axes

- **Original intent (spec §15.4):** No single fit score. Operators must
  always see all 12 axes.
- **Current:** Axes always present in payload, but for several months
  no UI consumer rendered them. Pass A closed the UI gap. **Drift
  largely corrected; residual risk:** `overall_label` is still
  *available* as a single field — any future internal consumer could
  bind to it alone and bypass axes.
- **Acceptable?** Yes for UI today. Add a lint/convention that no
  caller reads `overall_label` without also reading `axes[]`.
- **Correction path:** No code change required. Document the
  invariant in `SCHEMA_INVARIANTS.md`.

### Drift 3 — `EvidenceStatus` enum defined and unused by fallback writers

- **Original intent (spec §6.1, Wave 1 §5.6):** All claims tagged with
  one of 12 evidence statuses (`fact_from_source`, `vendor_claim`,
  `inference`, `unknown`, `inaccessible`, `stale`,
  `conflicting_evidence`, ...).
- **Current:** Enum is fully defined (`enums.py:10–22`). `EvidenceItem`
  carries the field. **But fit-axes are plain dicts without
  `evidence_status`. Deterministic services never tag their outputs.**
  An operator can't tell whether axis `topic = strong` came from venue
  text (fact) or keyword match (inference).
- **Why:** Fallback writers predate the enum; nobody back-filled.
- **Acceptable?** No, in principle. Yes, today, because the UI now
  shows "Комментарий пока не построен" / "Неизвестно: недостаточно
  данных" honest copy when axes lack reason — which is a *proxy*
  for "low-confidence inference" but not the spec taxonomy.
- **Correction path:** Add `evidence_status` field to `FitAxis`;
  back-fill deterministic writers to tag `inference` or
  `fact_from_source`; tag agent writers with provenance from
  `extraction_attempt`. ~100 LOC. **Wave 5 backlog.**

### Drift 4 — No ContextPack-like reproducibility for entity-level outputs

- **Original intent (spec §6.2, §36.5):** Every entity carries a
  `context_pack_id` linking back to the LLM call (prompt, response,
  model, temperature). Operator can re-run any decision.
- **Current:** `extraction_attempt` slot exists on `ArticleModel`,
  `FitAssessment`, etc., with shape `{llm_attempted, llm_provider,
  llm_model, llm_latency_ms, parse_status, fallback_used,
  raw_output_ref, ...}`. Agent path populates it. **Deterministic-only
  path does not** — `extraction_attempt` stays `None`. Operator can't
  trace fallback verdicts.
- **Why:** Fallback paths were added before extraction_attempt slot.
- **Acceptable?** Partially — `confidence="low"` + unknowns list give
  *implicit* "this came from fallback" signal, but not reproducible.
- **Correction path:** Have deterministic fallbacks populate a minimal
  `extraction_attempt` with `{source: "deterministic", version: "v1",
  llm_attempted: false}`. Tiny change, defer until Wave 5 ContextPack
  integration.

### Drift 5 — `SubmissionScenario` auto-synthesis when missing

- **Original intent (spec §6.17):** Scenario is *required* input.
  Without operator-stated constraints (deadline, prestige, APC, risk
  tolerance), fit assessment is meaningless.
- **Current:** `_run_fit_chain` synthesises a "preliminary" scenario
  if missing (commit `b48698e`), marks `scenario_preliminary=true`, UI
  shows a banner. Honest, not silent — but still a deviation.
- **Why:** Vertical-slice pressure — needed fit chain to run before UI
  scenario panel existed.
- **Acceptable?** Yes for staging operator-preview, with the banner.
  Not acceptable for any future production claim.
- **Correction path:** Once the operator UI mandates scenario before
  fit, remove synthesis or convert to hard-fail. No code change today.

### Drift 6 — `CitationPlan` is ecology in *service*, padding in *Case*

- **Original intent (spec §6.21):** Ecology — bridge-tradition map
  between article's citation profile and venue's expectations.
- **Current:** Service implements ecology correctly
  (`citation_ecology.py`). **But the Case slot is never populated,**
  so the rest of the system experiences "no citation plan." Adaptation-
  plan endpoint lazy-builds it, but result is not persisted to Case.
- **Why:** Wiring oversight.
- **Correction path:** §10 Pass D.

### Drift 7 — `ComplianceChecklist` not regime-aware in practice

- **Original intent (spec §6.24, §15.7):** Venue + regime + article-
  type aware compliance check.
- **Current:** Service *takes* venue + guidelines and does check
  guidelines by regime keyword (`compliance.py:50–175`), but the
  service has no call site and `Case` has no slot. So in practice
  Kairon ships *no* compliance check at all in the runtime path.
- **Why:** Lane never opened.
- **Correction path:** §10 Pass E.

### Drift 8 — `SubmissionPack` exists as schema/report-text, not operational object

- **Original intent (spec §6.25):** Operational artefact — file list,
  cover letter, statements, ready-to-submit gate.
- **Current:** Schema correct. Service correct. **No Case slot, no
  stage transition, no UI binding.** Operator can't actually generate
  a pack.
- **Correction path:** Dedicated lane, deferred beyond next-5.

### Drift 9 — `VenueMemory` learning loop absent

- **Original intent (spec §6.29, §8.1):** `ReviewOutcome` →
  `VenueMemory` → next `FitAssessment` for same venue.
- **Current:** No `VenueMemory` schema class, no `ReviewOutcome`
  intake. Venues are stateless across cases.
- **Correction path:** Wave 7+. Not in next-5.

### Drift 10 — Mode-label mismatch on `scenario_interview` prompt family

- **Current:** `agents/prompt_families/catalog.py` says
  `execution_mode="deterministic"`; code at
  `agents/control/scenario_prober.py:28` attempts LLM. Honest fallback
  makes behaviour correct; doc is wrong.
- **Correction path:** One-line catalog fix. Doc-only audit defers.

---

## 9. Forgotten requirements ledger

Spec requirements that are not on the planned backlog but appear
forgotten or bypassed — not just "not yet built."

| # | Spec requirement | Why it matters | Current state | Architecture still supports? | Smallest restoration | Restore / redesign / drop? |
|---|---|---|---|---|---|---|
| 1 | Provenance/evidence status separation in every claim | Core to evidence-first promise (CLAUDE.md rule 1) | Enum defined, fit axes don't carry it (Drift 3) | Yes — add field to `FitAxis` | One field + back-fill writers | **Restore** in Wave 5 |
| 2 | ContextPack-like reproducibility at entity level | Audit trail for every decision | `extraction_attempt` slot exists; fallback path doesn't populate | Yes | Populate from deterministic writers | **Restore** when ContextPack lands |
| 3 | source-fact vs vendor-claim vs inference vs unknown distinction | Spec invariant 1 in CLAUDE.md | Schema present; not enforced in fit/risk/compliance writers | Yes | Same as #1 | **Restore** |
| 4 | Protected core / field-core risk on every change | Spec §15.5 — never silently touch core | `services/protected_core.py` exists; rewrite agent's gate dormant; deterministic rewrite service does call validator | Yes | Wire rewrite_planner agent (Pass C) | **Restore** |
| 5 | `SubmissionScenario` required for meaningful fit | Spec §6.17 | Auto-synth with honest banner (Drift 5) | Yes | Hard-fail when missing, after scenario panel is mandatory in UI | **Restore** when UI flow allows |
| 6 | `CitationPlan` as ecology, not bibliography padding | Spec §6.21 | Service correct, Case slot empty (Drift 6) | Yes | Wire one writer (Pass D) | **Restore** |
| 7 | `ComplianceChecklist` venue/regime-aware | Spec §6.24 | Service correct, no call site, no Case slot (Drift 7) | Yes (after schema add) | Pass E | **Restore** |
| 8 | `SubmissionPack` as operational object | Spec §6.25 | Schema correct; full lane missing (Drift 8) | Yes (after lane added) | Dedicated lane | **Restore later** |
| 9 | `VenueMemory` post-submission learning | Spec §6.29, §8.1 | No schema, no intake (Drift 9) | Needs new dataclasses | Wave 7+ | **Restore later** |
| 10 | `ReframePlan` — core-preserving alternative to rewrite | Spec §15.5b | Absent | Needs new dataclass + agent | Wave 5+ | **Restore** (cheap to design, hard to author without RewritePlan in place first) |
| 11 | `RevisionPlan` (post-review revision) | Spec §6.28 | Agent stub only, no dataclass | Needs new dataclass | Post-review lane | **Restore later** |
| 12 | `IssueModel`, `ResearchTopicModel` | Spec §6.7 | Absent | Needs new dataclasses | Cheap (5 fields each) | **Restore** when journal-section flow needs them |
| 13 | `FieldModelReference` (WhiteCrow back-reference) | Spec §6.5 | Absent | Needs new dataclass + bridge update | WhiteCrow lane | **Restore later** |
| 14 | Two-way Litops bridge | Ecosystem position diagram | Export-only | Needs import adapter | Litops lane | **Restore later** |
| 15 | `evidence_auditor` as final pipeline check | Spec §15.9 | Agent dormant | Yes | Pass E | **Restore** |

---

## 10. Recommended next 5 passes — ordered by dependency

Each pass is grounded *only* in this audit's findings. None creates a
new agent class from scratch (everything reuses an already-existing
file). None changes models, prompts, or env routing.

### Pass A — `routed_roles` tuple completion (4-line backend, 0 LOC UI)

**Justification:** Open since v1 (§3 row 13–14 in this audit, §1.3 in
v1). Three production-live roles silently ignore their per-role env
override.
**Scope:** Add `article_field_positioner`, `venue_field_positioner`,
`venue_discovery` to the `routed_roles` tuple in `llm/config.py:155–202`.
Add corresponding entries in `provider_status().model_per_role`.
**Risk:** ~Zero. No behavioural change unless someone sets those env
vars (today nobody does).
**Verification:** `/health` lists 13 roles instead of 10.

### Pass B — Wire `mismatch_mapper` agent into fit chain

**Justification:** §2.4 + §3.6 + §10 v1 Pass B. Agent
`agents/fit/mismatch_mapper.py` is fully coded, registered, never
invoked. Narrator currently runs on deterministic structure; adding
the LLM-structured layer between gives spec-shaped chain
[deterministic → LLM-structured → LLM-prose].
**Scope:** Insert agent call in `_run_fit_chain` between deterministic
`build_mismatch_map` and narrator. Add `mismatch_mapper` to
`routed_roles`. Schema-compat check: confirm mapper-enriched
`MismatchMap` keys are a superset of what narrator consumes.
**Risk:** Medium — schema alignment between mapper and narrator.
**Verification:** Pairings (philosophy/AI-ed scripts already in repo)
should show richer `description`/`possible_actions` per mismatch when
LLM on.

### Pass C — Wire `rewrite_planner` agent into fit chain

**Justification:** §2.5 + §3.1 + §6.1. Agent
`agents/fit/rewrite_planner.py` is fully coded with protected-core
gate (`rewrite_planner.py:55–59` → `services/protected_core.py`).
Today the service runs directly; agent is dormant. Wiring it activates
the protected-core gate end-to-end and adds LLM rationale to changes.
**Scope:** Replace direct `build_rewrite_plan` call in fit chain
(`cases.py:1254`) with `RewritePlannerAgent` invocation; agent
delegates to the service on fallback. Add to `routed_roles`. UI check:
`RewriteTaskCard` renders LLM-authored `desired_state` cleanly
alongside structural fields; `_blocked_reason`,
`_matched_core_elements` already typed.
**Risk:** Medium — UI render of LLM strings needs verification; LLM
output for `desired_state` must not be too long.
**Verification:** Adaptation studio shows LLM-authored rewrite text.

### Pass D — Wire `citation_planner` + `risk_officer` agents; render CitationPlan in Dossier

**Justification:** §2.6 + §2.7 + §3.2 + §3.3 + Drift 6. Both agents
exist; `CitationPlan` slot empty; `RiskReport` already UI-visible
(Pass A) but service-built only. Single integrated pass adds LLM
enrichment to two adjacent chain steps and closes the CitationPlan
orphan.
**Scope:** (a) Decide architecturally where citation ecology runs —
recommend fit chain after rewrite plan, with on-demand
`BibliographyProfile` build if missing. (b) Wire
`CitationPlannerAgent`; assign result to `Case.citation_plan`. (c)
Wire `RiskOfficerAgent`; replace direct `build_risk_report` call;
service fallback retained. (d) New `CitationPlanView` section in
`DossierView` mirroring the FitAxes pattern. (e) Both agents added to
`routed_roles`.
**Risk:** Medium — citation chain's `BibliographyProfile` dependency
must be solved.
**Verification:** Dossier shows citation plan; risk report items have
visibly richer descriptions when LLM on.

### Pass E — Compliance lane + `evidence_auditor` final gate

**Justification:** §2.8 + §3.4 + §3.5 + Drift 7 + Forgotten
requirement #7 and #15. Compliance is the largest still-missing fit-
chain output; evidence auditor is the spec-mandated final gate.
**Scope:** (a) Fix Z#3 substring bug in `services/compliance.py:141`
(one-line `\bai\b` change). (b) Add `Case.compliance_checklist`
attribute + snapshot persistence. (c) Wire `ComplianceAuditorAgent`
in fit chain post-CitationPlan. (d) Wire `EvidenceAuditorAgent` as
final pass; result writes `Case.quality_gates` entries with
provenance. (e) Both agents added to `routed_roles`. (f) UI: add
`ComplianceChecklistView` in DossierView; LLM-judged gates flagged in
`QualityGateBar`.
**Risk:** Medium-high — most components touched; depends on Passes
B-D having stabilised the chain.
**Verification:** Dossier shows compliance items + LLM gate verdicts.

**Explicitly out of scope of next-5:** SubmissionPack lane (drift 8),
`ReframePlan` (forgotten #10), VenueMemory loop (drift 9), `IssueModel`
/ `ResearchTopicModel` (forgotten #12), two-way Litops/WhiteCrow
bridges (forgotten #13–14). All real, all deferred to dedicated lanes.

---

## 11. "Do not build before checking this" checklist

Before authoring any new file for the lanes below, the operator MUST
verify the following exist on disk *first*. Inventory taken at
`542256d`.

### Before any new fit-chain agent

- [ ] `agents/fit/mismatch_mapper.py` — already done
- [ ] `agents/fit/rewrite_planner.py` — already done
- [ ] `agents/fit/citation_planner.py` — already done
- [ ] `services/fit_assessment.py`, `mismatch_mapping.py`,
      `rewrite_planning.py`, `citation_ecology.py` — already done
- [ ] `agents/prompt_families/catalog.py` entries for
      `mismatch_mapping`, `rewrite_planning`, `citation_ecology`,
      `risk_reporting`, `compliance_checklist` — already done
- [ ] `services/protected_core.py` validator + gate — already done

### Before any new submission-side agent

- [ ] `agents/submission/risk_officer.py` — already done
- [ ] `agents/submission/compliance_auditor.py` — already done
- [ ] `agents/submission/submission_pack_builder.py` — already done
- [ ] `services/risk_reporting.py`, `compliance.py`, `submission_pack.py`
      — already done
- [ ] `schema.py` `RiskReport`, `ComplianceChecklist`, `SubmissionPack`
      classes — already done
- [ ] `CaseStage.SUBMISSION_PACK` enum value — already done

### Before any new evidence/quality-gate agent

- [ ] `agents/evidence/evidence_auditor.py` — already done
- [ ] `services/source_evidence_packet.py` + `Case.source_evidence_packet`
      — already done
- [ ] `Case.quality_gates` + `/quality-gates` endpoint + `QualityGateBar`
      UI — already done

### Before any new venue-side agent

- [ ] `agents/venue_profiler.py` (covers most policy extraction) — already done
- [ ] `agents/venue/publication_regime_classifier.py` (optional regime
      LLM refinement) — already done
- [ ] `services/venue_profiling.py` (with negation guards) — already done
- [ ] **Fix Z#4 bilingual language bug before extending language
      extraction in any new agent.**

### Before any new scenario-side change

- [ ] `agents/control/scenario_prober.py` — already done
- [ ] `schema.py` `SubmissionScenario` + `scenario_preliminary` flag
      — already done
- [ ] **Fix `agents/prompt_families/catalog.py` mode label for
      `scenario_interview` (deterministic → llm_optional) before adding
      any new scenario doc.**

### Before any post-review lane

- [ ] `agents/review/*` 6 contract-only stubs — already done
- [ ] **Add schema classes first:** `RevisionPlan`, `VenueMemory`,
      `ReviewOutcome` (the agent stubs reference them).

### Before any new prompt family

- [ ] Check `prompts/__init__.py` (12 top-level families)
- [ ] Check `agents/prompt_families/catalog.py` (11 secondary)
- [ ] **Orphan prompts already on disk:** `corpus_pattern_mining` (no
      consumer), `review_outcome` (only stubs). Use these first if scope
      matches.

### Before any new Case slot

- [ ] Check `schema.py` for an existing dataclass and a snapshot
      key on `Case`. Many "absent" entities are present in schema
      and only missing the Case attribute.
- [ ] Check `cases.py` snapshot symmetry — every new slot needs
      `to_dict`/`from_dict` parity.

### Before any new UI component for a chain output

- [ ] Check `DossierView.tsx` for an existing section pattern (post-
      Pass A this includes Fit matrix + Risk Report — copy the same
      honest-fallback / muted-italic copy convention for new outputs).
- [ ] Check `ui/src/types/domain.ts` — many backend slots already have
      TypeScript interfaces; only the render is missing.

---

## 12. Confirmations

- **No code edits.** Only this document added under `docs/operations/`.
- **No env / model / temperature / max_tokens / timeout / retries /
  base_url / API-key changes.**
- **No agents created, no prompts edited, no routes added, no
  routing changed.**
- **No deletions.** All "deletion candidates" are advisory; all are
  `KEEP_*` today.
- **No deploy.** Branch `docs/legacy-compatibility-reuse-audit-v2`
  remains feature-branch only.
- **All file:line citations verified** at commit `542256d`.
- **All v1 findings re-evaluated:** the v1 "FitAssessment.axes
  invisible" and "RiskReport invisible" UI gaps are no longer open
  (closed by Pass A, commit `542256d`); other v1 findings (mapper
  bypassed, routed_roles gap, orphan agents) are carried forward and
  expanded here.
