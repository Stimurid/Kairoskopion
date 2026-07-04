# POST_MERGE_OUTSTANDING_BRANCH_MAP

**Date:** 2026-07-04
**Main commit:** 828a983

## Branches with commits ahead of main

| Branch | Ahead | Key commits | Status | Merge candidate? |
|--------|-------|-------------|--------|-------------------|
| `feature/p11-3-live-provider-smoke` | 2 | `5bb9089` P11.3 live LLM replay, `d0e0568` provider preflight | Smoke-tested on branch, NOT merged | YES — pending user decision |
| `feature/audit-refactor-optimize` | 4 | Contains P11.3 commits + audit fixes (audit part already merged via clean branch) | Partially merged | NO — superseded by `feature/audit-refactor-optimize-clean` |
| `feature/p10-ru-education-ai-operational-harvest` | 1 | `c85be3d` P10 venue discovery harvest | Completed on branch | YES — pending user decision |
| `chore/state-audit-2026-06-14` | 1 | `f701f4e` state audit + PROJECT_STATUS truth-up | Docs only | LOW priority |
| `feature/spec-coverage-alpha-demo` | 1 | `d03bc07` spec coverage, backlog, demo packaging | Docs only | LOW priority |

## Notable branch inventory (local, at main or behind)

35+ local branches total. Most are at or behind main (previously merged features).

## Remote state

Not checked (no push authorization in this pass).

## Verdict

**OUTSTANDING_BRANCH_MAP: COMPLETE** — 5 branches ahead of main, 2 are merge candidates pending user decision.
