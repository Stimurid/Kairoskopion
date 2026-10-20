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


## Existing TRM040 native Google Docs provider -> Factory source adapter

AORUS already has an installed read-only native Google Docs transport in
WhiteCrow/Trimurti (see WhiteCrow issue #40 and unmerged native-transport
code). It runs documents.get(includeTabsContent=true), independently
brackets provider revision, captures provider-bound immutable structural
JSON inside TrustedAcquisitionStore, re-verifies that snapshot from disk
and preserves missing comment/media coverage. Reuse it. Do NOT build
another Google API/OAuth client or copy credential material into Git.

When installed and authorized on the operator host, set the existing
TRIMURTI_DOCS_FETCH_COMMAND (a JSON argv template with explicit mode and
document-id slots) or TRIMURTI_GOOGLE_TOKEN_FILE outside the repository.
The operator chooses private paths. Python import environment must expose
both this checkout's src package and the already installed trimurti native
transport code.

    set PYTHONPATH=src;C:\installed\whitecrow-native-docs-worktree
    python scripts\run_native_docs_source_capture.py --source-id drive:FIXED_ORIGINAL_ID --source-url https://docs.google.com/document/d/FIXED_ORIGINAL_ID/edit --owner-capture-root C:\owner-private\native-captures

The script uses NativeGoogleDocsTransport and TrustedAcquisitionStore.
It writes the native structural snapshot under owner-private
trusted_native_docs and a separate text-run projection under text.
The written receipt proves exact provider object ID, stable revision,
independent complete structural traversal, snapshot SHA and a bytewise
relationship to the projected text. Source content and OAuth tokens are
never printed, checked into Git or sent to a journal.

To admit this source, copy the resulting receipt-fragment fields into
the PRIVATE case manifest, adding only the case-specific family/key,
carrier kind/version and author_state. The source's read_coverage must
be STRUCTURAL_TEXT_PROJECTION_COMMENTS_NOT_ACQUIRED. Existing
talk_corpus_intake will call verify_native_source on the provider-bound
trusted snapshot, re-derive the text projection, and reject a forged
local file/ID, corrupted record, changed revision or missing snapshot.
The verification result is pinned in the resulting SourceSnapshot.

Direct live AORUS test on 20 October 2026, case T3-NATIVE-DOCS-20261020:
- A06 Drive ID 1sFMFo3xzDBr4R3JIatouBDmIvQVfMDLpCuAcMVyPytk,
  structural SHA256 0b41678d9d687d0ddc4c277b646f526689b1e0047a6d446a67de52297c835059,
  projection SHA256 34eee646084b6a20fbaf7f6189125870328fc1a23debb61fd895cb6717fc6fdb.
- A07 Drive ID 1XUTyB5IsN9oBjKKTcRK6gJs4G7N4FeQnUsVtcyq6ZE0,
  structural SHA256 edbf16a30be2a18940645efb84b29cd184664aa0875b9669d4874bc0bc7d9cdb,
  projection SHA256 75cd0288024485cf67cea84412e553fe564cd8c2b3d09d9f51712cd607737e83.
- Both: actual read-only native Docs API; REVISION_STABLE,
  STRUCTURAL_FULL_TRAVERSAL, verified immutable snapshot;
  comments NOT_ACQUIRED and external media not silently promoted.
- Private independent source-stage root:
  C:\projects\trimurti\_ops\T3-TALK-20261019\factory-native-verified-A06A07-v1
- Factory source count=2, textual old/new comparison A06->A07,
  Kairon Evidence=2, LitOps Source=2, WhiteCrow context_pack=1,
  author approval=0, journal SEND=0. Cold process re-run: 0 duplicates.
  Immutable Factory receipt SHA256
  6b533919246df2ab940527e0c03b0e48edeebebeba985f4ed35aa68ef7aa7249,
  independently checked with certutil.
- 138 local regression tests PASS across native source mock adversity,
  TRM074 core/WhiteCrow, TRM073 W2 and factory/graph modules.

