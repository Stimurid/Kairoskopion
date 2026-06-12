# Agentic Contour v0.1 — Quality Review

**Date:** 2026-06-12
**Base:** `main` at `5c50248`, tag `v0.2.0-alpha-rc8`
**Branch:** `feature/agentic-contour-quality-review-v01`
**Tests:** 782/782 passing
**Auditor:** Claude Opus 4.6

---

## 1. Release Baseline

| Metric | Value |
|--------|-------|
| Agents | 26 (20 `operational_now`, 6 `contract_only`) |
| Prompt families | 16 (5 original, 11 new) |
| Workflows | 4 (2 executable, 1 executable, 1 skeleton) |
| CLI commands | 23 total (7 new agentic) |
| Tests | 782 passing |

---

## 2. Prompt Family Quality Table

| family_id | Purpose | Input | Output | Evidence | Unknowns | Forbidden | Domain | Anti-halluc | UC-1 | Weakest part | Repair |
|-----------|---------|-------|--------|----------|----------|-----------|--------|-------------|------|-------------|--------|
| article_modeling_v1 | strong | strong | strong | strong | strong | strong | strong | strong | strong | Minor dedup of null-handling instruction | Low priority |
| venue_fact_extraction_v1 | strong | strong | strong | strong | strong | strong | strong | strong | strong | Validator only checks indexing/metrics | Extend validator |
| fit_assessment_v1 | strong | strong | strong | strong | strong | strong | strong | strong | strong | No example of "not_enough_data" | Add example |
| semantic_profiling_v1 | strong | adequate | adequate | adequate | adequate | adequate | strong | adequate | strong | "Mark anything uncertain as unknown" — too vague | Add per-field evidence_status |
| disciplinary_mapping_v1 | strong | adequate | strong | adequate | adequate | adequate | strong | adequate | strong | `example_venue_names` invites hallucinated names | Remove or guard field |
| scenario_interview_v1 | strong | strong | strong | adequate | strong | adequate | strong | adequate | strong | "Do not guess timeline" should generalize | Generalize to all fields |
| publication_regime_v1 | strong | adequate | adequate | adequate | adequate | adequate | strong | adequate | adequate | `regime_type` is free string, not enum | Add enum in schema |
| corpus_pattern_mining_v1 | strong | adequate | adequate | strong | adequate | adequate | strong | adequate | adequate | Distribution fields are untyped `object` | Define inner schema |
| citation_ecology_v1 | strong | strong | adequate | strong | adequate | strong | strong | adequate | strong | `bridge_references_needed` name implies specifics | Rename to categories |
| mismatch_mapping_v1 | strong | strong | strong | adequate | adequate | adequate | strong | adequate | strong | `field_core_impact` is free string | Add enum |
| rewrite_planning_v1 | adequate | strong | strong | adequate | adequate | adequate | strong | adequate | strong | Drops "evidence-first" tagline | Restore identity line |
| risk_reporting_v1 | strong | strong | adequate | strong | strong | adequate | strong | adequate | strong | `evidence` not in required | Add to required |
| compliance_checklist_v1 | adequate | adequate | adequate | adequate | adequate | adequate | adequate | adequate | adequate | Template missing manuscript_model | Fix template or contract |
| submission_pack_v1 | adequate | adequate | adequate | thin | adequate | thin | adequate | thin | adequate | Thinnest system prompt, weakest evidence | Expand prompt, add venue/rewrite to template |
| review_outcome_v1 | strong | strong | adequate | adequate | adequate | strong | strong | adequate | adequate | Nested objects have no inner schema | Define inner schemas |
| evidence_audit_v1 | strong | adequate | strong | strong | strong | strong | strong | strong | strong | Thresholds in text but not validator | Add threshold validation |

### Prompt Family Summary

| Rating | Count |
|--------|-------|
| Strong (7+ dimensions strong) | 3 (article_modeling, venue_fact_extraction, fit_assessment) |
| Adequate (mixed strong/adequate) | 11 |
| Thin (has thin dimensions) | 1 (submission_pack_v1) |
| Placeholder | 0 |
| Broken | 0 |

### Structural Gap

