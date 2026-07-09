# Intake Attempt Metadata Fix — Post-Merge Report

**Date:** 2026-07-09
**Starting main commit:** `30a504d`
**Feature branch:** `fix/intake-attempt-metadata-propagation`
**Feature commit:** `de47c9d`
**Merge commit:** `20b6452`
**Merge message:** `merge: preserve LLM attempt metadata in article intake`

---

## Commits merged

| Commit | Message |
|---|---|
| `de47c9d` | fix: preserve LLM attempt metadata in article intake |

4 files changed, 529 insertions.

---

## Post-merge deterministic gates

| Gate | Result |
|---|---|
| pytest tests -q | 3196 passed, 8 deselected, 0 failed |
| Focused intake metadata tests | 7/7 passed |
| Focused P11 replay tests | 8/8 passed |
| Focused LLM hardening tests | 19/19 passed |
| Total focused | 34/34 passed |
| TypeScript typecheck | PASS |
| Vite build | PASS (377 kB JS, 102 kB CSS) |

### Deterministic checks

| Check | Result |
|---|---|
| Normal primary-success intake preserves full metadata | PASS (test_agent_role_preserved, test_attempts_preserved, test_requested_effective_model_preserved) |
| Deterministic fallback preserves requested/effective models and ordered attempts | PASS (test_fallback_metadata_preserved) |
| Provider failure preserves final error and does not create fake ArticleModel | PASS (test_failure_preserves_attempts_and_error_code, test_failure_no_fake_article_model) |
| Persistence roundtrip preserves fields | PASS (test_persistence_roundtrip_preserves_metadata) |
| P11 replay remains green | PASS (8/8 tests) |

---

## Live post-merge smoke

| Check | Result |
|---|---|
| Backend startup | PASS (uvicorn, port 8000) |
| Health endpoint | PASS (status=ok, llm available, gpt-4o-mini) |
| Soft-auth signup | PASS |
| Case creation | PASS (case_466f3f85a771) |
| Text intake | PASS (article_model_built=True, stage=article_model) |

### Intake extraction_attempt (live)

| Field | Value |
|---|---|
| agent_role | article_modeler |
| requested_model | gpt-4o-mini |
| effective_model | gpt-4o-mini |
| fallback_used | False |
| fallback_reason | not_applicable |
| attempt_count | 1 |
| attempts | 1 attempt (model=gpt-4o-mini, latency=30096ms, agent_role=article_modeler) |
| llm_attempted | True |
| llm_provider | openai_compatible |
| llm_model | gpt-4o-mini |
| parse_status | parsed_ok |
| repair_attempted | False |
| final_error_code | None |
| warning_for_user | None |

**All 6 new fields (agent_role, requested_model, effective_model, attempt_count, attempts, final_error_code) present and correct.**

### P11 replay regression check (live)

| Field | Value |
|---|---|
| agent_role | article_model_replay |
| requested_model | gpt-4o-mini |
| effective_model | gpt-4o-mini |
| fallback_used | False |
| attempt_count | 2 |
| parse_status | parsed_ok |
| provider_status | ok |
| final_error_code | None |

**P11 replay: no regression.**

---

## What was fixed

`ArticleModelerAgent` in `src/kairoskopion/agents/article_modeler.py` built
`LLMAttemptMetadata` directly at 3 call sites (success, provider exception,
parse failure) without passing the 6 new attempt-history fields added by
the LLM hardening merge. The fix adds `getattr(response, ...)` extraction
and `agent_role="article_modeler"` at all three sites.

P11 replay (`cases.py`) was NOT affected because it uses `classify_llm_response()`
which already propagated all fields correctly.

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

---

## Production deploy status

NOT DEPLOYED — by spec constraint.

---

## Summary

| Item | Value |
|---|---|
| Starting main | `30a504d` |
| Feature commit | `de47c9d` |
| Merge commit | `20b6452` |
| Default tests | 3196 passed |
| Focused tests | 34/34 passed |
| TypeScript | PASS |
| Build | PASS |
| Live intake metadata | PASS (all 6 fields present) |
| Live P11 replay | PASS (no regression) |
| Secrets committed | NO |
| Unrelated files committed | NO |
| Prod deploy | NOT DEPLOYED |

**RESULT:** `INTAKE_METADATA_FIX_MERGED_POST_MERGE_PASS`
