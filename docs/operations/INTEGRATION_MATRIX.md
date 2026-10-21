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
