# AUDIT_REFACTOR — Clean Branch Plan

Date: 2026-07-04
Source (polluted) branch: `feature/audit-refactor-optimize` @ `ef39b5b`
Base: `main` @ `51672c8`
Target: `feature/audit-refactor-optimize-clean` — audit changes only.

## Commits unique to the audit branch (main..HEAD)

| Commit | Classification | Files |
|--------|---------------|-------|
| `d0e0568` docs(P11.3): provider preflight | **P11.3 stray — EXCLUDE** | `docs/operations/P11_3_PROVIDER_PREFLIGHT.md` (+53) |
| `5bb9089` feat(P11.3): live LLM provider replay | **P11.3 stray — EXCLUDE** | `docs/operations/P11_3_PROVIDER_PREFLIGHT.md`, `src/kairoskopion/api/workbench.py` (+20), `src/kairoskopion/services/pipeline_replay.py` (+105), `tests/test_p11_3_live_provider_replay_smoke.py` (new, +265) |
| `e67db58` fix(audit): security/correctness/test-isolation + perf | **AUDIT — CHERRY-PICK** (minus one file, see below) | `CLAUDE.md`, `agents/article_modeler.py`, `api/app.py`, `api/cases.py`, `exchange.py`, `llm/openai_compat.py`, `quality.py`, `services/bibliography_parsing.py`, `vault.py`, tests: `test_article_model_json_hardening.py`, `test_p11_3_live_provider_replay_smoke.py`*, `test_quality_gates_hardened.py`, `test_round3p7_llm_smoke.py`, `test_vault_exchange_freshness.py` |
| `ef39b5b` test: validate audit refactor against P11 browser workflow | **AUDIT (gate fixes) — CHERRY-PICK** | `api/app.py` (CORS PATCH), `tests/test_api_cases.py`, `tests/test_workbench_api.py`, `docs/operations/AUDIT_REFACTOR_*.md` (6 reports) |

\* `tests/test_p11_3_live_provider_replay_smoke.py`: the audit commit's change
to this file is pure test-isolation cleanup, **but the file itself is a P11.3
product artifact created by stray commit `5bb9089`** — it does not exist on
main. Including the fixed file would smuggle 265 lines of the blocked P11.3
live-smoke suite into main through the audit branch. Decision: **EXCLUDE the
file entirely** from the clean branch. The isolation fix already lives on
`feature/audit-refactor-optimize` (commit `e67db58`) and must accompany the
P11.3 branch whenever that is merged. Note: the env-poisoning bug this fix
addresses only exists where that file exists, so main without the file is not
exposed.

## Cherry-pick conflict expectation

`e67db58` modifies `test_p11_3_live_provider_replay_smoke.py`, absent on main
→ expected modify/delete conflict; resolution: `git rm` the file (per the
exclusion decision above). No other files overlap with P11.3 commits
(`workbench.py` and `pipeline_replay.py` are untouched by audit commits).

## Forbidden content check (planned)

- No `.env` (never tracked).
- No runtime outputs / P10 harvest dirs (untracked locally, never staged).
- No `P11_3_PROVIDER_PREFLIGHT.md`, no `workbench.py`/`pipeline_replay.py`
  deltas.
- AUDIT_REFACTOR_*.md reports are historical gate records; they reference the
  P11.3 situation textually but carry no product code.

## Final clean diff summary (post-execution)

Branch `feature/audit-refactor-optimize-clean`, 2 cherry-picked commits:
`6b03f71` (from `e67db58`) + `4d2f45c` (from `ef39b5b`).

`git diff --stat main...HEAD`: **21 files, +571 / −105.**

Contents: 8 src files (exchange, quality, openai_compat, article_modeler,
cases, app, bibliography_parsing, vault), 6 test files, 6
AUDIT_REFACTOR_*.md reports, CLAUDE.md. Grep over the name-status list for
`p11_3|pipeline_replay|workbench\.py|\.env|p10|seed_registry` → **no
matches**. The only conflict during cherry-pick was the predicted
modify/delete on `tests/test_p11_3_live_provider_replay_smoke.py`, resolved
by exclusion per plan.

Consequence of the exclusion: the clean branch has **no** P11.3 live smoke
file, so `-m network` on this branch collects only the 4 legacy adapter
network tests; the env-poisoning fix travels with
`feature/audit-refactor-optimize`/P11.3 and must be kept when that branch
is eventually merged.