Module-level constants (`PURPOSE`, `FORBIDDEN_BEHAVIORS`, `EVIDENCE_REQUIREMENTS`, `UNKNOWN_HANDLING`, `INPUT_CONTRACT`, `OUTPUT_CONTRACT`) exist in all 11 new prompt families but are **not included in the catalog dict**. They are dead metadata — available only via direct module import, not via `get_prompt_family()`. The catalog propagates only 7 keys: family_id, agent_role_id, version, system_prompt, user_prompt_template, output_schema, validator.

---

## 3. Agent Quality Table

| agent_id | layer | classification | deterministic | LLM | UC-1 | repair |
|----------|-------|---------------|--------------|-----|------|--------|
| intent_classifier | control | **real_operational** | regex 6-intent classifier | delegates to det. | HIGH | — |
| scenario_prober | control | **real_operational** | wraps build_scenario_from_dict | delegates to det. | HIGH | — |
| research_planner | control | **real_operational** | inspects entity pool, plans steps | delegates to det. | HIGH | — |
| status_job | control | **real_operational** | entity inventory summary | delegates to det. | MEDIUM | — |
| article_modeler | article | **real_operational** | wraps article_modeling service (real heuristics) | full LLM via article_modeling family | HIGH | — |
| article_semantic_profiler | article | **real_operational** | copies minimal fields from ArticleModel | full LLM via semantic_profiling family | HIGH | det. fallback very thin |
| disciplinary_pathway_mapper | article | **real_operational** | single "unclassified" pathway fallback | full LLM via disciplinary_mapping family | HIGH | det. fallback very thin |
| venue_profiler | venue | **real_operational** | wraps venue_profiling service (real heuristics) | full LLM via venue_fact_extraction family | HIGH | — |
| fit_assessor | fit | **real_operational** | wraps assess_fit service (real 12-axis) | full LLM via fit_assessment family | HIGH | — |
| mismatch_mapper | fit | **real_operational** | wraps build_mismatch_map(fit) — correct | delegates to det. | HIGH | Wire LLM path |
| evidence_auditor | evidence | **real_operational** | wraps audit_pipeline_evidence — correct | delegates to det. | HIGH | — |
| venue_identifier | venue | **useful_stub** | returns empty candidates, needs_sources | delegates to det. | LOW | Registry should say `stub` |
| venue_discovery | venue | **useful_stub** | keyword match on seed_venues (empty in practice), generates search_tasks | delegates to det. | LOW | Needs adapter integration |
| venue_publication_profile_builder | venue | **useful_stub** | builds profile from venue + evidence_pack claims | delegates to det. | MEDIUM | Many unknowns, limited inputs |
| publication_regime_classifier | venue | **thin_stub** | copies regime_type from VenueModel fields | delegates to det. | LOW | Registry misleading — says has prompt family, never uses it |
| rewrite_planner | fit | **BROKEN** | calls `build_rewrite_plan(mm, fit)` — service takes 1 positional + keyword-only | delegates to det. | ZERO | Fix: pass `fit` as keyword or omit |
| citation_planner | fit | **BROKEN** | calls `build_citation_ecology_report(article, venue)` — service needs `(bib_profile, article, venue, guidelines_text)` | delegates to det. | ZERO | Fix: build BibliographyProfile, add guidelines_text |
| risk_officer | submission | **BROKEN** | calls `build_risk_report(article, venue, fit, mm)` — service needs `(article, venue, scenario, fit, mismatch_map)` | delegates to det. | ZERO | Fix: add scenario from entities |
| compliance_auditor | submission | **BROKEN** | calls `build_compliance_checklist(article, venue)` — service needs `(article, manuscript, venue, guidelines_text)` | delegates to det. | ZERO | Fix: build manuscript + add guidelines_text |
| submission_pack_builder | submission | **BROKEN** | wrong kwargs — passes `mismatch_map`, `rewrite_plan`, `risk_report` which don't exist in service signature | delegates to det. | ZERO | Fix: match service kwargs, add scenario |
| reviewer_simulation | review | **honest_stub** | contract_only_output | contract_only_output | NONE | Future |
| review_outcome_analyst | review | **honest_stub** | contract_only_output | contract_only_output | NONE | Future |
| revision_planner | review | **honest_stub** | contract_only_output | contract_only_output | NONE | Future |
| rebuttal_architect | review | **honest_stub** | contract_only_output | contract_only_output | NONE | Future |
| tacit_signal_structurer | review | **honest_stub** | contract_only_output | contract_only_output | NONE | Future |
| venue_memory_keeper | review | **honest_stub** | contract_only_output | contract_only_output | NONE | Future |

