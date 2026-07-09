# Intake Attempt Metadata Propagation — Fix Report

**Date:** 2026-07-09
**Branch:** `fix/intake-attempt-metadata-propagation`
**Base:** main @ `30a504d`

---

## Defect

Normal article intake via `/cases/{case_id}/article-model` returned:
- `agent_role`: empty string
- `attempts`: empty array

P11 replay returned all fields correctly.

## Exact loss point

**File:** `src/kairoskopion/agents/article_modeler.py`
**Three call sites** to `LLMAttemptMetadata.parse_ok()` and `.fallback()`:

1. **Success path (line 159):** `parse_ok()` called without
   `requested_model`, `effective_model`, `attempt_count`, `attempts`,
   or `agent_role` — defaults to empty.

2. **Provider exception fallback (line 91):** `fallback()` called without
   `attempts`, `final_error_code`, or `agent_role`.

3. **Parse failure fallback (line 138):** `fallback()` called without
   `requested_model`, `effective_model`, `attempt_count`, `attempts`,
   or `agent_role`.

P11 replay uses `classify_llm_response()` which extracts these fields from
the response object via `getattr()` — that path was correct.

## Fix

Added `getattr(response, ...)` extraction and `agent_role="article_modeler"`
at all three call sites. Also propagated `response.fallback_used` flag
(matching `classify_llm_response()` behavior).

**Changed file:** `src/kairoskopion/agents/article_modeler.py` only.

## Persistence compatibility

`LLMAttemptMetadata.from_dict()` already defaults missing fields safely:
- `agent_role=""` → empty string (no crash on old data)
- `attempts=[]` → empty list
- `requested_model=None`, `effective_model=None`

Older persisted ArticleModels remain readable — new fields appear as
defaults on deserialization.

---

## Tests

### New: `tests/test_intake_attempt_metadata.py` — 7 tests

| Test | What it proves |
|---|---|
| test_agent_role_preserved_in_extraction_attempt | agent_role="article_modeler" survives LLM → agent → ArticleModel |
| test_attempts_preserved_in_extraction_attempt | attempts array with model/transition preserved |
| test_requested_effective_model_preserved | requested/effective model round-trip |
| test_persistence_roundtrip_preserves_metadata | to_dict → from_dict → to_dict preserves all fields |
| test_fallback_metadata_preserved | fallback_used, requested≠effective, 2 attempts, error codes |
| test_failure_preserves_attempts_and_error_code | provider exception → attempts + final_error_code |
| test_failure_no_fake_article_model | provider error → fallback, no fake success |

### Pre-fix: 5 of 7 tests FAILED (confirming defect)
### Post-fix: 7 of 7 tests PASS

### Existing tests: no regressions

- P11 replay: 8 tests PASS
- LLM hardening: 19 tests PASS
- Full suite: 3196 passed, 8 deselected, 0 failed

---

## Live smoke

| Check | Result |
|---|---|
| Provider available | YES |
| Model | gpt-4o-mini |
| Key present | YES |
| Live intake | PASS |
| agent_role in article-model | `article_modeler` |
| attempts in article-model | 1 attempt (model=gpt-4o-mini, transition=success) |
| requested_model | gpt-4o-mini |
| effective_model | gpt-4o-mini |
| attempt_count | 1 |
| parse_status | parsed_ok |
| fallback_used | False |
| final_error_code | None |
| Secrets in extraction_attempt | NO |

### P11 replay regression check

| Check | Result |
|---|---|
| llm_available | True |
| agent_role | article_model_replay |
| requested_model | gpt-4o-mini |
| effective_model | gpt-4o-mini |
| attempt_count | 1 |
| provider_status | ok |
| parse_status | parsed_ok |

**P11 replay: NO REGRESSION**

---

## Gates

| Gate | Result |
|---|---|
| pytest tests -q | 3196 passed, 8 deselected, 0 failed |
| Focused intake tests | 7 passed |
| P11 replay tests | 8 passed |
| LLM hardening tests | 19 passed |
| TypeScript typecheck | PASS |
| Vite build | PASS |

---

## Owner answers

| Question | Answer |
|---|---|
| Normal intake agent role preserved | YES |
| Normal intake attempts preserved | YES |
| Persistence roundtrip preserves metadata | YES |
| API exposes metadata | YES |
| Fallback metadata survives | YES |
| Failure metadata survives | YES |
| P11 replay unaffected | YES |
| Secrets absent | YES |

---

## Real fallback status

`REAL_MULTI_MODEL_FALLBACK_NOT_CONFIGURED` — not a blocker.

---

## What was NOT done

- No fallback model configuration
- No retry policy changes
- No logging redesign
- No P10 work
- No deploy
- No merge to main
- No secrets committed
