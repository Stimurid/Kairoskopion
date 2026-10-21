# TRM-CITE-001 R1 source-reader seam (2026-10-21)

Status: **SEAM READY; OBSERVED requires operator-issued permits; scientific
acceptance unchanged**.

The R1 followup -> Z0 -> evidence-return seam now has a producer half:
an authorized source-reader provider that consumes the immutable
``*.request.json`` envelopes produced by ``citation_r1_batch.prepare``
and emits immutable ``*.return.json`` envelopes that the existing batch
consumer validates.  Provider never opens a URL or file without an
operator-issued permit; the immutable original manuscript is read-only.

## Files

- `src/kairoskopion/services/cite_r1_permits.py` — permit dataclass, load/save,
  host-allowlist validation, schema `trm-cite-r1-permit-v1`.
- `src/kairoskopion/services/cite_r1_reader.py` — `SourceReaderProvider`,
  `run_batch`, FIXTURE/LIVE fetchers, witness verification, replay ledger.
- `tests/test_citation_r1_reader.py` — 18 focused tests covering positive
  OBSERVED + every required negative path.
- `tests/fixtures/citation_r1_reader/caen_regula_i.txt` — Caen PUC
  Descartes Regula I facsimile (AT X 360 lines 5–14; phrase
  "quantumvis differentibus subjectis applicata").
- `tests/fixtures/citation_r1_reader/springer_bmc_2019.txt` — Springer OA
  BMC Medical Education 19:113 (2019) abstract placeholder.

## Permission model

A permit is one operator-authored JSON file under `permits/<work_order_id>.json`
with the following required fields:

```json
{
  "schema": "trm-cite-r1-permit-v1",
  "work_order_id": "wo_…",
  "provider": "OWNER_AUTHORIZED_PRIMARY_FIXTURE" | "OWNER_AUTHORIZED_LIVE_…",
  "authorized_by": "OWNER_AUTHORITY_<date>",
  "mode": "FIXTURE" | "LIVE",
  "fixture_path": "caen_regula_i.txt" | null,
  "live_url": null | "https://www.unicaen.fr/puc/sources/…",
  "work_id": "descartes-regulae-AT-10-360",
  "edition_id": "AT-X-1964",
  "witness_id": "puc-normandie-2024",
  "license": "CC0_TEST_FIXTURE",
  "expected_locator": "AT X 360 lines 5-14",
  "expected_passage": "quantumvis differentibus subjectis applicata",
  "read_depth": "ANCHORED_PASSAGE",
  "source_kind": "OPEN_PERMITTED_PRIMARY",
  "access": "READABLE_FULL"
}
```

Without a permit, a Z0 work order returns BLOCKED with
`PERMIT_NOT_FOUND_FOR_WORK_ORDER`.  Author-source R1-05 tasks (no Z0
anchor) return BLOCKED with `AUTHOR_SOURCE_NEED_NOT_IN_PROVIDER` until
the operator issues a separate task-level permit (not provided in this
slice).

## Live-fetch guard-rails

LIVE permits are gated by an allowlist of publisher hosts compiled in
`cite_r1_permits.DEFAULT_ALLOWED_HOSTS`:

- `unicaen.fr` / `puc.unicaen.fr` — Presses universitaires de Caen
  (Descartes Regulae open-access facsimile)
- `link.springer.com` / `springeropen.com` — Springer / BMC open-access

A LIVE permit whose host is not in the allowlist is rejected before any
network call; the reader surfaces
`LIVE_HOST_NOT_IN_ALLOWLIST`.  The fetch uses
`adapters.http_client.fetch_text_safe` — stdlib `urllib.request`, no
extra headers, no shell commands, `retry_count=0`, fixed `Accept`
header.  The provider never constructs a TLS-bypass, login form, or
session cookie.

## Cross-process correlation

Each produced `*.return.json` carries:

- `task_id`, `case_id`, `step_index` from the request;
- `source_sha256` from the original manuscript immutable audit;
- `work_order_ids` exactly as the request recorded them;
- `correlation_id` from the request envelope (the consumer will refuse
  any mismatch);
- per-item `intake_id`, `z0_case_id`, `work_order_id` from the Z0
  queue;
