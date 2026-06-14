# Real Venue Pool Discovery v0 — Implementation Map

> **Status: superseded for scope decisions.**
> The "not an all-journal database", "no web crawling", and
> "SnapshotCrawler explicit-URL-only" constraints below are lifted by
> [VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md](VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md)
> (see [DECISIONS.md](DECISIONS.md) ADR-16).
> This document remains valid as the v0 MVP implementation record and
> for the rules NOT lifted by v1 (user-seed-only screening, DOAJ ≠
> Scopus inference, UNKNOWN ≠ absent, closed-source degradation).

## What venue discovery means in Kairoskopion

Venue discovery is the process of turning an article's semantic profile, disciplinary
pathways, and submission scenario into a pool of candidate publication venues, each
backed by traceable adapter evidence and authority assessments.

A candidate is NOT a recommendation until evidence supports the relevant claims.
Unknowns and missing evidence must remain visible throughout.

## What venue discovery is NOT

- **Not an all-journal database.** We do not maintain or build a comprehensive journal list.
- **Not web crawling.** No broad scraping, no arbitrary search result parsing.
- **Not a final recommendation engine.** Discovery produces candidates, not rankings.
- **Not guaranteed acceptance prediction.** No adapter can predict editorial decisions.
- **Not a replacement for user judgment.** Candidates with weak/missing evidence say so.

## Input objects

| Object | Source | Role |
|--------|--------|------|
| ArticleModel | Pipeline step 0 | Core article metadata |
| ArticleSemanticProfile | Pipeline step 1 | Disciplinary registers, schools, argument type |
| DisciplinaryPathway | Pipeline step 2 | Pathway branches with fit strength, venue hints |
| SubmissionScenario | User/fixture | Constraints: language, indexing, OA, deadline |
| VenueDepthPolicy | System | How deep evidence stack should go per candidate |

## Output objects

| Object | Role |
|--------|------|
| VenueDiscoveryQuery | Adapter search plan per pathway |
| VenueCandidate | Single candidate with sources, evidence, authority, status |
| VenueCandidatePool | All candidates for article + scenario + pathways |
| VenueCandidateScreeningResult | Preliminary fit screening per candidate |
| CandidateEvidenceMatrix | Cross-candidate evidence/gap/conflict summary |

## Adapter roles in discovery

| Adapter | Discovery role | Authority |
|---------|---------------|-----------|
| OpenAlex | Primary venue/source discovery by discipline/topic | metadata_api |
| DOAJ | OA/indexing discovery, journal inclusion verification | index_registry |
| Crossref | Metadata confirmation, ISSN/publisher verification | metadata_api |
| SnapshotCrawler | Official page evidence — explicit URL only, not search | official_webpage |
| OpenCitations | Secondary: citation ecology evidence, not primary discovery | citation_graph |
| Unpaywall | Secondary: OA access evidence per article DOI, not venue discovery | metadata_api |

## Authority and unknown handling

- Every candidate carries adapter_result_refs and authority_assessments.
- Discovery source (which adapter found it) is explicit.
- When adapters disagree on metadata, EvidenceConflict is created.
- DOAJ inclusion does NOT imply Scopus/WoS/VAK indexing.
- Official webpage self-claim does NOT override metadata source.
- Missing evidence is preserved as evidence_gaps, never inferred.
- Weak-only signals produce status `needs_user_selection`.

## Acceptance criteria

1. Fixture/offline discovery produces VenueCandidatePool with candidates.
2. No candidate is promoted to `screened_in` without minimum evidence.
3. Adapter failures are preserved as state (status, error).
4. Cross-adapter conflicts are detected and surfaced.
5. No Scopus/WoS/VAK inference from DOAJ/OpenAlex.
6. No broad crawling or web search.
7. No live network tests required by default.
8. UC-1 workflow can use discovery mode or selected-venue mode.
9. CLI commands work offline.
10. All fixtures are synthetic.
