# P7.2B Source Authority Recovery — Final Report (Track 9)

**Date:** 2026-06-27
**Branch:** `feature/round3-p7-llm-integration`
**Previous:** P7.2 (commit f77096d) — owner rejected Track 4 "DEFERRED"

## What Was Done

The owner identified that P7.2 left Track 4 (populate from project materials) as
DEFERRED, claiming no local authority records could be created without Claude-memory
facts. This was incorrect — the project corpus already contained extensive source
authority evidence in venue evidence packs, discipline seeds, adapter code, and
operational docs.

### Recovery Steps

1. **Corpus audit** — found 17 distinct source authorities with traceable evidence
   across 5 venue evidence packs, 1 discipline seed file, 6 adapter implementations,
   and the external adapter registry.

2. **Record creation** — generated 17 SourceAuthorityRecord entries in
   `data/seed_registry/source_authorities/source_authority_records.jsonl`.
   Every `evidence_refs` entry points to a real project file.

3. **Sufficiency rerun** — with recovered authorities:
   - **RU/education: SUFFICIENT** (was 7/7 missing → now 0/7 missing)
   - **AR/fishing: correctly INSUFFICIENT** (1/7 missing: discipline_classification)
   - **GENERIC: correctly INSUFFICIENT** (1/7 missing: discipline_classification)

4. **Real Luksha dogfood** — processed the actual 75KB article
   ("Universities After AI"), not synthetic text.
   - Authority coverage for INTERNATIONAL: 4 types missing (structurally correct)
   - Article archetype extracted, 3 discipline lookups, 6 acquisition tasks
   - No paid API calls, no model-memory facts

5. **Tests** — added 11 recovery validation tests (56 total in file, 2870 suite-wide)

## Key Metric

| metric | P7.2 | P7.2B | improvement |
|--------|------|-------|-------------|
| Authority records | 0 | **17** | +17 |
| RU sufficiency | FAIL (7 missing) | **PASS (0 missing)** | complete |
| Test count | 2859 | **2870** | +11 |
| Dogfood article | synthetic | **real (75KB)** | corrected |

## Remaining Structural Gaps

These are NOT recovery failures — they're expected:

| gap | reason |
|-----|--------|
| discipline_classification for non-RU | No international classification (OECD FORD) in corpus |
| author_guidelines_source | Per-venue, discovered during deep profiling |
| editorial_board_source | Per-venue, discovered during deep profiling |
| journal_archive_source (non-RU) | CyberLeninka covers RU only |

These gaps correctly generate SourceAuthorityDiscoveryTasks.

## Constraints Compliance

| constraint | status |
|-----------|--------|
| No main merge | COMPLIED |
| No prod deploy | COMPLIED |
| No force push | COMPLIED |
| No paid LLM/API calls | COMPLIED |
| No 302.ai calls | COMPLIED |
| No model-memory source facts | COMPLIED — all evidence_refs verifiable |
| No synthetic dogfood | COMPLIED — real Luksha article used |
| All tests use tmp_path | COMPLIED |
| Private data gitignored | COMPLIED |
