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
