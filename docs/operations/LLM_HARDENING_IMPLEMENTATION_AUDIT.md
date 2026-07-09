# LLM Hardening: Implementation Audit

## Fallback Semantics

| Parameter | Value |
|-----------|-------|
| Primary model source | `KAIROSKOPION_LLM_MODEL` / `LLM_MODEL` env var |
| Fallback model configuration | `KAIROSKOPION_LLM_FALLBACK_MODELS` / `LLM_FALLBACK_MODELS` env var (comma-separated) |
| Retry count per model | `max_retries` (default 3, from config) |
| Timeout per attempt | `timeout_seconds` (default 90s, from `DEFAULT_TIMEOUT_MS / 1000`) |
| Statuses that retry same model | 408, 429, 500, 502, 503, 504, 529, `TimeoutError`, `URLError` (network) |
| Statuses that advance to fallback | After exhausting retries: any retryable status, `RETRIES_EXHAUSTED` |
| Statuses that fail immediately | 401, 403 (`AUTH_FAILED`); 400, 404 and other non-retryable HTTP (`PROVIDER_HTTP_ERROR`); `INVALID_JSON`; `EMPTY_RESPONSE_TEXT`; `MALFORMED_RESPONSE` |
| Final error when all models fail | `LLMError(error_code="RETRIES_EXHAUSTED")` raised to caller |

## Error Propagation Trace

### Layer: OpenAICompatProvider

- Catches `LLMError`: N/A (origin)
- Preserves `error_code`: YES (creates it)
- Can silently degrade to empty/unknown: NO (raises `LLMError` with typed code)
- Creates fake successful artifact: NO

### Layer: Agent (article_modeler, base_shell, etc.)

- Catches `LLMError`: YES (via `except Exception`)
- Preserves `error_code`: YES (`getattr(e, "error_code", None)`)
- Can silently degrade to empty/unknown: YES — deterministic fallback creates an ArticleModel with UNKNOWN fields
- Creates fake successful artifact: PARTIAL — creates a deterministic-fallback ArticleModel, but marks `extraction_attempt.fallback_used=True`, `fallback_reason="provider_error"`, `parse_status="not_attempted"`

### Layer: Service (base_shell.try_llm_call_with_outcome)

- Catches `LLMError`: YES (via `except Exception`)
- Preserves `error_code`: YES (via `type(exc).__name__` in `parse_failure_category`)
- Can silently degrade: NO — returns `LLMAttemptOutcome(ok=False)` with explicit failure fields
- Creates fake successful artifact: NO

### Layer: API (cases.py)

- Catches `LLMError`: YES (inherited from agent exception handling)
- Preserves `error_code`: YES (via `extraction_attempt` in response JSON)
- Can silently degrade: PARTIAL — API returns 200 with the deterministic fallback output, but `extraction_attempt` clearly marks failure
- Creates fake successful artifact: NO — the response contains the fallback data with explicit failure metadata

### Layer: UI (LLMAttemptBadge)

- Catches `LLMError`: N/A (receives JSON)
- Preserves `error_code`: YES — displays `parse_status`, `fallback_reason` in badge
- Can silently degrade: NO — badge shows "fallback (provider_error)" visibly
- Creates fake successful artifact: NO

**Conclusion:** Error propagation works. The deterministic fallback produces output with UNKNOWN fields (by design), but `extraction_attempt` metadata unambiguously marks the failure. The UI renders the failure status via `LLMAttemptBadge`.

## Session Log Semantics

### What one "session file" means

One `LLMSessionLog` instance = one process/API lifecycle. Created once per `get_session_log()` initialization (lazy singleton). All LLM calls during that process lifetime append to the same file.

- **NOT** one file per LLM call
- **NOT** one file per HTTP request
- **NOT** one file per PipelineRun or case
- One file per process/server lifecycle (or explicit `reset_session_log()`)

### Details

| Parameter | Value |
|-----------|-------|
| File naming | `{YYYYMMDD_HHMMSS}_{session_id}.jsonl` |
| Session identifier | Default `"api"`, or caller-specified string |
| Concurrency | Append-only writes, each `log_call()` opens/writes/closes file. Safe for sequential calls within one process. NOT safe for parallel processes writing the same file — but each process creates its own file via the timestamp+session_id naming |
| Rotation trigger | On `LLMSessionLog.__init__()` (process start) |
| Retention unit | Files, not bytes or records. Keep latest 50 by mtime |
| Fields logged | `ts`, `session`, `agent_role`, `model`, `latency_ms`, `input_tokens`, `output_tokens`, `parse_status`, `attempt`, optional: `messages_preview` (truncated 500 chars), `response_preview` (truncated 500 chars), `error_code`, `error_message` (truncated 300 chars), `fallback_model`, `extra` |
| Prompt/manuscript text logged | YES but truncated to 500 chars in `messages_preview`. This is the last message content only (user prompt), not full conversation |
| Secrets/Authorization headers | NO — the provider constructs the Authorization header in `_complete_single()` and it never reaches the log. `messages_preview` is raw user prompt text, not HTTP headers. API key env var name is stored in config but the key value is never logged |

### Privacy risk assessment

- `messages_preview`: Contains up to 500 chars of the user prompt (which includes manuscript text). This is a deliberate trade-off for debuggability. Full manuscript text is NOT logged.
- `response_preview`: Contains up to 500 chars of the LLM response content. Safe — no secrets.
- Authorization headers: Never logged. The `Authorization: Bearer {key}` header is constructed in `_complete_single()` and never passed to `log_call()`.
- Log directory: `.kairoskopion/logs/llm_sessions/` — covered by `.gitignore` entry for `.kairoskopion/`.

## agent_role Propagation

The `agent_role` parameter is accepted by `OpenAICompatProvider.complete()` as a keyword-only argument with default `""`. The `LLMProvider` protocol does not include it — this is deliberate to maintain backward compatibility.

### Current state

All existing callers use the protocol signature (no `agent_role`), so logs record `agent_role=""`. The logging still captures model, latency, errors, and parse status — agent identification comes from the `LLMAttemptMetadata` in the agent layer instead.

### Why not wired to all callers

Adding `agent_role` to the protocol would break the interface contract and require updating ~30 callers and all mock providers in tests. The session log already captures enough to diagnose issues (model, timing, error codes). Agent-level identification is handled by the `LLMAttemptMetadata`/`LLMAttemptOutcome` layer above the provider.

## Defects Found and Fixed

1. **HTTP 408 not retryable** — Request Timeout should retry. Added to retryable set.
2. **HTTP 504 not retryable** — Gateway Timeout should retry. Added to retryable set.
3. **FIFO rotation negative-index bug** — `len(files) - max_files` could be negative, causing `files[:-N]` to delete files unexpectedly. Fixed with `max(0, ...)`.
