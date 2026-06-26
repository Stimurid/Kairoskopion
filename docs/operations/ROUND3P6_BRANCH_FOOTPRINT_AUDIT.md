# Round III-P6: Branch Footprint Audit

**Branch:** `feature/round3-six-phase-build-hardening`
**Base:** `origin/main`
**Date:** 2026-06-26

---

## Total branch delta

| Metric | Value |
|--------|-------|
| Files changed | 124 |
| Insertions | 27,537 |
| Deletions | 456 |
| Net delta | +27,081 |

---

## Breakdown by category

| Category | Files | Insertions | Deletions | % of insertions |
|----------|------:|----------:|---------:|---------------:|
| **docs/ (prompt exports)** | 39 | 16,405 | 0 | 59.6% |
| **docs/ (other operations)** | 18 | 2,282 | 37 | 8.3% |
| **tests/** | 19 | 3,378 | 47 | 12.3% |
| **src/ (prompts)** | 19 | 2,578 | 330 | 9.4% |
| **src/ (agents)** | 15 | 1,582 | 23 | 5.7% |
| **src/ (api)** | 2 | 577 | 0 | 2.1% |
| **src/ (other: schema, services, ids, logic)** | 5 | 419 | 13 | 1.5% |
| **ui/** | 7 | 316 | 6 | 1.1% |
| **Total** | **124** | **27,537** | **456** | **100%** |

### Observations

- **59.6% of all insertions are generated prompt-export docs** (`ROUND3P5D_PROMPTS_EXPORT_ALL.md` alone is 7,206 lines). These are machine-generated snapshots of resolved system prompts for owner review, not runtime code.
- **67.9% is documentation total** (prompt exports + operation reports). This is expected for a hardening/audit round.
- **Runtime code** (src/) accounts for 5,156 insertions (18.7%), split across 41 files.
- **Tests** account for 3,378 insertions (12.3%) across 19 files.
- **UI** is a minor addition: 316 lines across 7 files (two new panels + API client extensions).

---

## Top 50 files by added lines

| Rank | Added | Deleted | File |
|-----:|------:|--------:|------|
| 1 | 7,206 | 0 | `docs/operations/ROUND3P5D_PROMPTS_EXPORT_ALL.md` |
| 2 | 1,188 | 0 | `docs/operations/ROUND3P4_PROMPTS_EXPORT_ALL.md` |
| 3 | 866 | 0 | `tests/test_p4_llm_organs.py` |
| 4 | 728 | 0 | `tests/test_p5c_open_field_registry.py` |
| 5 | 665 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/venue_matrix_assessment_v2.md` |
| 6 | 620 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/venue_field_position_v2.md` |
| 7 | 603 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/venue_fact_extraction_v2.md` |
| 8 | 539 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/article_field_position_v2.md` |
| 9 | 442 | 0 | `tests/test_p5a_domain_agnostic.py` |
| 10 | 416 | 0 | `docs/operations/ROUND3P3_LLM_ORGAN_REQUIREMENTS.md` |
| 11 | 388 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/rewrite_planning_v2.md` |
| 12 | 382 | 0 | `src/kairoskopion/api/cases.py` |
| 13 | 333 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/discipline_seeding_v2.md` |
| 14 | 330 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/citation_ecology_analysis_v2.md` |
| 15 | 305 | 0 | `src/kairoskopion/prompts/citation_ecology_analysis.py` |
| 16 | 298 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/venue_funnel_planning_v2.md` |
| 17 | 298 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/article_modeling_v2.md` |
| 18 | 292 | 0 | `docs/operations/ROUND3P5D_OWNER_ACCEPTANCE_EVIDENCE.md` |
| 19 | 290 | 0 | `src/kairoskopion/prompts/rewrite_planning.py` |
| 20 | 286 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/compliance_assessment_v2.md` |
| 21 | 279 | 0 | `docs/operations/ROUND3P5C_PROMPTS_EXPORT_ALL.md` |
| 22 | 277 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/fit_assessment_vpkg_v1.md` |
| 23 | 266 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/fit_assessment_v1.md` |
| 24 | 260 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/discipline_intent_parsing_v2.md` |
| 25 | 257 | 0 | `src/kairoskopion/prompts/venue_funnel_planning.py` |
| 26 | 256 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/semantic_profiling_v2.md` |
| 27 | 245 | 0 | `src/kairoskopion/prompts/discipline_intent_parsing.py` |
| 28 | 240 | 0 | `tests/test_round3p5d_prompt_cleanup.py` |
| 29 | 240 | 0 | `src/kairoskopion/prompts/compliance_assessment.py` |
| 30 | 237 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/disciplinary_mapping_v2.md` |
| 31 | 221 | 0 | `tests/test_phase1_source_acquisition.py` |
| 32 | 215 | 0 | `src/kairoskopion/prompts/venue_matrix_assessment.py` |
| 33 | 209 | 0 | `src/kairoskopion/services/venue_memory.py` |
| 34 | 206 | 0 | `tests/test_phase4_venue_memory.py` |
| 35 | 205 | 0 | `src/kairoskopion/agents/compliance_assessor.py` |
| 36 | 197 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/depth_recommendation_v2.md` |
| 37 | 195 | 0 | `src/kairoskopion/api/app.py` |
| 38 | 188 | 0 | `src/kairoskopion/agents/depth_recommendation.py` |
| 39 | 187 | 0 | `src/kairoskopion/prompts/venue_family_context.py` |
| 40 | 187 | 0 | `src/kairoskopion/agents/rewrite_planner.py` |
| 41 | 184 | 0 | `src/kairoskopion/agents/citation_ecology.py` |
| 42 | 182 | 0 | `src/kairoskopion/prompts/depth_recommendation.py` |
| 43 | 181 | 0 | `src/kairoskopion/agents/venue_matrix_assessor.py` |
| 44 | 177 | 0 | `src/kairoskopion/agents/venue_funnel_planner.py` |
| 45 | 168 | 5 | `src/kairoskopion/schema.py` |
| 46 | 165 | 0 | `docs/operations/ROUND3P5C_OPEN_FIELD_AND_REGISTRY_REPAIR_REPORT.md` |
| 47 | 162 | 0 | `docs/operations/ROUND3P5C_OPEN_FIELD_BLOCKER_AUDIT.md` |
| 48 | 158 | 0 | `src/kairoskopion/agents/venue_family_context_builder.py` |
| 49 | 158 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/discipline_source_acquisition_v2.md` |
| 50 | 157 | 0 | `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/discipline_matching_v1.md` |

---

## Detailed runtime code breakdown (src/)

| Subsystem | Files | Insertions | Deletions | Net |
|-----------|------:|-----------:|----------:|----:|
| Agents (new organs + fixes) | 15 | 1,582 | 23 | +1,559 |
| Prompt families (new + hardened) | 19 | 2,578 | 330 | +2,248 |
| API layer (app + cases) | 2 | 577 | 0 | +577 |
| Schema (domain models) | 1 | 168 | 5 | +163 |
| Services (venue_memory + fixes) | 2 | 214 | 5 | +209 |
| Other (ids, logic) | 2 | 37 | 3 | +34 |
| **Total src/** | **41** | **5,156** | **366** | **+4,790** |

---

## Cleanup note

Branch cleanup was performed before this audit:

- **Scratch scripts deleted:** `_k3_rerun.py`, `_round3l_collect.py`, `_round3l_full_run.py`, `_round3n_rerun.py`, `_smoke2.py`, `_smoke3.py`, `_smoke3_http.py`, `_smoke3b_http.py` -- all removed from working tree (present as untracked, not committed to branch).
- **Superseded exports reverted:** earlier prompt-export iterations (P4, P5A individual files) were superseded by the final consolidated `ROUND3P5D_PROMPTS_EXPORT_ALL.md` but remain committed as historical audit trail of the iterative hardening process.
- **No force-push or history rewrite** was performed; the branch preserves full commit lineage.

---

## Summary

The branch is documentation-heavy by design: 67.9% of insertions are operation docs and prompt exports generated for owner review. The actual runtime footprint is 5,156 lines of new/modified Python (agents, prompts, API, schema, services) backed by 3,378 lines of tests across 19 test files. UI additions are minimal (316 lines). The branch is ready for merge review.