This is a full proof for TWO directly acquired Google-native documents
and the source/context stage only. It does not prove all 34 source
carriers can be fetched with this transport: DOCX, slides, raw chat,
audio and comments require their own typed adapters (#38/#39).
Authorized direct multi-file capture and a single manifest-to-fetch
invocation remain #37 follow-up. This code is DRAFT only, no CI or
production authorization claimed.


## Multi-GDoc manifest -> provider -> Factory, one operator action (2026-10-20)

One bounded Factory source CLI accepts --native-capture-root alongside
--manifest, --storage-root and optional --litops-root. A source element
with capture_transport=native_docs, original drive:GOOGLE_DOC_ID and
source_url is fetched by the EXISTING installed TRM040 native Docs
transport. No previous source fragment or temporary text path must
be supplied through ChatGPT. Normal local carrier rows may coexist,
but their own read authority remains explicitly limited.

Example PRIVATE author input (replace exact source ID; no real text in Git):

    {
      "schema": "TRM074_COLD_CASE_V1",
      "case_id": "EXAMPLE-OWNER-CORPUS-001",
      "publication_send": "DISALLOWED",
      "sources": [
        {
          "key": "N01", "family": "A", "kind": "SPEECH_SCRIPT",
          "version": "v0.1", "author_state": "NOT_VERIFIED",
          "capture_transport": "native_docs",
          "source_id": "drive:EXACT_GOOGLE_DOC_ID",
          "source_url": "https://docs.google.com/document/d/EXACT_GOOGLE_DOC_ID/edit"
        }
      ],
      "version_edges": [], "delta_pairs": [],
      "decision_events": [], "discussion_events": []
    }

Owner host configures the existing TRIMURTI_DOCS_FETCH_COMMAND (or
read-only TRIMURTI_GOOGLE_TOKEN_FILE), and installed native trimurti
code on PYTHONPATH. No new HTTP client or OAuth code was created.
LITOPS_ROOT and LITOPS_SKIP_DOTENV=1 are required if the operator
also requests real installed LitOps/WhiteCrow.

    python scripts\run_factory_source_stage.py --manifest C:\owner\case.json --storage-root C:\owner\factory --native-capture-root C:\owner\native-snapshots --litops-root C:\owner\litops

Original manifest, Factory storage, and capture root are isolated.
Source content and OAuth credentials never enter GitHub. Source ID
is exact; title and modifiedTime are not identity. The source must
be a Google-native Doc; Word, Slides, comments, audio and chats have
separate typed capture engines. No unproven FULL reads.

Durable partial resume: each completed native source is pinned in
owner-private case_pins/<case_id>/ keyed by ORIGINAL manifest SHA,
case ID and original Google Doc ID. Failure of the second document
retains a verified first. Retry re-verifies old TrustedAcquisitionStore
record and text projection before using the pin, fetching only missing
documents. A changed provider identity, forged snapshot, changed text,
missing snapshot, unsafe ID, duplicate ID or unauthorized author-state
promotion fails closed.

A pinned replay is an OLD-REVISION REPLAY, not evidence that the source
is still current in Drive. To refresh changed source text, explicitly
create a new case/wave/version; never silently rewrite the previous
scientific history. The durable receipt includes native_source_count,
derived_manifest_sha256 and native_replay_policy. CLI additionally
reports new_native_captures and reused_native_captures.

ACTUAL AORUS TWO-DOC NO-CHAT FACTORY RUN: authorized A06 and A07 exact
Google Docs IDs, fresh independent case T3-NATIVE-BATCH-20261020.
One operator command read both from Google Docs through existing native
provider; saved stable revision structural snapshots; admitted 2
SourceSnapshots; wrote 2 Kairon Evidence; 2 LitOps Sources; WhiteCrow
received 1 context_pack. Cold replay: 0 new native capture, 2 reused
pins, 0 new SourceSnapshot or LitOps/WhiteCrow record. Independent
Factory receipt SHA256:
807210bc7d008bc15e41c273ed6601e2642a05c0f8703ff6c7ffa7ec37d3d8cc .
All raw captures and the owner-only launch script live privately at
C:\projects\trimurti\_ops\T3-TALK-20261019\native-batch-direct .
Google comments NOT_ACQUIRED. No ArticleSeed, World mutation,
Artikl manuscript acceptance, published venue route or SEND.

147 targeted local tests passed, including 9 new native-manifest tests
for partial provider failure/retry, document-content revision under
a pinned case, forged provider/ID/snapshot, changed local text, author
decision gate, duplicate and unsafe IDs, mixed carrier types and
private root isolation. CI, independent host and production remain
unverified. Broader >=80 W12-qualified routes remains issue #43.


## W1/W2/W3 same-case SCIENTIFIC research-stage execution

The case runner accepts multiple repeatable --research-packet paths
(maximum 8 per invocation). Every packet must carry the supported W2
or W3 schema, exact same case_id, unique wave_id, pinned original bytes
and no author/World/send escalation. New independent W3 packet staging
was merged cleanly from existing public PR #44 (source commit ba48234),
preserving original scientifically bounded W3 research return.

Private AORUS operator handle:
C:\projects\trimurti\_ops\T3-TALK-20261019\TRM074_FULL_W1W2W3_OWNER_PRIVATE_20261020.ps1

Run with owner-private TRM073_W1_SOURCE_MANIFEST and exact
TRM073_ORIGINAL_HEAD_SOURCES source ID/version/byte SHA binding overlay,
real W1 manifest, real W2 and W3 science packets, isolated LitOps root.
The existing StageResearchPacket W3 verifier reopens and independently
re-hashes source A07 and C04 on its cold readback; do not mistake this
for independent researcher or author approval.

Verified REAL case on a NEW storage root:
34 source snapshots; 27 source evidence + 8 W2 official publisher
works; W3 source refs remain bounded scientific return, no false
extra fully-read items; 3 W1 author-HOLD proposals, 6 W2 held
field-reopens, 2 W3 held field-reopens; 9 proposed
DISCOVERED_PREQUALIFICATION routes (0 W12-equivalent); 3 LitOps/
WhiteCrow context packs. Research-stage W2 receipt remains
b76b50a4a6a14af147c20d3a9f1b0b2d4a50089f391da74f0ad3797183a5060b,
W3 receipt remains
40c43a9b93881f8de3d234fa53df39e751f7bb4ed94f8de3b7781490eb84f11a.
Two independent process CLI calls produced identical full-case receipt
SHA256 3827252a9e1a6e2c4567d35aefd52a600f678c50f920ac21ee393fdd3ef3ba72.
The second run added ZERO new source snapshots or WhiteCrow contexts.
No World/ArticleSeed/send mutation, no autonomous Indago hunt.

176 targeted local AORUS tests PASS on the combined W1/W2/W3/Docs/
LitOps/WhiteCrow runtime, including 5 new multiwave tests (typed
admission, duplicate wave-ID refusal, wrong case refusal before any
source writes, tampered prior wave packet, unsupported future W4 schema).
No GitHub CI run or production deployment is implied.
