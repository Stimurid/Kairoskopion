# POST_MERGE_BRANCH_INCLUSION_AUDIT

**Date:** 2026-07-04
**Main commit:** 828a983

## Expected merges — inclusion table

| Branch / Feature | Expected | In main? | Evidence |
|---|---|---|---|
| P11.2 real no-provider prompt replay | YES | ✓ | commit `51672c8` merge, `f4c9c18` feat |
| Audit/refactor/security fixes | YES | ✓ | commit `828a983` merge, `c3c6eb3` fix, `6b03f71` audit |
| CORS PATCH fix | YES | ✓ | part of `c3c6eb3` (allow_methods includes PATCH) |
| P11 browser regression tests | YES | ✓ | commit `4d2f45c` test, `f741c96` acceptance gate |
| Live-env isolation (.env autoload) | YES | ✓ | `_load_dotenv_if_present` in app.py, `KAIROSKOPION_NO_DOTENV` guard |
| P11.3 live provider smoke | NO | ✓ absent | commits `5bb9089`/`d0e0568` NOT in main |
| P10 outputs | NO | ✓ absent | `data/seed_registry/` untracked only |

## Exclusion verification

```
$ git log --oneline main | grep -i "p11.3\|live.provider.smoke"
(no results)
```

No P11.3 commits contaminating main.

## Verdict

**BRANCH_INCLUSION_AUDIT: PASS** — all expected merges present, all exclusions confirmed.
