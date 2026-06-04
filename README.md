# Kairoskopion

Evidence-first publication-positioning system.

Kairoskopion (formerly Journal-Yuga / Venue-Fit Engine) is a bounded context
within the Litops–WhiteCrow ecosystem.  It matches fields, manuscripts and
articles against academic publication containers — journals, sections, special
issues, conference proceedings — and produces traceable, evidence-backed fit
assessments, mismatch maps, adaptation plans, risk reports and submission packs.

## Core formula

```
Field / Idea / Draft / Manuscript / ArticleModel
×
VenueModel / JournalModel / IssueModel / SectionModel / PublicationRegimeModel
×
SubmissionScenario
→
FitAssessment → MismatchMap
→
RewritePlan / ReframePlan / CitationPlan / RiskReport
→
SubmissionPack / WhiteCrow Patch Queue / External Document Actions / VenueMemory
```

## What Kairoskopion is NOT

- Not a journal recommender with a single fit score
- Not an academic writing assistant or text rewriter
- Not a replacement for WhiteCrow (field/manuscript layer) or Litops (source/provenance layer)
- Not a peer-review authority or bibliometric arbiter

## Project status

**MVP-0 domain skeleton** — data models, enums, JSONL registry, evidence layer,
operation traces, quality gates, markdown card generation.  No UI, no LLM calls,
no external API integrations yet.

## Quick start

```bash
pip install -e ".[dev]"
pytest
```

## Architecture

- `src/kairoskopion/` — core domain package
- `src/kairoskopion/integrations/` — Litops / WhiteCrow compatibility stubs
- `src/kairoskopion/services/` — domain services (future)
- `src/kairoskopion/pipelines/` — operational pipelines (future)
- `src/kairoskopion/adapters/` — data adapters (future)
- `docs/` — specifications, origin, implementation plan
- `tests/` — pytest suite

## Licence

Private — not yet published.
