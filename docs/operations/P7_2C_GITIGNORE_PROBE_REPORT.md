# P7.2C Gitignore Probe Report (Track 3)

**Date:** 2026-06-27

## Probe Setup

Created two probe files:
- `data/seed_registry/_gitignore_probe/visible_probe.txt` — should be VISIBLE
- `data/private_work/_gitignore_probe/private_probe.txt` — should be IGNORED

## Results

### Seed registry probe
```
$ git check-ignore -v data/seed_registry/_gitignore_probe/visible_probe.txt
.gitignore:47:!data/seed_registry/**  data/seed_registry/_gitignore_probe/visible_probe.txt

$ git status --short data/seed_registry/_gitignore_probe/
?? data/seed_registry/_gitignore_probe/
```

**PASS** — negation rule `!data/seed_registry/**` matched. File appears as untracked (`??`) in git status without force-add.

### Private work probe
```
$ git check-ignore -v data/private_work/_gitignore_probe/private_probe.txt
.gitignore:51:data/private_work/  data/private_work/_gitignore_probe/private_probe.txt

$ git status --short data/private_work/_gitignore_probe/
(no output)
```

**PASS** — ignore rule `data/private_work/` matched. File does NOT appear in git status.

### Additional verification

| path | ignored? | expected |
|------|----------|----------|
| `data/venue_evidence_packs/test.md` | NO | NO |
| `data/disciplinary_landscape/seeds/test.jsonl` | NO | NO |
| `data/input/private/test.txt` | YES | YES |
| `data/registry/test.jsonl` | YES | YES |

All paths behave as expected.

## Probes Cleaned Up

Both probe directories removed after verification.
