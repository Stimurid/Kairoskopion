# AUDIT_REFACTOR — P11 Browser Smoke (after CORS hardening)

Date: 2026-07-04
Branch: `feature/audit-refactor-optimize` (+ CORS PATCH fix applied during this gate)
Setup: backend `uvicorn` on 127.0.0.1:8000 (isolated `KAIROSKOPION_DATA_DIR`,
`KAIROSKOPION_NO_DOTENV=1` — deterministic mode, no live LLM spend),
UI Vite dev server on 127.0.0.1:5173. Real cross-origin browser traffic,
so CORS preflights were genuinely exercised.

## Steps and results

| # | Step | Result | Evidence |
|---|------|--------|----------|
| 1 | soft-auth login (display name only) | PASS | POST /auth/signup 200; header shows "SmokeTester"; token in localStorage |
| 2 | create case | PASS | POST /cases 200 → `case_ef0e9e6eeb26`; intake text submitted (case stage → intake) |
| 3 | open PromptPipelineWorkbench | PASS | Workbench panel rendered; tabs Stages/Runs/Compare/Prompts(19)/Overrides |
| 4 | list runs/stages | PASS | 19 pipeline stages listed with producer + prompt family; Runs tab lists runs |
| 5 | create prompt override | PASS* | POST /api/cases/{id}/prompt-overrides → 200, `povr_7f4ddb46e1f0` |
| 6 | update prompt override | PASS* | **PATCH** …/prompt-overrides/{id} → **200** from browser origin 5173 (real CORS preflight); notes + status updated; second PATCH (archive) also 200 |
| 7 | rerun `article_model` | PASS | UI "Stage" button on Article Modeling row → POST /rerun-stage 200; Runs (0)→(1)→(3); node status `prompt_rendered_needs_llm` (honest no-provider status) |
| 8 | open prompt record | PASS | Node click → Prompt Record panel: `Family: article_modeling · Hash: 41d7db56c925da8e` — hash differs from base prompt `30465d733c486759`, i.e. **override was actually applied** |
| 9 | compare old/new runs | PASS | Compare tab renders per-stage diff table; override-run vs archived-override-run diff → `changedStages: [article_model]` (GET /pipeline-diff 200, non-empty) |

\* Steps 5–6 caveat: the typed client functions `createOverride`/`updateOverride`
exist in `ui/src/api/client.ts:482-493`, but **no UI component calls them** —
the Prompts tab is read-only and the Overrides tab says "Create one from the
Prompts tab" without a create control. This is a pre-existing UI gap (present
on main, not introduced by the audit branch). The smoke exercised the exact
requests the client functions issue, from the real browser origin, so the
CORS/API path is verified; the missing UI affordance is logged as a follow-up.

## Error sweep

- Browser console errors: **0**
- Backend server errors: **0**
- Failed network requests: only the expected pre-login `GET /auth/me → 401`
- No CORS preflight rejections anywhere in the session (all OPTIONS → 200)

## CORS-specific proof

The PATCH request in step 6 is the operation that was broken by the original
`e67db58` CORS narrowing (PATCH missing from `allow_methods`). After the fix
(`GET, POST, PATCH, DELETE, OPTIONS`) the browser preflight passes and the
request succeeds — verified live, not just via TestClient.

## Verdict

**PASS** — with two notes:
1. CORS PATCH regression existed in `e67db58` and was fixed during this gate
   (see AUDIT_REFACTOR_CORS_REGRESSION_CHECK.md).
2. Override create/update has no UI control (pre-existing gap, main has it too);
   API + CORS path fully verified from browser context.
