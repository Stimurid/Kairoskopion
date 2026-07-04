# POST_MERGE_P11_2_WORKBENCH_SMOKE

**Date:** 2026-07-04
**Main commit:** 828a983
**Case ID:** case_2d8e3d632598

## Browser smoke path (11 steps)

| # | Step | Method | Status | Detail |
|---|------|--------|--------|--------|
| 1 | Login | POST /auth/signup | ✓ 200 | Display name "Operator", token issued |
| 2 | Create case | POST /cases | ✓ 200 | case_2d8e3d632598 created |
| 3 | Intake article text | POST /cases/{id}/intake/text | ✓ 200 | LLM calls to 302.ai/gpt-4o-mini succeeded |
| 4 | Open Pipeline Workbench | GET /api/pipeline-stages, /api/prompts | ✓ 200 | 18 stages, 19 prompt families |
| 5 | Create prompt override | POST /api/cases/{id}/prompt-overrides | ✓ 200 | povr_51db342214a1 (article_modeling) |
| 6 | PATCH override to active | PATCH /api/cases/{id}/prompt-overrides/{id} | ✓ 200 | status: draft → active |
| 7 | Rerun article_model | POST /api/cases/{id}/rerun-stage | ✓ 200 | prun_635c3f9e1616, execution_status: prompt_rendered |
| 8 | Open prompt record | GET /api/.../nodes/{id}/prompt | ✓ 200 | override applied, system prompt contains "SMOKE TEST OVERRIDE" |
| 9 | Compare runs (diff) | GET /api/cases/{id}/pipeline-diff | ✓ 200 | 2 diff entries |
| 10 | Diff non-empty | — | ✓ | article_model: prompt_version_hash changed, prompt_override_id differs |
| 11 | No CORS errors | Console check | ✓ | Zero console errors, all OPTIONS preflight → 200 |

## Key observations

- **LLM integration:** 302.ai/gpt-4o-mini live calls succeed for article modeling, semantic profiling, discipline matching
- **CORS:** All methods (GET, POST, PATCH, DELETE, OPTIONS) work from localhost:5173 → localhost:8000
- **P11.2 replay:** `prompt_rendered_needs_llm` status correct (no LLM call on replay — main has no live replay path)
- **Override application:** Confirmed via PromptRunRecord — edited system prompt rendered, override_id tracked
- **Diff:** Override run vs clean run shows 2 changed fields: `prompt_version_hash`, `prompt_override_id`
- **UI rendering:** Workbench tabs (Pipeline Stages, Runs, Compare, Prompts, Overrides) all render; minor UI cache staleness on tab counters after API-created runs (cosmetic, not functional)

## CORS preflight audit (from network log)

All preflight OPTIONS requests returned 200:
- `/cases`, `/cases/{id}`, `/cases/{id}/intake/text`
- `/api/pipeline-stages`, `/api/prompts`
- `/api/cases/{id}/pipeline-runs`, `/api/cases/{id}/prompt-overrides`

No CORS blocks observed. PATCH method confirmed allowed.

## Verdict

**P11_2_WORKBENCH_BROWSER_SMOKE: PASS**
