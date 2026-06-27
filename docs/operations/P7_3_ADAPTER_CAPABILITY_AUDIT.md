# P7.3 Track 2 — Adapter Capability Audit

**Date:** 2026-06-27
**Branch:** `feature/round3-p7-llm-integration`

## External Adapter Registry

| adapter_id | enabled | requires_key | harvest capability |
|-----------|---------|-------------|-------------------|
| openalex | YES | no | venue lookup by ISSN/name, citation data, works count |
| crossref | YES | no | venue lookup by ISSN, DOI resolution, works metadata |
| opencitations | YES | no | citation links between DOIs |
| doaj | YES | no | OA journal registry, venue lookup |
| unpaywall | YES | no | OA status check by DOI |
| cyberleninka | YES | no | RU journal archive, article discovery |
| snapshot_crawler | YES | no | Web page snapshot/extraction |
| scopus | NO | yes | Quartiles, SJR, CiteScore, subject categories |
| wos | NO | yes | JCR, Impact Factor, ESCI/AHCI status |
| elibrary_ru | NO | yes | РИНЦ data, Russian journal metrics |
| semantic_scholar | NO | yes | AI-powered paper search, embeddings |
| scimago_sjr | NO | no | Free web, but no API adapter |
| vak_list | NO | no | No API; manual_url only |
| issn_portal | NO | no | No API; manual_url only |

## Harvest capability matrix

| what to harvest | free adapters available | blocked adapters |
|----------------|----------------------|-----------------|
| Venue by ISSN | openalex, crossref, doaj | scopus, wos, elibrary_ru |
| Venue by name | openalex, doaj, cyberleninka | elibrary_ru |
| Scopus quartiles | — | scopus |
| SJR metrics | — (manual_url) | — |
| RSCI metrics | — | elibrary_ru |
| Citation links | opencitations | — |
| OA status | unpaywall | — |
| RU journal archive | cyberleninka | elibrary_ru |
| Web snapshot | snapshot_crawler | — |

## Harvestable with no_paid_api=True

1. **Local evidence packs** → venue records, sections, metrics, classifications
2. **Discipline seed files** → discipline records
3. **OpenAlex** → venue enrichment by ISSN
4. **Crossref** → venue/DOI data
5. **DOAJ** → OA journal data
6. **OpenCitations** → citation links
7. **Unpaywall** → OA status
8. **CyberLeninka** → RU journal discovery

## Blocked without auth

- Scopus quartiles/SJR (paid)
- WoS Impact Factor/JCR (paid)
- eLibrary.ru РИНЦ (requires registration)
- Semantic Scholar (free API key, but disabled)

## VERDICT

**SUFFICIENT for local harvest.** 6 free API adapters + local evidence packs cover
venue identity, sections, partial metrics, classifications, and discipline data.
Scopus quartiles and RSCI metrics require either paid adapters or manual evidence
pack entries.
