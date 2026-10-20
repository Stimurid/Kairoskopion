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


## W12 first official-publisher-backed held route (20 October 2026)

Current owner-private Factory single command also accepts repeated
--venue-route-packet inputs (up to 80). It verifies exact original
claim/version evidence, separately acquired real official publisher
scope and submission policy, published opponent DOI, actual selected
opponent paragraph, target-specific RU/EN scholarly thesis, strongest
objection, negative evidence, falsification/design and author/rights
HOLD. The parser rejects unknown/future schemas, wrong case, duplicate
claim-version/journal pair, changed packet checkpoint and every
unreadable or mismatched source. This uses existing Kairon
SCHOLARLY_ROUTE_CHALLENGE and SOURCE_CONTRADICTION with VERIFIED_BYTES,
without creating ArticleSeed/OpportunityRoute or changing the WORLD.
Route stage records a research-only immutable HuntTrace and an
independently revalidated private receipt.

First REAL provisional W12-equivalent address:
- source: MFTI C04 v0.4, fixed original Drive document ID and source
  file raw SHA256 807df2a6d8f0f2eef0ef7052f8653c41727566a54693a5333be4c9414b2a54da;
  source paragraph 11 anchors the source question to reproducing new
  functions, common productive means and stable division of labor.
- existing W3 C-CROSS-INDUSTRY, HEAD-03, journal Review of Managerial
  Science; publication type REGULAR_MANUSCRIPT not special/active CFP.
- real official Springer RMS aims/scope bytes, SHA
  0fea34568b4e1aa775fff832db40a90aad17816e07a9aaaf715ec31f53244824,
  publicly accessible from
  https://link.springer.com/journal/11846/aims-and-scope.
- real RMS author instructions bytes SHA
  4ce6fd44808737b1abd1d1f56c5953ff3cb5746f3d3ff7eada581cfcf9023706,
  https://link.springer.com/journal/11846/submission-guidelines.
- real publisher full HTML of strongest opponent Ohlert/Broering 2026
  DOI 10.1007/s11846-026-01031-y bytes SHA
  72881a27eed879fc65f86378588383225f2a3a5b7aa99692e141d18a262d44f3,
  https://link.springer.com/article/10.1007/s11846-026-01031-y.
  Concrete read anchor: Methodology, survey of 60 managers as unit of
  opportunity exploitation. The study already discusses cross-industry
  structural transformation; the proposed delta cannot falsely claim
  that prior art ignores emerging industries. Proposed empirical
  falsifier: test longitudinal collective standards/third-party
  reproductions against manager-level exploitation conditions.
  An acquired complete HTML source is not itself certification that
  every section has been scientifically studied. The route's bounded
  science read is SELECTED_SECTIONS, deep TargetWorld count remains 0.

The W12 route packet, original Google Docs captures and published
papers are held only on OWNER-PRIVATE AORUS outside Git. Original
author permission is not assumed. Target-specific bilingual work and
opposition are still RESEARCH proposals and await intellectual review.

REAL fresh owner-private full chain W1 -> W2 -> W3 -> W12 ->
installed LitOps -> WhiteCrow:
C:\projects\trimurti\_ops\T3-TALK-20261019\TRM074_FACTORY_W1W2W3_RMS_W12_ONECMD_20261020.ps1
New storage root factory-W1W2W3-W12-first-20261020: first command
34 sources, 35 Kairon Evidence, 11 held research field reopens,
9 W3 UNQUALIFIED journal possibilities + 1 separate
W12_EQUIVALENT_HELD source/venue research route; 3 WhiteCrow
context packs, ArticleSeed=0, World mutations=0, journal sends=0.
Cold second process: ZERO new source snapshots/WhiteCrow writes and
identical Factory receipt SHA
969ade181dff4912e4ce74b7e324ca54c6ae5300f66ce198d71b972b7ffb8092.
Direct W12 source/venue route readback receipt SHA:
f7742390a64cfe935267ef400de73e4033358a9fe2a7dfd505cde315f004777d.
W12_EQUILVALENT_HELD=1 of owner target >=80; DEEP_QUALIFIED=0,
ARTIKL/AUTHOR_ACCEPTED=0; not a production publication capability.

