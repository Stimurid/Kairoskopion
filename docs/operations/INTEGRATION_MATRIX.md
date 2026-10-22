# TRM-074 / source-to-science Factory integration matrix — 2026-10-20

Owner epic: [#33](https://github.com/Stimurid/Kairoskopion/issues/33),
[#43](https://github.com/Stimurid/Kairoskopion/issues/43) and engineering
[#53](https://github.com/Stimurid/Kairoskopion/issues/53).

## Exact Git ancestry (verified with git merge-base --is-ancestor)

| Draft PR | observed SHA | source capability | actual relation |
| --- | --- | --- | --- |
| [#32](https://github.com/Stimurid/Kairoskopion/pull/32) | 996fbcb7ffbe00f2ccbdda728f340aaeeab0ec75 | research-stage rights & W12 scope | ancestor of PR46, open DRAFT |
| [#36](https://github.com/Stimurid/Kairoskopion/pull/36) | 4713f3ee214aad7e9d20cbcd0a472a6dfe847179 | multi-version three-talk source intake | ancestor of PR46, open DRAFT |
| [#44](https://github.com/Stimurid/Kairoskopion/pull/44) | ba482344dbd554cf90816d2de8e7e1173dbbcb5a | W2/W3 holder, source-return | ancestor of PR46, open DRAFT |
| [#46](https://github.com/Stimurid/Kairoskopion/pull/46) | baseline 16819edf3fca62935f977ee4a2a88350eb29acfa | one-command W1/W2/W3/W4/W12, LitOps/WhiteCrow and two initial venue research routes | current working branch ancestor, open DRAFT |

Branch integration/trm074-w2-test-20261020; actual owner-private worktree on AORUS.
Branch status and SHA must be rechecked after every commit, never assume
the listed SHA is current. NO parent merged; NO production deployment.

## Real independent sources / machine runs

**T3-TALK-20261019**: Exact source/metadata corpus 34; one Factory
operator W1→W2→W3→W4→2xW12→installed isolated LitOps→WhiteCrow.
Three scholarly objections (C04) plus two rejected comparator trails,
one author-HOLD C ArticleVersion research hypothesis; two earlier
distinct W12_EQUIVALENT_HELD routes (RMS and EPS), NOT submitted.
Two-process replay receipt SHA256
84ec5d865f7fbae257b1fff6627c4ac3209b5dc64e934c92b465365b1f428376.
The W4-R1 research dossier arrived through the connected Drive service
as a clearly marked chat relay. On AORUS the direct TRM040 Docs
transport returned UNAVAILABLE (neither configured fetch command nor
read-only token file). W4 is thus a source-bound research-note return,
not a certified autonomous Indago hunt.

**L3-CORPUS-20261020 (genuinely unrelated, original owner authority)**:
Existing L3 v0.3 owner manifest plus L3 source_capture receipt were
independently rehashed and converted BY CODE into standard
TRM074_COLD_CASE_V1 with no private text or invented source genealogy.
8 actual extractable local documents (7 owner Drive native text
projections, 1 actual source DOCX body) + 1 historical 2023 XLSX
retained as BINARY_HELD_NO_SCIENTIFIC_EXTRACTION. EXACT 9/9
provider/byte-hash pins retained, 4 source-only contexts admitted by
installed WhiteCrow via isolated LitOps. Same Factory
scripts/run_factory_source_stage.py, no new parallel execution engine.
2 Python invocations in distinct processes produced identical private
Factory receipt SHA256
00ec38f476808122dcf44ebe3974ee661f839340a673a9b820c4b005304f248c;
second call created 0 source or WhiteCrow duplicate objects. Owner
author states remain provisional, original DOCX comment-level read
not certified; workbook sheet/formula contents **not** read by Factory.
Previous L3 code-v07 private pilot had l3_pass=FALSE; the new source
bridge DOES NOT turn it into a fully research-accepted article.

## Source and actor/capability boundaries

| Boundary | Actually implemented and tested | What remains held |
| --- | --- | --- |
| Source identity | fixed provider IDs, owner manifest vs capture equality, exact byte SHA; version key separate from author status; same filenames not merged | independent native Docs revision/currentness on AORUS unconfigured |
| Binary file | DOCX paragraph-body extraction with comments unread; XLSX original byte SHA and historical date preserved | worksheet/formula semantics, author comments, current VAK rules |
| Source genealogy | only explicitly author/owner provided edges; no newest-file promotion | L3 owner comment decisions and rich F01/F02 chronology require separate verified source and human arbitration |
| LitOps / WhiteCrow | real isolated source registries + source-only context packs, no editor actions | scientific WhiteCrow adjudication, Artikl decision gate and changed ArticleVersion |
| W2–W4 science | actual three-talk W2/W3 and C04 W4 research-note source return with negative trail | native multi-wave Indago hunt, L3 scientific evidence importer, genuine author approval |
| Kairon W12 | 2/80 exact source-version/journal/published-opponent research HELD | other 78 routes, deep journal ecology, journal-native full texts |
| Manuscript and external send | ArticleSeed=0 in both cases, World unchanged, SEND=DISABLED | author sign-off, coauthor rights, editorial submission |
| Tests/CI | AORUS 216 W4-base tests; L3 bridge adds targeted negative tests and source cold replay; inspect separate test log | independent external review, full GitHub CI, staging admission, production |

**Operator example (OWNER-PRIVATE, no external submissions)**

The exact case manifest is constructed on the authorized machine from
two already pinned owner source receipts, using
kairoskopion.integrations.owner_corpus_manifest_bridge.
The resulting private manifest can be passed unchanged to:
python scripts/run_factory_source_stage.py --manifest <owner_manifest> --storage-root <isolated_factory_root> --litops-root <isolated_litops_root>
Set LITOPS_SKIP_DOTENV=1 and LITOPS_ROOT to the isolated LitOps root.
Repeat in a second process and require byte-identical receipt,
0 new source snapshots and 0 new WhiteCrow context records.
Do NOT commit owner manuscripts, source URLs, raw DOCX/XLSX, archive
or related private manifest contents to Git.

## Remaining concrete gates

1. TRM040 authenticated Docs command/token is absent on this host.
   Keep LIVE_NATIVE_PROVIDER_READ=BLOCKED, not a simulated pass.
2. L3 scientific opposition + field reopen previously exists as a
   separate narrow owner-private pilot; integrate its real evidence
   into this same Factory only with source/DOI/read-depth authority
   and independent replay, before L3 REAL_CASE_ACCEPTED.
3. Full CI on the PR46 SHA plus second independent machine/model
   review; no local tests alone certify release.
4. Root publication portfolio remains W12_EQUIVALENT_HELD=2/80,
   DEEP_TARGETWORLD=0, author accepted ArticleSeed=0,
   production deployed=NO, external sends=0.

Do not confuse source-only acceptance with scientific or production acceptance.


## L3 prior scientific-return bridge into the SAME Factory — 2026-10-21

The first L3 transfer accepted **sources and WhiteCrow context ONLY**.
The existing owner-private L3 code-v07 trial also contained a previously
tested scientific challenge. A second explicit CLI option now imports THAT
prior result into the SAME Kairon opportunity graph, without a new hunting
or text-generation engine.

Public code: src/kairoskopion/services/owner_prior_research_bridge.py.
CLI: scripts/run_factory_source_stage.py --owner-prior-research-receipt
<private_existing_L3_receipt.json> --owner-prior-graph-root
<private_verified_L3_graph_root>, together with standard --manifest,
--storage-root and optional --litops-root.
Both owner-prior flags MUST appear together; the restricted importer accepts
only a real matching L3 legacy-receipt schema and original case ID.

Source provenance proof is a live three-way comparison:
1. previous L3 full-content fingerprints for 11 Evidence, one Journal,
   one source contradiction and one FIELD_REOPEN_PROPOSAL;
2. nine owner source identities / raw byte SHA from the archived legacy
   receipt and original publisher-note annotations;
3. current eight Factory SourceSnapshot paths physically re-read and
   re-hashed + one independently re-hashed historical workbook.
Source collision, duplicate physical event ID, edited source, altered
receipt, injected ArticleSeed/World/Route, stale research note, or absent
original field reopen causes refusal. The historic XLSX remains
BINARY_HELD_NO_SCIENTIFIC_EXTRACTION; never treat its 2023 categories
as current VAK policy or its sheets as read scientific arguments.

The two published rivals are transferred as *INDEX_ONLY*
owner-research-note pointers with verified DOI identity, never as
FULL_TEXT publisher-exemplar proof. Exactly one old B09 source
contradiction and one proposed L2 field reopen are transferred with a
W2 research-note line and passage SHA. Their origin is attributed to
the previous OWNER SCIENCE NOTE. AuthorGate=HOLD;
ArticleSeed=0, World=0, W12_EQUIVALENT=0,
TargetWorld=unqualified, external send=disabled.

Real independent L3 V02 output on AORUS:
- existing source-only contexts admitted: eight texts, one binary HOLD,
  four actual WhiteCrow contexts;
- imported earlier source-bound research: two INDEX_ONLY DOI evidence
  pointers, one challenge, one L2 field reopen, one provenance HuntTrace;
- two separate same-operator Python runs; second 0 new sources,
  0 new WhiteCrow records, 0 new scientific event identities;
- joint SHA256:
  94c12f6bbde822c8f399e73cf2e8b088bf29479f40c339f92788c220a50ca256;
- source stage SHA256:
  17fd0cfff5c5780cb0c48cbbe95bf974168ee1fb040183a1bffdd880105add45;
- reconciled prior science SHA256:
  58e14de028131b42f0d536618b95e87a1e63c2d554d6bca1bba866df06e11791.

Important: this is **PROVISIONAL OWNER-RESEARCH-RETURN INTEGRATED**;
it does not certify a full journal field, regenerate an article, resolve
the F02 A/C/D author comments, run live Indago, or deploy to production.
It closes the prior-L3-results-disconnected-from-Factory defect, while
deep source reading, scholarly novelty adjudication, explicit author
decision, journal fit and permitted publications remain open.
The previous V01 private outputs are immutable and preserved as
historical receipts; V02 uses a fresh isolated storage root.


## Independent Claude Code read-only review of PR46 b29a7b2, 2026-10-21

A distinct model reviewed eight public code/tests/docs files and returned
CHANGES_REQUIRED. **This is a review of the earlier SHA b29a7b2**,
not acceptance of the subsequent repair. Full report and input log remain
owner-private on AORUS; no original manuscripts or owner private source
carriers were made available to reviewer.

- P1 CONFIRMED: global OpportunityGraphStore._write_once previously used
  exists/read then temp.replace, permitting concurrent immutable-ID overwrite.
  REPAIRED: unique temp + fsync + atomic os.link no-clobber, then compare
  actual winner; stable bytes stay untouched. Three targeted regressions
  include a forced incompatible racing writer, equal-content conflict and
  actual parallel competing writers.
- P2 RECOVERY: prior L3 bridge writes multiple provisional graph records
  before final receipt. Explicit owner-private immutable intent.json now
  precedes graph writes; absence of receipt means INCOMPLETE.
  Injected failure after both Evidence records confirms no completion
  receipt, and rerunning EXACT same one-command operation automatically
  resumes and yields one graph set and verified receipt without duplicates.
  A hard crash may strand exclusive lock; intentional fail-closed manual
  inspection is required before replay. This is recoverable-on-reinvoke,
  NOT a general ACID multi-object transaction, and readers must gate on
  completion receipt. Original published DOI notes never gain manuscript
  acceptance.
- P2 SCOPE: the prior science adapter is deliberately L3-specific; new
  unrelated corpora still need explicit schema/contract instead of lying
  about generic admission. CLI options mean "import verified L3 legacy
  research"; no general legacy-research promise.
- P3 OPEN: parent-junction ancestry verification across platform mounts
  and event ordering (lexicographic event_id without explicit timestamp)
  remain backlog hygiene; SHA-pin tampering checks are enforced.

Do not mark INDEPENDENT_RE_REVIEW=PASS until a distinct second review of
the repaired SHA. Production and deep field-science gates remain open.

## #64 — consumer-side science visibility gate (2026-10-21)

Implemented in the *existing* opportunity graph, portfolio, authenticated
trace API, and opportunity-to-Artikl handoff. This protects readers from
mistaking in-progress multi-record scientific import for completed research.

- Low-level `OpportunityGraphStore.list_records/get/replay_events` remain RAW,
  recovery/forensic interfaces for internal writers and exact receipt checks.
  A raw immutable Evidence or FIELD_REOPEN event is not an admitted result.
- `OpportunityGraphStore.consumer_snapshot(include_owner_prior=...)`
  is the explicit **read** contract for publication-facing consumers. A
  graph-only L3 object is withheld by default. Even with operator-authorized
  private read enabled, it is exposed only after
  `readback_owner_prior_science` checks the durable `intent.json`,
  completion `receipt.json`, nine original owner source bytes, existing
  Factory corpus pins, exact original graph events, and imported graph
  fingerprint. The returned science remains **PROVISIONAL / AUTHOR_HOLD**.
- Imported FIELD_REOPEN_PROPOSAL descendants inherit the originating
  SOURCE_CONTRADICTION's import visibility at read time; pre-existing
  immutable event content is not rewritten, so prior V02 hashes remain stable.
- Unknown case/schema, failed/pending receipt, changed bytes or graph events
  are **INCOMPLETE_OR_UNVERIFIED** and withheld. The consumer view reports
  withheld counts but does not infer missing academic results.
- `build_portfolio`, `GET /api/opportunities/trace` and the
  `prepare_opportunity_execution_handoff` now use that consumer read
  boundary. The API defaults to withholding private science under the
  existing operator opt-in flag. The Artikl handoff always withholds
  owner-prior science (its author approval cannot be inferred from a prior
  research note). No publisher fulltext, publication action, World or
  ArticleSeed is synthesized.
- Latest exact-code targeted AORUS proof: **63 passed, 1 skipped**.
  This includes pending/recovered science, unknown-schema refusal, missing
  case tag, deleted source event, unreceipted grandchild, conflicting ancestry,
  HTTP trace privacy and forged author-event rejection.
- Broad AORUS suite with short temp root and `-m "not network"` passed
  **3778 passed, 19 skipped, 8 deselected**. This broader run began before
  the last provenance-edge refinements; exact HEAD GitHub CI is a separate gate.
- Independent real owner-private L3 V02 cold readback:
  private OFF => 0 records / 0 events; privately VERIFIED =>
  3 graph records / 2 verified scientific events; original imported
  science receipt SHA256 `58e14de028131b42f0d536618b95e87a1e63c2d554d6bca1bba866df06e11791`
  unchanged; AUTHOR_HOLD and no external SEND preserved.
- Prior parent-junction protection commit `7efaaa4` passed GitHub CI
  [run 39652418031](https://github.com/Stimurid/Kairoskopion/actions/runs/39652418031).

Explicit OPEN: this is a guarded L3 bridge consumer interface, not a universal
cross-organ ACID transaction. Generic legacy-science schemas, authenticated
owner-private cross-host ACL admission, timestamp-proven chronological replay,
and third unrelated owner-authorized corpus remain #64 work. Production
deployment and journal submission remain forbidden.

## #64 — independent audit findings and bounded P1 remediation (2026-10-22)

Independent Claude Code read-only review of PR #46 at `b76d7e4`:
**CHANGES_REQUIRED** (1 P1 / 7 P2; 0 P0). The complete reviewer output
is preserved owner-private on AORUS at
`_ops/T3-TALK-20261019/issue64_crossreview_b76d7e4.txt`.
The reviewer did not access the private manuscript corpus, perform journal
research or authorize a production merge.

P1 proof: a prefixed but *untagged* Evidence/HuntTrace could appear in the
consumer as receipt-authenticated while the legacy readback fingerprint,
which selects only tagged records, never examined it. Attacker needed graph
write access; nevertheless verified status could falsely imply publisher
FULL_TEXT proof.

This corrective slice does not rebuild Factory:
- The existing L3 readback now returns ephemeral content-hash pins for **all
  three exactly verified records** and the **two exact scientific events**.
  These pins come from the independent original source/receipt/graph readback,
  not a guessed suffix or journal name. No historic receipt is rewritten.
- A consumer snapshot proves its own T0 record/event bytes against the
  authenticated T1 pins. An inserted, modified, deleted, tag-erased or
  unreceipted child record/event cannot be promoted using an ID prefix.
- One unsupported/mixed imported case, ambiguous event ancestry or one
  unreceipted extra record/event quarantines the entire owner-science
  projection, retaining only independent ordinary graph rows.
- Malformed private receipt roots/errors return a safe status and reason
  category, without source paths or private payloads in the public API.
  Relative graph-root resolution is fixed when the store is constructed.
- A legacy science root and target Factory storage cannot coincide or nest:
  an isolated original source boundary is mandatory.
- Raw graph stores remain for repair/replay, distinct from consumer admission.
  All original DOI pointers retain INDEX_ONLY; scientific result remains
  provisional and author HOLD, never an approved ArticleSeed or SEND.

Measured negative tests: six new adversarial tests **failed first** on the
reviewed version; after the patch, the combined targeted suite passed
**69 passed / 1 skipped**. The **exact patched AORUS full regression**
(`pytest --basetemp C:\\t64p1sha -m 'not network'`) passed
**3788 passed / 19 skipped / 8 deselected**, exit 0. Real L3 V02 cold
readback still returns three pinned records, two source-bound events,
zero unverified approval, with unchanged science receipt SHA256
`58e14de028131b42f0d536618b95e87a1e63c2d554d6bca1bba866df06e11791`.

REMAINING #64: CPU/IO amplification from fresh SHA validation on each
operator-enabled HTTP read (P2), authorized filesystem roots with Windows
reparse/junction behavior (P2), clearer withheld-vs-absent handoff diagnostics
(P2), generic graph/store service layering (P2), typed cross-case research
import, chronology with evidence, independent third owner-authorized corpus
and cross-organ transaction closure. Do not describe this slice as ACID,
release acceptance, or a universal importer. GitHub CI and independent
*re-review of the repaired SHA* are separate gates.

## #64 second independent read-only audit / identity fix (2026-10-22)

Claude Code re-reviewed exact `224dec1` and returned CHANGES_REQUIRED:
two class/identity bugs, not a retraction of the verified earlier fixes.
A record with an injected `event_id` previously shadowed its own `id` in
the *consumer-scoping* function, and a numeric event ID was converted to
string for the quarantine index but not on lookup. Both could evade a
consumer read filter.

The remedy is confined to `OpportunityGraphStore.consumer_snapshot`:
`owner_case(item, is_event=...)` selects the correct identity namespace,
and event scope membership uses the same normalized string representation
as the index. Three new adversarial tests first failed against `224dec1`;
after this patch the complete focused graph/portfolio/bridge/handoff
selection passed 72 tests (1 Windows symlink test skipped).

Real AORUS L3 V02 performance measurement (five reads each, sample mean,
not a load test): ordinary private-disabled read 1.1 ms; cryptographically
verified owner science consumer read 17.3 ms; owner-source readback alone
15.1 ms. A speculative cross-request hash cache is **not implemented**:
it adds cache-staleness risk for a local 15 ms source operation. Revisit
only with a measured operator load or large-corpus benchmark.

The separate MAI PR #50 already provides a 53-route deterministic
batch-runner, but that is not 53 scholarly-qualified W12 routes. Its
science execution frontier is #51. PR46 still has two true
W12_EQUIVALENT_HELD routes for the T3 case; do not inflate the count
by importing unqualified MAI batch cards.
