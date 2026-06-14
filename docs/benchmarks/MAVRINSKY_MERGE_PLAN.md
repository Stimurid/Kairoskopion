# Mavrinsky golden-run — integration merge plan

**Prepared:** 2026-06-14, end of director-level integration pass.
**Status:** ready for review, **not yet merged**.

## 1. Topology at this point

```
* fix/llm-agent-tolerance-mavrinsky   (HEAD, this branch)
* feature/sprint-alpha-evidence-policy
* feature/wire-fpm-pipeline
* main = v0.2.0-alpha-rc16 + 8 commits up to FieldPositionModel library
```

The stack is **strictly linear** — each branch is one commit on top
of the previous. There are no diverging changes from `main` outside
this stack, and no merge conflicts.

## 2. Commits in the merge train

In order of inclusion (each line is one commit, no squash):

| # | sha | branch tip | one-liner |
|---|---|---|---|
| 1 | `cb464f8` | `feature/wire-fpm-pipeline` | Wire FieldPositionModel into Case pipeline |
| 2 | `1a59812` | `feature/sprint-alpha-evidence-policy` | Sprint α: SourceEvidencePacket + ProtectedCorePolicy substrate (PIM v1 B1+B3) |
| 3 | `3c7ff49` | `fix/llm-agent-tolerance-mavrinsky` | Make LLM agents tolerant to 302.ai gateway output shapes; add e2e UC1 harness |
| 4 | TBD (this pass) | `fix/llm-agent-tolerance-mavrinsky` (next commit) | Add Mavrinsky golden-run benchmark baseline (this pass) |

Expected final HEAD after the integration commit: a new sha at the
tip of `fix/llm-agent-tolerance-mavrinsky` containing the benchmark
rubric, sanitized report, the renamed harness, and the 25 new
regression tests.

## 3. Inclusion check — all three branches required?

| branch | required for benchmark? | reason |
|---|---|---|
| `feature/wire-fpm-pipeline` | **yes** | provides `Case.article_field_position` / `Case.venue_field_position` / `Case.field_position_fit`, plus `ArticleFieldPositionerAgent` / `VenueFieldPositionerAgent`. Without it, scorer checks 3 (`field_coordinates`) and 9 (`fit_vector` FPM half) cannot pass and the harness imports break. |
| `feature/sprint-alpha-evidence-policy` | **yes** | provides `Case.source_evidence_packet`, `Case.protected_core_policy`, `Case.policy_blocked_changes`. The benchmark harness explicitly calls `case.get_source_evidence_packet()` and `case.get_protected_core_policy()`. Without it, scorer check 8 (`evidence_discipline`) cannot pass. |
| `fix/llm-agent-tolerance-mavrinsky` | **yes** | the agent-tolerance fixes are what made the LLM path survive 302.ai in the first place. |

No branch can be dropped without breaking either the harness imports
or specific scorer checks.

## 4. Merge order and method

The stack is linear → **fast-forward merge into `main` is possible
and recommended**, branch by branch. No rebase, no squash, history
preserved:

```powershell
# 1. From main, fast-forward to FPM wiring
git checkout main
git merge --ff-only feature/wire-fpm-pipeline      # → cb464f8

# 2. Fast-forward to Sprint α
git merge --ff-only feature/sprint-alpha-evidence-policy   # → 1a59812

# 3. Fast-forward to the LLM-tolerance fix + this pass's benchmark commit
git merge --ff-only fix/llm-agent-tolerance-mavrinsky      # → <new sha>

# 4. Push main (after Timur's explicit go-ahead — CLAUDE.md rule 17)
git push origin main
```

`--ff-only` guarantees the merge is a pointer move; if any commit
diverges from this plan, the command fails cleanly instead of
producing a merge commit.

Alternative if Timur prefers a single integration PR per branch:

- open one PR per branch (already pushed to origin),
- merge each via the GitHub UI with the "rebase and merge" or
  "create a merge commit" choice as preferred,
- in either case, no cherry-pick is needed.

## 5. Pre-merge validation checklist

- [x] full `pytest`: **1355 passed**, 4 deselected
- [x] UI build: `npx tsc --noEmit` clean, `npx vite build` clean
- [x] no private artifacts in git diff vs `main`
- [x] `.env` not tracked, `.env.example` is the only env reference
  in tracked files
- [x] 9 documented bugs each have a regression test in
  `tests/test_llm_agent_tolerance.py` (25 cases total)
- [x] benchmark rubric in `benchmarks/golden/mavrinsky_article_side_gold.md`
  contains no manuscript body
- [x] sanitized report in `docs/benchmarks/MAVRINSKY_GOLDEN_RUN_REPORT.md`
  contains no manuscript body
- [x] 302.ai gateway reality documented in
  `docs/LLM_PROVIDER_REALITY_302AI.md`

## 6. Tag recommendation

After the fast-forward, tag the integration as
`v0.2.0-alpha-rc17`:

```powershell
git tag -a v0.2.0-alpha-rc17 -m "v0.2.0 alpha RC17: FPM + Sprint α + Mavrinsky golden-run baseline"
git push origin v0.2.0-alpha-rc17
```

The version bump from rc16 → rc17 captures three coherent additions
(FPM wiring, PIM v1 evidence/policy substrate, LLM-tolerance +
benchmark harness). `pyproject.toml` `version` field should be
bumped to `0.2.0a17` in the same commit that lands this plan.

## 7. What to NOT merge in this train

- `chore/state-audit-2026-06-14` is on `main` content with audit
  patches; it should either land **before** or be rebased onto the
  new `main` HEAD after this train. Either is fine; no conflict
  expected because the audit only touched `docs/PROJECT_STATUS.md`
  and added one new doc file.
- Any local-only branches discovered during the state audit
  (`feature/reference-verification-v0`, `feature/ui-cockpit-v0`)
  remain a separate decision and are NOT part of this merge train.

## 8. Post-merge actions (separate work, not this PR)

1. Re-run the Mavrinsky harness 3× from clean checkout against
   `gpt-4o-mini` and record `mavrinsky_baseline_2026_06_14_post_rc17`
   for drift detection.
2. Validate the same flow inside the UI cockpit (operator preview)
   with `.env` configured. Capture screenshots into the next state
   audit appendix, not into this report.
3. Plan PIM v1 Sprint β (semantic profile enrichment B4–B7) as the
   next coherent block.

## 9. Recommendation

**Merge by fast-forward into `main` after one round of Timur's
review.** No squash, no rebase. Tag rc17. Do not push to staging
until rc17 is confirmed reproducible from a clean checkout.

Do not merge today blind. The benchmark itself is reproducible and
the failures are localized and documented; the merge gate is
operator sign-off, not technical readiness.
