# TRM-CITE-UI-001 — Google Docs sidecar for citation evidence (BACKLOG ONLY)

Recorded 2026-10-22, requested by owner during R1-R6 citation-module development. Not part of current source-ingest / article-portfolio acceptance. No production UI is claimed.

## User scene
Two Google Docs are visible side by side. A (main manuscript) stays at an author's working position. B (source document) opens adjacent to it with the exact quote/passage under focus. Highlighting a citation, quotation or phrase in A proposes candidate work / edition / witness / passage references, then navigates B to the matching fragment with context. A may be a manuscript Google Doc and B another Google Doc; PDF/source-library witnesses must stay accessible in a separate viewer if Google Docs lacks stable native offsets.

## Functional elements
1. Browser extension or host-side panel reads an explicit user selection from A, contextual section and manuscript version, without rewriting A.
2. Resolve the source in the existing citation graph: Z0 case -> R1 Work/Edition/Witness/Passage, preserve witness SHA / read-depth / passage counts; distinguish user PDF, library file and Google Doc links.
3. Open or focus B, navigate to the exact text in place, display bounded surrounding paragraphs and bibliographic identity. A source without confirmed unique passage must not appear as an exact match.
4. Keep several candidate witnesses when needed; allow author to disambiguate; show author-facing citation defects, pending R2-R4 repairs and reversible diff previews on COPY only.
5. Optional later mode: RAG with inspectable retrieval trail and visual concept/evidence neighbourhood; generated answers cannot replace passages.
6. Return a non-mutating session record: doc A ID/version, selection locator, doc B ID, witness anchor, confidence, which candidate author chose, elapsed latency and errors. No extraction of private documents to a public endpoint.

## Architecture choices to test, not presupposed
- Chrome/Edge extension content script + side panel: test permissions and ability to read real Google Docs selections (canvas-based rendering and changing DOM can defeat naive text read).
- Two independent tabs/windows via HYDRA/Conversation Membrane only if the actual selection/deep-link mechanism is available; do not invent a Google Docs API 'scroll to arbitrary character' capability.
- Drive API / Docs API for structural references, native document IDs and revisions; source PDFs/locally held files through existing LitOps.
- For semantic retrieval use a transparent RAG layer with accessible matched text, not a made-up page number from embedding similarity.
- Research exact browser UX, selection event capture, published Google Docs anchors and feasible navigation approaches before implementation.

## Acceptance criteria for future MVP
- Two distinct real Google Docs opened side by side; explicit user selection in main doc resolves a **confirmed unique** source quote in second document and places it in view, with 2 paragraphs before/after.
- Stable doc IDs, source witness digest and truthful match depth displayed. Wrong work, ambiguous quote, changed document revision, inaccessible source, or absent locator report typed refusal.
- Clicking 'compare' shows manuscript quote, source quote, bibliographic data, and pending R2-R6 candidate repairs; no author text changed.
- No citation repair is applied until an author-approved reversible patch against an immutable original version.
- Test on AORUS Chrome/Edge with at least two Google Docs and one owner-held PDF. Record video or screenshots, interaction trace and failure cases. Typical case response target may be set only after initial measurement.
- Unknowns: cross-document Google Docs DOM behavior, right-click selection reliability, Google account auth reuse, policy for Drive-sharing scopes, source page navigation. These are engineering unknowns, not reasons to block R1-R6 batch work.

## Dependencies / status
- Depends on TRM-CITE R1-R6 integrated code, G3/G4 portfolio sources, Drive access and browser capture reliability.
- BACKLOG / UNSTARTED. No extension implemented, no API feasibility accepted.
- When started, create its own tests, screenshots, browser-specific compatibility findings, and a reversible deployment plan.
