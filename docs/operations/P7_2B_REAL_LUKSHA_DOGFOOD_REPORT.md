# P7.2B Real Luksha Dogfood Report (Track 6)

**Date:** 2026-06-27
**Run ID:** `run_20260627_135151812194_dac211b9`
**Mode:** no-live-LLM, no-paid-API

## Input

| field | value |
|-------|-------|
| Article | `data/private_work/.../08_cited_clean_current_base.md` |
| Size | 75,775 chars / 279 lines |
| Language | English |
| Title | "Universities After AI: Epistemic Legitimation, Distributed Intellectual Production, and the Second-Tier University" |
| Target country | INTERNATIONAL |
| Target domain | higher_education_ai |
| Target zones | higher_education, AI_in_education, epistemic_legitimation |

## Comparison with P7.2 Dogfood

| aspect | P7.2 (synthetic) | P7.2B (real article) |
|--------|------------------|---------------------|
| Article | synthetic Luksha-domain text | REAL 75KB article with citations |
| Authority store | empty (0 records) | **17 recovered records** |
| Country | RU | INTERNATIONAL |
| Sufficient | NO (7/7 missing) | NO (4/7 missing for INT) |
| Source authority tasks | 7 | **4** |
| Blocked on authority | 1 | **0** |
| Article archetype | YES | **YES** |
| Discipline lookups | N/A | **3** |
| Acquisition tasks | 6 | **6** |
| Available adapters | 9 | **9** |

## Authority Coverage (INTERNATIONAL target)

| type | status |
|------|--------|
| citation_database | COVERED (OpenAlex, Crossref, OpenCitations) |
| national_journal_registry | COVERED (DOAJ) |
| metric_source | COVERED (Unpaywall, Scopus, WoS, ScimagoJR) |
| journal_index | COVERED (ISSN Portal) |
| scholarly_search | COVERED (Google Scholar, Semantic Scholar) |
| discipline_classification | **MISSING** (no international classification in corpus) |
| author_guidelines_source | **MISSING** (venue-specific, cannot pre-populate) |
| editorial_board_source | **MISSING** (venue-specific, cannot pre-populate) |
| journal_archive_source | **MISSING** (CyberLeninka is RU-only) |

## Analysis

The 4 missing types are structurally expected:
1. `discipline_classification` — no international classification system in corpus (OECD FORD would need to be added)
2. `author_guidelines_source` — per-venue, discovered during deep venue profiling
3. `editorial_board_source` — per-venue, discovered during deep venue profiling
4. `journal_archive_source` — CyberLeninka only covers RU journals; international archive sources are per-venue

These 4 types generate SourceAuthorityDiscoveryTasks rather than blocking the pipeline.

## Workflow Artifacts

Output at `data/seed_registry/dogfood_luksha_real/`:
- `dogfood_summary.json` — machine-readable summary
- Authority coverage, tasks, blocked items written by workflow

## Verdict

**PASS** — real Luksha article processed successfully with recovered authorities.
Authority recovery reduced missing types from 7 to 4 (for INTERNATIONAL target).
Remaining gaps are structurally correct (venue-specific or classification gap).
No synthetic text used. No model-memory facts. No paid API calls.
