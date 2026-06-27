# P7.2 External Source Adapters Registry (Track 6)

**Date:** 2026-06-27

## Overview

`ExternalAdapterRegistry` is Kairoskopion's self-knowledge about its
available data channels. It does NOT execute fetches — it maps authority
types to available connectors so the seed workflow knows what tools exist.

## 14 Built-in Adapters

| adapter_id | type | enabled | cost | search | full_text |
|------------|------|---------|------|--------|-----------|
| `local_file` | local_file | yes | free | no | yes |
| `manual_url` | manual_url | yes | free | no | no |
| `repo_docs` | local_file | yes | free | yes | yes |
| `openalex` | openalex | yes | free | yes | no |
| `crossref` | crossref | yes | free | yes | no |
| `doaj` | doaj | yes | free | yes | no |
| `unpaywall` | unpaywall | yes | free | no | no |
| `opencitations` | opencitations | yes | free | no | no |
| `cyberleninka` | cyberleninka | yes | free | yes | yes |
| `semantic_scholar` | semantic_scholar | **no** | free | yes | no |
| `sherpa_romeo` | sherpa | **no** | free | yes | no |
| `scopus` | scopus | **no** | **paid** | yes | no |
| `wos` | wos | **no** | **paid** | yes | no |
| `elibrary_ru` | elibrary | **no** | free | yes | no |

## Authority Type → Adapter Mapping

| authority type | suggested adapters |
|----------------|-------------------|
| citation_database | openalex, crossref, opencitations |
| metric_source | openalex (scopus disabled) |
| national_journal_registry | openalex, doaj, crossref (elibrary disabled) |
| journal_archive_source | cyberleninka, openalex |
| author_guidelines_source | manual_url |
| editorial_board_source | manual_url, openalex |
| discipline_classification | manual_url, repo_docs |
| scholarly_search | openalex (semantic_scholar disabled) |

## Design Rules

- Paid adapters (scopus, wos) disabled by default — `no_paid_api` constraint
- Auth-required adapters (elibrary, semantic_scholar, sherpa) disabled until keys provided
- `suggest_for_authority_type()` returns only **enabled** adapters
- Unknown authority types fall back to `["manual_url", "local_file"]`
