# P10 Provisional Semantics Audit

**Date:** 2026-07-09
**Branch:** `feature/p10-operational-harvest-final`

---

## Invariant

`verification decision = keep_provisional` must never become accepted registry truth.
The 87 P10 records are provisional candidates for operator review — not accepted sources.

## Storage paths

| Purpose | Path |
|---|---|
| Provisional venue records | `data/seed_registry/education_ai_russia/p10_harvest/provisional_venue_records.jsonl` |
| Provisional candidate export | `data/seed_registry/education_ai_russia/p10_harvest/provisional_candidate_export.jsonl` |
| Verification decisions | `data/seed_registry/education_ai_russia/p10_harvest/verification_decisions_final.jsonl` |
| Review packets | `data/seed_registry/education_ai_russia/p10_harvest/review_packet_final.{md,jsonl,tsv}` |
| Harvest summary | `data/seed_registry/education_ai_russia/p10_harvest/harvest_summary_final.json` |
| Domain classification | `data/seed_registry/education_ai_russia/p10_harvest/domain_classification.json` |
| Acquisition tasks | `data/seed_registry/education_ai_russia/p10_harvest/acquisition_tasks_final.json` |

## Status fields

All 87 records have:

- `source_status`: `provisional`
- `review_status`: `pending`

## Mislabelling corrections

| Location | Before | After |
|---|---|---|
| `data/.../registry_ready_output.jsonl` | filename implied "registry-ready" | renamed to `provisional_candidate_export.jsonl` |
| `scripts/run_p10_harvest_final.py` | "registry-ready outputs" | "provisional candidate export" |
| `harvest_summary_final.json` | key `registry_ready` | key `provisional_candidate_export` |
| `tests/test_p10_harvest_final.py` | class `TestRegistryReadyOutput` | class `TestProvisionalCandidateExport` |
| `docs/operations/P10_OPERATOR_SMOKE.md` | "Inspect registry-ready output" | "Inspect provisional candidate export" |
| `docs/operations/P10_OPERATIONAL_SCOPE.md` | "Produce registry-ready outputs" | "Produce provisional candidate export" |
| `docs/operations/P10_OPERATIONAL_HARVEST_FINAL_REPORT.md` | heading "Registry-ready outputs" | heading "Provisional candidate export" |

## Accepted truth count

**0** — no records were promoted to accepted status.

## Provisional candidate count

**87** — all records remain provisional with `review_status: pending`.

## Tests added

6 new tests in `TestProvisionalSemanticsInvariants`:

1. `test_all_87_retain_provisional_status` — verifies all 87 records have `source_status == "provisional"`
2. `test_accepted_count_is_zero` — verifies no accepted records exist
3. `test_provisional_records_not_in_accepted_registry` — verifies a fresh RegistryHub contains no venue records
4. `test_export_preserves_provenance_and_evidence` — verifies all records have provenance and evidence_refs
5. `test_noise_records_not_promoted` — verifies noise-tier records remain provisional/pending
6. `test_unclassified_records_not_promoted` — verifies unclassified records remain provisional/pending

## Verdict

No records were previously mislabelled as accepted. The terminology corrections prevent future misinterpretation. All 87 records correctly remain provisional candidates for operator review.
