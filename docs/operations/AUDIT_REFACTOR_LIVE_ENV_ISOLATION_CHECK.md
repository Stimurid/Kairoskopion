# AUDIT_REFACTOR — Live-Provider Test Isolation Check

Date: 2026-07-04
Branch: `feature/audit-refactor-optimize`
Subject: fix in `tests/test_p11_3_live_provider_replay_smoke.py` (commit `e67db58`)

## Background (the bug being fixed)

On the P11.3 parent branch, `_load_dotenv_for_test()` wrote `.env` (real
302.ai key + model) into `os.environ` at **module import time**. pytest
imports all test modules during collection, so a plain `pytest tests -q`
poisoned every other test with a live LLM provider: the suite took 9+
minutes and failed order-dependently in `test_citation_ecology`
(TypeError on a malformed live LLM response).

## Requirements and verification

| Requirement | Check performed | Result |
|-------------|-----------------|--------|
| Importing the module must not mutate `os.environ` | Imported the module in a fresh interpreter, diffed env before/after | **PASS** — added: NONE, changed: NONE |
| `.env` loading must not happen at import time | `_read_dotenv()` parses into `_DOTENV_VARS` dict only; availability probe uses `unittest.mock.patch.dict` (auto-restoring); vars applied per-test via autouse fixture | **PASS** (code inspection + env diff above) |
| Live test marked `network` | `pytestmark = [pytest.mark.network, skipif(...)]` | **PASS** — marks: `['network', 'skipif']` |
| Default `pytest tests -q` deselects network tests | `pyproject.toml` addopts `-m 'not network'`; default run of the file → "4 deselected in 0.19s"; full suite: 3110 passed, **8 deselected** (4 legacy network + 4 P11.3 live) | **PASS** |
| Explicit live run still works with provider configured | `pytest tests/test_p11_3_live_provider_replay_smoke.py -q -m network` → **4 passed in 89.21s** (real 302.ai calls) | **PASS** |
| Live run must not poison other tests | After live run: fresh env has no `KAIROSKOPION_LLM*` vars; `test_citation_ecology.py` (the original order-dependent victim) → 14 passed | **PASS** |

## Verdict

**PASS** on all six requirements. The original failure mode (order-dependent
suite failure + 14× slowdown) is closed; live capability is preserved behind
an explicit `-m network` opt-in.
