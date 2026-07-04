# P11.2 Real Replay Execution Fix Report

**Date:** 2026-07-04
**Branch:** `feature/p11-2-real-replay-execution`
**Base commit:** `a38c0d8` (main)
**Verdict:** **PASS** (all acceptance criteria met without LLM provider)

---

## Problem Statement

P11.1 replay engine created scaffold nodes for LLM-capable stages but did not:
- Look up prompt families from PromptRegistry
- Apply active overrides from PromptOverrideStore
- Create PromptRunRecord entries
- Produce meaningful diff between runs

All LLM-capable stages returned `stage_not_yet_replayable` with empty PromptRunRecord (HTTP 404).

## Fix Summary

Modified `execute_replay_run()` in `pipeline_replay.py` to render prompts for LLM-capable stages even without an LLM provider:

1. Added `prompt_registry` parameter to `execute_replay_run()`
2. New helper `_render_prompt_for_stage()` that:
   - Looks up prompt family from PromptRegistry
   - Checks for active override via `PromptOverrideStore.get_active_override()`
   - Applies override (edited_system_prompt / edited_user_template) if present
   - Computes `prompt_version_hash` from rendered prompts
   - Creates a real `PromptRunRecord` with `provider_status="not_called"`
   - Sets node status to `prompt_rendered_needs_llm`
3. New helper `_get_stage_prompt_family()` for stage-to-family lookup
4. Stages without a prompt family in the registry still get `stage_not_yet_replayable`
5. Updated workbench API (`workbench.py`) to pass `prompt_registry` to all 3 rerun endpoints

## Files Changed

| File | Change |
|------|--------|
| `src/kairoskopion/services/pipeline_replay.py` | Added `prompt_registry` param, `_render_prompt_for_stage()`, `_get_stage_prompt_family()`, prompt rendering logic |
| `src/kairoskopion/api/workbench.py` | Pass `prompt_registry` to `execute_replay_run` in all 3 rerun endpoints |
| `tests/test_p11_2_real_replay_execution.py` | 5 new tests for the fix |
| `tests/test_p11_smoke.py` | Updated assertion to accept `prompt_rendered` status |
| `tests/test_workbench_api.py` | Updated assertion to accept `prompt_rendered` / `prompt_rendered_needs_llm` |

## Test Results

### New Tests (5/5 PASS)

| Test | What it proves |
|------|----------------|
| `test_rerun_article_model_creates_prompt_run_record` | Rerunning `article_model` creates PromptRunRecord with prompt_family_id, version_hash, provider_status=not_called |
| `test_rerun_with_override_applies_override` | Active override's edited_system_prompt appears in PromptRunRecord, override_id recorded on node |
| `test_diff_non_empty_after_override_rerun` | diff_runs between no-override and with-override runs produces non-empty changed fields |
| `test_canonical_prompt_unchanged_by_override` | Override does not mutate PromptRegistry's canonical prompt |
| `test_execution_status_is_prompt_rendered` | Return status is `prompt_rendered` (not `partial_not_replayable`) |

### Full Suite

- **3106 passed**, 4 deselected, 0 failed
- TypeScript typecheck: clean
- No regressions

## Browser Smoke Verification

Verified via API calls from browser (localhost:5173 + localhost:8000):

| Check | Result | Evidence |
|-------|--------|----------|
| Create case + intake | **PASS** | Case created, text ingested |
| Create override for `article_modeling` | **PASS** | `povr_7c89fe733e1e` created and activated |
| Rerun-stage with override | **PASS** | `execution_status: "prompt_rendered"` |
| Node status | **PASS** | `prompt_rendered_needs_llm` (was `stage_not_yet_replayable`) |
| PromptRunRecord exists | **PASS** | HTTP 200, 1 record (was 404) |
| Override applied in record | **PASS** | `rendered_system_prompt` = custom text |
| provider_status honest | **PASS** | `not_called` (no fake success) |
| Diff non-empty | **PASS** | 11 changed fields (prompt_version_hash, prompt_override_id) |

## User Path Verified

```
existing case/article
  -> choose article_model (LLM-capable stage)
  -> view prompt (article_modeling family)
  -> create override (custom system prompt)
  -> activate override
  -> rerun that same stage
  -> new run has PromptRunRecord with override_id  [CONFIRMED]
  -> diff is non-empty                              [CONFIRMED]
```

## What This Does NOT Do (by design)

- Does NOT call any LLM provider
- Does NOT produce semantic output (article model, venue profile, etc.)
- Does NOT implement all 18 stages — only stages with a prompt_family in the registry
- Does NOT change the full pipeline execution path (`rerun_all` with text)
- Does NOT touch P10, prod deploy, or paid APIs
