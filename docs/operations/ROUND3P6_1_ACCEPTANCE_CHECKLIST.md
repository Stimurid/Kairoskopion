# Round III-P6.1 — Acceptance Checklist

## Product-path proof

| Requirement | Status | Evidence |
|---|---|---|
| Discipline: accepted record → canonical, no LLM | PASS | `test_case_discipline_matcher_uses_registry`: registry_first=True, usage_status=canonical |
| Discipline: miss → acquisition task, no source facts | PASS | `test_miss_creates_acquisition_task`, `test_miss_produces_no_source_facts` |
| VenueFunnel: accepted venue → known_corpus_candidate | PASS | `test_accepted_venue_returns_as_known_corpus`: record_id/source_status/review_status/usage_status/evidence_refs |
| VenueSection: independent from parent | PASS | `test_section_candidate_independent`, `test_section_scope_not_substituted_by_parent` |
| VenueMatrix: provenance enrichment | PASS | `test_case_venue_matrix_enriches_candidates`: canonical enriched, unknown warned |
| VenueFactExtraction → registry | PASS | `test_case_investigate_venue_creates_registry_records`: provisional records created |
| Metrics: per db/year/category, no scalar | PASS | `test_metrics_per_db_year_category`, `test_no_scalar_quartile` |
| Provisional never canonical | PASS | `test_provisional_never_appears_canonical` |
| LLM never promotes to canonical | PASS | `store_venue_extraction` creates provisional only, `record_usage_status` enforces |

## Bypass audit

| Requirement | Status |
|---|---|
| All product-path agent calls audited | PASS — 13 direct call sites assessed |
| Registry-relevant calls wired | PASS — DisciplineMatcherAgent (Track 3), VenueProfilerAgent (Track 7) |
| Remaining direct calls documented safe | PASS — non-registry agents (article, fit, compliance) |
| VenueDiscoveryAgent bypass documented | PASS — P6.2 candidate |
| Pipeline bypass documented | PASS — legacy/batch path |

## Integration contract compliance

| Rule | Status |
|---|---|
| canonical = fact | PASS |
| provisional = show with warning | PASS |
| rejected = exclude | PASS |
| unknown = create task | PASS |
| LLM never promotes | PASS |
| source facts from packets/adapters/user only | PASS |
| No model-memory source facts | PASS |
| Section scope independent | PASS |
| Metrics per db/year/category | PASS |

## Deferred items

| Item | Reason | Target |
|---|---|---|
| UI review panel for registry status | API visibility exists (`_registry_status`), UI component not built | P6.2 |
| VenueDiscoveryAgent → registry ingest | Discovery creates candidates, not registry records | P6.2 |
| Pipeline registry wiring | Batch/CLI path, not interactive case path | P6.2 |

## Final verdict

**P6.1 PASS** — registry integration wired into all specified product paths.
37 new tests, 2719 total tests passing, zero regressions.
