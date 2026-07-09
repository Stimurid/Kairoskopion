# LLM Hardening Repair — Acceptance Report

**Branch:** `feature/llm-timeout-fallback-session-logging`
**Base:** main @ `987fd7f`
**Date:** 2026-07-07
**Test suite:** 3181 passed, 8 deselected, 0 failed

---

## Defects addressed

### 1. "Session log" terminology — FIXED

**Problem:** Code, log fields, and docstrings used "session log" — misleading
when the system has no user sessions (JSONL per-process, not per-login).

**Fix:**
- `session_log.py` docstring: "Provider diagnostic log — per-process JSONL"
- Log record field: `session` → `process_file`
- Warning message: "Failed to write provider diagnostic log"
- Constants: `MAX_SESSION_FILES` → `MAX_PROCESS_FILES`
- Class docstring explains "session" means backend process lifecycle

**Size rotation added:**
- `DEFAULT_MAX_BYTES = 10 MB` per file (env: `KAIROSKOPION_LLM_LOG_MAX_BYTES`)
- `MAX_PROCESS_FILES = 50` (env: `KAIROSKOPION_LLM_LOG_MAX_FILES`)
- `_rotate_if_needed()` creates new file with `_N` suffix when size exceeded
- FIFO rotation on new file creation

### 2. Structured attempt metadata — FIXED

**Problem:** `LLMAttemptMetadata` lacked fields to track which model was
requested vs. which actually answered, how many attempts were made, and
what happened at each attempt.

**Fix — new dataclass `LLMModelAttempt`:**
```
attempt_index, model, agent_role, started_at, latency_ms,
provider_status, response_status, parse_status,
error_code, retryable, transition
```
With `to_dict()` / `from_dict()` round-trip.

**Fix — `LLMAttemptMetadata` extended:**
- `requested_model: str | None`
- `effective_model: str | None`
- `attempt_count: int`
- `attempts: list[LLMModelAttempt]`
- `final_error_code: str | None`
- `agent_role: str`

All three factory methods (`parse_ok`, `fallback`, `not_attempted`) accept
the new fields. `to_dict()` / `from_dict()` serialize/deserialize them.

**Fix — `LLMResponse` extended:**
- `requested_model`, `effective_model`, `fallback_used`, `attempt_count`,
  `attempts`, `agent_role`

**Fix — `OpenAICompatProvider.complete()` rewritten:**
- `all_attempts: list[LLMModelAttempt]` collector
- `_record_attempt()` helper called on every success/error path
- Attempts attached to both `LLMResponse` and `LLMError` (via monkey-patch)
- Transitions: "success", "retry", "exhausted", "terminal"

### 3. `agent_role` propagation — FIXED

**Problem:** `agent_role` was always empty for all callers.

**Fix:**
- `LLMProvider` protocol: `agent_role: str = ""` keyword arg
- `base_shell.py`: passes `agent_role` from prompt family or explicit arg
- All 19 agent files updated with explicit `agent_role="<role_id>"`:
  - article_modeler, semantic_profiler, discipline_matcher, venue_profiler,
    citation_ecology, compliance_assessor, depth_recommendation,
    disciplinary_mapper, discipline_intent_parser, discipline_seeder,
    discipline_source_acquisition, fit_assessor (2 calls),
    input_classifier, mismatch_narrator, rewrite_planner,
    venue_family_context_builder, venue_funnel_planner, venue_matrix_assessor
- `cases.py` P11 replay: `agent_role="article_model_replay"`

### 4. Attempt history visible in P11 trace — FIXED

**Problem:** `classify_llm_response()` ignored new response fields.

**Fix:**
- `classify_llm_response()` now extracts `requested_model`, `effective_model`,
  `attempt_count`, `attempts`, `agent_role`, `fallback_used` from response
- All three code paths (fast, repair, fallback) propagate these to
  `LLMAttemptMetadata`
- `cases.py` error handlers extract `attempts` and `error_code` from caught
  exceptions and pass to `LLMAttemptMetadata.fallback()`
- P11 replay returns `attempt_metadata` dict in response payload

### 5. UI typed provider failures — FIXED

**Problem:** `ExtractionAttempt` type lacked fields for attempt history.
`LLMAttemptBadge` showed only `parse_status` and `fallback_reason`.

**Fix — `domain.ts`:**
- New `LLMModelAttemptRecord` interface
- `ExtractionAttempt` extended: `requested_model`, `effective_model`,
  `attempt_count`, `attempts`, `final_error_code`, `agent_role`

