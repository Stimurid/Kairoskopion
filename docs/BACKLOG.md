# Engineering Backlog — Kairoskopion

**Last updated:** 2026-06-09

Each sprint package is a self-contained autonomous unit. An agent reads CLAUDE.md → PROJECT_STATUS → SPEC_COVERAGE_MATRIX → this BACKLOG, picks the next sprint, implements on a feature branch, updates docs/tests/status, commits, pushes. No manual micromanagement required.

---

## Sprint 1: Real Document Intake

**Goal:** Accept PDF, DOCX, TXT, MD files and extract text content for pipeline processing.

**Scope:**
- PDF text extraction using `pymupdf` (fitz) or `pdfplumber` — lightweight, no Java
- DOCX text extraction using `python-docx`
- Improved MD/TXT intake (section detection, bibliography extraction)
- Updated `source_intake.py` with extraction dispatching
- `ManuscriptModel` gains `word_count`, `section_count` from extracted text
- New optional dependency group: `pip install kairoskopion[extract]`

**Non-goals:**
- No OCR (scanned PDFs remain `not_extracted`)
- No image/figure extraction
- No GROBID integration
- No layout analysis

**Files likely touched:**
- `src/kairoskopion/adapters/source_intake.py`
- `src/kairoskopion/services/article_modeling.py`
- `src/kairoskopion/services/bibliography_parsing.py`
- `pyproject.toml` (optional deps)
- `tests/test_document_intake.py` (new)
- `tests/fixtures/` (sample PDF, DOCX)

**Tests required:**
- PDF extraction: text present, page count, bibliography section found
- DOCX extraction: text present, section headers detected
- Binary fallback: unsupported format → `not_extracted` status
- Empty file handling
- Large file handling (truncation policy)

**Acceptance criteria:**
- `kairoskopion run-local --manuscript paper.pdf` works
- Extracted text feeds into pipeline normally
- SourceSnapshot records extraction method and status
- No new required dependencies (extract deps are optional)

**Risk notes:**
- `pymupdf` has a complex license (AGPL); `pdfplumber` is MIT. Choose carefully.
- DOCX extraction quality varies with document complexity.

**Depends on:** None (current main is sufficient base).

---

## Sprint 2: Real Optional Adapters

**Goal:** Connect OpenAlex, Crossref, OpenCitations APIs with real HTTP calls, disabled by default.

**Scope:**
- `openalex.py`: real `search_works(query)` and `get_work(openalex_id)` via REST API
- `crossref.py`: real `lookup_doi(doi)` and `search_works(query)` via REST API
- `opencitations.py`: real `get_citations(doi)` via REST API
- All adapters: `is_mock=False` when using real API, `is_mock=True` preserved for mock path
- `AdapterConfig.is_mock` flag controls behavior (default: `True`)
- Rate limiting: simple retry with backoff
- Network disabled by default: `KAIROSKOPION_ADAPTERS_LIVE=1` env var to enable
- Mock path preserved and tested independently

**Non-goals:**
- No API key management UI
- No DOAJ, Sherpa, Semantic Scholar, Unpaywall
- No caching/dedup layer
- No fuzzy title matching

**Files likely touched:**
- `src/kairoskopion/adapters/openalex.py`
- `src/kairoskopion/adapters/crossref.py`
- `src/kairoskopion/adapters/opencitations.py`
- `src/kairoskopion/adapters/base.py` (rate limit helpers)
- `pyproject.toml` (optional `requests` or `httpx` dep)
- `tests/test_adapters_live.py` (new, skipped unless `KAIROSKOPION_ADAPTERS_LIVE=1`)
- `tests/test_adapters.py` (mock tests preserved unchanged)

**Tests required:**
- Mock tests: unchanged, always run
- Live tests: marked `@pytest.mark.skipunless(KAIROSKOPION_ADAPTERS_LIVE)`, test real API calls
- Rate limit: test backoff logic with mock HTTP
- Error handling: network timeout, 404, 429, 500
- Evidence bridge: real adapter results → SourceSnapshot → EvidenceItem with `is_mock=False`

