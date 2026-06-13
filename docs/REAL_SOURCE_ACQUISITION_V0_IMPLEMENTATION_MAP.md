# Real Source Acquisition v0 — Implementation Map

**Date:** 2026-06-13
**Branch:** `feature/real-source-acquisition-v0`
**Base:** `v0.2.0-alpha-rc11` (`b34ddd7`), 943 tests

## Goal

Make the venue evidence stack capable of using real external source adapters
in opt-in live/cached mode, while enforcing the Source Authority Model at
the adapter boundary.

Target flow:
```
External source / fixture / cache
  → VenueAdapterResult (with source_access_mode + authority_assessment)
    → SourceAuthorityAssessment + EvidenceConflict
      → VenueEvidenceStack
        → EvidenceAuditor
```

## V0 included sources

| Adapter | Access mode | Key authority scopes | Status |
|---------|------------|---------------------|--------|
| OpenAlex | metadata_api | venue_identity, issn_identity, publisher_identity, article_metadata | Upgrade existing |
| Crossref | metadata_api | venue_identity, issn_identity, publisher_identity, article_metadata | Upgrade existing |
| DOAJ | index_registry | indexing_status (DOAJ only), OA/license/APC metadata | New |
| Unpaywall | metadata_api | article_full_text access, OA status per article | New |
| OpenCitations | citation_graph | citation_relations | Upgrade existing |
| Snapshot (explicit URL) | official_webpage / generic | formal_requirements, submission_policy (if official) | Upgrade existing |

## V0 optional / stub / future

- Semantic Scholar — future
- Sherpa/RoMEO — future
- PhilPapers — future
- ISSN Portal — future
- Scopus/WoS — future (requires auth)
- PubPeer/retraction live checks — future
- Mass crawling — explicitly out of scope

## Adapter contract

Every `VenueAdapterResult` must include:

| Field | Type | Required |
|-------|------|----------|
| adapter_id | str | yes |
| mode | VenueAdapterMode value | yes |
| query | dict | yes |
| status | str (success/partial/no_results/error/unavailable) | yes |
| source_access_mode | str (SourceAccessMode value) | **new, yes** |
| authority_assessment | dict (SourceAuthorityAssessment.to_dict()) | **new, yes** |
| evidence_status | str (EvidenceStatus value) | yes |
| claims | list[VenueAdapterClaim] | yes |
| unsupported_claims | list[str] | **new, yes** |
| prohibited_claims | list[str] | **new, yes** |
| raw_data / vault_ref / cache_ref | optional | existing |
| error | str or None | existing |
| unknowns | list[str] | existing |
| fetched_at | str or None | **new** |
| cached_at | str or None | **new** |
| provenance | str | **new** |

## Live / offline / cache modes

| Mode | Behavior |
|------|----------|
| offline_stub | Returns hardcoded fixture data, no I/O |
| fixture | Loads from fixture JSON file |
| cached | Reads from vault/cache if available, returns unavailable otherwise |
| live_api | Makes real HTTP request, caches result |

- Default mode: `offline_stub`
- Live mode: opt-in only via config flag + CLI `--live`
- Global enable: `KAIROSKOPION_LIVE_ADAPTERS=true` env var or config
- Per-adapter enable: config dict

## Source authority output contract

Each adapter calls `assess_source_authority()` from the source authority
service and attaches the result. The assessment determines:
- which scopes the adapter's access mode supports
- which scopes are prohibited
- max authority strength per scope

Claims that exceed their max authority are downgraded by `check_claim_authority()`.

## Cache / vault behavior

- HTTP responses cached by URL hash in adapter cache dir
- Venue snapshots stored in LocalFsVault under `venue-snapshots/`
- Cache TTL configurable (default 24h for API, 7d for snapshots)
- Cache miss in cached mode → status `unavailable`, not error

## Failure-as-state behavior

- HTTP timeout → status `error`, error message preserved
- HTTP 404 → status `no_results`
- HTTP 429 → status `error`, error `"rate_limited"`
- HTTP 5xx → status `error`, error message preserved
- Invalid JSON → status `error`, error `"invalid_response"`
- No match → status `no_results`, claims empty
- Adapter disabled → status `unavailable`
- Network unavailable → status `error`, degradation note

Never raise exceptions through adapter boundary. All failures become
VenueAdapterResult with appropriate status and error fields.

## Evidence status mapping

| Source type | Evidence status |
|-------------|----------------|
| API metadata (OpenAlex, Crossref) | FACT_FROM_API_METADATA |
| Index registry (DOAJ) | FACT_FROM_API_METADATA |
| OA lookup (Unpaywall) | FACT_FROM_API_METADATA |
| Citation graph (OpenCitations) | FACT_FROM_API_METADATA |
| Official webpage | FACT_FROM_SOURCE |
| User-provided URL | VENDOR_CLAIM (until verified) |

## Acceptance criteria

1. All 6 adapters return VenueAdapterResult with authority assessment
2. Default mode is offline-safe (no network)
3. Live mode is opt-in only
4. Prohibited claims are marked, not silently accepted
5. Conflicts across adapters are detected
6. Failures preserved as state, not exceptions
7. VenueEvidenceStack passes authority to coverage/audit
8. EvidenceAuditor sees authority/conflict objects
9. All existing 943 tests still pass
10. New tests cover all adapter/authority/conflict paths
11. CLI commands work in fixture mode
12. No real copyrighted content in fixtures
13. No secrets required for public API adapters
14. No broad crawling

## Limitations (v0)

- No adapter-level rate limiting coordination across adapters
- No cross-session cache sharing
- No automatic freshness refresh
- No adapter health monitoring
- Snapshot crawler: explicit URL only, no discovery
- DOAJ: journal-level only, no article-level
- Unpaywall: article-level only, requires DOI
- OpenCitations: citation relations only, no quality assessment