**Fix — `LLMAttemptBadge.tsx`:**
- Displays effective model name
- Shows attempt count when > 1
- Shows error code on fallback (e.g. `[AUTH_FAILED]`)
- Tooltip includes: requested/effective model, attempt count, agent role,
  error code

---

## Test evidence

### New tests: `tests/test_llm_hardening_repair.py` (19 tests)

| Test class | Count | What it proves |
|---|---|---|
| `TestLLMModelAttemptRoundTrip` | 2 | to_dict/from_dict identity, defaults |
| `TestLLMAttemptMetadataNewFields` | 4 | parse_ok/fallback/not_attempted carry new fields, round-trip |
| `TestClassifyLLMResponseBridge` | 3 | classify_llm_response propagates attempt fields in all 3 paths |
| `TestErrorPropagationThroughAgent` | 3 | Scenarios A (auth), B (exhausted), C (success with role) |
| `TestSizeRotation` | 3 | Rotation triggers, env vars respected |
| `TestAgentRolePropagation` | 2 | article_modeler and fit_assessor pass agent_role |
| `TestProviderDiagnosticLogTerminology` | 2 | process_file field, agent_role in log record |

### Existing tests: 3162 passed (0 regressions)

The test import fix (`MAX_SESSION_FILES` → `MAX_PROCESS_FILES` in
`test_llm_session_log_and_fallback.py`) was required and applied.

---

## Files changed

| File | Change |
|---|---|
| `src/kairoskopion/llm/attempt_metadata.py` | LLMModelAttempt, 6 new fields, classify bridge |
| `src/kairoskopion/llm/response.py` | 6 new fields on LLMResponse |
| `src/kairoskopion/llm/provider.py` | agent_role in protocol |
| `src/kairoskopion/llm/openai_compat.py` | Attempt collector, all_attempts attachment |
| `src/kairoskopion/llm/session_log.py` | Terminology, size rotation, env vars |
| `src/kairoskopion/agents/base_shell.py` | agent_role passthrough |
| `src/kairoskopion/agents/*.py` (19 files) | agent_role="<id>" on provider.complete() |
| `src/kairoskopion/api/cases.py` | Attempt propagation in error handlers, P11 replay metadata |
| `ui/src/types/domain.ts` | LLMModelAttemptRecord, ExtractionAttempt extended |
| `ui/src/components/LLMAttemptBadge.tsx` | Model/attempts/error display |
| `tests/test_llm_hardening_repair.py` | 19 new tests |
| `tests/test_p11_replay_trace.py` | 8 P11 replay trace tests |
| `tests/test_llm_session_log_and_fallback.py` | Import fix |

---

## Call site audit

**Total call sites:** 22
**Distinct agents:** 19 (+ base_shell 2 generic + cases.py 1 replay)
**Empty roles:** 0

| file | role | non-empty | tested |
|---|---|---|---|
| agents/article_modeler.py | article_modeler | YES | YES |
| agents/semantic_profiler.py | semantic_profiler | YES | YES |
| agents/discipline_matcher.py | discipline_matcher | YES | YES |
| agents/venue_profiler.py | venue_profiler | YES | NO (no spy test) |
| agents/venue_funnel_planner.py | venue_funnel_planner | YES | NO |
| agents/venue_matrix_assessor.py | venue_matrix_assessor | YES | NO |
| agents/venue_family_context_builder.py | venue_family_context_builder | YES | NO |
| agents/fit_assessor.py (×2) | fit_assessor | YES | YES |
| agents/citation_ecology.py | citation_ecology | YES | YES |
| agents/compliance_assessor.py | compliance_assessor | YES | NO |
| agents/depth_recommendation.py | depth_recommendation | YES | NO |
| agents/disciplinary_mapper.py | disciplinary_pathway_mapper | YES | NO |
| agents/discipline_intent_parser.py | discipline_intent_parser | YES | NO |
| agents/discipline_seeder.py | discipline_seeder | YES | NO |
| agents/discipline_source_acquisition.py | discipline_source_acquisition | YES | NO |
| agents/input_classifier.py | input_classifier | YES | NO |
| agents/mismatch_narrator.py | mismatch_narrator | YES | NO |
| agents/rewrite_planner.py | rewrite_planner | YES | NO |
| agents/base_shell.py (try_llm_call) | from family["agent_role_id"] | YES | NO |
| agents/base_shell.py (try_llm_call_with_outcome) | from agent_role arg | YES | NO |
| api/cases.py (P11 replay) | article_model_replay | YES | YES |

Critical roles resolved:
- article_modeler: YES
- discipline_matcher: YES
- semantic_profiler: YES
- venue_discovery: covered by venue_funnel_planner + venue_profiler + venue_matrix_assessor + venue_family_context_builder (no single "venue_discovery" agent calls provider.complete())
- article_model_replay: YES

