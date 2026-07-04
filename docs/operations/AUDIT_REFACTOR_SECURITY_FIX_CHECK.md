# AUDIT_REFACTOR — Security Fix Validation

Date: 2026-07-04
Branch: `feature/audit-refactor-optimize`

## Method

For every claimed security/correctness fix: (a) confirm a dedicated test
exists, (b) temporarily restore the pre-fix source file from `main`, run the
test, and confirm it **fails** on old behavior, (c) restore the branch file
and confirm it passes. All five checks executed in this session.

## Results

| fix | test exists | behavior verified | risk |
|-----|------------:|------------------:|------|
| zip-slip in bundle import (`exchange.py`) | `test_vault_exchange_freshness.py::TestImportBundle::test_import_rejects_zip_slip_vault_path` | FAILS on main's code, PASSES on branch | closed; import of a malicious bundle now aborts with explicit error before writing outside vault root |
| CaseStore path traversal (`api/cases.py::_case_path`) | `test_api_cases.py::TestCaseStore::test_case_path_rejects_traversal_components` (+ positive-case test) — **added during this gate**, was missing in `e67db58` | FAILS on main's code (no guard), PASSES on branch | closed; defense-in-depth — ids are generated internally, FastAPI path parsing is the first line |
| malformed LLM response — empty/missing `choices` (`llm/openai_compat.py`) | `test_round3p7_llm_smoke.py::TestOpenAICompatProvider::test_complete_missing_choices_raises_llm_error` | FAILS on main's code (raw KeyError), PASSES on branch (LLMError MALFORMED_RESPONSE) | closed; proxy error bodies with HTTP 200 no longer crash outside the LLM error taxonomy |
| dict enum values from live LLM (`agents/article_modeler.py`) | `test_article_model_json_hardening.py::TestUnhashableEnumValues` | FAILS on main's code (TypeError: unhashable type), PASSES on branch (degrades to "unknown") | closed; this was the actual crash observed with live gpt-4o-mini |
| stale naive/aware datetime (`quality.py`) | `test_quality_gates_hardened.py::TestEvidenceCompletenessGate::test_stale_source_naive_timestamp_still_detected` | FAILS on main's code (staleness silently skipped), PASSES on branch | closed; naive ISO timestamps now coerced to UTC, stale sources flagged |

## Notes

- The CaseStore traversal test was a gap in `e67db58` (fix shipped without a
  test, violating repo test policy #24). Closed in this gate.
- CORS narrowing is validated separately in
  AUDIT_REFACTOR_CORS_REGRESSION_CHECK.md (including the PATCH regression
  found and fixed) with a preflight regression test in
  `tests/test_workbench_api.py::TestCORSPreflight`.

## Verdict

**PASS** — all five fixes have tests; all five tests demonstrably fail on
pre-fix code and pass on the branch.
