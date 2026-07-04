# AUDIT_REFACTOR — CORS Regression Check

Date: 2026-07-04
Branch: `feature/audit-refactor-optimize`
Scope: verify the CORS narrowing in commit `e67db58`
(`allow_methods=["*"] → explicit list`) against actual UI client usage.

## Method

1. Inventoried every HTTP method in `ui/src/api/client.ts` and all direct
   `fetch()` calls in `ui/src/components/**` (`HumanModelView.tsx` is the
   only component with direct fetches — both GET).
2. Inventoried backend route decorators in `src/kairoskopion/api/app.py`
   and `src/kairoskopion/api/workbench.py`.
3. Cross-checked against the middleware config in `app.py`.

## Findings

**REGRESSION FOUND (fixed in this pass):** commit `e67db58` set
`allow_methods=["GET", "POST", "DELETE", "OPTIONS"]`. The UI client uses
**PATCH** for prompt-override update:

- UI: `ui/src/api/client.ts:70-76` (`patch<T>()`),
  `ui/src/api/client.ts:493` (`updatePromptOverride`)
- Backend: `src/kairoskopion/api/workbench.py:206`
  (`@router.patch("/cases/{case_id}/prompt-overrides/{override_id}")`)

A browser preflight for PATCH would have been rejected (Starlette CORS
returns 400 "Disallowed CORS method"), breaking prompt-override editing
in the P11 workbench. Fixed: PATCH added to `allow_methods`.

Custom headers: none found (no `X-*` headers in UI or API). The only
request headers the UI sets are `Content-Type` and `Authorization`
(`ui/src/api/client.ts:31-42, 151-156`) — both allowed.

`PUT`: not used by UI, no backend `@app.put`/`@router.put` routes — not allowed, correct.

## Operation matrix

| UI/API operation | HTTP method | headers | CORS allows? | status |
|------------------|-------------|---------|-------------:|--------|
| soft-auth signup/continue/logout (`/auth/*`) | POST | Content-Type | yes | PASS |
| auth me (`/auth/me`) | GET | Authorization | yes | PASS |
| case list/get (`/cases`, `/cases/{id}`) | GET | Authorization | yes | PASS |
| case create (`/cases`) | POST | Content-Type, Authorization | yes | PASS |
| case delete (`/cases/{id}`) | DELETE | Authorization | yes | PASS |
| intake submit (`/cases/{id}/intake-text`) | POST | Content-Type, Authorization | yes | PASS |
| intake file upload (`/cases/{id}/intake-file`) | POST | Authorization + multipart (browser-set) | yes | PASS |
| human view / source text (direct fetch, HumanModelView.tsx:305,336) | GET | Authorization | yes | PASS |
| workbench: list prompts/stages/runs (`/api/prompts`, `/api/pipeline/stages`, `/api/cases/{id}/replay-runs`) | GET | Authorization | yes | PASS |
| **prompt override create** (`/api/cases/{id}/prompt-overrides`) | POST | Content-Type, Authorization | yes | PASS |
| **prompt override update** (`/api/cases/{id}/prompt-overrides/{ovr}`) | **PATCH** | Content-Type, Authorization | **was NO → fixed** | PASS after fix |
| **rerun-stage** (`/api/cases/{id}/rerun-stage`) | POST | Content-Type, Authorization | yes | PASS |
| **rerun-from-stage** (`/api/cases/{id}/rerun-from-stage`) | POST | Content-Type, Authorization | yes | PASS |
| **pipeline diff** (`/api/cases/{id}/replay-runs/{a}/diff/{b}`) | GET | Authorization | yes | PASS |
| prompt record view (`/api/cases/{id}/prompt-records/...`) | GET | Authorization | yes | PASS |

## Final config

```python
allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
allow_headers=["Content-Type", "Authorization"]
```

No return to wildcard. Regression test added:
`tests/test_workbench_api.py::TestCORSPreflight` — parametrized preflight
check for every UI method + header check (would fail on the `e67db58`
config, passes after fix).

## Verdict

**FIX_APPLIED / PASS.** One real regression (PATCH) found and fixed;
everything else on the narrowed list was already correct.