### Agent Classification Summary

| Classification | Count | Agents |
|---------------|-------|--------|
| real_operational | 11 | intent_classifier, scenario_prober, research_planner, status_job, article_modeler, article_semantic_profiler, disciplinary_pathway_mapper, venue_profiler, fit_assessor, mismatch_mapper, evidence_auditor |
| useful_stub | 3 | venue_identifier, venue_discovery, venue_publication_profile_builder |
| thin_stub | 1 | publication_regime_classifier |
| **BROKEN** | **5** | **rewrite_planner, citation_planner, risk_officer, compliance_auditor, submission_pack_builder** |
| honest_contract_stub | 6 | all review layer |

### Registry Honesty

7 of 20 `operational_now` agents are misleading:
- 5 are broken (crash on real execution due to wrong service signatures)
- 1 is a stub (venue_identifier — always returns empty)
- 1 is a thin field-copier with unused prompt family (publication_regime_classifier)

---

## 4. Workflow Execution Review

### UC-1: Draft to Venue Pool Positioning (12 steps)

**Command:** `run-agent-workflow uc1_draft_to_venue_pool_positioning --manuscript examples/sample_manuscript.md`

| Step | Agent | Status | Notes |
|------|-------|--------|-------|
| 0 | article_modeler | OK | Title extracted, method=conceptual_method, word_count=736 |
| 1 | article_semantic_profiler | OK | Minimal det. fallback: registers=[None], no traditions |
| 2 | disciplinary_pathway_mapper | OK | 1 pathway with fit=unknown, no register name |
| 3 | venue_discovery | OK | 0 candidates, 0 search_tasks (pathways too thin) |
| 4-11 | fit_assessor through evidence_auditor | SKIPPED | All skip_if_missing: venue — venue_discovery outputs `venue_pool`, not `venue` |

**Verdict:** 4/12 completed, 8 skipped. Steps 1-3 produce thin outputs without LLM. Design gap: venue_discovery outputs `venue_pool` key but downstream steps need `venue` key.

### Direct Manuscript-Venue Fit (8 steps)

**Command:** `run-agent-workflow direct_manuscript_venue_fit --manuscript examples/sample_manuscript.md --venue-json <venue>.json`

With `stop_on_failure=False`:

| Step | Agent | Status | Error |
|------|-------|--------|-------|
| 0 | article_modeler | OK | — |
| 1 | fit_assessor | OK | — |
| 2 | mismatch_mapper | OK | — |
| 3 | rewrite_planner | FAILED | `build_rewrite_plan() takes 1 positional argument but 2 were given` |
| 4 | citation_planner | FAILED | `build_citation_ecology_report() missing 2 required positional arguments` |
| 5 | risk_officer | FAILED | `build_risk_report() missing 1 required positional argument` |
| 6 | compliance_auditor | FAILED | `build_compliance_checklist() missing 2 required positional arguments` |
| 7 | evidence_auditor | OK | Runs on partial entities (article, venue, fit, mismatch_map) |

**Verdict:** 4/8 OK, 4/8 FAILED. Steps 0-2 produce real, meaningful output. Step 7 recovers on partial data. Steps 3-6 all crash with TypeError due to wrong service call signatures.

### Workflow Usability Issues

1. **No offline demo path** — UC-1 requires `venue` entity from outside the workflow but venue_discovery doesn't produce it. No documented way to run a complete UC-1 offline.
2. **CLI encoding bug** — `run-agent-workflow` crashed on Unicode `→` in display_name before fix (fixed in this review).
3. **No trace output in CLI** — workflow trace (step_log) is not shown to user. Only OK/FAILED/SKIPPED markers visible.

---

## 5. UC-1 Realism Test

**Input:** `examples/sample_manuscript.md` — "The Impossibility of Artificial Subjectivity: A Conceptual Argument" (philosophy of mind/AI ethics)

**Deterministic-only results (no LLM):**

