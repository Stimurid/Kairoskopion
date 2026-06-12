# GPT-16 Alignment Matrix

Canonical bridge from external architectural critique (16 points) into Kairoskopion planning.

Created: 2026-06-13, after v0.2.0-alpha-rc10.

## Matrix

| # | Concern | Spec | Backlog | Code | Gap type | Priority | Recommended action |
|---|---------|------|---------|------|----------|----------|-------------------|
| 1 | Source reconciliation / EvidenceConflict | YES (§6.1, CONFLICTING_EVIDENCE status) | NO | Enum exists, no reconciliation service | backlog_missing | P0 source authority | Sprint: EvidenceConflict + reconciliation service |
| 2 | Entity lifecycle / freshness / staleness | YES (§27, staleness_policy) | YES (v0.1) | StalenessStatus enum, freshness.py | covered | — | Maintenance only |
| 3 | Venue canonical identity / ISSN-L / aliases | YES (§26.10, VenueModel fields) | YES (v1-v2 foundation) | VenueModel.aliases, ISSN fields | covered | — | Maintenance only |
| 4 | ArticleModel from field / WhiteCrow / protected core | YES (§4.7, ProtectedCore) | YES (Sprint 8) | WhiteCrow bridge stub | covered | — | Sprint 8 implementation |
| 5 | SubmissionScenario mandatory object | YES (§6.17, extensive) | YES (Sprint 6, UC-1) | SubmissionScenario schema, scenario service | covered | — | Maintenance only |
| 6 | Corpus representativeness / selection_strategy / bias_notes | YES (lines 157, 3792) | NO | PublishedArticleCorpus has selection_strategy field | backlog_missing | P1 evidence integrity | Sprint: corpus bias tracking hardening |
| 7 | Full-text access ≠ metadata authority / shadow layer | NO | NO | No separation | true_gap | P0 source authority | ADR + SourceAccessMode/SourceAuthorityScope enums + service |
| 8 | Author/affiliation/funder — ORCID, ROR, CRediT | YES (lines 8729, 10790, 10895) | NO | No AuthorSubmissionProfile | backlog_missing | P2 publication readiness | Sprint: AuthorSubmissionProfile model |
| 9 | Citation integrity — retraction, PubPeer | PARTIAL (padding warnings, no retraction) | NO | No retraction check | spec_partial | P1 evidence integrity | Spec expansion + CitationIntegrityCheck model |
| 10 | AI disclosure / prompt-injection scanner | YES (AI disclosure in RiskReport) | NO | risk_officer checks AI disclosure | backlog_missing | P2 publication readiness | Sprint: AIUseDisclosure scanner agent |
| 11 | Reporting guideline selector — EQUATOR per type | YES (line 1443, 3551) | NO | reporting_guideline field in ComplianceChecklist | backlog_missing | P2 publication readiness | Sprint: ReportingGuidelineSelection model + selector |
| 12 | PublicationHistoryModel — preprint/thesis/conference | PARTIAL (publication regime, no history entity) | NO | No history model | spec_partial | P1 evidence integrity | Spec expansion + PublicationHistoryModel |
| 13 | Submission-system readiness — OJS/EM field alignment | YES (lines 2370, 11513) | NO | SubmissionPack exists, no portal alignment | backlog_missing | P2 publication readiness | Sprint: submission portal field mapping |
| 14 | Humanities/special-issue/CFP — OpportunityModel | YES (§26.14, humanities adapters) | NO | VenueType.SPECIAL_ISSUE exists, no OpportunityModel | backlog_missing | P2 publication readiness | Sprint: OpportunityModel + CFP watcher stub |
| 15 | Evaluation suite — scenario acceptance fixtures | YES (lines 10321, 12387) | PARTIAL (6 validation cases) | UC-1 demo pack + 890 tests | backlog_missing | P3 evaluation/ops | Sprint: adversarial evaluation fixtures |
| 16 | Failure-as-state — AdapterResult preserved | YES (§25.1, 11 status values) | NO | AdapterResult.status has values, not fully enforced | backlog_missing | P0 source authority | Sprint: failure-state enforcement audit |

## Priority legend

- **P0 source authority** — architectural foundation: what source can claim what, and how conflicts are tracked.
- **P1 evidence integrity** — citation, corpus, and publication history verification before output.
- **P2 publication readiness** — author metadata, reporting guidelines, AI disclosure, submission portals.
- **P3 evaluation/ops** — testing infrastructure and operational hardening.

## Status legend

- **covered** — in spec, in backlog, partially or fully in code.
- **backlog_missing** — spec defines it, code may have stubs, but no explicit backlog sprint.
- **spec_partial** — spec mentions it but not fully specified; needs expansion.
- **true_gap** — neither spec nor backlog addresses it; needs ADR + spec + backlog + code.

## Architectural rule (from this audit)

> Full-text access is not metadata authority. Metadata authority is not publication-pattern authority. Official venue claim is not independent verification. Corpus evidence is not formal policy. User memory is not public fact.

This rule must be encoded as `SourceAccessMode` × `SourceAuthorityScope` with prohibited combinations and downgrade logic.
