# P7.2B Recovered Source Authority Records (Track 3)

**Date:** 2026-06-27

## Output File

`data/seed_registry/source_authorities/source_authority_records.jsonl` — 17 records

## Record Summary

| # | authority_name | type | country | status | review | evidence_count |
|---|---------------|------|---------|--------|--------|----------------|
| 1 | VAK nomenclature | discipline_classification | RU | provisional | pending | 1 |
| 2 | VAK journal list | national_journal_registry | RU | accepted | curator_confirmed | 3 |
| 3 | eLibrary.ru / РИНЦ | national_journal_registry | RU | accepted | curator_confirmed | 3 |
| 4 | РИНЦ metrics | metric_source | RU | provisional | pending | 1 |
| 5 | CyberLeninka | journal_archive_source | RU | accepted | curator_confirmed | 2 |
| 6 | OpenAlex | citation_database | INT | accepted | curator_confirmed | 2 |
| 7 | Crossref | citation_database | INT | accepted | curator_confirmed | 2 |
| 8 | OpenCitations COCI | citation_database | INT | accepted | curator_confirmed | 1 |
| 9 | DOAJ | national_journal_registry | INT | accepted | curator_confirmed | 1 |
| 10 | Unpaywall | metric_source | INT | accepted | curator_confirmed | 1 |
| 11 | Scopus | metric_source | INT | provisional | pending | 2 |
| 12 | Web of Science | metric_source | INT | provisional | pending | 2 |
| 13 | ScimagoJR | metric_source | INT | accepted | curator_confirmed | 2 |
| 14 | ISSN Portal | journal_index | INT | accepted | curator_confirmed | 1 |
| 15 | ISTINA MSU | national_journal_registry | RU | accepted | curator_confirmed | 2 |
| 16 | Google Scholar | scholarly_search | INT | provisional | pending | 1 |
| 17 | Semantic Scholar | scholarly_search | INT | provisional | pending | 1 |

## Evidence Integrity

Every `evidence_refs` entry points to a real project file:
- `venue_evidence_pack` → `data/venue_evidence_packs/*.md`
- `adapter_code` → `src/kairoskopion/adapters/venue/*.py` or `services/external_source_adapters.py`
- `project_data` → `data/disciplinary_landscape/seeds/ru_seed.jsonl`

No model-memory facts. No fabricated ISSNs, quartiles, or editors.

## Authority Type Coverage

| type | count | RU | INT |
|------|-------|-----|-----|
| metric_source | 5 | 1 | 4 |
| national_journal_registry | 4 | 3 | 1 |
| citation_database | 3 | 0 | 3 |
| scholarly_search | 2 | 0 | 2 |
| discipline_classification | 1 | 1 | 0 |
| journal_archive_source | 1 | 1 | 0 |
| journal_index | 1 | 0 | 1 |
