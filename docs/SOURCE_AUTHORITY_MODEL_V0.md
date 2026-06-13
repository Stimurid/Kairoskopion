# Source Authority Model v0

## Overview

The source authority model encodes a fundamental architectural rule:

> Full-text access is not metadata authority. Metadata authority is not
> publication-pattern authority. Official venue claim is not independent
> verification. Corpus evidence is not formal policy. User memory is not
> public fact.

This model ensures that Kairoskopion never treats a PDF download as proof of
ISSN identity, never treats a metadata API as proof of editorial taste, and
never treats user memory as public venue fact.

## Components

### SourceAccessMode (how we accessed the source)

12 modes: `metadata_api`, `full_text_pdf`, `full_text_html`, `official_webpage`,
`submission_system_page`, `editorial_board_page`, `corpus_sample`, `citation_graph`,
`index_registry`, `user_memory`, `review_history`, `manual_note`.

### SourceAuthorityScope (what the source can legitimately claim)

20 scopes: `venue_identity`, `issn_identity`, `publisher_identity`,
`formal_requirements`, `submission_policy`, `publication_regime`, `indexing_status`,
`article_metadata`, `article_full_text`, `citation_relations`, `corpus_pattern`,
`editorial_board_signal`, `community_signal`, `author_identity`,
`affiliation_identity`, `funding_statement`, `ai_disclosure_policy`,
`reporting_guideline`, `prior_outcome`, `tacit_signal`.

### Authority matrix

Each access mode has a fixed set of scopes it can support, each capped at a
maximum authority strength (authoritative / supported / weak). Scopes not in
the set are prohibited for that access mode.

Key prohibitions:
- `full_text_pdf` cannot support `issn_identity`, `indexing_status`, `formal_requirements`
- `metadata_api` cannot support `corpus_pattern`, `formal_requirements`
- `official_webpage` cannot support `indexing_status` (self-claim, not independent verification)
- `corpus_sample` cannot support `submission_policy`, `formal_requirements`
- `user_memory` cannot support `venue_identity`, `issn_identity`

### SourceAuthorityClaim

A claim that a source makes about an entity, annotated with access mode,
authority scope, and authority strength. The service can validate and
downgrade claims based on the authority matrix.

### SourceAuthorityAssessment

Assessment of what a source is allowed to claim, with lists of supported
and prohibited scopes.

## Service: source_authority.py

Four functions:

1. `assess_source_authority(source_ref, access_modes)` → what the source can claim
2. `check_claim_authority(claim)` → validate/downgrade a single claim
3. `detect_conflicts(entity_id, field_name, claims)` → find conflicting values
4. `reconcile_evidence(entity_id, claims, conflicts)` → produce reconciliation result

All deterministic. No network. No LLM.

## Integration with EvidenceAuditor

The evidence audit service accepts optional `authority_assessments` and
`evidence_conflicts` parameters. When present:

- Prohibited authority use → blocking issue
- Unsupported claims → unsupported_claims warning
- Unresolved conflicts → warning (or blocking if severity is blocking)

Backward-compatible: existing callers without these parameters behave identically.

## Limitations (v0)

- Authority matrix is deterministic; no confidence scoring
- No live retraction/PubPeer integration
- ~~No adapter-level enforcement~~ → implemented in Real Source Acquisition v0: all 6 venue adapters call `_attach_authority()` at parse time
- PublicationHistoryModel requires user or source input
- CitationIntegrityCheck is a model, not a live service
- ReportingGuidelineSelection has no selection logic yet

## Files

| File | Role |
|------|------|
| `src/kairoskopion/enums.py` | SourceAccessMode, SourceAuthorityScope, AuthorityStrength, ConflictType, ConflictSeverity, ConflictResolutionStatus, RetractionStatus, PriorVersionType |
| `src/kairoskopion/ids.py` | ID factories for new models |
| `src/kairoskopion/source_authority.py` | Domain models |
| `src/kairoskopion/services/source_authority.py` | Authority checker service |
| `src/kairoskopion/services/evidence_audit.py` | Extended evidence audit |
| `tests/test_source_authority.py` | 53 tests |
| `docs/GPT16_ALIGNMENT_MATRIX.md` | GPT-16 alignment tracking |
