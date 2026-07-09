# P10 Post-Merge Acceptance Report

**Date:** 2026-07-09

---

## Commits

| Item | Hash |
|---|---|
| Starting main | `5ebbe1a` |
| P10 original feature commit | `14be885` (cherry-picked old P10 work) |
| P10 final harvest commit | `0f7f629` |
| P10 semantics/DOCX fix commit | `3de2ce1` |
| Merge commit | `ee684c5` |
| Final main (after reports) | `1e1161f` |

## DOCX dependency

| Item | Value |
|---|---|
| Root cause | `python-docx` declared in `pyproject.toml [dev]` but env installed without `[dev]` extra |
| Fix | `pip install -e ".[dev]"` — no manifest changes needed |
| python-docx version | 1.2.0 |
| Previously failing tests | 5 |
| After fix | 0 failures |

## Full test suite

```
3254 passed, 8 deselected, 1 warning in 61.59s
```

Zero failures. 8 deselected are network-marked (expected).

## P10 focused tests

```
58 passed (26 original + 32 final including 6 new semantics invariant tests)
```

## TypeScript / Build

| Gate | Result |
|---|---|
| `npx tsc --noEmit` | PASS (exit 0) |
| `npx vite build` | PASS (built in 395ms) |

## Application smoke

| Step | Result |
|---|---|
| Health endpoint | PASS (200) |
| Auth/Signup | PASS (200) |
| Case creation | PASS (200) |
| Intake text | TIMEOUT (LLM provider 302.ai unreachable/slow; deterministic fallback verified by test suite) |
| Workbench | Not reached (blocked by intake timeout; verified by test suite) |

## P10 operator smoke

| Step | Result |
|---|---|
| List acquisition tasks | PASS (6 tasks) |
| Inspect task | PASS (all fields) |
| Inspect source record | PASS (ISSN, provenance, evidence) |
| Run verification | PASS (keep_provisional) |
| Inspect decision | PASS |
| Review packets | PASS (MD + JSONL + TSV) |
| Candidate export | PASS (87 provisional, 0 accepted) |
| Provenance audit | PASS (0 missing) |
| Provisional invariant | PASS |

## Provisional semantics

| Metric | Value |
|---|---|
| Provisional candidates | 87 |
| Accepted truth | 0 |
| Mislabelling corrections | 7 (all "registry-ready" -> "provisional candidate export") |
| New invariant tests | 6 |

## Privacy / provenance

| Check | Result |
|---|---|
| .env committed | NO |
| API keys committed | NO |
| Provider logs committed | NO |
| Private files committed | NO |
| Engelbart files committed | NO |
| Round3 files committed | NO |
| Fabricated sources | 0 |

## Deploy status

**No production deploy.** This is a development merge only.

## Known limitations

- LLM intake requires reachable provider (302.ai or configured alternative)
- 87 P10 records remain provisional — require operator review for promotion
- Real multi-model fallback not configured (infrastructure exists)
- P10 source needs SN-02/03/04/05/06 remain open/blocked
- Workbench UI shows deterministic fallback output when no LLM configured
