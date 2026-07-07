# LLM Hardening: Acceptance Report

## Summary

| Field | Value |
|-------|-------|
| Branch | `feature/llm-timeout-fallback-session-logging` |
| Base commit | `987fd7f` (main) |
| Date | 2026-07-07 |

## Files Changed

### Modified (6)
- `src/kairoskopion/agents/article_modeler.py` — dict extraction from LLM enum fields
- `src/kairoskopion/llm/config.py` — 90s timeout, fallback_models, env parsing
- `src/kairoskopion/llm/json_repair.py` — null coercion for required non-nullable fields
- `src/kairoskopion/llm/openai_compat.py` — fallback queue, session logging, typed errors, retryable codes
- `tests/test_article_model_json_hardening.py` — updated for coercion + dict extraction
- `tests/test_round3p7_llm_smoke.py` — updated AUTH_FAILED error code

### New (4)
- `src/kairoskopion/llm/session_log.py` — FIFO session logging module
- `tests/test_llm_session_log_and_fallback.py` — 42 acceptance tests
- `docs/operations/LLM_HARDENING_DIRTY_STATE_INVENTORY.md`
- `docs/operations/LLM_HARDENING_IMPLEMENTATION_AUDIT.md`
- `docs/operations/LLM_HARDENING_ACCEPTANCE_REPORT.md`

## Original Problem

Russian academic text submitted through UI produced `parse_status: schema_validation_failed` with all fields UNKNOWN. Root cause: `_schema_required_present` rejected null values for non-nullable required array fields (e.g. `protected_core_candidate: null`), and LLM returned dict-valued enum fields that couldn't be extracted.

Secondary: 30s timeout too short for complex Russian text; no fallback when primary model fails; no session logging for debugging; no typed errors surfacing to the user.

## Session Definition

One session file = one process lifecycle. All LLM calls within that process append to the same JSONL file. FIFO retains the latest 50 files by mtime. File naming: `{YYYYMMDD_HHMMSS}_{session_id}.jsonl`.

## Fallback Policy Table

| HTTP Status | Policy | Retry same model? | Advance to fallback? | Terminal? |
|-------------|--------|-------------------|---------------------|-----------|
| 401, 403 | AUTH_FAILED | NO | NO | YES (immediate) |
| 400, 404 | PROVIDER_HTTP_ERROR | NO | NO | YES |
| 408 | Retryable | YES | YES (after retries) | NO |
| 429 | Retryable | YES | YES (after retries) | NO |
| 500 | Retryable | YES | YES (after retries) | NO |
| 502 | Retryable | YES | YES (after retries) | NO |
| 503 | Retryable | YES | YES (after retries) | NO |
| 504 | Retryable | YES | YES (after retries) | NO |
| 529 | Retryable | YES | YES (after retries) | NO |
| TimeoutError | Retryable | YES | YES (after retries) | NO |
| URLError (network) | Retryable | YES | YES (after retries) | NO |
| Invalid JSON | INVALID_JSON | NO | NO | YES |
| Empty response | EMPTY_RESPONSE_TEXT | NO | NO | YES |
| Malformed (no choices) | MALFORMED_RESPONSE | NO | NO | YES |

## Error Propagation Result

Provider -> Agent -> API -> UI chain is intact. Each layer:
- Provider: raises `LLMError` with typed `error_code`
- Agent: catches `Exception`, creates `LLMAttemptMetadata` with `fallback_used=True`, `fallback_reason`, `parse_status="not_attempted"`
- API: returns 200 with deterministic fallback + `extraction_attempt` metadata
- UI: `LLMAttemptBadge` displays "fallback (provider_error)" visibly

## Trace/Workbench Visibility

`extraction_attempt` in API response contains: `parse_status`, `fallback_used`, `fallback_reason`, `llm_model`, `llm_latency_ms`. The UI's `LLMAttemptBadge` and `HumanDossierView` render these fields. P11 Workbench trace is NOT directly updated by session_log — the session log is provider-local JSONL for operator debugging, while the agent-layer `LLMAttemptMetadata` is the trace that reaches the API and UI.

## Log Privacy Result

- API keys: NEVER logged (Authorization header constructed after log point)
- Manuscript text: truncated to 500 chars in `messages_preview`
- Response text: truncated to 500 chars in `response_preview`
- Error messages: truncated to 300 chars
- Log directory: `.kairoskopion/logs/llm_sessions/` — covered by `.gitignore`
- No full prompt templates or system prompts logged
- No stack traces logged

## Deterministic Scenario Results

| Scenario | Tests | Result |
|----------|-------|--------|
| A. Primary succeeds | 2 | PASS |
| B. Primary retryable, fallback succeeds | 5 (429, 503, timeout, network, log verification) | PASS |
| C. Authentication failure | 4 (401, 403, no artifact, agent propagation) | PASS |
| D. All models fail | 3 (exhaustion, order, no fake model) | PASS |
| HTTP status policy (408/429/500/502/503/504/529/400/404/401/403) | 7 tests, 11 subtests | PASS |
| Session log semantics | 5 | PASS |
| FIFO rotation | 5 | PASS |
| Log privacy | 5 | PASS |
| Config | 3 | PASS |
| LLMError structure | 3 | PASS |
| **Total acceptance tests** | **42 tests + 11 subtests** | **ALL PASS** |

## Live Smoke Results

Not performed in this session. Live smoke requires active provider credentials and would test against production API. Deterministic tests fully cover the fallback/retry/error logic using fake transports. Live validation should be done separately with the existing safe provider configuration.

## Test Results

| Suite | Count | Result |
|-------|-------|--------|
| Default (no network) | 3162 passed | PASS |
| Network tests | 4 failed (pre-existing venue discovery failures, unrelated) | PRE-EXISTING |
| Focused hardening tests | 42 passed + 11 subtests | PASS |
| TypeScript typecheck | 0 errors | PASS |
| Vite build | success (376 KB JS, 102 KB CSS) | PASS |

## Remaining Limitations

1. **`agent_role` not propagated to provider** — all provider-level log records show `agent_role=""`. Agent identification happens at the `LLMAttemptMetadata` layer. Adding `agent_role` to the provider protocol would require updating ~30 callers.
2. **Session log is process-local** — P11 Workbench and PipelineRun see attempt metadata via the agent layer, not the session log. The session log is for operator debugging.
3. **Live smoke not performed** — would require active API credentials.
4. **Parallel process safety** — each process creates its own log file (unique timestamp+session_id), so no corruption. But if two processes use the same session_id within the same second, filenames could collide (extremely unlikely).

## Owner Answers

| Question | Answer |
|----------|--------|
| Dirty main isolated | YES |
| Primary success preserved | YES |
| Fallback actually works | YES (deterministic proof) |
| Effective model traceable | YES (via `LLMResponse.model` and `extraction_attempt.llm_model`) |
| Auth failure avoids fallback | YES |
| All-model failure visible to user | YES (via `LLMAttemptBadge` "fallback (provider_error)") |
| Fake success prevented | YES (deterministic fallback has `fallback_used=True`, `parse_status="not_attempted"`) |
| Session definition coherent | YES (one file per process lifecycle) |
| FIFO/concurrency safe | YES (sequential within process, separate files across processes) |
| Secrets absent from logs/git | YES |
| P11 replay unaffected | YES (no changes to replay path) |

## Merge Recommendation

`LLM_HARDENING_MERGE_READY`
