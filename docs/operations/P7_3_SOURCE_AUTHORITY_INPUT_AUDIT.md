# P7.3 Track 1 — Source Authority Input Audit

**Date:** 2026-06-27
**Branch:** `feature/round3-p7-llm-integration`

## Input: 17 SourceAuthorityRecords

| # | authority_name | authority_type | country | adapter_hint | source_status | review_status |
|---|---------------|----------------|---------|-------------|---------------|---------------|
| 1 | VAK nomenclature of scientific specialties | discipline_classification | RU | manual_url | provisional | pending |
| 2 | VAK journal list (Перечень ВАК) | national_journal_registry | RU | manual_url | accepted | curator_confirmed |
| 3 | eLibrary.ru / РИНЦ | national_journal_registry | RU | elibrary_ru | accepted | curator_confirmed |
| 4 | РИНЦ metrics / eLibrary indicators | metric_source | RU | elibrary_ru | provisional | pending |
| 5 | CyberLeninka (cyberleninka.ru) | journal_archive_source | RU | cyberleninka | accepted | curator_confirmed |
| 6 | OpenAlex | citation_database | INTERNATIONAL | openalex | accepted | curator_confirmed |
| 7 | Crossref | citation_database | INTERNATIONAL | crossref | accepted | curator_confirmed |
| 8 | OpenCitations COCI | citation_database | INTERNATIONAL | opencitations | accepted | curator_confirmed |
| 9 | DOAJ | national_journal_registry | INTERNATIONAL | doaj | accepted | curator_confirmed |
| 10 | Unpaywall | metric_source | INTERNATIONAL | unpaywall | accepted | curator_confirmed |
| 11 | Scopus (Elsevier) | metric_source | INTERNATIONAL | scopus | provisional | pending |
| 12 | Web of Science / ESCI / AHCI | metric_source | INTERNATIONAL | wos | provisional | pending |
| 13 | ScimagoJR | metric_source | INTERNATIONAL | manual_url | accepted | curator_confirmed |
| 14 | ISSN Portal | journal_index | INTERNATIONAL | manual_url | accepted | curator_confirmed |
| 15 | ISTINA MSU | national_journal_registry | RU | manual_url | accepted | curator_confirmed |
| 16 | Google Scholar | scholarly_search | INTERNATIONAL | manual_url | provisional | pending |
| 17 | Semantic Scholar | scholarly_search | INTERNATIONAL | semantic_scholar | provisional | pending |

## Coverage by authority_type

| authority_type | count | countries |
|---------------|-------|-----------|
| national_journal_registry | 5 | RU(3), INTERNATIONAL(2) |
| metric_source | 5 | RU(1), INTERNATIONAL(4) |
| citation_database | 3 | INTERNATIONAL(3) |
| discipline_classification | 1 | RU(1) |
| journal_archive_source | 1 | RU(1) |
| journal_index | 1 | INTERNATIONAL(1) |
| scholarly_search | 2 | INTERNATIONAL(2) |

## Status summary

| status | count |
|--------|-------|
| accepted/curator_confirmed | 11 |
| provisional/pending | 6 |

## Evidence grounding

All 17 records trace to project corpus evidence:
- 12 reference venue_evidence_packs
- 7 reference adapter_code
- 1 references project_data (discipline seeds)

No model-memory facts. No fabricated data.

## VERDICT

**PASS** — 17 authority records available, corpus-grounded, covering RU + INTERNATIONAL.
