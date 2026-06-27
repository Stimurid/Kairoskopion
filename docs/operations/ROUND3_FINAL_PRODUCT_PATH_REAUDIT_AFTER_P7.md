# Round III — Final Product-Path Invariant Re-Audit After P7

**Date:** 2026-06-27
**HEAD:** `7ecf823`

## Scan Results

Pattern searched:
```
VenueDiscoveryAgent|VenueFunnelPlanner|VenueFamilyContextBuilder|VenueMatrixAssessor|
VenueProfilerAgent|ManuscriptVenueFitPipeline|RegistryIntegrationService|
discipline_lookup|store_venue_extraction|enrich_candidates_with_provenance|
propagate_status|review-queue|record_usage_status
```

### Hits: 11 locations across 4 files

| file | line | symbol | path type |
| ---- | ---: | ------ | --------- |
| `artifacts.py` | 39, 156 | `ManuscriptVenueFitPipeline` | Artifact generation — reads pipeline output |
| `persistence.py` | 31, 64 | `ManuscriptVenueFitPipeline` | Result persistence — saves pipeline output |
| `cli.py` | 62, 64, 67 | `RegistryIntegrationService`, `RegistryHub` | CLI helper — creates registry service |
| `cli.py` | 134, 160, 219, 274 | `ManuscriptVenueFitPipeline` | CLI commands — runs pipeline with registry |

### API path (cases.py) — pre-existing from P6

| line | symbol | purpose |
| ---: | ------ | ------- |
| 44 | `RegistryIntegrationService` import | Case orchestrator dependency |
| 89, 96 | `RegistryIntegrationService` constructor | Case accepts optional registry |
| 640 | `discipline_lookup` | Disciplinary pathway uses registry |
| 912 | `store_venue_extraction` | investigate_venue stores to registry |
| 942 | `propagate_status` | Status propagation after venue investigation |
| 1246 | `propagate_status` | Status propagation in discovery path |
| 1695 | `store_venue_extraction` | Batch venue processing stores to registry |
| 1714 | `propagate_status` | Batch processing status propagation |

### Registry router (registry_router.py) — pre-existing from P6

| line | symbol | purpose |
| ---: | ------ | ------- |
| 17 | `record_usage_status` import | Status computation |
| 59, 71, 89, 95, 113, 126, 141 | `record_usage_status` | Applied to all record responses |
| 133–134 | `review-queue` route | GET endpoint for review queue |

## Invariant Verification

| invariant | status | evidence |
| --------- | ------ | -------- |
| Case product path protected | PASS | `cases.py` uses `RegistryIntegrationService` (P6 wiring, unchanged by P7) |
| discover_venues protected | PASS | `cases.py:1246` propagates status through registry |
| CLI pipeline protected | PASS | P7.3 wired `registry_service` to both `cmd_run_fixture` and `cmd_run_local` |
| Review queue available | PASS | `registry_router.py:133` serves `/review-queue`; UI panel consumes it |
| No new unprotected venue/discipline fact path added | PASS | P7 added no new venue/discipline creation paths — only wired existing pipeline to existing registry |

## New paths added by P7

Only P7.3 added a new registry integration path:
- `cli.py` → `ManuscriptVenueFitPipeline(registry_service=...)` → `store_venue_extraction(source_type="pipeline_venue_profiler")`
- This stores as **provisional** — no canonical promotion
- Fault-tolerant — registry failure does not crash pipeline

## Verdict: PASS

No new unprotected fact paths. All existing protections intact. P7.3's CLI wiring follows the same pattern as the P6 API path.
