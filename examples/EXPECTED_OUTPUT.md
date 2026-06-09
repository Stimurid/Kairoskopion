# Expected Output — Kairoskopion Alpha Demo

Running the demo pipeline with the provided sample files produces the following results.

## Pipeline summary

| Field | Value |
|-------|-------|
| Overall fit label | `possible_but_costly` |
| Mismatches | 5 |
| Risk items | 6 |
| Compliance items | 9 (3 missing) |
| Pipeline status | completed |
| Registries written | 15 |
| Vault cards written | 8 |

## Fit Assessment (8 axes)

The fit assessment compares a philosophy-of-mind paper against an STS journal:

- **Topic fit**: medium — AI subjectivity is relevant to STS but not core STS topic
- **Discipline fit**: weak — paper is philosophy of mind, journal expects STS/sociology
- **Genre fit**: weak — theoretical essay, journal prefers empirical research articles
- **Method fit**: weak — conceptual analysis, journal expects empirical or mixed methods
- **Citation ecology fit**: medium — some overlap (Dreyfus, Chalmers) but missing STS anchors
- **Language register fit**: medium — philosophical register, journal expects sociological
- **Formal compliance fit**: medium — format mostly compatible
- **Publication regime fit**: medium — classic journal peer review matches

## Mismatches found

Typical mismatches between a pure philosophy paper and an STS journal:
1. Discipline mismatch (philosophy vs STS/sociology)
2. Genre mismatch (theoretical essay vs empirical research)
3. Method mismatch (conceptual analysis vs empirical/case-based)
4. Citation ecology gaps (missing STS-specific references)
5. Language register difference (philosophical vs sociological)

## Risk items

Typical risks identified:
1. Scope mismatch risk (philosophy paper in STS venue)
2. Method weakness risk (no empirical component)
3. Citation gap risk (STS anchors missing)
4. Reviewer misunderstanding risk (philosophical argument in social science venue)
5. Field-core loss risk (adapting philosophy to STS may require deep reframe)
6. Formal compliance items (minor formatting adjustments)

## Vault cards generated

```
.kairoskopion_demo/vault/
  articles/   art_XXXX.md      — ArticleModel card
  venues/     ven_XXXX.md      — VenueModel card
  fits/       fit_XXXX.md      — FitAssessment with cross-links to article + venue
  risks/      risk_XXXX.md     — RiskReport with cross-links
  compliance/ cc_XXXX.md       — ComplianceChecklist with cross-links
  mismatches/ mm_XXXX.md       — MismatchMap with cross-link to fit
  citations/  citeco_XXXX.md   — CitationEcologyReport with cross-links
  traces/     run_XXXX.md      — Full pipeline trace
```

## Registries written

```
.kairoskopion_demo/registries/
  article_models.jsonl
  bibliography_profiles.jsonl
  citation_ecology_reports.jsonl
  compliance_checklists.jsonl
  fit_assessments.jsonl
  manuscripts.jsonl
  mismatch_maps.jsonl
  operation_traces.jsonl
  pipeline_runs.jsonl
  publication_regimes.jsonl
  quality_gates.jsonl
  rewrite_plans.jsonl
  risk_reports.jsonl
  submission_scenarios.jsonl
  venue_models.jsonl
```

## Notes

- Entity IDs are UUID-based and differ between runs
- Timestamps differ between runs
- The overall fit label and mismatch/risk counts are deterministic for the same input files
- All evidence is heuristic-extracted (no LLM), so extraction quality depends on text structure
