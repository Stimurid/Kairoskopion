# P7.2C Gitignore Policy Report (Track 2)

**Date:** 2026-06-27

## Problem

Line 36 of `.gitignore` was:
```
data/
```

This ignores the `data/` **directory** itself. When git ignores a directory, it never enters it, so negation patterns like `!data/seed_registry/` at line 65 have no effect on NEW files. Already-tracked files are unaffected (git tracks them regardless of gitignore), which is why `data/venue_evidence_packs/` and `data/disciplinary_landscape/` appeared to work — they were tracked before the rule was added.

## Fix

Changed `data/` to `data/*`:

```gitignore
# BEFORE:
data/

# AFTER:
data/*
```

`data/*` ignores the **contents** of `data/` but not the directory itself. Git still traverses into `data/`, evaluates each entry against gitignore rules, and applies negations correctly.

## Before/After

| path | before (`data/`) | after (`data/*`) |
|------|------------------|-----------------|
| `data/seed_registry/new/output.json` | IGNORED (invisible) | **NOT ignored** (visible) |
| `data/venue_evidence_packs/test.md` | not ignored (already tracked) | **NOT ignored** (structural) |
| `data/disciplinary_landscape/seeds/x.jsonl` | not ignored (already tracked) | **NOT ignored** (structural) |
| `data/private_work/article.md` | IGNORED | **IGNORED** (unchanged) |
| `data/input/private/raw.txt` | IGNORED | **IGNORED** (unchanged) |
| `data/registry/venues.jsonl` | IGNORED | **IGNORED** (unchanged) |

## Additional Cleanup

- Consolidated `data/input/private/` to `data/input/` (the entire input directory should be ignored)
- Removed redundant separate `data/private_work/` and `data/input/private/` lines from the bottom of the file (now handled in the main data section)
- Grouped curated vs. ignored data in a single readable block

## Full Data Section (after fix)

```gitignore
# Data: ignore contents by default, then un-ignore curated subtrees.
# Using data/* (not data/) so negations can re-include subdirectories.
data/*

# Curated project data — tracked and reviewable.
!data/disciplinary_landscape/
!data/disciplinary_landscape/**
data/disciplinary_landscape/registry/
!data/venue_evidence_packs/
!data/venue_evidence_packs/**
!data/seed_registry/
!data/seed_registry/**

# Private/runtime data — always ignored.
data/input/
data/private_work/
data/registry/
```
