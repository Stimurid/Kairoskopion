# FACTORY-FIRST: no-submit source/research stage, operator contract

## Meaning and acceptance

This is a single CLI orchestration over EXISTING Kairoskopion modules
talk_corpus_intake, talk_corpus_research_bridge, talk_corpus_reopen,
trm073_research_stage, and installed LitOps registry + WhiteCrow
litops_import and first_workset. It is not a new workbench.

Accepted locally: bounded source identities, version relations, quote
provenance, read-depth-limited Evidence, manual W1/W2 scientific-return
staging and actual WhiteCrow context receiver. Unaccepted: independent
live Indago search, WhiteCrow/Artikl scientific judgment, journal route
qualification, author acceptance, journal send, production deployment.

The owner target of issue #43 is at least 80 W12-equivalent distinct
ArticleVersion/problem x real editorial venue routes with source-anchored
opposition, official policy and precise genre; this stage produces ZERO.
Never confuse 8 publisher works with 8 routes or a published issue with CFP.

## General case, one command

Private sources must be captured by an authorized operator before the call.
A manifest TRM074_COLD_CASE_V1 has case_id, publication_send=DISALLOWED, a
bounded sources list of exact original Drive IDs/URLs/private local paths,
source carrier kind, version, read and author state, typed version edges,
and optional source-quote-anchored discussion events.

Run from combined PR36+PR44 checkout, on any new corpus with arbitrary
family codes (no artificial A/B/C case lock):

    set PYTHONPATH=src
    python scripts\run_factory_source_stage.py --manifest C:\owner-private\new-case\manifest.json --storage-root C:\owner-private\new-case\factory-stage

The operator may omit W1 and W2. Omission is reported as NOT_RUN, not as a
success. Content hash and exact original ID, not a title or last modified
time, determine identity.

## Full existing T3-TALK owner-private research-stage replay

    set LITOPS_SKIP_DOTENV=1
    set LITOPS_ROOT=C:\owner-private\T3-TALK\litops-isolated
    set PYTHONPATH=src;C:\projects\trimurti\whitecrow\conceptarticle;C:\projects\trimurti\whitecrow\whitecrow-skeleton
    python scripts\run_factory_source_stage.py --manifest C:\owner-private\T3-TALK\case-manifest-v3-w1.json --storage-root C:\owner-private\T3-TALK\factory-stage --research-packet C:\owner-private\T3-TALK\TRM073_W2_SCIENCE_INPUT_20261020.json --litops-root C:\owner-private\T3-TALK\litops-isolated --manual-w1-reopen

Only request manual W1 when the source ledger includes an actual, dated
research W1 notebook with required under-read warnings. A W2 research
packet is optional but its case_id must match the source manifest. Keep
the LitOps root separate from Factory and from primary LitOps storage.
Disable operator .env overlays with LITOPS_SKIP_DOTENV=1.

The entry validates manifests and research packet before mutating. On
replay it compares checkpointed manifest bytes, research packet bytes
AND re-extracts all currently supplied source captures with the EXISTING
source intake. If private source bytes changed under the same path or
the persisted source ledger changed, it must fail closed; changed input
requires new case/wave revision. Partial failures can resume using the
existing child-component idempotent registries.

## Actual unified run on AORUS (20 October 2026)

Independent worktree:
C:\projects\trimurti\_ops\T3-TALK-20261019\integrate-pr44-20261020

Private owner storage:
C:\projects\trimurti\_ops\T3-TALK-20261019\factory-single-command-v1

First single-command run: 34 original source snapshots; 35 Kairon
Evidence (27 from sources/W1 + 8 W2 publisher works); 12 quote-anchored
discussion events; 3 manual W1 L0 proposals; 6 W2 held reopen proposals;
34 LitOps Source records; 3 WhiteCrow context_pack artifacts accepted by
real importer and first_workset. No Manuscript, author-approved
ArticleSeed, WORLD mutations, W12 route qualifications or external sends.

Second execution in another process: ZERO new SourceSnapshots, discussion
events, LitOps Sources, WhiteCrow contexts. Readback SHA256 equals
0308c4b083e24d23b7238f01d47384f139e667c835eed5015f620dd400e2f4b1
for factory_research_cases/T3-TALK-20261019/source_stage_receipt.json.
Independent certutil verified this exact file digest. No second physical
host acceptance or production deployment has occurred.

New unrelated case synthetic source family Z and case NEW-CORPUS-001:
single-entry source intake, optional distinct W2 packet, actual installed
LitOps+WhiteCrow context receipt and independent subprocess replay passed
with source mismatch, authority, failure-recovery and duplication tests.
This qualifies only source/research-stage reproducibility.

## Boundaries and backlog

- No automatic acquisition of Drive carrier bytes; owner-scoped direct
  connector-to-worker route remains #37.
- Native 20 Word comments and image-only Slides are not semantically read,
  remain #38; real ChatGPT message UUID/provenance remains #39.
- Manually curated W1/W2 packets may be ingested, but no autonomous
  scientific literature hunt is executed by this script.
- Full publication opportunities, TargetWorld deep evidence, venue
  policies, author gates and >=80 W12-equivalent routes remain #43.
- Never commit private doc bodies/audio/transcripts to public Git.
- No production mutation without explicit owner GO.

## Regression command

    set LITOPS_SKIP_DOTENV=1
    set PYTHONPATH=src;C:\projects\trimurti\whitecrow\conceptarticle;C:\projects\trimurti\whitecrow\whitecrow-skeleton
    python -m pytest -q tests\test_corpus_factory_entry.py tests\test_trm073_research_stage.py tests\test_trm074_litops_whitecrow_stage.py tests\test_trm074_w1_field_reopen.py tests\test_trm074_talk_corpus_intake.py tests\test_trm074_research_stage_handoff.py tests\test_opportunity_graph.py tests\test_opportunity_execution_handoff.py tests\test_submission_package_factory.py tests\test_target_world_catalog.py tests\test_intake_attempt_metadata.py tests\test_intake_input_limits.py

Missing LitOps/WhiteCrow installs make only specific live integration tests
skip; never claim WhiteCrow acceptance or CI success from that state.