**Acceptance criteria:**
- `kairoskopion adapters-smoke` works with mocks (default)
- `KAIROSKOPION_ADAPTERS_LIVE=1 kairoskopion adapters-smoke` calls real APIs
- Real adapter results have `is_mock=False`, evidence_status=`VENDOR_CLAIM`
- All 351+ existing tests still pass
- No required new dependencies

**Risk notes:**
- OpenAlex polite pool requires email in User-Agent header
- Crossref rate limits may cause flaky live tests
- OpenCitations API may have downtime

**Depends on:** None.

---

## Sprint 3: Venue Profile Builder

**Goal:** Build VenueModel from locally saved journal pages and guidelines files.

**Scope:**
- `venue_profiling.py` enhanced: accept multiple source files (aims/scope, guidelines, editorial board, policy pages)
- Extract venue properties from structured text: scope, article types, language policy, submission system, review process, indexing claims, APC
- `VenueModel` gains: `official_urls`, `indexing_claims`, `metrics_claims`, `open_access_status`, `APC_policy`, `review_process_claims`
- New CLI command: `kairoskopion profile-venue --sources dir_of_pages/ --storage-root ...`
- Each source file registered with source role

**Non-goals:**
- No HTTP fetch (user saves pages locally)
- No JournalModel/SectionModel/IssueModel sub-entities
- No editorial board profiling
- No corpus mining

**Files likely touched:**
- `src/kairoskopion/services/venue_profiling.py`
- `src/kairoskopion/schema.py` (VenueModel field additions)
- `src/kairoskopion/adapters/source_intake.py`
- `src/kairoskopion/cli.py`
- `src/kairoskopion/cards.py` (venue card enrichment)
- `tests/test_venue_profiling.py`
- `tests/fixtures/` (sample venue pages)

**Tests required:**
- Multi-source venue profiling: 3+ source files → richer VenueModel
- Source role assignment per file
- Missing fields → UNKNOWN, not absent
- Empty guidelines → minimal VenueModel with unknowns
- Pipeline integration: profiled venue feeds into fit assessment

**Acceptance criteria:**
- User can save journal pages as .md/.txt/.html, point CLI at directory
- VenueModel has more fields filled than from single guidelines file
- Evidence refs trace to specific source files
- Vault card shows enriched venue profile

**Risk notes:**
- Text extraction from saved HTML pages may lose structure
- Venue page formats vary wildly between publishers

**Depends on:** Sprint 1 (better file intake) recommended but not strictly required.

---

## Sprint 4: Bibliography Robustness

**Goal:** Improve reference extraction, citation gap analysis, and DOI resolution.

**Scope:**
- Multiple bibliography styles: APA, MLA, Chicago, Vancouver, numbered
- Better DOI extraction from reference strings
- Reference deduplication
- Year range analysis improvements
- Citation gap tasks with specific search queries
- Reference → adapter linking (when adapters are live)

**Non-goals:**
- No fuzzy title matching via API
- No automatic reference verification
- No citation graph analysis

**Files likely touched:**
- `src/kairoskopion/services/bibliography_parsing.py`
- `src/kairoskopion/services/citation_ecology.py`
- `tests/test_bibliography_parsing.py`
- `tests/test_citation_ecology.py`
- `tests/fixtures/` (bibliography samples in different styles)

**Tests required:**
- APA, Vancouver, numbered reference parsing
- DOI extraction from various formats
- Dedup: same reference in different formats
- Citation gap detection with actionable search queries

**Acceptance criteria:**
- 80%+ DOI extraction rate from well-formed references
- Multiple bibliography styles recognized
- No duplicate references in analysis output

**Risk notes:**
- Reference parsing without ML is inherently fragile
- Edge cases in humanities citation styles

**Depends on:** None.

---

## Sprint 5: Report Quality Layer

**Goal:** Better markdown reports, SubmissionPack entity, improved export bundles.

**Scope:**
- `SubmissionPack` entity: metadata, files, statements, checklist, missing items, ready status
- Improved pipeline artifact: executive summary, evidence trail, actionable next steps
- Better vault card formatting
- Export bundle includes human-readable summary report
- `kairoskopion generate-report --storage-root ...` CLI command

