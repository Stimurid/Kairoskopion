# Milestones — Kairoskopion

**Last updated:** 2026-06-09

---

## v0.1.0-alpha — Usable Local Build (current)

**Status:** Released on `main`

**Included capabilities:**
- Domain skeleton: 18+ dataclass models, 23 enums, JSONL registries
- 18-step deterministic pipeline: manuscript × venue → fit assessment
- 11 domain services (article modeling, venue profiling, scenario, fit, mismatch, rewrite, risk, compliance, evidence audit, bibliography, citation ecology)
- Source acquisition: local file registration (.md, .txt, .json, .html)
- Mock adapters: OpenAlex, Crossref, OpenCitations with evidence bridge
- Vault: markdown cards with cross-links, indexes, manifest, link validation
- Export/import: zip bundles with metadata
- Freshness/staleness tracking
- Quality gates: fit gate, submission gate
- CLI: 9 commands

**Excluded capabilities:**
- No PDF/DOCX extraction
- No real API calls
- No LLM
- No UI beyond CLI
- No SubmissionPack
- No review loop

**CLI commands:** `status`, `run-fixture`, `run-local`, `inspect-storage`, `adapters-smoke`, `vault-index`, `export-bundle`, `import-bundle`, `validate-bundle`

**Tests:** 351 passing

**Demo:** `kairoskopion run-local --manuscript examples/sample_manuscript.md --venue-guidelines examples/sample_venue_guidelines.md --scenario examples/sample_scenario.json`

---

## v0.2.0-local-documents — Robust Local File Intake

**Status:** Planned (Backlog Sprint 1)

**Included capabilities (cumulative):**
- Everything in v0.1.0-alpha
- PDF text extraction (pymupdf or pdfplumber)
- DOCX text extraction (python-docx)
- Improved section detection from extracted text
- Bibliography extraction from PDF/DOCX
- ManuscriptModel with word count and section count from extraction

**Excluded capabilities:**
- No OCR for scanned PDFs
- No image/figure extraction
- No GROBID integration

**CLI commands (new):** None new; `run-local` accepts .pdf and .docx files

**Tests expected:** 370+ (existing + document intake tests)

**Demo:** `kairoskopion run-local --manuscript paper.pdf --venue-guidelines guidelines.docx --scenario scenario.json`

---

## v0.3.0-real-adapters-optional — Real Metadata Adapters

**Status:** Planned (Backlog Sprint 2)

**Included capabilities (cumulative):**
- Everything in v0.2.0
- OpenAlex real API: work search, author lookup
- Crossref real API: DOI lookup, work search
- OpenCitations real API: citation links
- Rate limiting with backoff
- Live mode via `KAIROSKOPION_ADAPTERS_LIVE=1`
- Mock mode preserved as default

**Excluded capabilities:**
- No DOAJ, Sherpa, Semantic Scholar, Unpaywall
- No caching/dedup
- No fuzzy title matching

**CLI commands (new):** None new; `adapters-smoke` gains live mode

**Tests expected:** 390+ (existing + live adapter tests, mock tests unchanged)

**Demo:** `KAIROSKOPION_ADAPTERS_LIVE=1 kairoskopion adapters-smoke`

---

## v0.4.0-venue-profile — Venue Profile Builder

**Status:** Planned (Backlog Sprint 3 + 4)

**Included capabilities (cumulative):**
- Everything in v0.3.0
- Multi-source venue profiling from local files
- Multiple bibliography styles (APA, Vancouver, numbered)
- Better DOI extraction and reference dedup
- Enriched VenueModel with indexing, metrics, APC, review process fields
- Citation gap tasks with search queries
- New CLI: `profile-venue`

**Excluded capabilities:**
- No JournalModel/SectionModel sub-entities
- No editorial board profiling
- No corpus mining
- No automated venue page fetching

**CLI commands (new):** `profile-venue`

**Tests expected:** 430+

**Demo:** `kairoskopion profile-venue --sources venue_pages/ --storage-root .kairoskopion_demo`

---

## v0.5.0-litops-bridge — Litops Compatibility

**Status:** Planned (Backlog Sprint 5 + 6)

**Included capabilities (cumulative):**
- Everything in v0.4.0
- SubmissionPack entity with ready status
- Improved report generation
- Litops-compatible source registration
- ContextPack creation from pipeline evidence
- Vault cards compatible with Litops Obsidian vault
- Export as Litops-importable artifact bundle
- New CLI: `generate-report`

**Excluded capabilities:**
- No live Litops API connection
- No real-time sync

**CLI commands (new):** `generate-report`

**Tests expected:** 470+

---

## v0.6.0-whitecrow-bridge — WhiteCrow Patch Queue

**Status:** Planned (Backlog Sprint 7)

**Included capabilities (cumulative):**
- Everything in v0.5.0
- Patch candidate generation from RewritePlan
- ProtectedCore import from WhiteCrow export
- Field-core impact labels on every patch
- Export as WhiteCrow-importable patch bundle

**Excluded capabilities:**
- No live WhiteCrow API
- No Google Docs integration
- No automatic manuscript modification

**Tests expected:** 500+

---

## Future milestones (only when requested)

- **v0.7.0-llm-extraction** — Optional LLM-assisted article/venue modeling
- **v0.8.0-telegram-intake** — Telegram bot for file intake
- **v0.9.0-web-ui** — Minimal web panel for results browsing
- **v1.0.0** — Production-ready with all bridges and quality gates
