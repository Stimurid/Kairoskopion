# Real Venue Pool Discovery v0

## Overview

Venue pool discovery transforms an article's semantic profile and disciplinary
pathways into a pool of **candidate venues** — not recommendations. Each
candidate carries its discovery source, evidence provenance, and any gaps or
conflicts.

## Pipeline

```
ArticleSemanticProfile + DisciplinaryPathways + SubmissionScenario
  → VenueDiscoveryQuery plans (per pathway)
  → adapter queries (fixture or live)
  → VenueCandidate objects
  → identity normalization + dedupe
  → VenueCandidatePool
```

## Key concepts

- **VenueDiscoveryQuery**: search plan for one pathway, with terms and
  constraints from the scenario. Not executed directly — passed to adapters.
- **VenueCandidate**: a venue that appeared in adapter results or user seeds.
  Has canonical name, ISSN/ISSN-L, sources, discovery reasons, authority
  assessments, and raw adapter data.
- **VenueCandidatePool**: collection of candidates from all queries and sources,
  with dedupe notes, rejected candidates, and unknowns.

## Discovery sources

| Source | Role | Default |
|--------|------|---------|
| OpenAlex | Primary discovery + identity | fixture |
| DOAJ | Primary OA discovery | fixture |
| Crossref | Identity confirmation | fixture |
| user_seed | User-provided venues | passthrough |
| local_fixture | Test data | fixture |

Live mode (`live_enabled=True`) is available but returns empty by default —
adapters are not yet wired.

## Identity normalization

- ISSN normalization: strip to XXXX-XXXX format
- Name normalization: NFKD, lowercase, strip punctuation, remove articles
- Strong merge: same ISSN → merge sources, reasons, aliases
- Weak merge: same normalized name (no ISSN) → merge with warning
- Conflict: same name + different ISSN → blocking conflict

## Constraints

The `fixtures` parameter controls fixture data:
- `None` (default): use built-in `DISCOVERY_FIXTURES`
- `{}` (empty dict): no fixtures, empty results
- Custom dict: use provided fixtures

## Files

| File | Purpose |
|------|---------|
| `services/venue_discovery_planner.py` | Query plan generation |
| `services/venue_pool_discovery.py` | Pool discovery (fixtures + live) |
| `services/venue_candidate_identity.py` | Normalization + dedupe |
| `agents/venue/venue_discovery.py` | Agent shell |

## What this is NOT

- Not a recommendation engine
- Not a journal database
- Not a web scraper
- Not a live API client (in v0)
