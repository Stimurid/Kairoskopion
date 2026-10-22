# TRIMURTI × ARTIKL — Citation engine and article portfolio frontier, 2026-10-22

**Integration candidate:** `f82c400eea8b4a1b52760f72e0bce8df514e7af0` in `fix/trm-cite-integrated-corpus-r2-20261021`. No merge to product main, production deploy, author citation patch, editor submission or publication certification has been authorized.

**QA:** exact worktree `C:\AI\llm\aiye-executor\worktrees\trm-cite-integrated-20261021`, `python scripts/run_project_qa.py`: **3599 passed, 8 deselected, 0 failed** on integrated code. Operator receipt: `runs/TRM_CITE_Z0_20261020/TRM_CITE_R1_R6_INTEGRATION_RECEIPT_20261022.json`, SHA-mirrored on Drive.

## I. Citation machine functional slices

### Z0 — Original-manuscript intake / claim and citation map
**Current:** implemented for Markdown/TXT; produces immutable audit, repair cases, original snapshot and work orders. Synthetic regression covered; owner manuscript SHA unaffected.
**Acceptance:** original bytes stable, each extracted citation bound to manuscript version, no invented page/identity. **VERTICAL PASS** for tested inputs. Broader DOCX/Google Docs editing not passed.

### R1 — Owned corpus → actual passage evidence
**Current:** accepts existing owner-held PDF/DOCX/TXT/MD without publisher or paid-source gates. Existing Sci-Hub MCP and LitOps are recognized input ecology, not mandatory paper purchase flow. PDF parsing fixed: use real PDF page-text extraction, never compressed stream bytes. Passage ID unique + locator present, honest parse confidence and SHA. R1 partial-replay and witness-class consumer tightened.
**Real pilot:** P. B. Mrdulyash (2019), local PDF (source SHA `6247620fce66cc680876282d62b6fe2d297be3db19888e722c5c26d62998d2ad`), unique page-1 passage, 1 OBSERVED, 0 BLOCKED; source PDF and separate synthetic claim manuscript unmodified. R1 transport is NOT a claim-entailment review.
**Acceptance:** real source bytes, real text extract and unambiguous passage, full provenance, no synthetic evidence laundered. **PASS for 1 bounded PDF pilot**, not systemwide coverage.

### R2 — Citation intent reconstruction
**Current:** provisional author-need from original quote, case, prior R1 evidence; new bridge consumes `source_evidence[]` returned by real R1. **FUNCTIONAL/PRELIMINARY**.
**Acceptance:** retain original author's claim and uncertainty; no fictional author intention. Needs author science review for independent PASS.

### R3 — Narrow Indago reentry
**Current:** produces bounded `QUEUED_NOT_EXECUTED` only where evidence insufficient. Real R1 passage recognised means no duplicate Indago hunt. Prior negatives preserved. **PLANNING PASS, LIVE PROVIDER WIRING OPEN**.
**Acceptance:** ingest actual Indago Return envelope and new passages, reuse old hunts, track request/return correlation and stop on saturation. **OPEN** for live multi-wave demonstration.

### R4 — Multiple intellectually distinct repair choices
**Current:** bibliography repair, change source, scope/thesis repair, normative-author-position, citation removal, abstain. A blocked source is *not* evidence of an incorrect citation. Deletion suggestion requires actual consulted witness plus explicit failure of support; actual anchored positive witness vetoes deletion. **FUNCTIONAL/PRELIMINARY**.
**Acceptance:** distinct effects/costs, real source support, counterarguments, author-visible scientific debts. Independent semantic review is **OPEN**.

### R5 — Version-locked proposal / copy-only reversible edit
**Current:** candidate diff, inverse, SHA binding, author receipt required, no automatic original mutation. Only structural citation removal is machine-renderable; other scholarly prose needs authored or analyst-approved wording. **SYNTHETIC E2E PASS**.
**Acceptance:** real author selected patch, original doc unchanged, new copy roundtrips, undo exact; Google Docs/native document editing **NOT IMPLEMENTED**.

### R6 — Post-patch reread
**Current:** reread altered copy through Z0, validate original unchanged and keep V1–V5 NOT_CHECKED. Typed refusal if original vanished. **SYNTHETIC E2E PASS**.
**Acceptance:** real author patch / real selected journal profile / independent V1–V5 human-scientific review. **NOT YET ACCEPTED**.

## II. Portfolio science and venue pairing

**G1:** exactly 20 local seeds S01–S20, old family IDs kept (F03, F08, F01-B, F12, F13, F15 etc.). **G2:** five-seed prepass records nearest work, access depth and novelty blockers. **G3:** 8 ArticleModels (S11,S12,S13,S14,S15,S16,S18,S20) plus 3 substantive argument skeletons (S11,S14,S18), Google Doc `1GKvkeW_oFtGEJthLqRW_GLaDVGcbvERhNP_g7N-KGqM`. Source depths still incomplete; no new manuscript passes.

**G4:** 100 hypothesis rows = 20 seeds × 5 pre-existing venue evidence packs; 40 model-backed rows and 60 seed-only. 20 rows for Filosofskiy Zhurnal are on editorial-route hold: OJS closed but separate email guide published. ALL rows NOT QUALIFIED, submissions ZERO. Google Doc `18cF1q90qgHCnNpd63z-ZDc0Q55cFQ4uv3wkYSrOCjDs`, private JSONL and replay script SHA-mirrored to Drive.

**G5 accepted for queue by AORUS Hub:** `jx-5f87048497da` (journal L3 actual article corpus), `jx-ed8efa9c18bd` (fulltext nearest precedents and novelty). Both QUEUED on owner's pinned Claude route at last observation, NOT claimed completed.

## III. Integration blockers before production and journal submission

1. Reconcile, review and merge f82c400 branch; run complete QA on true target product HEAD. No automatic merge.
2. Live Indago source return adapter ↔ R3; 5–10 genuinely held works with passage-level proof and rerun/negative-case semantics.
3. Author-facing scientific adjudication of source-to-claim entailment and novel contribution. Mere OBSERVED source does not imply V4.
4. DOCX and native Google Docs manuscript support; currently honest exact-copy patch is Markdown/TXT only.
5. Side-by-side source Google Docs panel is backlog `TRM-CITE-UI-001` in `docs/TRM_CITE_GOOGLE_DOCS_SIDECAR_BACKLOG_20261022.md`; do not block the scientific backend for it.
6. Article-target variants must be true scientific variants with documented editorial-field evidence (L3), full nearest predecessors, journal acceptance route, owner approval. Avoid parallel submission of substantially same manuscript.
7. Preserve durable source hunting results near project HEAD and per-seed records. G5 source collection feeds G4 instead of overwriting it.

## IV. Honesty of status
`3599 tests green` proves the machine's tested behavior on branch f82c400. It does not prove scientific novelty, represent the author's decision, establish an open call for papers, or indicate an article was submitted. Current stage is **INTEGRATED CANDIDATE + PRELIMINARY PORTFOLIO**.
