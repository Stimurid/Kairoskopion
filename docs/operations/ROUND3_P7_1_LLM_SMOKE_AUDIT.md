# Round III — P7.1 LLM Smoke Test Audit

**Date:** 2026-06-27
**Commit:** `18ef6c8`
**File:** `tests/test_round3p7_llm_smoke.py` (846 lines, 46 tests)

## Verification Checklist

| criterion | status | evidence |
| --------- | ------ | -------- |
| Tests mock HTTP/provider layer | PASS | `_fake_openai_response()` builds fake HTTP response; `_mock_urlopen()` patches `urllib.request.urlopen` |
| No live API key required | PASS | All env vars set via `monkeypatch`; key is `"test-key-12345"` |
| No real network call | PASS | `urllib.request.urlopen` patched in every provider test; no `httpx`/`requests` imports |
| Provider config coverage | PASS | 9 tests: `from_env` none/config/role override/available/status |
| Role config coverage | PASS | 4 tests: per-role model override, fallback, status listing |
| Prompt message build | PASS | `TestArticleModelerAgentLLM` verifies agent builds prompt and sends to provider |
| Parsing path coverage | PASS | 8 JSON repair tests: valid, fenced, trailing comma, smart quotes, prose extraction, invalid, schema validation, optional fields |
| Agent execute path | PASS | 5 ArticleModeler tests: success, provider error fallback, invalid JSON fallback, run dispatch LLM/deterministic |
| InputClassifier coverage | PASS | 1 test: classification with mocked LLM |
| classify_llm_response helper | PASS | 3 tests: fast-path parsed dict, repair path, fallback path |
| LLMAttemptMetadata | PASS | 4 tests: parse_ok, fallback, not_attempted factories, roundtrip serialization |
| Case.intake_text with LLM | PASS | 2 tests: LLM classification used, fallback without LLM |
| Per-role routing E2E | PASS | 2 tests: different models for different roles, provider_status lists all |
| Input limits | PASS | 3 tests: constant exists, short text unchanged, long text truncated |
| Failure modes covered | PASS | Provider error → fallback, invalid JSON → fallback, 429 retry, empty response → error |
| Existing deterministic fallback not broken | PASS | `test_run_dispatches_to_deterministic_when_no_provider` confirms fallback still works |

## Test Classes

1. `TestLLMConfig` (9 tests)
2. `TestGetLLMProvider` (4 tests)
3. `TestOpenAICompatProvider` (5 tests)
4. `TestJSONRepairSmoke` (8 tests)
5. `TestArticleModelerAgentLLM` (5 tests)
6. `TestInputClassifierAgentLLM` (1 test)
7. `TestClassifyLLMResponse` (3 tests)
8. `TestLLMAttemptMetadata` (4 tests)
9. `TestCaseIntakeWithLLM` (2 tests)
10. `TestPerRoleRoutingE2E` (2 tests)
11. `TestLLMInputLimits` (3 tests)

## Test Run

```
46 passed in 0.43s
```

## Verdict: ACCEPT

Zero production code changes. All tests mock-only. Full LLM execution path covered from config through provider, JSON repair, agent dispatch, and fallback. No blockers.
