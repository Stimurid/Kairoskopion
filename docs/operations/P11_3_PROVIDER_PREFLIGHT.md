# P11.3 Provider Preflight Check — RECOVERED

**Date:** 2026-07-04
**Branch:** `feature/p11-3-live-provider-smoke`
**Base commit:** `51672c8` (main, P11.2 merged)

## Initial False Negative

Initial check ran `python -c "import os; print(os.environ.get('KAIROSKOPION_LLM_MODEL'))"` in bare shell.
This returned `None` because the shell env has no LLM vars set — the project
uses `.env` autoload in `app.py:_load_dotenv_if_present()` at uvicorn startup.

## Recovery: .env Found

File: `.env` at repo root (239 bytes, dated 2026-06-14, gitignored).

| Env Variable | Status |
|-------------|--------|
| `KAIROSKOPION_LLM_MODEL` | SET (gpt-4o-mini) |
| `KAIROSKOPION_LLM_BASE_URL` | SET (https://api.302.ai/v1) |
| `KAIROSKOPION_LLM_API_KEY` | SET (51 chars, not printed) |

## Autoload Mechanism

`src/kairoskopion/api/app.py` lines 29-57: `_load_dotenv_if_present()` reads
`.env` at module import time. Skips under `pytest` (checks `PYTEST_CURRENT_TEST`).
This is why `uvicorn` sees the vars but bare `python -c` does not.

## Programmatic Verification

```python
# After manual dotenv load:
from kairoskopion.llm.config import LLMConfig
cfg = LLMConfig.from_env()
# cfg.model = "gpt-4o-mini"
# cfg.base_url = "https://api.302.ai/v1"
# cfg.api_key = "sk-..." (51 chars)
# cfg.is_llm_available() = True
```

## Live Smoke Result

4/4 live replay tests passed (81.56s total, real API calls to 302.ai):

- `test_live_replay_produces_completed_node` — PASS
- `test_live_replay_creates_prompt_run_record` — PASS
- `test_live_replay_with_override` — PASS
- `test_diff_live_vs_no_provider` — PASS

## Verdict

| Question | Answer |
|----------|--------|
| Provider configured? | **YES** |
| Provider/model name | 302.ai / gpt-4o-mini |
| API key present? | **YES** (51 chars) |
| LLM available? | **YES** |
| Live replay works? | **YES** |

No secret values printed or committed.

## Code Changes

1. `src/kairoskopion/services/pipeline_replay.py` — `_render_prompt_for_stage` now
   accepts `llm_provider` + `manuscript_text`; new `_execute_article_model_live`
   function calls ArticleModelerAgent with real provider when available.

2. `src/kairoskopion/api/workbench.py` — rerun-stage and rerun-from-stage endpoints
   now accept optional `manuscript_text` in request body; construct LLM provider
   from env config and pass to `execute_replay_run`.

3. `tests/test_p11_3_live_provider_replay_smoke.py` — 4 live smoke tests (guarded,
   skip when no .env).

## Result

`P11_3_LIVE_PROVIDER_SMOKE_PASS`
