# Kairoskopion merged W1/W2/W3 + source-Factory instructions

The two sections below apply cumulatively: the general Factory contract and the specific W3 scientific-return constraints. Neither grants new owner authority.

# Kairoskopion / TRIMURTI — repository agent instructions

This is the Kairoskopion product repository: an evidence-first publication
positioning subsystem in the LitOps / WhiteCrow / Artikl / Kairon / Indago
ecosystem. Its README and explicit existing architecture take precedence over
guesswork from component names. These instructions give repository-local
operating constraints; they confer NO extra owner or production authority.

## Before touching code

- Read the relevant issue and relevant existing modules/tests. For the
  three-talk case use Kairoskopion #33 (TRM-074), #41 (TRM-073), and #43
  (80 venue-qualified source-version routes); the single-command bridge
  runbook is docs/operations/FACTORY_SOURCE_RESEARCH_STAGE.md.
- Check the actual Git branch, commit SHA, dirty status, and upstream
  dependencies. Use an isolated worktree for review/edits. Never erase
  another agent's unstaged changes or silently merge stacked draft PRs.
- Owner-authorized delegated code/review operations route through the
  existing AIYE Executor Hub; do not bypass a blocked provider/owner gate.
  A read-only review may read code and synthetic test fixtures only.

## Knowledge, provenance and author controls

- Stable provider object ID + provider revision + exact source bytes/SHA
  are the capture identity. Filename, human title and modifiedTime do not
  certify a source, author, revision genealogy or scientific fact.
- A bounded text projection of Google Docs does not contain comments or
  external embedded-object bytes. Native Docs FULL_CONTENT_READ requires
  independently verified provider-bound structural snapshot and stable
  revision. Never silently promote missing comments/media to FULL.
- Preserve research-source depth: index/abstract != sections != full
  paper; an editorial != a research article; a published issue != an
  active CFP; a bibliography claim != a located passage anchor.
- SourceNote, context_pack and provisional Evidence are NOT an author
  approved ArticleSeed, certified Field, qualified TargetWorld, manuscript,
  submission-ready package, or permission to mutate the canonical WORLD.
- No author-decision inference from a newer file, renamed draft, ChatGPT
  answer, editor prestige, or the presence of a prior source. Author-HOLD
  must remain HOLD until an explicit, anchored owner decision.
- All external journal submissions, emails, production writes, OAuth
  credential changes and scientific source publication are forbidden
  without specific owner authorization. No source text in GitHub issues,
  public PR comments, logs or test fixtures; redact secret paths/content.

## Engineering and acceptance

- Reuse the existing source intake, Kairon OpportunityGraphStore,
  LitOps registry, WhiteCrow importer and TRM040 NativeGoogleDocsTransport.
  Do not create a parallel OAuth client, data authority or article engine.
- A new source-case input uses fixed IDs and typed manuscript carriers.
  Model partial failure, zero-duplicate replay, immutable checkpoints,
  stale provider revisions and counterexample tests. Report each read
  boundary and independent input/output SHA. A prior pinned snapshot
  can be replayed; that DOES NOT prove current provider freshness.
- Test the module with pytest, use read-only independent test invocations,
  and record actual PASS/FAIL, local vs CI vs production separately.
  Integration tests with missing installed packages must not be called
  live passes. Track raw sensitive data only in authorized private stores.
- State source-stage acceptance, scientific WhiteCrow/Artikl acceptance,
  venue qualification and production deployment as four distinct claims.
  The >=80 W12-equivalent routes target in #43 is still open; a corpus
  source count or journal count is not that achievement.

## Operating test handles

Source-only CLI: scripts/run_factory_source_stage.py
Native Docs adapter: src/kairoskopion/integrations/native_docs_capture.py
Source intake: src/kairoskopion/services/talk_corpus_intake.py
Core tests: tests/test_factory_native_manifest_batch.py,
tests/test_native_docs_source_capture.py,
tests/test_corpus_factory_entry.py and tests/test_trm073_research_stage.py.

