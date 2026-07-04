# P11.3 Live Replay Provider Call — Implementation Report

**Date:** 2026-07-04
**Branch:** `feature/p11-3-live-replay-provider-call`
**Base commit:** `54a813d` (main)
**Provider:** 302.ai / gpt-4o-mini

---

## 1. Goal

Wire the replay/rerun path to call the same live LLM provider that the intake
path already uses. Supported stage: `article_model` / `article_modeling`.

## 2. What changed

### `src/kairoskopion/services/pipeline_replay.py`

- Added `_execute_article_model_live()` — calls `ArticleModelerAgent.execute()`
  with real provider during replay. Supports `_prompt_family_override` for
  prompt overrides. Records `PipelineNode` status (`completed` / `provider_failed`)
  and `PromptRunRecord` with response excerpt, provider status, and diagnostics.
- Modified `_render_prompt_for_stage()` — accepts `llm_provider` and
  `manuscript_text` params. When both are present and stage is `article_model`,
  routes to `_execute_article_model_live()` instead of the `not_called` fallback.
- Modified `execute_replay_run()` — accepts and passes `llm_provider` and
  `manuscript_text`. Tracks `any_live_executed` flag. Returns
  `status: "live_executed"` when any node completed via live provider.

### `src/kairoskopion/api/workbench.py`

- Added `_get_llm_provider()` — constructs provider from env config (mirrors
  `cases.py` pattern).
- Added `manuscript_text: str | None = None` to `RerunStageRequest` and
  `RerunFromStageRequest`.
- `rerun_single_stage` and `rerun_from_stage` endpoints now construct provider
  and pass `llm_provider` + `manuscript_text` to `execute_replay_run`.

### `tests/test_p11_3_live_replay_provider_call.py` (NEW)

- 3 unit tests (default suite, no provider needed):
  - `test_replay_with_provider_none_still_renders_prompt`
  - `test_replay_with_override_renders_edited_prompt`
  - `test_import_does_not_load_env`
- 4 network tests (`@pytest.mark.network`, deselected by default):
  - `test_live_replay_calls_provider`
  - `test_live_replay_prompt_record`
  - `test_live_replay_with_override`
  - `test_live_diff_vs_no_provider`

## 3. Test results

| Suite | Count | Result |
|-------|-------|--------|
| Default (`pytest tests -q`) | 3120 passed, 4 deselected | ALL PASS |
| Network (`pytest -m network`) | 4 passed (3.66s) | ALL PASS |
| Typecheck (`npx tsc --noEmit`) | 0 errors | PASS |
| UI build (`npx vite build`) | clean | PASS |

## 4. Browser smoke

Full end-to-end browser smoke passed (11/11 steps). See
[P11_3_LIVE_REPLAY_BROWSER_SMOKE.md](P11_3_LIVE_REPLAY_BROWSER_SMOKE.md).

Key results:
- Live rerun: `execution_status=live_executed`, node `status=completed`,
  `provider_status=success`, `parse_status=success`
- Override applied: custom system prompt in rendered output
- Diff live vs no-provider: 2 changed fields (status, output_hash)
- No CORS errors

## 5. Env/test isolation

- Import of test module does NOT mutate `os.environ` (verified by unit test)
- `_try_get_provider()` saves/restores env vars in finally block
- Default test suite deselects network tests (no provider leakage)
- `.env` not committed, gitignored

## 6. What was NOT changed

- No new architecture or agents
- No changes to intake path
- No changes to UI components (API contract unchanged — `manuscript_text` is
  optional field)
- No P10 work
- No production deploy
- No force push

## 7. Sub-reports

- [P11_3_PROVIDER_APP_PATH_PREFLIGHT.md](P11_3_PROVIDER_APP_PATH_PREFLIGHT.md)
- [P11_3_LIVE_REPLAY_BROWSER_SMOKE.md](P11_3_LIVE_REPLAY_BROWSER_SMOKE.md)

## Verdict

**P11.3_LIVE_REPLAY_PROVIDER_CALL: PASS**
