# UC-1 Discovery Mode

## Overview

UC-1 now supports venue **pool discovery** as its primary mode. When no
specific venue entity is provided, UC-1 runs through the discovery pipeline
and produces a `VenueCandidatePool` with screening results and an evidence
matrix.

## Modes

| Mode | Trigger | Output |
|------|---------|--------|
| Venue pool discovery | No `venue` entity in initial_entities | VenueCandidatePool + CandidateEvidenceMatrix |
| Selected venue fit | `venue` entity provided | FitAssessment + MismatchMap + full submission pack |
| Submission preparation | `venue` + `scenario` entities | Full pack: fit + rewrite + citation + risk + compliance |

## Workflow steps (discovery mode)

1. **article_modeler** → ArticleModel
2. **article_semantic_profiler** → ArticleSemanticProfile
3. **disciplinary_pathway_mapper** → DisciplinaryPathways
4. **venue_discovery** → VenueCandidatePool (queries + candidates + screening + matrix)
5. Steps 5-12 (fit_assessor through evidence_auditor) **skip** when no `venue` entity exists

## CLI commands

```bash
# Plan discovery queries
python -m kairoskopion.cli plan-venue-discovery

# Discover candidate pool
python -m kairoskopion.cli discover-venue-pool [--output pool.json]

# Screen candidates
python -m kairoskopion.cli screen-venue-candidates [--output screening.json]
```

## Demo path

```bash
python -m kairoskopion.cli run-uc1
```

In discovery mode (default), this runs steps 1-4 and produces the pool.
Steps 5+ are skipped because `skip_if_missing=["venue"]` gates them.

## Evidence rules

- Candidates are NOT recommendations
- All outputs include the disclaimer note
- Candidates with only user_seed evidence cannot be screened_in
- Missing evidence is surfaced as gaps, never inferred
