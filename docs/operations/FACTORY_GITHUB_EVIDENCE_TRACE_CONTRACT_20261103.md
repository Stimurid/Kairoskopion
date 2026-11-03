# TRIMURTI FACTORY — GitHub scientific evidence trail (owner directive, 2026-11-03)

**Decision:** Every meaningful intermediate research, synthesis, criticism, rewriting, review, rollback and negative step of an agent/factory run must be durably capturable as an independently readable, source-linked **Git commit**, with its final GitHub permalink and human-readable event view. This is not merely a final manuscript commit. The operator can click from a claim in a manuscript to why and how it changed, what sources actually supported the change, who or which executor proposed it, and whether the author accepted it.

**Status:** OWNER_ACCEPTED_OBSERVABILITY_CONTRACT / ENGINEERING_INTEGRATION_AND_END_TO_END_ACCEPTANCE_OPEN. This document is a required specification for the existing Trimurti pipelines (LitOps, WhiteCrow/Artikl, Indago, Kairon/Kairoskopion, scientific portfolio and Publisher Board). A documentation commit does NOT mean all those runners already comply.

## Contract: required event units

Every substantive stage has a **stable event ID**, an ordered step within a stable run / research wave and a durable event record:

1. **Intake / scope:** actual source IDs, exact source revision and content SHA, consent/access boundary, existing accepted author decisions, protected idea nuclei, task/seed/ArticleIdentity IDs, temporal authority; missing materials recorded explicitly.
2. **Search / discovery:** actual research question, query strings/filters, provider and date, returned candidate IDs/DOIs/URLs, rejected/duplicate/not-retrievable URLs and why; provenance of reused prior hunts. No reconstructed fake query history.
3. **Read / source evidence:** stable DOI/publisher URL/provider ID, original content location and version, `read_depth=INDEX|ABSTRACT|PASSAGES|SECTIONS|FULLTEXT`; exact inspected section/short permissible quotation/passages and stable anchors, evidence rights/license, what was and **was not** read. A `FULLTEXT` claim requires independently verifiable full coverage; `ABSTRACT` can never authorize a full-content rebuttal.
4. **Finding / prior-art collision:** precise manuscript claim X@revision/span, external P@source/span, argument of agreement/contradiction/novelty pressure, negative and rival explanations, proposed operations, source access restrictions. Distinguish `SOURCE_OBSERVED`, `OPERATOR_INFERRED`, `RETROSPECTIVE_RECONSTRUCTION`.
5. **Decision / branch:** proposed alternatives, reasons for discard/HOLD/REVISE/REJECT/NEW_ARTICLE/MERGE_PROPOSAL; actual author decision linked to verifiable approval from authorized person; do not promote an executor label, local test or model review into author authorization.
6. **Execution / revision:** actor/carrier, model/provider if known, operator code/contract rev, actual prompt or access-controlled prompt ref and digest (no internal model thoughts required), exact input hashes, chosen branch and parent ID, allowed change scope, output full text hash, exact text diff + conceptual/claim delta, what remains untouched, failed attempts and stderr/log receipts (sanitized).
7. **Review / release:** reviewer independence, quality/test verdict tied to candidate SHA, claim/span/source validation, publication/rights/venue gates, human decision, latest Drive provider revision ID, Git tree ref, expected/observed sync state, actual external-send provider receipt if and only if a human authorized a real send.

An event may have `no_text_change=true`; a negative finding, failed search, source 403, rejected rival, stale target or failed check **still must be visible**. One execution may contain many read/finding events. All source and hypothesis aliases retain their original identities.

## GitHub checkpoint and navigability rule