Use the pinned installed LitOps/WhiteCrow/Trimurti host dependencies for
their integration tests, not test-local fake acceptance objects. The
operator environment, test evidence and private receipt are in the
linked worktree/runbook; no production deployment is implied by a green
local pytest suite.

---

# Kairoskopion / Kairon — TRM073 AIxSRT W3 runtime

## Entry order for this project-local developer worktree
1. Read `CLAUDE.md` in full. Its source/provenance boundary and no-submission constraints govern work.
2. Read `docs/PROJECT_STATUS.md`, `docs/SPEC_COVERAGE_MATRIX.md`, `docs/BACKLOG.md`, `docs/MILESTONES.md` as appropriate; where stale, inspect code/tests and report the difference.
3. Read `docs/operations/TRM073_VENUE80_FIRST_SLICE.md` and the current existing `src/kairoskopion/services/trm073_research_stage.py`, `src/kairoskopion/kairon_provider/opportunity_graph.py`, `src/kairoskopion/kairon_provider/target_world_catalog.py`.
4. The specific owner override for this work is GitHub epic https://github.com/Stimurid/Kairoskopion/issues/43, W2 defect https://github.com/Stimurid/Kairoskopion/issues/41, stacked implementation https://github.com/Stimurid/Kairoskopion/pull/44.

## Scope / identity
This is the Kairoskopion provider within LitOps–WhiteCrow/Artikl–Kairoskopion (Kairon) TRIMURTI ecosystem. The immediate task is **TRM073 AIxSRT W3 runtime**: multi-head, multi-venue scholarly discovery intake and backward challenges to prior research heads A/C. This worktree is a derived implementation checkout, *not* a canonical semantic WORLD or an autonomous research organ.

Private owner input (read-only; not to commit): `C:\projects\trimurti\_ops\T3-TALK-20261019\TRM073_W2_SCIENCE_INPUT_20261020.json` and `TRM073_W3_SCIENCE_INPUT_20261020.json`. The WORLD research dossier is https://docs.google.com/document/d/1tRMfUq4iHtGvjObJczKxQgjDUMKDjgTOTFx-ST6bhDM/edit .

## Non-negotiable boundaries
- Implement on the existing `OpportunityGraphStore` / `TargetWorldCatalog`. Never substitute a new monolithic research engine or treat manuscript sources as controlled by Kairoskopion.
- Retain every source DOI/URL/genre/read_depth and NEGATIVE verdict. AB​​STRACT/SELECTED_HTML is not FULL_TEXT; a published old issue is not a live CFP; publisher-native != externally cited or institute hosted.
- Source heads `HEAD-01` (A) and `HEAD-03` (C) are *not* author-admitted ArticleSeeds; any challenge to original text without exact passage identity must remain `SOURCE_ANCHOR_PENDING` and author-gated.
- ArticleSeed=0, W12-qualified routes=0, author approval=HOLD, WORLD canonical mutation=0, SEND=0 until owner and Artikl science gates genuinely pass. Preserve full transcripts and coauthor/private rights; no private packet in Git.
- No production writes/deployment or SSH attempts. Do not alter adjacent PR #36 untracked files. Do not use 302.ai or open external model gateways. No generated fake receipts.
- Hub-managed worktrees, Hub-run test suite pinned in `.aiye/pipeline.json`, independent reviewer mandatory; return evidence of an actual W2+W3 pair of real replay runs (not just synthetic tests).
- User's outcome: any subsequent corpus must be able to use the runtime without a ChatGPT operator. An unsupported W4 schema must fail closed; do not claim the full goal is accepted before nontrivial future-corpus replay.

## Current known local baseline
Base commit contains TRM073 first runnable W2 slice, documented and independently replayed on AORUS. W2 -> 8 publisher records, 6 scientific objections, 6 FieldReopen proposals, idempotent local receipt; W3 -> `unsupported research packet schema` exit 2 before changes. Fix the latter without breaking the former. All local test paths must respect Windows. This is a code work assignment; not a request to send article submissions.