---

## P11 trace propagation proof

8 tests in `test_p11_replay_trace.py`:

| Scenario | Fields verified | Result |
|---|---|---|
| Primary success | requested_model, effective_model, fallback_used=False, attempt_count=1, provider_status=ok, parse_status=parsed_ok, agent_role, final_error_code=None | PASS |
| Fallback success | requested≠effective, fallback_used=True, attempt_count=2, 2 attempts with error_code/transition | PASS |
| Auth failure | provider_status=error, final_error_code=AUTH_FAILED, parse_status=not_attempted, safe error reply, no traceback | PASS |
| Auth failure no fake model | article_model unchanged after auth error | PASS |
| All-model exhaustion | final_error_code=RETRIES_EXHAUSTED, attempt_count=2, 2 attempts | PASS |
| Exhaustion safe error | reply contains "Ошибка", no Traceback, no "sk-" | PASS |
| Parse status set | parse_status=parsed_ok on valid JSON | PASS |
| No provider | llm_available=False, no attempt_metadata | PASS |

---

## Live app-path smoke

| Check | Result |
|---|---|
| Provider available via app | YES |
| Model name | gpt-4o-mini |
| Key present (boolean) | YES |
| Normal intake | PASS (deterministic article model built) |
| P11 live replay | PASS |
| PromptRunRecord/API attempt_metadata | requested_model=gpt-4o-mini, effective_model=gpt-4o-mini, fallback_used=False, attempt_count=1, provider_status=ok, parse_status=parsed_ok, agent_role=article_model_replay |
| Provider diagnostic JSONL | 4 log files, latest has agent_role=article_model_replay, process_file field, no "session" field |
| Non-empty agent_role in log | YES (semantic_profiler, article_field_positioner, article_model_replay) |
| Requested/effective model in log | YES (gpt-4o-mini) |
| No secrets in log | YES (no sk-, no Authorization, no api_key) |
| No full manuscript/prompt in log | YES (max line 1034 chars, all truncated to 500) |
| UI badge/Workbench | PARTIAL (login/case/intake work, no CORS errors; badge rendering not directly observable — preview server runs without .env so deterministic fallback produces no extraction_attempt for badge) |

---

## Browser smoke

| Check | Result |
|---|---|
| Login | PASS |
| Case creation | PASS |
| Intake submission | PASS (200 OK) |
| Article model loaded | PASS |
| No CORS errors | PASS |
| No console errors | PASS |
| LLM badge visible | NOT OBSERVABLE (preview backend uses deterministic fallback; badge requires LLM extraction_attempt) |
| Effective model visible | NOT OBSERVABLE (same reason) |
| Typed error on failure | COVERED BY API TESTS (8 scenarios) |
| No raw secrets/stack traces | PASS (no console errors, no secrets in network) |

Browser automation could not force an LLM failure because the preview server runs without .env. API-test evidence (8 scenarios) covers the rendering data contract.

---

## Owner answers

| Question | Answer |
|---|---|
| All provider call sites classified | YES (22/22) |
| Five critical roles non-empty | YES |
| Attempt history in P11 trace | YES |
| Effective model in P11 API | YES |
| Auth/all-exhausted failures explicit | YES |
| Fake success prevented | YES |
| Browser renders metadata | PARTIAL (TypeScript clean, badge updated, API data correct; visual rendering not directly observable) |
| Live intake passed | YES |
| Live P11 replay passed | YES |
| Real live fallback | NOT_CONFIGURED (KAIROSKOPION_LLM_FALLBACK_MODELS empty) |
| Diagnostic log bounded/private | YES |
| Secrets absent from git | YES |

---

## Gates

| Gate | Result |
|---|---|
| pytest tests -q | 3189 passed, 8 deselected, 0 failed |
| Focused hardening tests | 69 passed (19 + 8 + 42), 11 subtests |
| npm run typecheck | PASS |
| npm run build | PASS (377 kB JS, 102 kB CSS) |

---

## Recommendation

`LLM_HARDENING_MERGE_READY`

All contract gaps repaired. All critical roles non-empty. P11 trace propagation proved by 8 focused API tests and live smoke. Live provider available and tested. Real fallback NOT_CONFIGURED (no fallback_models in env), but deterministic fallback tests cover the code path. Browser badge rendering is PARTIAL (data contract proved, visual not directly observable due to preview server limitations).

---

## What was NOT done (by spec constraint)

- No merge to main
- No deploy to prod
- No P10 work
- No architecture changes
- No new agents or logging subsystems
- No secrets committed
