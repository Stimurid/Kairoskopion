# Venue Candidate Screening v0

## Overview

Candidate screening evaluates each venue candidate against the article's
semantic profile, disciplinary pathways, and submission scenario. It produces
a preliminary fit assessment, evidence gaps, and authority warnings.

**A candidate is not a recommendation until evidence supports the claim.**

## Pipeline

```
VenueCandidatePool + SemanticProfile + Pathways + Scenario
  → per-candidate screening
  → VenueCandidateScreeningResult (fit, gaps, status)
  → CandidateEvidenceMatrix (summary view)
```

## Screening axes

| Axis | What it checks | Possible values |
|------|---------------|-----------------|
| discipline | Topic overlap with profile | match, partial, unknown, mismatch |
| article_type | Venue accepts this type | match, unknown, mismatch |
| language | Scenario constraint | match, unknown, mismatch |
| publication_regime | Works count / activity | active, unknown, low |
| indexing | Scenario indexing target | match, unknown, mismatch |
| corpus_evidence | Adapter data depth | present, partial, missing |
| authority_confidence | Number of authority sources | high, medium, low, none |

## Preliminary fit levels

| Level | Meaning |
|-------|---------|
| likely | Strong match on multiple axes |
| possible | Partial match, some unknowns |
| insufficient_evidence | Cannot assess — missing data |
| weak | Low confidence or thin evidence |
| rejected | Blocking mismatch or constraint violation |

## Status mapping

- `rejected` → `screened_out`
- `likely` or `possible` with no blocking gaps → `screened_in`
- `insufficient_evidence` → `insufficient_evidence`
- `weak` → `insufficient_evidence`

## Evidence rules

1. User-seed-only candidates cannot be `screened_in`
2. Missing corpus evidence is always an evidence gap
3. Unknown indexing is never treated as negative
4. Blocking conflicts from identity always create blocking gaps
5. DOAJ inclusion does NOT imply Scopus indexing

## CandidateEvidenceMatrix

Summary view of all candidates with:
- Per-candidate screening row (status, fit, axes)
- `missing_evidence_by_candidate`: what's unknown
- `conflicts_by_candidate`: identity conflicts
- `authority_warnings_by_candidate`: authority issues

## Files

| File | Purpose |
|------|---------|
| `services/venue_candidate_screening.py` | Screening logic + matrix builder |
| `tests/test_venue_pool_discovery.py` | 58 tests covering all screening scenarios |
