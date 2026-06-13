# Source Adapter Authority Contract

Every venue adapter in Kairoskopion must follow this contract.

## Required fields on VenueAdapterResult

| Field | Type | Description |
|-------|------|-------------|
| `adapter_id` | str | Unique adapter identifier (e.g., `openalex_venue`) |
| `mode` | str | Adapter mode used (`offline_stub`, `fixture`, `live_api`, `cached`) |
| `status` | str | `success`, `partial`, `no_results`, `unavailable`, `error`, `rate_limited` |
| `source_access_mode` | str | From `SourceAccessMode` enum (e.g., `metadata_api`) |
| `authority_assessment` | dict | Result of `assess_source_authority()` — scopes, prohibitions |
| `unsupported_claims` | list | Claims the adapter cannot support |
| `prohibited_claims` | list | Claims the adapter must never make |
| `provenance` | str | Adapter identifier for traceability |
| `fetched_at` | str | ISO timestamp of data acquisition |
| `cached_at` | str | ISO timestamp if from cache |
| `cache_ref` | str | Cache file path if applicable |
| `claims` | list[VenueClaim] | Extracted claims with evidence status and confidence |
| `unknowns` | list[str] | What the adapter could not determine |
| `error` | str | Error description if status is error/unavailable |

## Authority attachment

Every adapter must call `self._attach_authority(result)` after populating claims.
This method:

1. Calls `assess_source_authority()` with the adapter's `source_access_mode`
2. Populates `result.authority_assessment` with the assessment dict
3. Copies `prohibited_scopes` to `result.prohibited_claims`
4. Copies `authority_scopes` to the assessment

## Failure-as-state

Adapters MUST NOT raise exceptions. All error conditions become structured
`VenueAdapterResult` entries with appropriate `status` and `error` fields:

| Condition | Status | Error |
|-----------|--------|-------|
| Network timeout | `error` | `timeout` |
| HTTP 429 | `rate_limited` | `rate_limited` |
| HTTP 404 | `no_results` | `not_found` |
| JSON parse failure | `error` | `json_decode_error` |
| No matching data | `no_results` | — |
| Adapter disabled | `unavailable` | `disabled` |
| Cache miss | `unavailable` | `cache_miss` |

## Authority scope matrix (summary)

| Access mode | CAN claim | CANNOT claim |
|-------------|-----------|--------------|
| `metadata_api` | venue_identity, issn_identity, indexing_status | formal_requirements, submission_policy, corpus_pattern |
| `index_registry` | indexing_status, oa_policy | formal_requirements, submission_policy, corpus_pattern |
| `citation_graph` | corpus_pattern (partial) | venue_identity, formal_requirements, submission_policy |
| `official_webpage` | formal_requirements, submission_policy | indexing_status (self-claim, not independent) |
| `manual_note` | — (weak on all) | venue_identity, formal_requirements |

See `docs/SOURCE_AUTHORITY_MODEL_V0.md` for the full authority matrix.

## Adding a new adapter

1. Subclass `VenueAdapter` from `adapters/venue/base.py`
2. Set `source_access_mode` class attribute
3. Implement `lookup_venue()` with fixture/live/cached paths
4. Implement `parse_response()` for external fixture injection
5. Call `self._attach_authority(result)` at end of parse
6. Never raise — return error VenueAdapterResult
7. Register in `ALL_ADAPTER_IDS` in `services/real_source_acquisition.py`
8. Add to `_build_adapter()` factory
9. Add fixture data (synthetic only)
10. Add tests covering: fixture parse, authority prohibitions, failure state
