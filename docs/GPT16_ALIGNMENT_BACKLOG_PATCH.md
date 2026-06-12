# GPT-16 Alignment — Backlog Patch

**Date:** 2026-06-13
**Trigger:** External architectural critique (16 points from GPT analysis)
**Branch:** `feature/source-authority-integrity-v0`

## What was done

### Implemented (code + tests)

1. **Source Authority Model** — SourceAccessMode (12), SourceAuthorityScope (20), AuthorityStrength (4), authority matrix, claim validation service
2. **Evidence Conflict/Reconciliation** — EvidenceConflict, EvidenceReconciliationResult models, detect_conflicts(), reconcile_evidence()
3. **Citation Integrity Model** — CitationIntegrityCheck with retraction/PubPeer/DOI fields, RetractionStatus enum
4. **Publication History Model** — PublicationHistoryModel, PriorVersion, PriorVersionType enum
5. **Reporting Guideline Selection Model** — ReportingGuidelineSelection model
6. **EvidenceAuditor Integration** — optional authority_assessments and evidence_conflicts parameters
7. **53 new tests** covering all models, authority rules, conflict detection, reconciliation, and auditor integration

### Documented (spec alignment)

8. **GPT16_ALIGNMENT_MATRIX.md** — canonical 16-point matrix with spec/backlog/code status
9. **12 backlog sprint entries** (GP-1 through GP-12) for all GPT-16 items
10. **Spec coverage matrix** updated with 5 new entries
11. **Architecture doc** updated with Source Authority section
12. **SOURCE_AUTHORITY_MODEL_V0.md** — model documentation
13. **EVIDENCE_CONFLICT_RECONCILIATION_V0.md** — conflict/reconciliation documentation

### Not implemented (explicitly future)

- Live retraction/PubPeer integration (GP-3 future)
- AuthorSubmissionProfile with ORCID/ROR/CRediT (GP-7 future)
- AIUseDisclosure scanner agent (GP-8 future)
- Submission-system field alignment (GP-9 future)
- OpportunityModel for CFPs (GP-10 future)
- Adversarial evaluation fixtures (GP-11 future)
- Adapter-level authority enforcement (GP-12 future)

## GPT-16 coverage after this patch

| Status | Before | After |
|--------|--------|-------|
| Fully covered (spec + backlog + code) | 4 | 7 |
| In backlog with model stub | 0 | 5 |
| In backlog, future only | 0 | 4 |
| True gap | 1 | 0 |
