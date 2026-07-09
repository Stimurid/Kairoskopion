# LLM Hardening — Post-Merge Acceptance Report

**Date:** 2026-07-09
**Starting main commit:** `987fd7f`
**Feature commit:** `4f55c5d`
**Merge commit:** `a63ebab`
**Merge message:** `merge: harden LLM timeouts fallbacks and provider diagnostics`

---

## Commits merged

| Commit | Message |
|---|---|
| `27b60d1` | fix: harden LLM timeouts fallbacks and session logging |
| `4f55c5d` | fix: expose LLM fallback attempts and bound provider logs |

38 files changed, 2781 insertions, 31 deletions.

---

## Post-merge deterministic gates

| Gate | Result |
|---|---|
| pytest tests -q | 3189 passed, 8 deselected, 0 failed |
| Focused hardening tests | 69 passed (19 + 8 + 42), 11 subtests |
| TypeScript typecheck | PASS |
| Vite build | PASS (377 kB JS, 102 kB CSS) |

### Deterministic checks

| Check | Result |
|---|---|
| Primary success does not invoke fallback | PASS (test_primary_called_once_no_fallback) |
| Retryable primary error advances to fallback | PASS (test_429/503/timeout/network_error) |
| 401/403 terminate without fallback | PASS (test_401/403_immediate_error_no_fallback) |
| All models exhausted → typed failure | PASS (test_all_models_exhausted_raises_retries_exhausted) |
| No fake ArticleModel on failure | PASS (test_exhaustion_no_fake_article_model, test_auth_failure_no_fake_article_model_change) |
| Attempt history ordered | PASS (test_attempt_metadata_present_on_success) |
| Effective model traceable | PASS (test_fallback_metadata_propagated) |
| Agent role non-empty (22/22 call sites) | PASS |
| Diagnostic log rotates by size | PASS (test_rotation_triggers_on_max_bytes) |
| Diagnostic log rotates by file count | PASS (test_rotation_keeps_exactly_max) |
| No secrets in logs | PASS (test_no_api_key_in_log) |
| No full manuscript/prompt in logs | PASS (test_messages_preview_truncated, test_response_preview_truncated) |
| P11 API exposes attempt_metadata | PASS (8 tests in test_p11_replay_trace.py) |

---

## Live app-path smoke

| Check | Result |
|---|---|
| Provider available via app | YES |
| Model name | gpt-4o-mini |
| Key present (boolean) | YES |
| Base URL provider | 302.ai |
| Normal intake | PASS (article_model built, parse_status=parsed_ok) |
| Live P11 replay | PASS |

### P11 replay attempt_metadata (live)

| Field | Value |
|---|---|
| requested_model | gpt-4o-mini |
| effective_model | gpt-4o-mini |
| fallback_used | False |
| attempt_count | 1 |
| provider_status | ok |
| parse_status | parsed_ok |
| agent_role | article_model_replay |
| final_error_code | None |
| attempts | 1 attempt, model=gpt-4o-mini, transition=success |

### Provider diagnostic JSONL (live)

| Check | Result |
|---|---|
| Log files present | 6 files |
| process_file field (not session) | YES |
| agent_role in latest record | article_model_replay |
| Model in log | gpt-4o-mini |
| No API key in log | YES |
| No Authorization header | YES |
| No full manuscript | YES |
| No full prompt | YES |
| Record size bounded | 347 chars |

---

## Workbench UI smoke

| Check | Result |
|---|---|
| Effective model in API data | YES (gpt-4o-mini) |
| Attempt count in API data | YES (1) |
| Agent role in API data | YES (article_model_replay) |
| Attempt list in API data | YES (1 attempt) |
| TypeScript types clean | YES |
| LLMAttemptBadge renders model/count/error | YES (code verified) |
| Visual rendering in browser | NOT DIRECTLY OBSERVABLE (preview server does not load .env) |
| Fallback state rendering | NO REAL FALLBACK RUN (deterministic tests cover code path) |
| No secrets in UI | PASS (no console errors, no raw payloads) |

**Verdict:** `PARTIAL_NO_REAL_FALLBACK`

---

## Real fallback status

`REAL_MULTI_MODEL_FALLBACK_NOT_CONFIGURED`

`KAIROSKOPION_LLM_FALLBACK_MODELS` is empty in `.env`.
Primary provider (gpt-4o-mini via 302.ai) is available and working.
Deterministic fallback tests (42 tests) cover multi-model fallback code paths.

---

## Excluded unrelated files

| Category | Present in diff | Committed |
|---|---|---|
| .env | NO | NO |
| API keys | NO | NO |
| Provider diagnostic JSONL | NO | NO |
| Case/runtime data | NO | NO |
| P10 | NO | NO |
| Engelbart | NO | NO |
| Seed registry outputs | NO | NO |
| Unrelated reports | NO | NO |

---

## Production deploy status

NOT DEPLOYED — by spec constraint.

---

## Summary

| Item | Value |
|---|---|
| Starting main | `987fd7f` |
| Feature commit | `4f55c5d` |
| Merge commit | `a63ebab` |
| Default tests | 3189 passed |
| Focused tests | 69 passed, 11 subtests |
| TypeScript | PASS |
| Build | PASS |
| Live provider | YES (gpt-4o-mini, 302.ai) |
| Live intake | PASS |
| Live P11 replay | PASS |
| P11 attempt trace | PASS (all 9 fields present) |
| Workbench UI | PARTIAL_NO_REAL_FALLBACK |
| Diagnostic log | PASS (bounded, private, correct terminology) |
| Real fallback | REAL_MULTI_MODEL_FALLBACK_NOT_CONFIGURED |
| Secrets committed | NO |
| Unrelated files committed | NO |
| Prod deploy | NOT DEPLOYED |

**RESULT:** `LLM_HARDENING_MERGED_PARTIAL_NO_REAL_FALLBACK`
