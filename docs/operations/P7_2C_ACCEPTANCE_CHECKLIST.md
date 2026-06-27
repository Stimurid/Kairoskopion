# P7.2C Seed Tracking Hygiene — Acceptance Checklist

**Date:** 2026-06-27
**Branch:** `feature/round3-p7-llm-integration`

## Requirements

| requirement | status | evidence |
|------------|--------|----------|
| P7.2B artifacts tracked | DONE | `git ls-files data/seed_registry/` — 8 files |
| No raw private article tracked | DONE | `git ls-files data/private_work/` — empty |
| `data/seed_registry/**` naturally trackable | DONE | probe visible as `??` without force-add |
| `data/private_work/**` ignored | DONE | probe invisible in git status |
| `data/input/private/**` ignored | DONE | `git check-ignore` confirms ignored |
| New generated seed output visible in git status | DONE | `p72c_tracking_proof/` appears as `??` |
| No `git add -f` required for new seed outputs | DONE | workflow rerun proved it |
| Validation passes | DONE | seed workflow ran successfully |
| Tests pass | DONE | 2881 passed |
| Typecheck passes | DONE | clean |
| Build passes | DONE | clean |
| No new architecture | DONE | one-char gitignore fix + regression tests |
| No paid LLM/API | DONE | no calls made |
| No main merge | DONE | feature branch only |
| No prod deploy | DONE | |
| No force push | DONE | |

## Files Created/Modified

| file | change |
|------|--------|
| `.gitignore` | `data/` → `data/*`, consolidated data section |
| `tests/test_seed_registry_gitignore_policy.py` | 11 regression tests (NEW) |
| `docs/operations/P7_2C_PREFLIGHT.md` | Track 0 report |
| `docs/operations/P7_2C_P7_2B_ARTIFACT_AUDIT.md` | Track 1 report |
| `docs/operations/P7_2C_GITIGNORE_POLICY_REPORT.md` | Track 2 report |
| `docs/operations/P7_2C_GITIGNORE_PROBE_REPORT.md` | Track 3 report |
| `docs/operations/P7_2C_SEED_WORKFLOW_TRACKING_REPORT.md` | Track 4 report |
| `docs/operations/P7_2C_SEED_TRACKING_HYGIENE_REPORT.md` | Track 7 final report |
| `docs/operations/P7_2C_ACCEPTANCE_CHECKLIST.md` | This file |
| `data/seed_registry/p72c_tracking_proof/` | Workflow rerun outputs (tracking proof) |

## Test Count

- Before: 2870
- New: 11 (gitignore policy)
- Total: 2881
- Failures: 0

## VERDICT

**DONE** — all requirements met.
