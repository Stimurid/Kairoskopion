# P10 Operational Harvest Report — RU Education/AI Venue Discovery

**Date:** 2026-06-27
**Branch:** `feature/p10-ru-education-ai-operational-harvest`
**Constraints:** No paid LLM, no paid API, no fabricated facts, no auto-promotion.

## 1. Execution Summary

| phase | result |
|-------|--------|
| Adapter queries (OpenAlex, DOAJ) | 90 raw results |
| Deduplication | 87 unique |
| Provisional records created | 87 |
| Loaded to registry (after internal dedup) | 60 |
| Verification gate decisions | 601 (441 venue + 160 classification) |
| Verification verdicts | 601 keep_provisional, 0 promoted |
| Review packet exported | MD + JSONL + TSV |
| Tests | 3040 passed (26 new P10 tests) |

## 2. Adapter Fixes Applied

Two bugs fixed in venue adapters during P10 execution:

1. **OpenAlex `search_venues` URL** — used `&type=journal` (invalid query param, caused HTTP 400). Fixed to `&filter=type:journal`.
2. **DOAJ `_parse_response` `oa_start`** — expected dict `{year: N}` but DOAJ API returns plain int. Fixed to handle both int and dict.

Both fixes covered by tests (in `test_p10_harvest.py`).

## 3. Key Venues Discovered (RU Education/AI Relevant)

### Tier 1 — Directly Relevant (Russian education journals)

| venue | ISSN | source |
|-------|------|--------|
| Vysshee Obrazovanie v Rossii = Higher Education in Russia | 0869-3617 | OpenAlex |
| Pedagogical Education in Russia | 2079-8717 | OpenAlex |
| Professional Education in Russia and Abroad | 2220-3036 | OpenAlex |
| RUDN Journal of Informatization in Education | 2312-8631 | OpenAlex |
| Higher Education in Russia and Beyond | — | OpenAlex |
| Вестник КемГУ (гуманитарные и общественные науки) | 2542-1840 | DOAJ |

### Tier 2 — AI in Education (international, high relevance)

| venue | ISSN | source |
|-------|------|--------|
| Computers and Education Artificial Intelligence | 2666-920X | OpenAlex |
| International Journal of Artificial Intelligence in Education | 1560-4292 | OpenAlex |
| Review of Artificial Intelligence in Education | 2965-4688 | OpenAlex |
| Artificial Intelligence in Education | 3049-5474 | OpenAlex |
| International Journal of Learning Analytics and AI for Education (iJAI) | 2706-7564 | OpenAlex |
| Artificial Intelligence Education Studies | 3079-8086 | OpenAlex |
| Journal of Applied Artificial Intelligence in Education | 3109-7081 | OpenAlex |
| International Journal of AI and Education Technology | 2835-2432 | OpenAlex |

### Tier 3 — Educational Technology (international)

| venue | ISSN | source |
|-------|------|--------|
| British Journal of Educational Technology | 0007-1013 | OpenAlex |
| Educational Technology Research and Development | 1042-1629 | OpenAlex |
| Educational Technology & Society | 1176-3647 | OpenAlex |
| International Journal of Educational Technology in Higher Education | 2365-9440 | OpenAlex |
| Contemporary Educational Technology | 1309-517X | OpenAlex |
| Technology Pedagogy and Education | 1475-939X | OpenAlex |

### Tier 4 — Higher Education (international)

| venue | ISSN | source |
|-------|------|--------|
| Higher Education | 0018-1560 | OpenAlex |
| Studies in Higher Education | 0307-5079 | OpenAlex |
| The Journal of Higher Education | 0022-1546 | OpenAlex |
| Research in Higher Education | 0361-0365 | OpenAlex |
| Higher Education Research & Development | 0729-4360 | OpenAlex |
| The Internet and Higher Education | 1096-7516 | OpenAlex |

### Noise (not education/AI relevant — should be filtered in owner review)

