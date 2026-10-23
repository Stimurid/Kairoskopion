# MAI W12: verified batch execution / 2026-10-20

## Implemented code

This change extends the existing Kairoskopion codebase. It adds a typed pre-author scheduler, source provenance importer and batch-first guard. The follow-up fix prohibits out-of-order completion or empty completion evidence. All explicit external SEND/SUBMIT actions remain human-only.

It also adds two real-data batch operations:
* `python -m kairoskopion.kairon_provider.w12_packets`: reads a caller-supplied authenticated sheet-derived W12 snapshot and creates one deterministic source-provenance editorial dossier per route, CSV/JSON, and a Russian HTML Kanban. External editorial events can be supplied as a separate local JSON file and are never generated from venue names.
* `python -m kairoskopion.kairon_provider.mai_w12_runner`: automatically calls **existing** `kairoskopion.cli run-local` over those dossiers, recording its diagnostics, fit, mismatch, risks, compliance, bibliography, traces and registry/vault artifacts. Cold replay uses stable input hashes, skips already executed unchanged routes. No separate article engine.

## Actual host acceptance

Input: authenticated Google Sheets W12 (original W12 53-route tab), explicitly derived JSONL snapshot; original 21-tab XLSX byte-equivalence **not** claimed.

* 53 source routes, six source families, 27 distinct meaning versions.
* Source-derived JSONL SHA256: `9210da3b761903795907e757950d24c65b99a312554578d0e49860ecde1b9a0c`.
* Actual output: 53 JSON source dossiers, 53 Russian markdown abstracts, Russian HTML board, CSV/JSON Kanban and file/hash manifest.
* User-approved external events imported separately on authorized AORUS: 1 confirmed received, 1 sent/unconfirmed, 6 Gmail drafts, 2 portal pre-submissions, 43 source-only routes. Raw private email content is **not in Git**.
* Existing Kairoskopion `run-local`: 53/53 local deterministic diagnostics completed using real source abstracts + unverified W12 venue summaries. First 10 ran, remaining 43 ran; cold full rerun got **53 CACHED / 0 duplicates**. Each job saved its own registries, vault cards and execution receipt. No LLM provider or new scholarly source reading in this deterministic mode.
* Strict phase negative probe: direct terminal jump rejects; empty scientific evidence rejects when the phase is current. A full 53-route real source plan with CLI `--status completed` but no evidence left 53 on explicit HOLD, 0 ready — correct fail-closed behavior.
* Targeted verification: 73 passing new/related tests. Full suite host: 3509 passed, 6 failed, 1 skipped, 8 deselected (remaining errors in unrelated corrupted file/existing fulltext fallback and Windows temporary file path tests). Treat full test suite as **NOT ALL PASS**.

This delivers an executed source-and-diagnostic batch, not automated completed scientific objections or venue-native fulltext research. No claims of full end-to-end independent article production, author approval or submission. Ready statuses require real organ receipts.

## Reproduce on an authorized machine

1. Obtain a permissioned export of the W12 53-route native Google Sheet with original A:M rows and a matching derived JSONL carrying source identity and row references. Keep raw data outside the public repository.
2. Prepare packets:

```powershell
$env:PYTHONPATH = 'src'
python -m kairoskopion.kairon_provider.w12_packets --source '<PRIVATE_ROOT>\W12_routes_derived_from_live_sheet.jsonl' --snapshot '<PRIVATE_ROOT>\W12_sheet_A1_M54_verified_read_snapshot.json' --output '<PRIVATE_ROOT>\packets'
```

3. Run existing diagnostic engine across 10 then 53 routes:

```powershell
python -m kairoskopion.kairon_provider.mai_w12_runner --source-packets '<PRIVATE_ROOT>\packets' --output '<PRIVATE_ROOT>\diagnostics' --limit 10
python -m kairoskopion.kairon_provider.mai_w12_runner --source-packets '<PRIVATE_ROOT>\packets' --output '<PRIVATE_ROOT>\diagnostics' --limit 53
```

4. Optionally rerender the read-only Kanban with `--analysis-root '<PRIVATE_ROOT>\diagnostics'` and `--outreach '<PRIVATE_ROOT>\private_editorial_events.json'`.
5. Open `<PRIVATE_ROOT>\packets\index.html` locally.

## Remaining engineering ownership

* Artikl/WhiteCrow: actually execute scholarly critique and claims genealogy, preserving FULL_TEXT vs abstract; produce signed/hashed stage receipts.
* Indago: automatically generate sustained scholarly hunts and preserve their records.
* Kairon: acquire actual venue-native texts, current CFP/AI rules and fit models; do not promote an old W12 URL to a current policy.
* Publication Factory: build English journal-specific proposals and run real QA, compare independent article identity and prevent exclusive duplicate submission.
* Control Board issue #40: persist cross-chat editorial events and joins into permanent operator UI.

Project issues #23, #24, #40, #45. No external email/manuscript delivery via these changes.
