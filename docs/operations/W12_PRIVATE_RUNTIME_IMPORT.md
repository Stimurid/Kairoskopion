# W12 research-stage → user-scoped runtime import (staging only)

**Status:** CODE_ONLY / NOT_DEPLOYED / NOT_ARTIKL_ADMITTED / HUMAN_SEND_ONLY.

Related: [Indago #23/#24](https://github.com/Stimurid/Kairoskopion/issues/24), integration [PR #31](https://github.com/Stimurid/Kairoskopion/pull/31), private source admission
`docs/handoffs/INDAGO_W12_PRIVATE_SOURCE_ADMISSION_20261013.md`.

## Exact permitted source

The private original W12 XLSX was independently admitted in its **owner-only** Drive.
The private staging ZIP is not public and must not be committed, uploaded to CI
artifacts, or printed in logs.

- Source ZIP SHA-256: `9c7efd9396c3b95c9a6beb64058a84966d347b7775379a1aa211590ba61c377c`.
- Original W12 XLSX SHA-256: `c47143b4d9f4f3186add6473246e45cde48d9f414e8a8d382cb04bf6b6f9f73f`.
- Expected source SQLite SHA-256: `339ec939387e6bd4225614fbbb9b5307af7485df2033f2c1386c54576e10c9f3`.
- The private archive remains at [owner-only Google Drive](https://drive.google.com/file/d/1jL_9QxMbeXZnBWIEPm7kyv5J3e5U6IMU/view).

## Operator procedure

1. Authenticate as the intended research owner in a staging Kairoskopion instance.
   **Current session authentication is staging soft-auth; do not deploy a
   private research import to a public production host without hardening it.**
2. The operator downloads the owner-approved ZIP into a private local host path.
   Verify file ACLs. Do not put the archive in the Git checkout.
3. Find the existing authenticated `user_<12-hex>` workspace under
   `KAIROSKOPION_DATA_DIR/users/`; **never create a new identity solely to import**.
4. With the application's Python environment, execute:

```powershell
$env:PYTHONPATH = "src"
python scripts/import_w12_private_research.py `
  --zip "C:\Private\W12_MAI_PRIVATE_RESEARCH_STAGE_20261013.zip" `
  --user-id "user_000000000000" `
  --zip-sha256 "9c7efd9396c3b95c9a6beb64058a84966d347b7775379a1aa211590ba61c377c" `
  --xlsx-sha256 "c47143b4d9f4f3186add6473246e45cde48d9f414e8a8d382cb04bf6b6f9f73f"
```

The `user_000000000000` value is an **example**, not the owner's account ID.
This is not a remote upload API. The trusted operator must use the correct
existing user and locally authorized artifact.

5. Read back `GET /api/opportunities/research-stage` under that user's
   authenticated Bearer session and compare the SHA and counts.
6. The Russian `Возможности → Исследовательский W12` tab shows only
   research rows, source sheet anchors and blocker labels, never an automatic
   SEND control. Other users' endpoints must stay empty.

## Admission contract

The adapter verifies ZIP hash, original source hash, member whitelist, CRC,
uncompressed bound, SQLite checksum/integrity, foreign keys, all 728
source-row digests, 21 sheets and the six distinct W12 object families.
It rejects falsified `FULL_TEXT`, accepted editorial policy, accepted independent
Article objects, author decisions or external sends. Same-byte restaging is
idempotent, different ZIP versions cannot silently overwrite admission.

One expected staging projection: 6 directions, 27 research versions, 81
candidate venues, 53 **unqualified** editorial routes, 67 planned actions,
728 source snapshots; all 53 route statuses `POLICY_UNVERIFIED`,
all author decisions `HOLD`, all Artikl admissions 0, and submissions 0.

**No** `ArticleSeed`, `ArticleOpportunity`, `TargetVariant`, route-accepted
QA or submission event is created from the staged research corpus. Author
fields and route-contact details are not projected into the read API.

## Verification and remaining gates

- Run synthetic fixture tests:
  `PYTHONPATH=src pytest tests/test_w12_private_runtime.py tests/test_opportunity_portfolio_api.py -q`.
- Check authenticated per-user GET, duplicate import, changed SHA, mutated DB,
  no-source state, fake route acceptance and cross-user isolation.
- Private real-archive verification can run **only** on an authorized isolated
  host. It is not part of public CI and must not emit raw rows.
- Current API/session scheme is **soft-auth** and not adequate by itself for
  production-grade confidential source access.
- Priority journal policies, genuine FULL_TEXT exemplars, author/coauthor
  decisions, Artikl independent-article admission, P06/P07 QA/render receipts
  and any external submission remain separate gates.

A code/CI PASS means only `PRIVATE_RESEARCH_STAGE_CODE_READY`.
It does **not** certify live runtime ingestion or journal readiness.