- Clinical and Research Journal in Internal Medicine
- Кавказология
- Медицина и организация здравоохранения
- Graduate Medical Education Research Journal
- Various non-education DOAJ results (math education, medical education, etc.)

## 4. Gaps Identified

1. **Education/AI venue universe is bootstrapped from free adapter queries only** — no eLibrary.ru, no RSCI, no Scopus/WoS.
2. **eLibrary.ru data not available** (needs API key) — this is the primary Russian bibliographic database.
3. **RSCI data not available** (needs API key) — Russian Science Citation Index.
4. **Scopus/WoS data not available** (paid) — quartile/ranking data missing.
5. **VAK list corroboration done by adapter cross-reference only** — no direct VAK list import yet.
6. **Discipline seeds remain llm_draft** — no authoritative corroboration.
7. **No CyberLeninka crawl** — adapter exists but requires manual URL input.
8. **No ScimagoJR data** — needs web scraping or manual import.
9. **Venue metrics (SJR, CiteScore, h-index) entirely absent** — requires Scopus/ScimagoJR sources.
10. **No venue sections** — requires per-venue evidence packs.

## 5. What Was NOT Produced (and Why)

| output | status | reason |
|--------|--------|--------|
| Verified venue records | 0 | No records promoted — adapter-only evidence insufficient |
| Venue metrics | 0 | Requires Scopus/ScimagoJR/WoS (paid/manual) |
| Venue sections | 0 | Requires per-venue analysis with evidence packs |
| Discipline corroboration | 0 | VAK passport data requires manual import |
| Crossref enrichment | 0 | Crossref adapter lacks search_venues (lookup_venue only) |

## 6. Files Produced

| file | location |
|------|----------|
| Harvest script | `scripts/run_p10_education_ai_harvest.py` |
| Target scope | `data/seed_registry/education_ai_russia/p10_target_scope.yaml` |
| Raw adapter results | `data/seed_registry/education_ai_russia/p10_harvest/adapter_raw_results.jsonl` |
| Provisional records | `data/seed_registry/education_ai_russia/p10_harvest/provisional_venue_records.jsonl` |
| Verification decisions | `data/seed_registry/education_ai_russia/p10_harvest/verification_decisions.jsonl` |
| Review packet (MD) | `data/seed_registry/education_ai_russia/p10_harvest/review_packet.md` |
| Review packet (JSONL) | `data/seed_registry/education_ai_russia/p10_harvest/review_packet.jsonl` |
| Review packet (TSV) | `data/seed_registry/education_ai_russia/p10_harvest/review_packet.tsv` |
| Harvest summary | `data/seed_registry/education_ai_russia/p10_harvest/harvest_summary.json` |
| Preflight doc | `docs/operations/P10_OPERATIONAL_HARVEST_PREFLIGHT.md` |
| Input inventory | `docs/operations/P10_INPUT_INVENTORY.md` |
| This report | `docs/operations/P10_OPERATIONAL_HARVEST_REPORT.md` |
| Tests | `tests/test_p10_harvest.py` (26 tests) |

## 7. Verdict

**P10_PARTIAL_LOCAL_EVIDENCE_ONLY**

The operational harvest successfully bootstrapped the education/AI venue universe with 87 provisional records from free adapter queries (OpenAlex, DOAJ). However:

- No records were promoted beyond `keep_provisional` — expected, since adapter-only evidence is insufficient for promotion.
- No venue metrics, sections, or discipline corroboration were produced — requires blocked/paid sources.
- The harvested records include noise that requires owner review and filtering.
- Two adapter bugs were fixed (OpenAlex search URL, DOAJ oa_start parsing).

**Owner action required:**
1. Review the 87 provisional records and flag noise for rejection.
2. Decide on eLibrary.ru API key acquisition.
3. Decide on manual ScimagoJR/VAK list import.
4. Prioritize which venues need full evidence packs.
