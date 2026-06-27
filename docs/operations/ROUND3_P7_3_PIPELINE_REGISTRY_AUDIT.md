# Round III — P7.3 Pipeline Registry Wiring Audit

**Date:** 2026-06-27
**Commit:** `7ecf823`

## Files Changed

| file | change | lines |
| ---- | ------ | ----: |
| `src/kairoskopion/pipelines/manuscript_venue_fit.py` | Import `RegistryIntegrationService`, accept in constructor, store venue extraction after profiling, try/except fault tolerance | +19, -1 |
| `src/kairoskopion/cli.py` | `_resolve_registry_service()` helper, wire into `cmd_run_fixture` and `cmd_run_local` | +15, -2 |
| `tests/test_round3p7_pipeline_registry.py` | 7 tests across 3 test classes | +180 |

## Verification Checklist

| criterion | status | evidence |
| --------- | ------ | -------- |
| Pipeline accepts optional `registry_service` | PASS | `__init__(self, *, llm_provider=None, registry_service=None)` |
| CLI fixture path passes RegistryIntegrationService | PASS | `cli.py:160`: `ManuscriptVenueFitPipeline(llm_provider=llm, registry_service=registry)` |
| CLI local path passes RegistryIntegrationService | PASS | `cli.py:274`: same pattern |
| Venue extraction stores provisional records | PASS | `store_venue_extraction(venue_dict, source_url=None, source_type="pipeline_venue_profiler")` after venue profiling step |
| Errors are fault-tolerant | PASS | `try/except Exception: pass` wraps registry call; test `test_registry_error_does_not_break_pipeline` confirms |
| No silent canonical promotion | PASS | `store_venue_extraction` → `venue_extraction_to_provisional` — records stored as provisional, never canonical |
| Source/evidence refs preserved | PASS | `source_type="pipeline_venue_profiler"` passed; `source_url=None` (pipeline has no URL context) |
| Backward compatible | PASS | `registry_service=None` default means existing callers unaffected; `test_pipeline_works_without_registry` confirms |

## Test Coverage

| test class | tests | description |
| ---------- | ----: | ----------- |
| `TestPipelineRegistryWiring` | 4 | Mock registry: call verification, no-registry fallback, canonical_name presence, error tolerance |
| `TestPipelineWithRealRegistry` | 1 | Real RegistryHub on `tmp_path`: venue stored as provisional after pipeline run |
| `TestCLIRegistryHelper` | 2 | `_resolve_registry_service` creates service and registry dir |

## Test Run

```
7 passed in 0.39s
```

## Architecture Notes

- `_resolve_registry_service(root)` creates `RegistryHub(data_dir=root/"registry")` + `RegistryIntegrationService(hub=hub)`
- Registry dir created with `mkdir(parents=True, exist_ok=True)` — safe for first run
- Only venue extraction is stored; article extraction goes through the existing agent output path
- The try/except swallows all registry errors silently — acceptable for best-effort integration; pipeline completion is more important than registry storage

## Verdict: ACCEPT

Backward-compatible, fault-tolerant, tested with both mock and real registry. No silent promotion. CLI path wired at both call sites.