187 local targeted tests PASS including new exact-passage, policy
tamper, bad DOI, W3 source-byte binding, changed claim-version
packet, missing rights/author and future-date negative tests.
No CI pass, no second-host acceptance, no production deployment.


## Second W12-equivalent HELD route from real A07 native source

The SAME reusable W12 stage was invoked with another actual W3-head,
publication venue and primary intellectual provenance, without
rewriting the route implementation or inflating one journal/paper as
multiple opportunities:

- Original source: A07 "Sysli" v0.7, exact stable Drive ID
  1XUTyB5IsN9oBjKKTcRK6gJs4G7N4FeQnUsVtcyq6ZE0, original private
  source raw SHA256
  4252d0bffd3d1aae25bb69faa3206b4543fa4502725106027650a776deaa2e4e.
  Exact line 77 anchors the question about a new capability of the
  person-language-means-methods-learning system.
- W3 A-EPISTEMIC-POSITION HEAD-01; journal:
  Epistemology & Philosophy of Science / Эпистемология и философия науки,
  verified official scope https://journal.iphras.ru/about
  source SHA ce98eef2fffe136a30c5d6d0f6f9740bec8a08be721c9693f1e7fb49c3dee86c.
- Official article submission page
  https://journal.iphras.ru/about/submissions
  SHA 1eac75e44a90e6ab84868438b3430e279ad6917814b99ea8f971739e08fdefc2;
  this is a REGULAR_MANUSCRIPT route, not an asserted active CFP.
- Real journal-native science comparator: Lisenkova/Bylieva 2026
  DOI 10.5840/eps202663350,
  https://journal.iphras.ru/article/view/12654
  HTML SHA a49daaddb122f4bcf4ddf5e4c25e7469d25f6357ea9ab08dd8820bca66d65523.
  Journal-native HTML provided article abstract and references; the
  route records ABSTRACT_ONLY, not full published research read.
- Strongest opponent already argues AI has metascientific role
  reconfiguring research field; general AI-as-participant cannot serve
  as novelty. Source-specific proposed distinction: reproducible
  operations that transform available methods, evidence warrants,
  conceptual distinctions and learning organization; empirical/
  philosophical counterexamples and author decision pending.
- Exact original line, DOI, source-version W3 VERIFIED_BYTES binding,
  official scope/guidelines/opponent quotes, separate RU/EN route
  abstracts and unresolved author co-consent are present in private
  packet W4_EPS_A_EPISTEMIC_OWNER_PRIVATE_20261020.json.
- Source/venue verifier returned 1 W12_EQUIVALENT_HELD, 0 deep
  certified, 0 author-approved, 0 sends; direct W12 readback SHA256
  7342130758c04dba3e37bfb22c6ced7547fb1f9f92751bbda2d1ac0d9dc03508.

NEW owner-private full single factory command, W1+W2+W3+TWO
distinct W12 research-route packets, installed LitOps and WhiteCrow:
C:\projects\trimurti\_ops\T3-TALK-20261019\TRM074_FACTORY_W1W2W3_TWO_W12_ONECMD_20261020.ps1
Fresh output root factory-W1W2W3-W12-two-20261020.
First command real work complete; cold second command 0 new source or
WhiteCrow objects, same Factory receipt SHA256
ff0b78e5054b7274408c5de437a73d09b7febdea67f78723a3f96c70779936c4.
W12_EQUIVALENT_HELD=2 of owner >=80; 9 W3 found routes still remain
proposed/prequalification; DEEP_QUALIFIED=0; ARTICLE_SEED=0;
AUTHOR_APPROVED=0; EXTERNAL_SEND=0; PROD=NO.

189 targeted real-installed-host Python tests PASS, including tests
that abstract-only opponent HTML can never silently self-certify
full published scholarly paper depth. Research route status still
author-HOLD, never a blanket article publication approval.


## W4-R1 source science: actual Factory research-stage readback, scientific HOLD

New third W4 science schema: TRM073_W4_SCHOLARLY_SOURCE_RETURN_INPUT_V1.
The same stage_research_packet dispatch and existing Kairon OpportunityGraphStore
now process W2, W3, W4 and then separate W12 venue-route packets. This is
one Factory, no second parallel scholarly workbench.

