# P10 Operational Scope — RU Education/AI Harvest

**Date:** 2026-07-09
**Branch:** `feature/p10-operational-harvest-final`
**Base:** `5ebbe1a` (main, post-LLM-hardening + intake metadata fix)

---

## Domain definition

Russian higher education, AI in education, educational technology, university digital transformation, pedagogy research and policy.

## Source needs

### SN-01: RU education venue universe bootstrap
- **Question:** Which journals publish research on Russian higher education, AI in education, and educational technology?
- **Required authority:** Bibliographic database (OpenAlex, DOAJ, Crossref) or official registry (VAK)
- **Source type:** Venue metadata from API queries
- **Language:** Russian, English
- **Geography:** Russia-focused or international with Russian relevance
- **Date:** Active (publishing in 2020-2026)
- **Exclusion:** Non-education journals, medical-only journals, purely physical-science venues
- **Acceptance evidence:** API metadata with ISSN, canonical name, publisher from at least one authoritative source
- **Stopping condition:** Exhaustion of free adapter search queries (OpenAlex + DOAJ)

### SN-02: ISSN and publisher verification
- **Question:** Do the discovered venues have verifiable ISSNs and publishers?
- **Required authority:** ISSN Portal, Crossref, or publisher website
- **Source type:** Cross-reference lookup
- **Acceptance evidence:** ISSN confirmed by second source OR publisher website accessible
- **Stopping condition:** All provisional records with ISSN checked against at least one secondary source

### SN-03: Discipline corroboration for pedagogy seeds
- **Question:** Are the ru-vak-pedagogy and ru-pedagogical-psychology discipline seeds correct?
- **Required authority:** VAK passport list (public web) or Ministry of Education registry
- **Source type:** Official registry data
- **Acceptance evidence:** VAK code and name match official list
- **Stopping condition:** Core 3 discipline seeds corroborated or marked BLOCKED

### SN-04: Venue ranking/metrics
- **Question:** What are the Scopus/WoS/RSCI rankings of discovered venues?
- **Required authority:** ScimagoJR (public web), Scopus (paid), WoS (paid), eLibrary.ru (key required)
- **Source type:** Ranking data
- **Status:** BLOCKED — requires paid API or manual import
- **Stopping condition:** N/A (blocked)

### SN-05: Russian-language venue coverage
- **Question:** Which Russian-language education journals are missing from OpenAlex/DOAJ?
- **Required authority:** CyberLeninka (public web), eLibrary.ru (key required)
- **Source type:** Repository search
- **Status:** PARTIALLY_BLOCKED — CyberLeninka available but requires manual URL input; eLibrary.ru blocked
- **Stopping condition:** CyberLeninka query for 3 core terms, or marked BLOCKED

### SN-06: Venue section structure
- **Question:** What sections/rubrics do the top-tier venues have?
- **Required authority:** Venue website or evidence pack
- **Source type:** Per-venue analysis
- **Status:** DEFERRED — requires per-venue evidence pack build
- **Stopping condition:** Not in scope for first harvest pass

---

## Adapters available

| Adapter | Mode | Status |
|---|---|---|
| OpenAlex | LIVE_API | Available, used in first harvest |
| DOAJ | LIVE_API | Available, used in first harvest |
| Crossref | LIVE_API | Available, lookup-only (no search_venues) |
| Unpaywall | LIVE_API | DOI-only enrichment |
| OpenCitations | LIVE_API | DOI-only enrichment |
| CyberLeninka | Manual | Requires URL input |
| eLibrary.ru | Blocked | Needs API key |
| Scopus/WoS | Blocked | Paid |
| ScimagoJR | Manual | Web scraping |

## First harvest data (from old P10 branch)

- 90 raw adapter results (OpenAlex + DOAJ)
- 87 unique after dedup
- 60 loaded to registry (27 duplicates within registry)
- 601 verification decisions (all keep_provisional)
- Review packets exported (MD + JSONL + TSV)

## This pass scope

1. Reconcile existing harvest data onto clean branch
2. Re-run verification gate on existing records
3. Classify records by domain relevance (Tier 1-4 + Noise)
4. Generate acquisition tasks for unresolved source needs
5. Export review packets for NEEDS_REVIEW records
6. Produce registry-ready outputs for provisional records
7. Prove operator path end-to-end
