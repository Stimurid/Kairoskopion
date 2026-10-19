# TRM-074 — Three-talk corpus intake and Kairon research handoff

Status: **CODE + LOCAL REAL-CORPUS PARTIAL**. This operation is staged on PR #36
(derived from the owner-scoped private research PR #32). Do not describe an
unmerged draft as deployed or universally available.

## Existing owner runtime reused

- `kairoskopion.adapters.source_intake.register_local_source` — local source
  extraction and `SourceSnapshot` with stable source ID.
- `source_snapshots` and `talk_discussion_events` under existing JSONL registry.
- `kairoskopion.kairon_provider.opportunity_graph.OpportunityGraphStore` —
  research-stage immutable `Evidence` record readback. No `ArticleSeed` created.
- Manuscript/venue-fit and submission factory remain separate subsequent gates.

## Replaying from authorized real data

An independent operator must obtain the exact owner-authorized case manifest
and all referenced captured source bytes. A Drive URL, chat title or file name
is insufficient. Connectors/permissions must be revalidated by the operator.
Keep private source text, chat exports, Word files and media off public Git.

On Windows from the PR #36 checkout:

```cmd
set PYTHONPATH=src
python scripts\run_trm074_three_talk_intake.py ^
  --manifest C:\path\to\private\case-manifest-v2.json ^
  --storage-root C:\path\to\private\t3-runtime
python scripts\run_trm074_research_stage_handoff.py ^
  --storage-root C:\path\to\private\t3-runtime
python -m kairoskopion.cli ^
  --storage-root C:\path\to\private\t3-runtime inspect-storage
certutil -hashfile C:\path\to\private\t3-runtime\talk_corpora\T3-TALK-20261019\case_ledger.json SHA256
certutil -hashfile C:\path\to\private\t3-runtime\talk_corpora\T3-TALK-20261019\research_stage_handoff.json SHA256
```

Do not copy previously observed digests as a substitute for recalculating
on the target host. For idempotence, execute both scripts twice and verify
unchanged digests and no duplicate SourceSnapshots/discussion events/Evidence.

Expected private outputs:

- `registries/source_snapshots.jsonl` — typed, pinned original source identities.
- `registries/talk_discussion_events.jsonl` — exact quotes / provenance only,
  speaker attribution **UNVERIFIED_FROM_TEXT_EXPORT**.
- `talk_corpora/T3-TALK-20261019/case_ledger.json` — source inventory,
  version edges, bounded textual deltas, recognized version-label collisions,
  documentary decision events and unread media.
- `talk_corpora/T3-TALK-20261019/research_stage_handoff.json` — graph
  `Evidence` IDs and exact revisions, original WORLD link, held research status.
- `kairon_provider/opportunity_graph/records/` — immutable, replayable Evidence.
  All emitted evidence has `read_depth=SECTIONS`, not full scientific read.

## Cross-domain and authority gate

Downstream research may load the exact Evidence ID/revision from
`OpportunityGraphStore(storage).get("Evidence", id, revision)`. Evidence
supports source location and candidate investigation. It is NOT journal
policy proof, an Indago completed hunt, a scholarly claim, or an author
decision. The standalone AI×SRT WORLD is a read-only external reference;
the Factory never rewrites it.

Case distinctions to preserve:
- two different documents may share a title or version label;
- file title version and internal title version may conflict;
- author-adopted conceptual baseline ≠ approved later manuscript;
- a Word **body text extraction** excludes embedded DOCX comment threads;
- 32 image-backed Slides are structurally addressable but NOT semantically
  read because their native text layer is empty;
- raw transcript, reconstruction, speech script and recorded performance
  are separate carriers. No original audio has been certified here;
- a delta with >12 change blocks emits an explicit `omitted_blocks` warning;
- external submissions are NEVER allowed by these commands.

## Test contract and acceptance boundaries

```cmd
set PYTHONPATH=src
python -m pytest -q tests\test_trm074_talk_corpus_intake.py tests\test_trm074_research_stage_handoff.py tests\test_opportunity_graph.py tests\test_opportunity_execution_handoff.py tests\test_submission_package_factory.py tests\test_intake_attempt_metadata.py tests\test_intake_input_limits.py
```

The real-case operator ledger is private. Tests use independent synthetic
fixtures and do not replicate user documents in a public repository.

Still open: direct Drive connector→installed worker adapter; chat backup
conversation ID attribution; embedded DOCX comments and visual slide/image
content; verified recorded performances; independent cold replay on a second
host; TRM-073 topic→author→venue research cycle; WhiteCrow/Artikl semantic
review and user scientific approval; secure identity/ACL and production
deployment. Any external journal submission remains HUMAN_ONLY.