Real source C04 v0.4, original Drive ID
16dAYSIhubAVUmx7Hp5ZXxrf2E_A2v5F3jRAnsUEMM2Y, exact original raw
SHA256 807df2a6d8f0f2eef0ef7052f8653c41727566a54693a5333be4c9414b2a54da;
line 11 re-read and W3 VERIFIED_BYTES source binding checked on replay.
Canonical WORLD W4-R1 science notes:
https://docs.google.com/document/d/1cwW5doPsSNBge0KNqu8ZBU9UY5Vebp_RmlC9rcWXvko/edit
Private text-byte SHA256 ef379d56ba633aea47a6387f8e86cf76b5f97442ce9fed273d21107c56be55ce.
The host direct authenticated TRM040 reader returned UNAVAILABLE because
neither TRIMURTI_DOCS_FETCH_COMMAND nor TRIMURTI_GOOGLE_TOKEN_FILE is set.
Therefore W4-R1 input was copied to owner-private AORUS through the connected
Drive connector and explicitly labeled GOOGLE_DRIVE_CONNECTOR_CHAT_RELAY_NOT_NATIVE_TRM040.
No native revision/full content certification is claimed for this fallback.

Owner-private W4_R1_C04_STAGED_OWNER_PRIVATE_20261020.json raw SHA256
9d25d191903f61fdb51359dc1ab4650a53629727c732c46cd07b0df38cd7af3e.
Five exact W3 DOI comparator edges were tested; three qualified as
source-specific SCIENTIFIC_OBJECTION_HELD:
Ohlert/Broring 2026 RMS SELECTED_FULL_HTML (verified publisher HTML passage);
Borsato/Cefis 2026 ICC ABSTRACT_ONLY; Li/Xia/Tang/Tang 2026 I&I ABSTRACT_ONLY.
Each caused one separate L2 FieldReopenProposal to C04, all AUTHOR_HOLD.
Calvino/Fontanelli ICC was REJECTED_READING_INSUFFICIENT (W3 metadata only).
Bohnsack/Pinkse/Reischauer I&I was REJECTED_READING_INSUFFICIENT (TARGET_ARTICLE
genre, not a peer-empirical original). Negative trails and falsifiers persisted.
One C-INDUSTRIAL-CAPABILITY-v0 working hypothesis stored as research-only
HuntTrace; NOT an owner-admitted ArticleSeed or protected WORLD mutation.

Direct W4 source-read stage SHA256
56888c29ac919b64ac1645c249b57c3315a76683fb7aaffb052468b6482dd83a;
independent cold readback SHA256
56c1abd776c138febca13a9425f7948d75b1d858817476776e8aac5013293ab1.
Cold readback rehashes exact W4 input, dossier, original C04 and selected
publisher HTML, then verifies W3 DOI edges, passage anchors and Kairon events.

Full owner-private W1/W2/W3/W4/W12/LitOps/WhiteCrow runner:
C:\projects\trimurti\_ops\T3-TALK-20261019\TRM074_FACTORY_W1W2W3W4_TWO_W12_ONECMD_20261020.ps1
Two real independent process executions in a NEW isolated store succeeded
with exactly the same whole-Factory receipt SHA256:
84ec5d865f7fbae257b1fff6627c4ac3209b5dc64e934c92b465365b1f428376.
Second call produced ZERO duplicate source captures or WhiteCrow contexts.
Total retained: 34 source snapshots, 3 WhiteCrow context packs,
3 W4 source challenges, 2 rejected negative trails, 1 held article hypothesis,
and 2/80 earlier genuinely distinct W12_EQUIVALENT_HELD routes; no additional
W12 credit merely for W4 challenges. ARTICLESEED=0, AUTHOR_APPROVAL=0,
WORLD_MUTATION=0, TARGETWORLD_DEEP=0, EXTERNAL_SEND=0, PROD=NO.

This is science-dossier staging over existing publisher evidence and a
manual Google Drive connector fallback. It does NOT prove an autonomous
multi-day Indago research hunt, a complete new article, CI success,
author approval or a full native Google Docs capture. Another unrelated
owner corpus and direct authorized TRM040 Docs access remain required.
