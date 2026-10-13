# Bounded publication import runner

Status: source and tests written; host pytest and CI pending. No P06/P07 live
acceptance is claimed. This is the offline import seam over PR19, not an export
engine, semantic author, QA producer, or submission actuator.

## Commands

From the repository with Python >=3.11 and the package installed:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m kairoskopion.kairon_provider.publication_runner --manifest private_inputs/P06/manifest.json --approval private_inputs/P06/approval.json --input-root private_inputs/P06 --catalog-root private_inputs/catalog --output-root private_inputs/runs/P06
python scripts/run_publication_controls.py --input-root private_inputs --catalog-root private_inputs/catalog --output-root private_inputs/runs/controls
python -m pytest tests/test_publication_runner.py tests/test_submission_package_factory.py tests/test_submission_gate.py -q
python -m pytest --tb=short -q
```

All directories must be explicit, authorized local workspace directories. The
catalog is a local, operator-provided copy, never a production root. These
commands do not fetch files or call an endpoint. Missing imports produce exit 2
and `BLOCKED_NEEDS_ADAPTER`. Failed or stale evidence produces exit 2 and
`BLOCKED`. Successful verification produces exit 0 and `DRY_RUN_COMPLETE`;
this means a request is available for human review, not live readiness.

One worker per output root, serialized by the coordinator, is required by PR19.
After confirming the old worker stopped, repeat the same command with `--resume`.
It resets unfinished claims with `store.recover`, preserves terminal evidence,
and writes a deterministic `recovery-<before-state-digest>.json` containing
before/after digests. Every retry reopens and verifies input bytes and catalog
identity/status; it never trusts the cached phase alone. An in-progress claim
without `--resume` blocks. This runner does not provide a scheduler or lock lease.

`--allow-fixtures` explicitly enables manifests marked `FIXTURE`. Their only
request output is `fixture_gate_request`, status `FIXTURE_DRY_RUN_COMPLETE`.
`finalization_request` remains null. Both modes always report
`live_acceptance=NOT_CLAIMED` and no external submit events.

## Input and trust contracts

The exact interchange schema is [publication-import.schema.json](../publication-import.schema.json).
The root describes the manifest; `$defs.receipt` and `$defs.approval` describe
separate JSON files. Runtime enforces the safety bindings without requiring
the jsonschema package; producers can validate the complete schema separately.

- `spec` contains the existing factory's explicit article, venue, immutable
  authoritative sibling, frozen TargetWorld, submission skeleton, policy refs,
  route and author-field statuses. The import adapter requires a SHA-256 even
  when a revision exists; a revision-only source needs a resolver adapter.
- `sibling_file` and every artifact `file` have a relative `path` under
  `--input-root` and lowercase SHA-256 of exact bytes. Absolute paths and resolved
  traversal outside the root are rejected. No URI is automatically opened.
- Each of the four artifact kinds has `version`, `file`, `source_sibling`, and
  three `qa` file pointers. The adapter always requires all four kinds and all
  three QA types; input policy lists cannot downgrade this requirement.
- QA receipts bind article, kind, exact artifact ref/revision/hash, source
  sibling, TargetWorld ID/digest, policy refs, evidence mode, producer ref,
  PASS/FAIL and nonempty evidence-file pointers. VISUAL_RENDER additionally
  requires `page_count` and exactly pages 1..N in order, each with file/hash.
  The accepted producer attests the page count and the actual inspection;
  file hashing does not perform semantic, privacy, or visual QA.
- The independently supplied approval file pins the canonical manifest digest,
  explicitly approved QA receipt byte hashes, an authority reference, mode,
  `APPROVED_FOR_LOCAL_DRY_RUN`, and a timezone-aware expiry. Canonical digest is
  SHA-256 of UTF-8 JSON with sorted keys, `ensure_ascii=False`, separators
  `(',', ':')`, matching PR19 `_digest`. QA pins hash original receipt bytes.
- Approval is an **operator trust input**, not a digital signature or an identity
  authentication system. A trusted coordinator must supply it after the human
  accepts the source/export lineage, evidence producers, policy, route and
  author facts. Never create REAL approvals from fixture receipts. The runner
  cannot establish that an arbitrary self-authored approval is authoritative.
  It never generates approvals or PASS receipts itself.
- Catalog package snapshot bytes are rehashed with the existing catalog digest
  function, and both package and current index entry must match the frozen
  expected ID/digest/status. Currentness of the offline copy is bounded by the
  approval's scope and expiry; it is not a live provider freshness claim.

Exports, page images and QA reports must already exist. Unknown or inaccessible
source, exporter, QA producer, or evidence is `BLOCKED_NEEDS_ADAPTER`. The human
owns semantic and publication acceptance. Source text is never transformed.

## Saved evidence and API compatibility

`output-root/` contains the shared PR19 factory store and exact approved receipt
bytes in `evidence/receipts/`. `output-root/<canonical-manifest-digest>/` contains
opaque content-addressed imported bytes in `imports/`, recovery receipts and
`result.json`. Changing the manifest cannot bypass terminal artifact/QA
immutability: factory identity stays shared across manifest revisions. Corrected
terminal materialization/QA requires a new versioned sibling or policy input.
This local job bundle
is not a new canonical manuscript store. Artifact refs retain original lineage;
the imported bytes are located by their SHA in `imports/`. The source sibling
itself is checked in place. The operator must retain the input bundle for resume.

Atomic writes flush/fsync the temporary file and replace its destination. As in
PR19, this protects process interruption, not all filesystem/power-loss modes.
`current.json` at the output root is first replaced by CHECKING with null
requests, then evidence is reverified. A later blocked run removes the current
request even when the manifest changed. Per-execution result files and historical
PR19 `handoff_request` remains historical state, not a current delivery permit.
Only the successfully revalidated output-root `current.json` is the handoff surface.

`factory.build_finalization_request` returns Python gate kwargs. The HTTP model
instead needs `target_world_package_id`; the adapter converts that field and
leaves the existing API/gate unchanged. It never POSTs this request. A consumer
must revalidate current catalog and human/route evidence before any later use;
the current API does not authenticate imported QA receipts. Do not bypass the
runner's evidence checks by treating the gate alone as receipt verification.

## Reuse search and PR19 review

Search scope was the assigned worktree, including `src`, `scripts`, tests and
operational docs. Separate Artikl/WhiteCrow repositories and live providers were
outside the delegated scope and were not read or invoked.

| Existing surface | Finding and disposition |
| --- | --- |
| `kairon_provider/submission_package_factory.py` | Reused start/begin/record/recover/handoff unchanged. ID binds normalized sibling, target, policies and gates; terminal artifacts and QA immutable. Unique temp + fsync + replace handles interrupted writes under serialized-worker assumption. |
| `kairon_provider/submission_gate.py` | Reused fail-closed gate. Gate normalizes QA by artifact ref and does not open evidence; strong byte/version/provenance verification belongs to adapter + PR19. |
| `kairon_provider/target_world_catalog.py` | Reused frozen package lookup/current index and snapshot digest; no import or promotion performed by runner. |
| `api/kairon_provider.py:SubmissionPackageFinalizeRequest` | Existing HTTP body differs from PR19 Python kwargs; package ID conversion added and covered by a model compatibility test. |
| `integrations/whitecrow_bridge.py` | Patch-candidate JSONL exporter, not a manuscript DOCX exporter or QA producer. Not repurposed. |
| `integrations/whitecrow.py`, `kairon_provider/artikl_projection.py` | Semantic projection boundaries; no executable artifact/QA producer found. Preserved. |
| `adapters/source_intake.py` | Extraction/intake does not prove export, privacy scrub or full-page rendering; not used as a QA substitute. |
| `kairon_provider/batch_runtime.py`, `batch_executor.py` | Existing qualification job execution has a different contract; no new global scheduler introduced. |
| `docs/operations/CURRENT_WORKING_STATE.md` | Historical P06 manual proof and P07 missing-materialization boundary. Read as historical evidence, not a new live test result. |

PR19 remains a reference-only store with no authenticated receipt verifier,
file opening or catalog freshness check. This adapter supplies bounded local
import verification; a live export/QA producer is still absent from this scope.

## P06/P07 evidence matrix

| Article | Stage | Blocked | What source now supports | Evidence |
| --- | --- | --- | --- | --- |
| P06 | Input acquisition / artifact import | No authorized real sibling/export/QA bundle supplied; historical route BLOCKED and author_fields OPEN must not be overwritten | Local versioned-byte import, QA binding, restart and gate request construction when all inputs are accepted | `tests/test_publication_runner.py`, fixture-only P06 control; execution pending |
| P07 | Independent reuse | Same missing real input/QA bundle; no live reproducibility claim | Same runner and separate deterministic execution identity | Same test file, fixture-only P07 and paired harness; execution pending |

The fixture DOCX files are ZIP/XML containers with synthetic text. The fixture
render evidence is explicitly synthetic text, not a real page render or visual
inspection. The tests exercise receipt verification plumbing only.

Host validation and GitHub CI must run before review acceptance. Existing
`.github/workflows/tests.yml` collects the new pytest module on Python 3.11–3.13.
No production, OpenClaw/HESTIA, secrets, remote submission, merge or deployment
is part of these commands.
