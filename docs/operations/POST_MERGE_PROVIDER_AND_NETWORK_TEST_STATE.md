# POST_MERGE_PROVIDER_AND_NETWORK_TEST_STATE

**Date:** 2026-07-04
**Main commit:** 828a983

## .env file

- **Present:** yes (repo root)
- **Gitignored:** yes (2 entries in .gitignore)
- **Keys defined:** KAIROSKOPION_LLM_PROVIDER, KAIROSKOPION_LLM_MODEL, KAIROSKOPION_LLM_BASE_URL, KAIROSKOPION_LLM_API_KEY, KAIROSKOPION_LLM_TIMEOUT_MS
- **Values:** not printed (secrets policy)

## Autoload mechanism

- `_load_dotenv_if_present()` in `src/kairoskopion/api/app.py:29`
- Called at module load time (line 59)
- Guarded by `KAIROSKOPION_NO_DOTENV` env var — if set, skips loading
- Under pytest, autoload skipped (test fixtures set `KAIROSKOPION_NO_DOTENV=1`)

## Shell env (outside uvicorn)

- `KAIROSKOPION_LLM_MODEL`: not set
- `KAIROSKOPION_LLM_BASE_URL`: not set
- `KAIROSKOPION_LLM_API_KEY`: not set
- `KAIROSKOPION_DATA_DIR`: not set
- `KAIROSKOPION_NO_DOTENV`: not set

LLM env vars are NOT leaked into the shell. The .env is only loaded by uvicorn via the autoload function.

## Test isolation

- `tests/test_workbench_api.py`: sets `KAIROSKOPION_NO_DOTENV=1` via monkeypatch
- `tests/test_p11_smoke.py`: sets `KAIROSKOPION_NO_DOTENV=1` via monkeypatch
- All 3117 tests pass without .env contamination

## Network test state

- No tests make real HTTP calls to 302.ai on main (P11.3 live tests are on feature branch only)
- Adapter tests use mock/fixture mode
- Browser smoke (manual) confirmed 302.ai reachable via uvicorn autoload

## Verdict

**PROVIDER_AND_NETWORK_TEST_STATE: PASS** — .env present but gitignored, autoload isolated from tests, no secrets in env.
