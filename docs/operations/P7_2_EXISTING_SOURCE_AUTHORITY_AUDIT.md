# P7.2 Existing Source Authority Audit (Track 1)

**Date:** 2026-06-27

## Summary

Kairoskopion already has extensive source infrastructure. The P7 Bootstrap
dogfood said "no sources" because the seed workflow did not know WHERE to
look, not because sources are absent.

## Existing Adapters (Implemented)

| adapter | type | status | files |
|---------|------|--------|-------|
| OpenAlex | API (metadata, search) | 6 adapters implemented | `adapters/venue/openalex.py` + `adapters/openalex.py` |
| Crossref | API (metadata, search) | 3 adapters implemented | `adapters/venue/crossref.py` + `adapters/crossref.py` |
| DOAJ | API (OA directory) | Implemented | `adapters/venue/doaj.py` |
| CyberLeninka | Crawl (articles) | Implemented | `adapters/venue/cyberleninka.py` |
| Unpaywall | API (OA status) | Implemented | `adapters/venue/unpaywall.py` |
| OpenCitations | API (citation links) | Implemented | `adapters/venue/opencitations.py` + `adapters/opencitations.py` |
| Local file | Ingest (PDF, DOCX, MD, TXT, HTML, JSON) | Implemented | `adapters/source_intake.py` |
| URL snapshot | Reference | Implemented | `adapters/url_snapshot.py` |
| HTTP client | Fetch utilities | Implemented | `adapters/http_client.py` |

## Existing Enums

- `SourceAccessMode` — 12 access modes (METADATA_API, FULL_TEXT_PDF, etc.)
- `SourceAuthorityScope` — 20 scope levels (VENUE_IDENTITY, ISSN_IDENTITY, etc.)
- `AuthorityStrength` — 5 tiers (AUTHORITATIVE through PROHIBITED)

## Existing Services

- `source_authority.py` — authority ASSESSMENT (claim validation, conflict reconciliation, _AUTHORITY_MATRIX)
- `venue_evidence_pack_resolver.py` — multi-source evidence resolution
- `venue_discovery_tradecraft.py` — URL patterns, aggregator allowlist

## Deferred (Auth/Paid Required)

| source | reason |
|--------|--------|
| eLibrary.ru / РИНЦ | Auth required, no public API |
| Scopus | Institutional subscription (paid) |
| Web of Science | Institutional subscription (paid) |
| Semantic Scholar | API key required (free signup) |
| Sherpa RoMEO | API key required |
| ORCID | Not yet implemented |

## Conclusion

The project has 9 working adapters covering metadata, search, full text,
and citation links. The gap was not "no sources" but "no source-of-sources
registry" connecting authorities to the seed workflow.
