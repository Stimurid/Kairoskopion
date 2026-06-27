# P7.2B Gitignore and Seed Output Audit (Track 4)

**Date:** 2026-06-27

## .gitignore Rules for Seed Data

```
# In .gitignore:
data/seed_registry/      — IGNORED (default)
!data/seed_registry/     — EXCEPTION: tracked
!data/seed_registry/**   — EXCEPTION: all contents tracked
data/input/private/      — IGNORED (never commit)
data/private_work/       — IGNORED (never commit)
```

## Files That WILL Be Tracked (committed)

| file | purpose |
|------|---------|
| `data/seed_registry/source_authorities/source_authority_records.jsonl` | 17 recovered source authority records |
| `data/seed_registry/dogfood_luksha_real/dogfood_summary.json` | Dogfood run summary |
| `data/seed_registry/dogfood_luksha_real/*.json` | Workflow output artifacts |

## Files That WILL NOT Be Tracked

| file | reason |
|------|--------|
| `data/private_work/luksha_article_*/` | Private work — gitignored |
| `data/input/private/` | Private input — gitignored |

## Verification

- `!data/seed_registry/` exception confirmed in `.gitignore`
- Source authority JSONL created at correct path
- Dogfood outputs at `data/seed_registry/dogfood_luksha_real/`
- No private data in tracked paths
