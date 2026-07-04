# AUDIT_REFACTOR — Clean Merge Report

Date: 2026-07-04
No merge performed. No prod deploy. No force push. No new refactors.

## Provenance

- Source (polluted) branch: `feature/audit-refactor-optimize`, final commit
  `ef39b5b`. Not mergeable as-is: carried two unrelated P11.3 commits.
- **Stray P11.3 commits excluded:** `5bb9089` (live LLM provider replay:
  workbench.py +20, pipeline_replay.py +105, live smoke test +265, preflight
  doc) and `d0e0568` (provider preflight doc).
- Clean branch: `feature/audit-refactor-optimize-clean` (from `main` @
  `51672c8`).
- Method: cherry-pick `e67db58` → `6b03f71` (one predicted modify/delete
  conflict on `tests/test_p11_3_live_provider_replay_smoke.py`, resolved by
  excluding the file — it is a P11.3 artifact absent on main; its isolation
  fix stays with the P11.3 branch), cherry-pick `ef39b5b` → `4d2f45c`
  (clean). Plan and diff audit: AUDIT_REFACTOR_CLEAN_BRANCH_PLAN.md.
- Clean diff vs main: 21 files, +571/−105; zero P11.3 / `.env` / runtime /
  P10 content (grep-verified).

## Gate results on the clean branch

| Check | Result |
|-------|--------|
| `pytest tests -q` (exclusive run) | **PASS** — 3117 passed, 4 deselected, 44s |
| `npx tsc --noEmit` | **PASS** |
| `npx vite build` | **PASS** (~0.3s) |
| Explicit P11 tests (p11_2 real replay, p11 smoke, pipeline_replay, workbench_api) | **PASS** — 52 passed |
| CORS regression tests (`TestCORSPreflight`) | **PASS** — 5 passed |
| Live env isolation | **PASS** — the P11.3 live smoke file does not exist on this branch (no import-time env mutation possible by construction); default run deselects the 4 legacy `network` tests; `-m network` collects only those 4 |
| P11 browser smoke (UI :5173 → API :8000) | **PASS** — login, case create, intake (`article_model_built: true`), 18 stages, override create 200, **PATCH 200** (activate + archive), rerun ×2, prompt record 200 (`article_modeling`), diff 200 **non-empty** (`article_model` changed); 0 console/server/CORS errors |
| Security fix tests | **PASS** — all five present on the clean branch and passing (fail-on-old-code demonstrated during the prior gate; underlying fixes identical by cherry-pick) |

## Known pre-existing issue (not introduced, not blocking)

The 4 legacy `network`-marked tests
(`test_venue_pool_discovery.py::TestLiveNetworkDiscovery`) fail identically
on `main` (live OpenAlex/DOAJ responses drifted). Deselected by default;
out of audit scope.

## Transient noise during gate (resolved)

One background full-suite run showed a single auth-test failure
(`test_continue_unknown_email_returns_404`) — caused by this gate running
concurrent pytest processes sharing a data dir. Passes in isolation (21
passed) and in the exclusive full run. Not a branch defect.

## Secrets

No secrets committed (diff-verified). `.env` never tracked. **302.ai key
rotation recommended** (key was echoed into an assistant session transcript
during the original audit) — owner action; see
AUDIT_REFACTOR_SECRET_EXPOSURE_NOTE.md.

## Follow-ups (non-blocking)

1. Rotate 302.ai API key.
2. When P11.3 (`feature/audit-refactor-optimize` or its parent) is merged
   later, its live smoke test file already contains the env-isolation fix —
   do not merge the pre-fix version.
3. UI gap (pre-existing on main): no control invokes
   `createOverride`/`updateOverride` in the workbench Prompts tab.

## Recommendation

**CLEAN_MERGE_READY**
