# P7.2C P7.2B Artifact Audit (Track 1)

**Date:** 2026-06-27

## P7.2B Committed Artifacts (commit `12891ab`)

| artifact group | expected | tracked | notes |
|---------------|----------|---------|-------|
| `source_authority_records.jsonl` | YES | YES | 17 records, force-added |
| `dogfood_luksha_real/` outputs (7 files) | YES | YES | force-added |
| `docs/operations/P7_2B_*.md` (9 files) | YES | YES | normal add |
| `tests/test_source_authority_registry.py` | YES | YES | modified, +11 tests |
| `P7_2_SOURCE_AUTHORITY_ACCEPTANCE_CHECKLIST.md` | YES | YES | Track 4 updated |
| Raw private article | NO | NOT tracked | `data/private_work/` ignored |
| Legacy ROUND3* docs | NO | NOT tracked | unrelated, not staged |

## Force-Add Problem

All `data/seed_registry/` files in P7.2B were added with `git add -f` because:
- `.gitignore` line 36: `data/` (bare directory ignore)
- Git does not traverse an ignored directory, so `!data/seed_registry/` negation at line 65 never takes effect
- Files tracked via `git add -f` remain tracked, but NEW seed outputs would still be invisible

This is the hygiene debt P7.2C fixes.
