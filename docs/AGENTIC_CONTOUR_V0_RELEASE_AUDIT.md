# Agentic Contour v0.1 — Release Audit Report

**Date:** 2026-06-12
**Tag:** `v0.2.0-alpha-rc8`
**Commit:** `21522b1` on `main`
**Auditor:** Claude Opus 4.6

## Audit Phases

| Phase | Description | Verdict |
|-------|-------------|---------|
| 1. Branch state | Clean working tree, tracking origin, 782 tests | PASS |
| 2. Diff scope | 63 files, +5307/-28 lines. Agentic layer only, no unrelated drift | PASS |
| 3. Semantic audit | 26 agents verified, all real prompts, correct service wrapping, executor/orchestrator coherent | PASS |
| 4. CLI audit | 7 new commands tested. Unicode fix applied (_print_json helper). Callable filter for prompt families. | PASS |
| 5. Test quality | 76 new tests: runtime models (17), registry (16), shells (18), executor (5), workflows (10), CLI (10). All pass. | PASS |
| 6. Docs audit | BACKLOG, SPEC_COVERAGE_MATRIX, PROJECT_STATUS updated. Architecture + report docs exist. | PASS |
| 7. Repo hygiene | No secrets in git, no private_inputs, no generated storage. .gitignore covers all patterns. Diagnostics print boolean has_api_key, not key values. | PASS |
| 8. Merge to main | FF-only merge successful (bd035d4..21522b1) | PASS |
| 9. Tag | `v0.2.0-alpha-rc8` created, pushed | PASS |
| 10. Final report | This document | PASS |

## Summary: 10/10 PASS

## Bugs Found and Fixed During Audit

1. **CLI inspect-agent UnicodeEncodeError** — `cmd_inspect_agent` used `print(json.dumps(...))` which crashes on Windows cp1251 when agent specs contain Unicode characters. Fixed: use `_print_json()` helper that writes via `sys.stdout.buffer` with UTF-8 encoding.

2. **CLI inspect-workflow UnicodeEncodeError** — Same issue with workflow descriptions containing `→` (U+2192). Fixed: same `_print_json()` helper.

3. **CLI inspect-prompt-family callable leak** — Prompt family dicts included validator functions which `json.dumps(default=str)` rendered as `<function validate_... at 0x...>`. Fixed: filter callable values before serialization.

## Scope Verification

### What IS in this release
- 26 agents across 7 layers (control, article, venue, fit, submission, review, evidence)
- Agent registry with 26 AgentSpec entries
- Agent executor (task/run/trace lifecycle)
- Sequential workflow orchestrator (entity pool, skip_if_missing)
- 4 workflow specs (8/12/3/6 steps)
- 16 prompt families (5 existing + 11 new) with catalog
- 7 new CLI commands
- 7 new enums + 7 new ID factories
- 76 new tests (782 total)
- Architecture and report docs

### What is NOT in this release (by design)
- LLM execution paths not exercised in tests
- Review layer: 6 contract-only stubs (awaiting LLM)
- No parallel orchestration (sequential only)
- No web crawling or live network calls
- No fabricated data

## Docs Updated
- `docs/BACKLOG.md` — added Agentic Contour v0.1 entry
- `docs/SPEC_COVERAGE_MATRIX.md` — Wave 6 updated from "Deferred" to 6 partial/implemented rows
- `docs/PROJECT_STATUS.md` — branch, agent table, CLI count, prompt family table, test count
- `CHANGELOG.md` — [Unreleased] section for Agentic Contour v0.1

## Known Limitations (not blockers)

1. Prompt family catalog dicts contain only 7 keys (family_id, agent_role_id, version, system_prompt, user_prompt_template, output_schema, validator). Module-level constants (PURPOSE, FORBIDDEN_BEHAVIORS, etc.) are not in the catalog dict.

2. `run-agent-workflow` command requires manual file paths — no interactive mode.

3. Review-layer agents all return explicit "not implemented" outputs — correct behavior for contract-only status.
