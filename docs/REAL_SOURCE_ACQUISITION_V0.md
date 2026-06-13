# Real Source Acquisition v0

**Branch:** `feature/real-source-acquisition-v0`
**Base:** `v0.2.0-alpha-rc11` (`b34ddd7`), 943 tests
**Date:** 2026-06-13

## Summary

Makes the venue evidence stack capable of using real external source adapters
in opt-in live/cached mode, while enforcing the Source Authority Model at the
adapter boundary.

**Target flow:**

```
External source / fixture / cache
    → VenueAdapterResult (with source_access_mode, authority_assessment)
    → SourceAuthorityAssessment (prohibited/supported scopes)
    → EvidenceItem / EvidenceConflict
    → VenueEvidenceStack
    → EvidenceAuditor
```

## Key rule

No adapter may return "facts" without declaring:
- Access mode (metadata_api, index_registry, citation_graph, official_webpage, manual_note)
- Authority scope (what it CAN claim)
- Prohibited claims (what it MUST NOT claim)
- Evidence status (FACT_FROM_API_METADATA, VENDOR_CLAIM, CORPUS_OBSERVATION, etc.)
- Provenance (adapter_id)
- Failure/degradation state (never exceptions — always structured VenueAdapterResult)

## V0 adapters (6)

| Adapter | Source access mode | Status |
|---------|-------------------|--------|
| `openalex_venue` | `metadata_api` | Fixture + live + cached |
| `crossref_venue` | `metadata_api` | Fixture + live + cached |
| `doaj_venue` | `index_registry` | Fixture + live + cached |
| `unpaywall` | `metadata_api` | Fixture + live (DOI-only) |
| `opencitations_venue` | `citation_graph` | Fixture + live (venue-level degraded) |
| `venue_snapshot_crawler` | `official_webpage` / `manual_note` | Fixture + live (URL-only, no broad crawl) |

## Adapter modes (5)

| Mode | Network | Description |
|------|---------|-------------|
| `offline_stub` | No | Returns built-in fixture (default) |
| `fixture` | No | Returns caller-provided fixture data |
| `live_api` | Yes | Real HTTP call (requires `live_enabled=True`) |
| `cached` | No | Read from file cache, degrade if miss |
| `cached_snapshot` | No | Legacy alias for cached |

## Authority enforcement

Each adapter calls `_attach_authority()` at the end of parse, which:
1. Imports `assess_source_authority()` from the service layer
2. Populates `result.authority_assessment` with supported/prohibited scopes
3. Populates `result.prohibited_claims` for downstream filtering

### Key prohibitions (examples)

- OpenAlex (metadata_api): cannot claim `formal_requirements`, `submission_policy`, `corpus_pattern`
- DOAJ (index_registry): cannot claim `formal_requirements`; CAN claim `indexing_status`
- Unpaywall (metadata_api): article OA ≠ journal policy; cannot claim `formal_requirements`
- OpenCitations (citation_graph): cannot claim `venue_identity`, `formal_requirements`
- Official webpage: CAN claim `formal_requirements`; cannot independently verify `indexing_status`

## Failure-as-state

All adapter errors become `VenueAdapterResult` with appropriate status/error fields.
No adapter ever raises exceptions to the caller. The aggregation service catches
unexpected exceptions at the adapter boundary and converts them.

## CLI commands added (3)

| Command | Description |
|---------|-------------|
| `acquire-venue-sources` | Run all enabled adapters, print summary |
| `list-source-adapters` | List 6 available adapters with access modes |
| `inspect-adapter <id>` | Show adapter details |

Plus: `--use-source-adapters` flag on `build-venue-evidence-stack`.

## Cross-adapter conflict detection

When multiple adapters return claims for the same field (e.g., publisher_or_owner),
the aggregation service groups them by `claim_path`, converts confidence to
`AuthorityStrength`, and calls `detect_conflicts()` from the source authority service.

## Tests

67 new tests covering:
- Adapter config/mode (10)
- HTTP boundary (6)
- OpenAlex adapter (6)
- Crossref adapter (4)
- DOAJ adapter (4)
- Unpaywall adapter (4)
- OpenCitations adapter (3)
- Snapshot adapter (6)
- Aggregation service (6)
- VenueEvidenceStack integration (7)
- EvidenceAuditor authority integration (2)
- CLI commands (6)
- Adapter list/inspect (3)

## Limitations

- No Sherpa/RoMEO, Semantic Scholar, GROBID adapters (future)
- No retraction/PubPeer live lookup
- No broad crawling
- No real all-journal database
- Unpaywall requires DOI (venue-level lookup degrades)
- OpenCitations venue-level citation ecology requires DOI aggregation (future)
- Official webpage authority requires explicit `is_official` flag
- Live mode tests not in CI (require network)
