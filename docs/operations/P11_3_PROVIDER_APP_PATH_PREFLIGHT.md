# P11_3_PROVIDER_APP_PATH_PREFLIGHT

**Date:** 2026-07-04
**Base commit:** 54a813d (main)
**Branch:** feature/p11-3-live-replay-provider-call

## Provider availability

| Check | Result |
|-------|--------|
| Shell env provider visible | NO (env vars not set in shell) |
| App/backend provider visible | YES (via .env autoload in uvicorn) |
| Intake path provider call | YES (confirmed in post-merge browser smoke) |
| Provider/model | 302.ai / gpt-4o-mini |
| Secrets printed | NO |

## Evidence

- Post-merge browser smoke confirmed live LLM calls succeed via intake:
  article_model, discipline_matcher, semantic_profiler all called 302.ai
- `.env` exists at repo root, gitignored, loaded by `_load_dotenv_if_present()`
- `_try_get_provider()` in test constructs provider from .env without polluting env
- Live network tests (4/4) passed with provider in 3.66s

## Verdict

**APP_PATH_PROVIDER: AVAILABLE** — proceed with live replay implementation.
