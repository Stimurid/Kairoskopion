# P7.2B Existing Authority Corpus Audit (Track 2)

**Date:** 2026-06-27

## Methodology

Searched the project corpus (not model memory) for source authority evidence:
- `data/venue_evidence_packs/` — 5 evidence packs with verified authority references
- `data/disciplinary_landscape/seeds/` — VAK passport references
- `src/kairoskopion/adapters/venue/` — 6 implemented venue adapters
- `src/kairoskopion/services/external_source_adapters.py` — 14 adapter definitions
- `docs/` — operational docs, tradecraft, funnel doctrine

## Authorities Found in Corpus

### Russian-Specific (6 records)

| authority | type | evidence source |
|-----------|------|-----------------|
| VAK nomenclature | discipline_classification | ru_seed.jsonl (5.7.1, 5.7.8, 5.8.1, 5.3.4) |
| VAK journal list | national_journal_registry | 3 venue evidence packs |
| eLibrary.ru / РИНЦ | national_journal_registry | 2 venue packs + adapter code |
| РИНЦ metrics | metric_source | voprosy_filosofii evidence pack |
| CyberLeninka | journal_archive_source | adapter code + venue pack |
| ISTINA MSU | national_journal_registry | 2 venue evidence packs |

### International (11 records)

| authority | type | evidence source |
|-----------|------|-----------------|
| OpenAlex | citation_database | adapter code (6 classes) + venue pack |
| Crossref | citation_database | adapter code (3 classes) + venue pack |
| OpenCitations COCI | citation_database | adapter code |
| DOAJ | national_journal_registry | adapter code |
| Unpaywall | metric_source | adapter code |
| Scopus | metric_source | 2 venue evidence packs |
| Web of Science | metric_source | 2 venue evidence packs |
| ScimagoJR | metric_source | 2 venue evidence packs |
| ISSN Portal | journal_index | venue evidence pack |
| Google Scholar | scholarly_search | venue evidence pack |
| Semantic Scholar | scholarly_search | adapter code |

## Status Classification

| status | count | criteria |
|--------|-------|----------|
| accepted (curator_confirmed) | 11 | Multiple evidence sources AND/OR implemented adapter |
| provisional (pending) | 6 | Single evidence source OR no implemented adapter |

## Not Recovered (no corpus evidence)

- ГРНТИ — mentioned in sufficiency hints but no records in any evidence pack
- OECD FORD classification — no project evidence
- National classifications for non-RU countries — no corpus data
- author_guidelines_source — venue-specific, cannot pre-populate
- editorial_board_source — venue-specific, cannot pre-populate
