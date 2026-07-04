# P11_3_LIVE_REPLAY_BROWSER_SMOKE

**Date:** 2026-07-04
**Branch:** feature/p11-3-live-replay-provider-call
**Base commit:** 54a813d (main)

## Environment

- Backend: uvicorn on port 8000 (.env autoloaded)
- Frontend: Vite dev on port 5173
- Provider: 302.ai / gpt-4o-mini

## Smoke steps

| # | Step | Result |
|---|------|--------|
| 1 | Login as operator | PASS |
| 2 | Create case "P11.3 smoke" | PASS — `case_a3237fb9a74e` |
| 3 | Intake article text (cognitive load study) | PASS — LLM calls to 302.ai succeeded (article_model, discipline_matcher, semantic_profiler) |
| 4 | Create override for `article_modeling` | PASS — `povr_7ffc4dd3441f` |
| 5 | PATCH activate override | PASS |
| 6 | Rerun `article_model` with `manuscript_text` | PASS — `execution_status: "live_executed"` |
| 7 | Verify node status | PASS — `status=completed`, `provider_status=success`, `parse_status=success`, `output_hash=5534bedecfbbf863` |
| 8 | Verify PromptRunRecord | PASS — `provider_status=success`, `response_status=success`, `response_excerpt_or_ref` 2000 chars, override text "P11.3 LIVE REPLAY SMOKE TEST" in rendered prompt |
| 9 | Run no-provider rerun (no manuscript_text) | PASS — `prun_7c94ea44aba7`, `execution_status: "prompt_rendered"` |
| 10 | Diff live vs no-provider | PASS — 2 changed fields: `status`, `output_hash` on `article_model` |
| 11 | CORS errors in console | PASS — 0 errors |

## Key evidence

- **Live run:** `prun_8a505833553b` — `live_executed`, node completed with output hash
- **No-provider run:** `prun_7c94ea44aba7` — `prompt_rendered`, node status `prompt_rendered_needs_llm`
- **Diff:** 2/2 fields changed on `article_model` stage (status, output_hash)
- **Override applied:** `povr_7ffc4dd3441f` override ID present in node, custom system prompt in rendered output
- **No CORS errors:** browser console clean

## Verdict

**BROWSER_SMOKE: PASS** — live replay provider call works end-to-end through the UI.