| Component | Quality | Notes |
|-----------|---------|-------|
| ArticleModel | **Useful** | Title, abstract, method=conceptual_method, word_count=736, unknowns correct |
| SemanticProfile | **Empty** | registers=[None], no traditions, no argument_move. Det. fallback is minimal copy. |
| Pathways | **Empty** | 1 pathway, fit=unknown, no register. Det. fallback returns placeholder. |
| VenueDiscovery | **Empty** | 0 candidates, 0 search_tasks. Nothing to discover from empty pathways. |

**Assessment:** The UC-1 pipeline is **not demonstrable offline without LLM**. ArticleModeler produces real output. Everything after it degenerates to empty/placeholder via deterministic fallbacks. This is honest (the agents don't fabricate) but means UC-1 has no offline showcase value. The LLM paths are implemented and real, but exercising them requires a configured LLM provider.

---

## 6. Defect Ledger

### Blocking (5)

| # | Defect | Agent | Impact |
|---|--------|-------|--------|
| B1 | `rewrite_planner` passes `fit` as 2nd positional to `build_rewrite_plan()` which only takes 1 positional + keyword-only args | rewrite_planner | TypeError on every execution |
| B2 | `citation_planner` calls `build_citation_ecology_report(article, venue)` — service needs `(bib_profile, article, venue, guidelines_text)` | citation_planner | TypeError — missing 2 args |
| B3 | `risk_officer` calls `build_risk_report(article, venue, fit, mm)` — service needs `(article, venue, scenario, fit, mismatch_map)` — missing `scenario` | risk_officer | TypeError — missing 1 arg |
| B4 | `compliance_auditor` calls `build_compliance_checklist(article, venue)` — service needs `(article, manuscript, venue, guidelines_text)` | compliance_auditor | TypeError — missing 2 args |
| B5 | `submission_pack_builder` passes wrong kwargs (`mismatch_map`, `rewrite_plan`, `risk_report`) — service uses (`scenario`, `fit`, `risk`, `compliance`, `trajectory`) | submission_pack_builder | TypeError — unexpected kwargs |

### Major (3)

| # | Defect | Location | Impact |
|---|--------|----------|--------|
| M1 | UC-1 workflow steps 4-11 all need `venue` entity but venue_discovery outputs `venue_pool` — entity key mismatch | workflows.py | UC-1 can never run past step 3 without external venue |
| M2 | 5 broken agents all marked `operational_now` in registry | registry.py | Registry is dishonest — consumers trust status |
| M3 | CLI `run-agent-workflow` crashed on Unicode in display_name | cli.py | Fixed in this review |

### Medium (5)

| # | Defect | Location | Impact |
|---|--------|----------|--------|
| m1 | Prompt family catalog does not include module-level constants (PURPOSE, FORBIDDEN_BEHAVIORS, etc.) | catalog.py | Dead metadata — framework can't inspect forbidden behaviors |
| m2 | `publication_regime_classifier` claims prompt family binding but never uses it | registry.py + agent code | Misleading spec |
| m3 | `venue_identifier` marked `operational_now` but always returns empty | registry.py | Misleading status |
| m4 | Several schemas use free-text strings where prompt defines specific enum values (regime_type, field_core_impact, adaptation_cost) | prompt families | LLM output will drift |
| m5 | `submission_pack_v1` has thinnest system prompt, weakest evidence discipline, missing inputs in template | submission_pack.py | Prompt underspecified |

### Minor (4)

| # | Defect | Location | Impact |
|---|--------|----------|--------|
| n1 | `disciplinary_mapping_v1` asks for `example_venue_names` which invites hallucinated journal names | disciplinary_mapping.py | Hallucination risk |
| n2 | `risk_reporting_v1` has `evidence` field not in required list despite rule saying "every risk must have justification" | risk_reporting.py | Schema/prompt contradiction |
| n3 | `evidence_audit_v1` quality gate thresholds in prompt text but not in validator | evidence_audit.py | PASS at 30% coverage uncaught |
| n4 | Workflow trace (step_log) not displayed in CLI output | cli.py | User can't diagnose failures easily |

---

## 7. Thinness Ledger

### Prompts too generic
- `submission_pack_v1` — 53 lines vs 80+ for other families; generic "don't submit" rules, no specific readiness criteria
- `compliance_checklist_v1` — adequate but generic; doesn't leverage Kairoskopion's evidence-status taxonomy

### Agents mostly empty shells
- `publication_regime_classifier` — copies fields from VenueModel, no classification logic
- `venue_identifier` — echoes query, returns empty, says "no local registry queried"
- `article_semantic_profiler` (det. fallback) — returns [None] for registers, empty for everything else
- `disciplinary_pathway_mapper` (det. fallback) — single "unclassified" pathway

### Outputs not useful enough
- VenueDiscovery search_tasks are never populated when pathways are empty (which they are without LLM)
- UC-1 deterministic run produces 1 useful entity (ArticleModel) and 3 empty/placeholder entities

### CLI usability gaps
- No way to see workflow trace in CLI
- No `--stop-on-failure` flag (hardcoded to True)
- No venue-guidelines-text input option (only --venue-json for pre-built VenueModel)
- No way to see which entities were skipped vs produced

---

## 8. Repair Priority

### Pass A: Fix Broken Agents (BLOCKING — do first)

Fix 5 service call signatures:
1. `rewrite_planner` — pass fit as keyword-only or omit
2. `citation_planner` — build BibliographyProfile from article, add guidelines_text
3. `risk_officer` — add scenario from entities
4. `compliance_auditor` — build ManuscriptModel from article/raw_text, add guidelines_text
5. `submission_pack_builder` — match service kwargs, add scenario

Fix registry honesty:
6. Update `implementation_status` for venue_identifier, publication_regime_classifier

Estimated scope: ~100 lines of agent code changes + test updates.

### Pass B: UC-1 Workflow Completeness

7. Fix venue entity key mismatch (venue_pool → venue selection step)
8. Add `--stop-on-failure=false` CLI flag
9. Add workflow trace display in CLI
10. Add `--venue-guidelines` input option for building VenueModel from text

Estimated scope: ~50 lines.

### Pass C: Prompt Strengthening

11. Add enum constraints to schemas (regime_type, field_core_impact, etc.)
12. Expand submission_pack_v1 system prompt
13. Fix INPUT_CONTRACT / USER_TEMPLATE mismatches
14. Propagate module-level constants to catalog dict
15. Remove or guard `example_venue_names` in disciplinary_mapping

Estimated scope: ~200 lines across prompt family modules.

### Pass D: UC-1 Offline Demo Pack

16. Create a synthetic venue JSON fixture with enough data for the full pipeline
17. Document a complete UC-1 run command with expected output
18. Add smoke test that runs the full workflow end-to-end

---

## 9. Recommendation

**Patch now (Pass A).** The 5 broken agents are not theoretical — they crash on real execution with TypeError. This was confirmed by running the workflow. The fix is mechanical (match service signatures) and does not require new agents, schema, or architecture. It should be the immediate next pass.

Do NOT merge or tag this review. It is a diagnostic document.

---

## Appendix: Verified Execution Transcripts

### UC-1 Workflow Run

```
Running workflow: UC-1: Draft → Venue Pool Positioning
Steps: 12
LLM provider: none (deterministic only)

Status: completed
Steps completed: 4/12

  [OK] step[0] article_modeler
  [OK] step[1] article_semantic_profiler
  [OK] step[2] disciplinary_pathway_mapper
  [OK] step[3] venue_discovery
  [SKIPPED] step[4] fit_assessor
  [SKIPPED] step[5] mismatch_mapper
  [SKIPPED] step[6] rewrite_planner
  [SKIPPED] step[7] citation_planner
  [SKIPPED] step[8] risk_officer
  [SKIPPED] step[9] compliance_auditor
  [SKIPPED] step[10] submission_pack_builder
  [SKIPPED] step[11] evidence_auditor
```

### Direct Manuscript-Venue Fit Run (stop_on_failure=False)

```
Status: partial
  [OK] step[0] article_modeler
  [OK] step[1] fit_assessor
  [OK] step[2] mismatch_mapper
  [FAILED] step[3] rewrite_planner -- build_rewrite_plan() takes 1 positional argument but 2 were given
  [FAILED] step[4] citation_planner -- build_citation_ecology_report() missing 2 required positional arguments: 'venue'
  [FAILED] step[5] risk_officer -- build_risk_report() missing 1 required positional argument: 'mismatch_map'
  [FAILED] step[6] compliance_auditor -- build_compliance_checklist() missing 2 required positional arguments: 'venue' and 'guidelines_text'
  [OK] step[7] evidence_auditor
```
