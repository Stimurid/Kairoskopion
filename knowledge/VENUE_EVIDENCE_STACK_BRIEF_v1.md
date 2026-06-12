# Venue Evidence Stack — Source Architecture Brief v1

**Author:** Timur Shchukin
**Date:** 2026-06-12
**Status:** Design input for implementation planning

## Purpose

This document captures the complete source-layer architecture for building
VenueModel in Kairoskopion. It defines 29 source categories, their data
yields, evidence statuses, and operational priorities.

The core insight: agents cannot follow a single route "through journals."
They must build a multi-layer **Venue Evidence Stack**: official pages first,
then API metadata, then published article corpus, then citation ecology,
then policy/compliance, then CFP/community, then external suggesters,
then editorial taste reconstruction.

## Governing Formula

```
candidate venue → verified VenueModel → deep FitAssessment → submission-ready
```

- `candidate venue` from publisher finder / OpenAlex / PhilPapers / user input / CFP
- `verified VenueModel` only after official snapshot + API enrichment + corpus sample
- `deep FitAssessment` only after ArticleModel + SubmissionScenario + VenueModel + evidence pack
- `submission-ready` only after fresh guidelines, policy check, reference verification,
  compliance checklist, and explicit user acceptance

## Evidence Status Taxonomy

| Status | Meaning |
|--------|---------|
| FACT_FROM_SOURCE | Current official page or authoritative record |
| FACT_FROM_API_METADATA | Structured data from open API (OpenAlex, Crossref) |
| VENDOR_CLAIM | Publisher/journal self-reported (fast review, indexed, etc.) |
| CORPUS_OBSERVATION | Derived from analyzing published articles |
| INFERENCE | Reconstructed from patterns across sources |
| INFERENCE_WITH_EVIDENCE | RAG/QA answer backed by specific passages |
| SCENE_FIT_INFERENCE | Community/disciplinary scene match (not core fit) |
| EDITORIAL_BOARD_INFERENCE | Derived from board composition analysis |
| TACIT_SIGNAL | User's informal knowledge about venue |
| USER_NOTE | User-provided annotation |
| PRIOR_OUTCOME | Past submission result |
| USER_LIBRARY_FACT | From user's Zotero/Mendeley/citation manager |
| EXTERNAL_SUGGESTER_RESULT | From publisher finder / Trinka / JANE |
| EXTERNAL_COMPLIANCE_REPORT | From plagiarism/similarity checker |
| SECONDARY_SIGNAL | Google Scholar or fragile/scraping source |
| PUBLIC_REVIEW_CORPUS | From OpenReview public traces |
| POLICY_SOURCE | From Sherpa/DOAJ policy records |
| OFFICIAL_SERIAL_METADATA | From ISSN Portal |
| PAID_INDEX_METADATA | From Scopus/WoS/JCR (user-provided) |
| UNKNOWN | No evidence available |
| INACCESSIBLE | Source exists but cannot be reached |
| STALE | Source past freshness window |
| CONFLICTING_EVIDENCE | Multiple sources disagree |

## 29 Source Categories

### Level 0 — Identity Resolution
1. **Official journal site** — homepage, aims/scope, guidelines, board, policies
2. **Publisher portals** — Springer/Elsevier/Wiley/T&F/SAGE/Frontiers/MDPI finders
3. **ISSN Portal** — canonical serial identity, title history, aliases

### Level 1 — Open API Backbone
4. **OpenAlex** — sources, works, topics, authors, institutions, publishers
5. **Crossref** — DOI validation, journal/member, licenses, references
6. **OpenCitations** — citation ecology, reference/citation counts
7. **DOAJ** — OA journal validation, predatory signal
8. **Unpaywall** — OA status, legal full-text availability
9. **Semantic Scholar** — embeddings, recommendations, citation context

### Level 2 — Policy & Compliance
10. **Sherpa/Open Policy Finder** — self-archiving, funder compliance, rights
11. **DataCite** — dataset/software/supplement DOI metadata

### Level 3 — Corpus Analysis
12. **Publisher article corpus** — issue pages, latest/most read/cited articles
13. **OpenAlex/Crossref works by ISSN** — structured article metadata
14. **Full text where legal** — OA articles, preprints, user-provided

