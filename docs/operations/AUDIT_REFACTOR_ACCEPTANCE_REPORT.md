# AUDIT_REFACTOR — Acceptance Report (pre-merge gate)

Date: 2026-07-04
Scope: acceptance of `feature/audit-refactor-optimize` before merge.
No merge performed. No prod deploy. No new refactors beyond gate-mandated fixes.

## Branch / commits

- Branch: `feature/audit-refactor-optimize`
- Base: `main` @ `51672c8`
- Starting commit (gate input): `e67db58`
  "fix(audit): security, correctness, and test-isolation fixes + perf refactor"
- Note: the branch is 3 commits over main — it was forked from
  `feature/p11-3-live-provider-smoke`, so merging it also merges the two
  P11.3 commits (`5bb9089`, `d0e0568`). Diff vs main contains only
  audit/security/test changes + the P11.3 live-replay slice. No `.env`,
  no private files.
- Final commit: see git log (gate fixes committed on top of `e67db58`).

## Tests / build

| Check | Result |
|-------|--------|
| `pytest tests -q` (default, network deselected) | **PASS** — 3110+ passed (3117 after gate tests), 8 deselected, ~40–70s |
| Explicit P11: `test_p11_2_real_replay_execution.py`, `test_p11_smoke.py`, `test_pipeline_replay.py`, `test_workbench_api.py` | **PASS** — 47 passed (+4 CORS preflight guards added in gate) |
| `npx tsc --noEmit` (ui/) | **PASS** — exit 0 |
| `npx vite build` (ui/) | **PASS** — built in ~0.5s |

## CORS regression (owner's primary concern #1)

**REGRESSION CONFIRMED AND FIXED.** `e67db58` narrowed CORS to
`GET/POST/DELETE/OPTIONS`, but the UI client uses **PATCH** for prompt-override
update (`ui/src/api/client.ts:493` → `workbench.py:206`). Browser preflight
would have been rejected, breaking override editing in the P11 workbench.

Fix: `allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"]`. Headers
(`Content-Type`, `Authorization`) confirmed sufficient — no custom headers
exist in UI or API. Regression test added
(`test_workbench_api.py::TestCORSPreflight`, fails on the `e67db58` config).
Full operation matrix: AUDIT_REFACTOR_CORS_REGRESSION_CHECK.md.

## P11 browser smoke

**PASS** — real browser session (UI on :5173 → API on :8000, genuine CORS):
soft-auth login, case create, intake submit, workbench open, 19 stages listed,
override create (POST 200) + update (**PATCH 200 through real preflight**),
rerun `article_model` via UI (runs 0→4), prompt record visible with override
hash applied (`41d7db56…` ≠ base `30465d73…`), diff view renders; non-empty
diff (`article_model` changed) between override and no-override runs.
0 console errors, 0 server errors, 0 CORS rejections.
Caveat (pre-existing, also on main): `createOverride`/`updateOverride` exist
in the typed client but no UI control calls them — Prompts tab is read-only.
Details: AUDIT_REFACTOR_P11_BROWSER_SMOKE.md.

## Live-provider test isolation (owner's primary concern #2)

**PASS** on all requirements: module import mutates nothing (env diff: NONE),
`.env` parsed without `os.environ` writes and applied per-test via fixture,
file marked `network`, default run deselects (8 deselected), explicit
`-m network` run works live (**4 passed in 89s** against 302.ai), and after
the live run the previously-poisoned victim (`test_citation_ecology`) still
passes. Details: AUDIT_REFACTOR_LIVE_ENV_ISOLATION_CHECK.md.

## Security fixes

**PASS** — all five fixes (zip-slip, CaseStore traversal, malformed LLM
response, dict enum values, stale naive/aware datetime) have dedicated tests,
and each test was demonstrated to **fail on pre-fix code** (main's file
restored temporarily) and pass on the branch. Gap closed during gate: the
CaseStore traversal guard shipped in `e67db58` without a test — test added.
Details: AUDIT_REFACTOR_SECURITY_FIX_CHECK.md.

## Privacy / secrets

- No secrets committed (verified across `main...HEAD`).
- `.env` never tracked in git history.
- The 302.ai key was echoed into the audit session transcript by a subagent →
  **key rotation recommended** (precautionary). Not performed — requires
  owner's 302.ai access. Details: AUDIT_REFACTOR_SECRET_EXPOSURE_NOTE.md.

## Recommended action

**MERGE_READY** — with the gate fixes included (CORS PATCH + regression test,
CaseStore traversal test). Two follow-ups, neither blocking:

1. Rotate the 302.ai API key (owner action).
2. UI gap: no control invokes `createOverride`/`updateOverride` (pre-existing
   on main; the API and CORS path are verified working).