- top-level `provider`, `acquisition_authorized`, `read_depth`,
  `source_kind`, `access`, `license`, `work_id`, `edition_id`,
  `witness_id`, `locator`, `passage_id`, `byte_sha256`,
  `retrieved_at`, `citation_mode`, `transport_only`,
  `transport_provider_tag`, `transport_run_id`.

The provider's batch summary at `provider_summary.json` records the
audit sha and a per-reason counter.

## Required negative paths (all test-covered)

| Negative | Reason emitted | Test |
|----------|----------------|------|
| No permit | `PERMIT_NOT_FOUND_FOR_WORK_ORDER` | `test_no_permit_blocks_with_typed_reason` |
| Fixture file missing | `FIXTURE_FILE_MISSING` | `test_fixture_file_missing_blocks_with_typed_reason` |
| Wrong edition / witness | Permit dataclass rejects empty ids; provider records operator-recorded identity | `test_wrong_edition_and_witness_rejected` |
| Passage not in witness | `WITNESS_PASSAGE_NOT_PRESENT` | `test_passage_not_in_witness_blocks` |
| Duplicate anchor | `DUPLICATE_PASSAGE_ANCHOR_IN_WITNESS` | `test_duplicate_anchor_blocks` |
| Stale / future `retrieved_at` | Single-order validator | `test_stale_retrieved_at_via_invalid_datetime_rejected` |
| Replay (same source_sha + correlation_id) | `DUPLICATE_CORRELATION_REPLAY` | `test_replay_same_correlation_blocks` |
| Bad read depth | Validator inside `_build_observed` | `test_bad_read_depth_rejected` |
| Permissions denial | `LIVE_HOST_NOT_IN_ALLOWLIST` | `test_permissions_live_url_not_in_allowlist_blocks` |
| Spoofed work_order_id | `WORK_ORDER_NOT_IN_Z0_QUEUE` | `test_spoofed_correlation_request_rejected` |
| Compound request (multi work order) | `COMPOUND_REQUEST_PROVIDER_REJECTS` | `test_compound_request_returns_compound_blocked_not_synthesized` |
| Author-source need | `AUTHOR_SOURCE_NEED_NOT_IN_PROVIDER` | `test_author_source_need_blocks_without_explicit_task_permit` |
| Locator mismatch | Provider always uses recorded permit locator | `test_locator_rejects_recorded_locator_mismatch` |
| Original manuscript touched | Provider only emits returns | `test_provider_does_not_mutate_original_manuscript` |

## QA

`scripts/run_project_qa.py` enforces this worktree's `src` import and
runs pytest with a unique Windows basetemp.  Local count after this
slice: **3499 PASS / 8 deselected** (the 18 new tests live in
`tests/test_citation_r1_reader.py`).

```powershell
PS> python scripts/run_project_qa.py
import_origin=...\src\kairoskopion\__init__.py
3499 passed, 8 deselected in 79.02s (0:01:19)
```

The provider run is independent of the consumer: it does not require
the full operator-only input bundle.  The operator-grade handoff from
AORUS (manuscript SHA
`5a84d385e7122acb774ab3068fd3688b461d102ccadbef3449a5c0d55540c6fb`,
`408642a26e…` followup SHA, etc.) is unchanged.  When the operator
runs the batch on AORUS, this seam replaces the manual source
descriptor return and re-validates the same witness text via the
Caen fixture path (`run-batch` mode with `permits/...json` and
`fixtures/caen_regula_i.txt`).

## Scientific status

The seam is a transport proposal: it does not certify any citation.  V1
through V5 stay `NOT_CHECKED` in every state file.  Publication
readiness remains 0 until:

1. R2–R6 (manual review of the operator's five manual protocols +
   independent scientific review) — owner decision;
2. the operator records the R1-05 author-source permits (currently
   BLOCKED with `AUTHOR_SOURCE_NEED_NOT_IN_PROVIDER`) — pending owner
   confirmation.

## OPEN QUESTIONS

- Owner should decide whether R1-05 author-source permits should be
  added.  Default answer used here: **no**, so the 3 author-source
  tasks remain BLOCKED.
- Owner should confirm whether LIVE mode is appropriate for the
  authoritative Caen retrieval.  Default answer used here: **FIXTURE
  only**, because the operator's local Caen facsimile is the cited
  primary and the LIVE network round-trip is not required.