### Level 4 — Editorial & Community
15. **Editorial board pages** — names, affiliations, disciplines, roles
16. **PhilPapers** — philosophy categories, journals, topic taxonomy
17. **PhilEvents** — CFP, special issues, conferences for philosophy
18. **H-Net** — humanities/social science announcements
19. **Association sites** — 4S/STHV for STS, discipline-specific
20. **OpenReview** — public reviews, decisions, rebuttal norms (CS/AI/ML)

### Level 5 — External Suggesters
21. **Publisher finders** — Springer/Wiley/T&F/Elsevier journal matchers
22. **JANE** — PubMed/MEDLINE journal/author matching
23. **Trinka** — AI journal recommendations with OpenAlex data
24. **SciSpace/Penelope/JournalGuide** — author-service tools

### Level 6 — Scholarly Infrastructure
25. **arXiv/PubMed/PMC/SSRN/OSF/HAL/Zenodo** — preprint/repository corpus
26. **GROBID/CERMINE/AnyStyle/citation-js** — document ingestion layer
27. **PaperQA2** — claim-level evidence QA over corpus
28. **Zotero/Mendeley** — user citation memory

### Level 7 — User & Social Signals
29. **User tacit signals** — prior submissions, review letters, colleague reports
30. **Altmetric/most-read/trending** — attention and debate signals
31. **Russian sources** — eLIBRARY/РИНЦ, КиберЛенинка, ВАК

### Explicitly Excluded
- **Sci-Hub** — toxic provenance for product with Litops archive
- **Google Scholar** as core adapter — no stable API, fragile scraping

## Operational Depth Levels for Agents

| Level | Name | Sources | Output |
|-------|------|---------|--------|
| L0 | Identity Resolver | Official site, OpenAlex, Crossref, ISSN, DOAJ | Canonical identity, aliases, ISSN, publisher, URL |
| L1 | Official Snapshot | Homepage, guidelines, board, policies, CFP | SourceSnapshot, FormalSubmissionProfile, PolicyProfile |
| L2 | API Enrichment | OpenAlex, Crossref, S2, OpenCitations, DOAJ, Unpaywall, Sherpa, DataCite | IndexingAndMetrics, CorpusLight, OAProfile, CitationGraph |
| L3 | Corpus Profiler | Recent articles, OpenAlex works, full text | PublishedArticleCorpus, GenreMoveProfile, MethodExpectation |
| L4 | Humanities/CFP | PhilPapers, PhilEvents, H-Net, associations | IssueModel, SpecialIssueModel, CommunityVenueSignal |
| L5 | External Suggesters | Publisher finders, JANE, Trinka | Candidate venues (VENDOR_CLAIM, requires verification) |
| L6 | Risk/Compliance | Sherpa, Unpaywall, DOAJ, Crossref licenses, Penelope-like | RiskReport, ComplianceChecklist, SubmissionPackReadiness |
| L7 | VenueMemory/Review | User submissions, review letters, OpenReview | PriorOutcome, ReviewerObjectionMemory, VenueMemory |

## Minimal Adapter Set for Working MVP

**Core (must have):**
- OfficialVenueCrawler — journal homepage/guidelines/policies/board
- OpenAlexAdapter — source + works + topics + recent corpus
- CrossrefAdapter — DOI/journal/member/license/reference verification
- OpenCitationsAdapter — citation ecology
- GROBID/ingestion — manuscript/articles/references parsing
- ManualSnapshotAdapter — anything not reachable by API

**Soon (next sprint):**
- DOAJAdapter — OA journal validation
- UnpaywallAdapter — legal full-text availability
- SemanticScholarAdapter — embeddings, recommendations
- PhilPapers/PhilEventsAdapter — humanities discovery
- PublisherFinderAdapter — weak candidate generators

**Later (paid/optional):**
- Scopus/WoS/JCR — prestige metrics (user-provided snapshots)
- ISSN Portal — canonical serial identity
- Dimensions/Lens — broader impact graph
- SherpaAdapter — self-archiving/funder compliance

## Design Rules

1. Closed paid source must not block MVP — degrade to UNKNOWN_NOT_VERIFIED
2. Publisher-owned recommenders are VENDOR_CLAIM, not neutral fit
3. Sci-Hub excluded as agent source
4. Google Scholar is SECONDARY_SIGNAL only
5. Every claim must trace to source with evidence_status
6. Official page + API metadata + corpus sample = minimum for verified VenueModel
7. full_text_access_status: LEGAL_OA | USER_PROVIDED | SUBSCRIPTION_REQUIRED | INACCESSIBLE | UNKNOWN
8. If official page, API, and user note conflict — preserve conflict, don't resolve silently