**Non-goals:**
- No PDF report generation
- No Word/DOCX output
- No cover letter generation

**Files likely touched:**
- `src/kairoskopion/schema.py` (SubmissionPack)
- `src/kairoskopion/services/submission_pack.py` (new)
- `src/kairoskopion/cards.py`
- `src/kairoskopion/artifacts.py`
- `src/kairoskopion/cli.py`
- `src/kairoskopion/exchange.py`
- `tests/test_submission_pack.py` (new)

**Tests required:**
- SubmissionPack creation from pipeline result
- Ready status logic (blocking items prevent ready)
- Report generation from stored results
- Export bundle with summary

**Acceptance criteria:**
- SubmissionPack entity persisted to registry
- Vault card for SubmissionPack
- Report command produces comprehensive markdown
- Export bundle includes report

**Risk notes:**
- Report format requires user feedback to stabilize

**Depends on:** None (but better after Sprint 1-4).

---

## Sprint 6: Litops Compatibility Bridge

**Goal:** Export/import data in Litops-compatible format.

**Scope:**
- Source registration compatible with Litops Source model
- ContextPack creation from pipeline evidence
- Vault card format compatible with Litops Vault/Obsidian
- Export as Litops-importable artifact bundle

**Non-goals:**
- No live Litops API connection
- No real-time sync
- No Litops Telegram integration

**Files likely touched:**
- `src/kairoskopion/integrations/litops.py`
- `src/kairoskopion/exchange.py`
- `tests/test_litops_bridge.py` (new)

**Acceptance criteria:**
- Exported bundle can be manually imported into Litops vault
- Source IDs are compatible
- ContextPack references are valid

**Depends on:** Sprint 5 (SubmissionPack, better reports).

---

## Sprint 7: WhiteCrow Patch Queue Bridge

**Goal:** Generate patch candidates for WhiteCrow from RewritePlan.

**Scope:**
- Patch candidate generation from RewritePlan items
- ProtectedCore import from WhiteCrow export
- Field-core impact labels on every patch
- Export as WhiteCrow-importable patch bundle

**Non-goals:**
- No live WhiteCrow API
- No automatic manuscript modification
- No Google Docs integration

**Files likely touched:**
- `src/kairoskopion/integrations/whitecrow.py`
- `src/kairoskopion/services/rewrite_planning.py`
- `tests/test_whitecrow_bridge.py` (new)

**Acceptance criteria:**
- RewritePlan → patch candidates with core impact labels
- ProtectedCore respected (core_touching changes flagged)
- Exported patches importable by WhiteCrow

**Depends on:** Sprint 6 (Litops bridge patterns).

---

## Sprint 8: LLM-Assisted Extraction (when requested)

**Goal:** Optional LLM-powered article modeling and venue profiling.

**Scope:**
- LLM provider interface (OpenAI-compatible)
- LLM-assisted ArticleModel extraction
- LLM-assisted VenueModel extraction
- Deterministic fallback preserved
- Evidence status: LLM outputs marked as INFERENCE

**Non-goals:**
- No fine-tuned models
- No prompt optimization
- No multi-model comparison

**Depends on:** Sprint 1-4 (stable extraction layer).

---

## Sprint 9: Telegram / Web UI (much later)

**Goal:** User-facing interfaces beyond CLI.

**Scope:**
- Telegram intake bot (WhiteCrow-style)
- Minimal web panel for results browsing
- Upload → pipeline → results flow

**Non-goals:**
- No real-time collaboration
- No SaaS deployment

**Depends on:** Sprint 1-8.

---

## Sprint selection rules

1. Agent reads BACKLOG.md and SPEC_COVERAGE_MATRIX.md
2. Picks the lowest-numbered sprint whose dependencies are met
3. User can override by naming a specific sprint
4. Each sprint = one feature branch, one commit message, one push
5. No sprint may silently skip tests or docs
6. No sprint may break existing tests
7. After sprint: update PROJECT_STATUS, ROADMAP, SPEC_COVERAGE_MATRIX, CLAUDE.md
