# LLM Hardening: Dirty State Inventory

## Provenance

| Field | Value |
|-------|-------|
| Base commit | `987fd7f` (main) |
| Original branch | `main` |
| Feature branch | `feature/llm-timeout-fallback-session-logging` |
| Isolation date | 2026-07-07 |

## Modified tracked files (6)

| File | Change |
|------|--------|
| `src/kairoskopion/agents/article_modeler.py` | Dict extraction from LLM enum fields |
| `src/kairoskopion/llm/config.py` | Timeout 30s->90s, fallback_models field |
| `src/kairoskopion/llm/json_repair.py` | `_coerce_required_nulls()` for null arrays/strings |
| `src/kairoskopion/llm/openai_compat.py` | Fallback queue, session logging, typed LLMError, retryable codes |
| `tests/test_article_model_json_hardening.py` | Updated expectations for coercion + dict extraction |
| `tests/test_round3p7_llm_smoke.py` | Updated 401 error code: AUTH_FAILED |

## New untracked files (2 relevant)

| File | Purpose |
|------|---------|
| `src/kairoskopion/llm/session_log.py` | FIFO session logging module |
| `tests/test_llm_session_log_and_fallback.py` | 42 acceptance tests |

## Excluded untracked files (not staged)

| File | Reason |
|------|--------|
| `data/seed_registry/education_ai_russia/p10_harvest/` | P10 output data |
| `data/seed_registry/p73_harvest_output/` | P73 harvest output |
| `docs/operations/ROUND3K3_LIVE_ARTICLE_RERUN_REPORT.md` | Prior operation report |
| `docs/operations/ROUND3L_FULL_LIVE_ARTICLE_RUN_REPORT.md` | Prior operation report |
| `docs/operations/ROUND3L_LIVE_USER_RUN_REPORT.md` | Prior operation report |
| `docs/operations/ROUND3O_FULL_BUILD_PLAN.md` | Prior operation report |
| `docs/operations/ROUND3O_WORKFLOW_SPLIT_AUDIT.md` | Prior operation report |

## Initial reported test result

- Full suite: 3129 passed (before additional tests)
- After acceptance tests added: 3162 passed, 0 failed
