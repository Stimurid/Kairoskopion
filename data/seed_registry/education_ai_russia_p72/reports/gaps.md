# Seed Workflow — Gaps Report

**Run ID:** run_20260627_123415177604_4646f8b3

## Gaps

- Article archetype incomplete — needs LLM for: genre_detection, claim_extraction, method_detection
- Venue registry empty for domain 'education_ai_russia' — 3 acquisition tasks created
- No VenueMetricRecords in registry — Q1/Q2 ranking not possible without source-backed metrics
- Shortlist has 0 venues — shortage of 5 vs minimum 5. Populate registry with source-backed venue records.
- Article archetype needs LLM for full semantic extraction
- 7 source authority discovery tasks — resolve before factual acquisition

## Warnings

- Insufficient authority coverage — missing 7 types: discipline_classification, national_journal_registry, citation_database, metric_source, author_guidelines_source, editorial_board_source, journal_archive_source
- Venue universe is empty — only acquisition tasks exist. Populate registry with source-backed records first.
- Running in no-live-LLM mode — semantic analysis deferred
- 1 factual tasks blocked on missing source authorities
- 6 open acquisition tasks — resolve to populate registry