- Each **meaningful stage or bounded research wave** is finalized as an append-only, human-readable **checkpoint commit**. Do NOT commit each model token or UI animation. Do NOT omit substeps inside a wave: a machine-readable event index names every search/read/finding/operation and links to its retained payload or explicit `UNRECORDED` gap. For an unclean shutdown commit whatever was safely captured as `FAILED_PARTIAL` and resume with a new event, never invent a successful checkpoint.
- Use the existing **private content/evidence repository** with exact scope and permissions, NOT a public issue for raw private source bodies and NOT one repository per article. Git object trees may contain `events/<id>.json`, `causal_events/<id>.json`, `operations/<id>.json`, `runs/<run-id>/index.md`, source claim manifests, text diffs and safe disclosure notes. Reuse existing Pantheon ScientificPortfolio G3 event storage, existing scientific_git registrars and L3 evidence ledgers instead of spawning a second source of truth.
- Include `source_url` plus precise quote locator/read-depth; `previous_revision`, `new_revision`, parent SHA, claim ID, operator, query/run parameters, DOIs, issue/PR, `drive_doc_id` and provider revision, author gate, and `external_status`. Stable GitHub URLs include the **actual remote commit SHA**, file path, and line/span anchor when available. A moving branch URL alone is insufficient. A source pointer is not evidence if the source has not been read.
- Readable index: **each run has a `README/index.md` in GitHub** linking its stage commits, evidence, alternatives, diffs, reviewer reports and exact human-readable resulting texts, with a short 1–3 sentence why-this-changed summary for each stage. An owner should be able to reconstruct the trajectory without opening a chat or executing code.
- Lifecycle is explicit: `LOCAL_CAPTURED → GIT_COMMITTED_LOCAL → GITHUB_PUSHED → REMOTE_READBACK_VERIFIED`. A local SHA or a GitHub push response without readback is not proof of linked archive. A temporary outage produces `SYNC_PENDING`; it cannot be reported as `GITHUB_VERIFIED`.
- Git and Google Drive have independent copy states: `GIT_REMOTE_VERIFIED`, `DRIVE_REVISION_VERIFIED`, `BOTH_VERIFIED`, `DIVERGED`, `SYNC_PENDING`. Never overwrite changed Google Docs in the name of sync; use requiredRevisionId / three-way conflict and preserve source documents and their comment threads. Deletion does not propagate automatically.
- Protected source bytes, copyrighted fulltexts, private emails, personal data, secrets and unlicensed attachments are kept in authorization-appropriate encrypted/owner-only stores. The checkpoint contains stable safe refs + SHA + access/gap status. Never leak content by embedding it in a public GitHub URL, commit message, issue or code fixture.

## Scientific/release gates: prove or hold

- `SCIENCE_CHANGE_VERIFIABLE` requires a linked source/claim/finding/decision chain and actual version before/after; `GITHUB_TRAIL_COMPLETE` requires actual remote readback of every expected stage/event ref and a clickable complete index.
- `AUTHOR_GO` requires a human-author event; `INDEPENDENT_REVIEW_PASS` requires a genuine independent review on the **newest** SHA, with read coverage; `MANUSCRIPT_GO` and any external send remain separate D25/author authority.
- If an actor cannot capture a source, full prompt, read depth, failure or legal source bytes, mark `ACCESS_DENIED`, `NOT_CAPTURED`, `PARTIAL_READ` or `REDACTED_WITH_DIGEST`. Do not infer the absent data, nor self-certify `FULLTEXT`.
- This contract does not instruct agents to reveal hidden chain-of-thought. Required are observable queries, model/call metadata where available, scientific reasons stated for changes, inputs/outputs, checks and decisions.
- No downstream claim of a **complete auditable factory** if a real native source→prior art→variant→review→Drive/Git cycle was not executed on an independently chosen, not-hardcoded corpus with a permission-respecting readback.

## Engineering acceptance / existing hooks

A. Add/extend one shared trace checkpoint adapter at the existing factory runner boundary. Before finishing each scientific stage, persist immutable event payloads, index, diff and receipts; Git commit and push; verify actual remote tree and URLs. Stage acceptance fails closed or stays `SYNC_PENDING` if remote verification is absent. Journals/reviews/author acceptance must not become green because of code tests.
B. Cover negative tests: search returned only abstract; DOI exists but HTML unavailable; stale journal page; 403/read denied; review anchored to old SHA; Git push failed; untracked file omitted; dirty tree; author-name forged; contradictory decisions; Drive concurrent human edits; remote tag/ref moved; repeated wave; negative science finding; private source access leak; multi-agent concurrent writes.
C. Acceptance journey: arbitrary real author corpus → multi-wave Indago evidence → WhiteCrow/Artikl objection → target venue proposal → bounded revision → independent assessment → author HOLD → exact GitHub commit permalinks and Drive revision history. Verify cold resume and old source preserved; no external submit.

**Existing precedents and gaps:**
- MAV-R1 P02/P03/P04/P05 currently contain some source pressure, parent SHA, before-after, failed attempts and proof receipts. These are partial, not one complete graph.
- L3 event/decision ledger has 96 retrospective and live events, explicitly incomplete original search paths.
- Pantheon PR #8 scientific Git G3 has a local, source-anchored causal event Git commit feature, without full scientific episode and remote production sync; it is a foundation to extend, not another pipeline.
- G0–G7 Scientific Git critical path: `Stimurid/cognitive-workbench/docs/pantheon/SCIENTIFIC_GIT_CRITICAL_PATH_20261103.md`, branch `feature/scientific-portfolio-20261103`.
- Current factory source runner operating contract: `docs/operations/FACTORY_SOURCE_RESEARCH_STAGE.md`.
- Owner benchmark: MAV-BASE4 (F02/ATT/MEM/U04) scientific Git, plus separate B09/F06 bodies and genuinely unfamiliar independent corpus.

**Policy distinction:** this is the requirement for future work and integration. Actual progress is reported only when code, executable tests, real-run stage checkpoints, remote GitHub readback and private Drive readback have been separately observed.
