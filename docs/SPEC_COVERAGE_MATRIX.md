# Spec Coverage Matrix — Kairoskopion

**Last updated:** 2026-06-09
**Spec source:** `docs/KAIRON_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md` (10 waves, 12665 lines)
**Implementation:** `src/kairoskopion/` + `tests/`

## How to read this matrix

- **Implemented** — code exists, tests pass, CLI accessible
- **Partial** — core logic exists but spec requires more (fields, statuses, depth)
- **Stub** — type/contract exists but no real behavior behind it
- **Planned** — in ROADMAP/BACKLOG, not yet coded
- **Deferred** — explicitly postponed (needs LLM, UI, external infra)
- **Rejected** — spec item contradicts project decision or is superseded

Priority: P0 = blocking next milestone, P1 = next sprint candidate, P2 = mid-term, P3 = long-term/when requested.

---

## Wave 1 — Product Definition, Boundaries, Core Formula (§1–5)

| Spec area | Required capability | Status | Evidence | Acceptance criteria | Missing | Priority | Sprint |
|-----------|-------------------|--------|----------|-------------------|---------|----------|--------|
| §1 Product definition | Evidence-first publication-positioning system | Implemented | `schema.py`, `enums.py`, `evidence.py` | System produces traceable outputs | — | — | Done |
| §1 Core formula | ArticleModel × VenueModel × Scenario → Fit → Mismatch → Plans | Implemented | `pipelines/manuscript_venue_fit.py` (18 steps) | Pipeline runs end-to-end | — | — | Done |
| §2 Non-goals | No single fit score, no fake refs, no submission automation | Implemented | `enums.py` (FitAxisValue: strong/medium/weak/bad/unknown), ADR-04, ADR-07, ADR-08 | Tests enforce multi-axis, no score | — | — | Done |
| §2 Hard prohibitions | Evidence status taxonomy enforced | Implemented | `enums.py` (EvidenceStatus, 11 values) | Enum test coverage | — | — | Done |
| §3 Litops position | Bounded context, not Litops fork | Implemented | Separate repo, `integrations/litops.py` stubs | ADR-01 | — | — | Done |
| §3 WhiteCrow position | Field/manuscript layer respected | Implemented | `integrations/whitecrow.py` stubs | ADR-12 (protected core) | — | — | Done |
| §4 Core workflow formula | Full formula chain | Implemented | Pipeline: article→venue→scenario→fit→mismatch→rewrite+risk+compliance | Fixture pipeline output | CitationPlan as separate entity (merged into citation ecology) | P2 | — |
| §5.1 Article Context | ArticleModel, ManuscriptModel, ProtectedCore | Partial | `schema.py` (ArticleModel, ManuscriptModel) | Serialize/deserialize, unknowns field | FieldModelReference, ArticleVariant not implemented | P2 | Integration bridges |
| §5.2 Venue Context | VenueModel, JournalModel, SectionModel, IssueModel, PublicationRegimeModel | Partial | `schema.py` (VenueModel, PublicationRegimeModel) | VenueModel created from guidelines | JournalModel, SectionModel, IssueModel, SpecialIssueModel, EditorialBoardProfile, PublishedArticleCorpus, PublishedArticlePattern, CitationExpectationProfile, TacitVenueSignal — not implemented | P2 | Venue profile builder |
| §5.3 Submission Scenario | SubmissionScenario with user constraints | Implemented | `schema.py`, `services/scenario.py` | Created from fixture/user JSON | Scenario interview (interactive question flow) not implemented | P2 | — |
| §5.4 Fit & Adaptation | FitAssessment, MismatchMap, RewritePlan, CitationPlan | Partial | All 4 exist in `schema.py` + services | Multi-axis fit works | ReframePlan not implemented; CitationPlan is merged into CitationEcologyReport | P2 | — |
| §5.5 Compliance & Risk | RiskReport, ComplianceChecklist, SubmissionPack | Implemented | RiskReport (18 types) + ComplianceChecklist + SubmissionPack | Risk items, checklist, submission readiness | — | — | Done |
| §5.6 Evidence & Provenance | Evidence status on every claim | Implemented | `enums.py`, `evidence.py`, `schema.py` (evidence_refs, unknowns on all entities) | 11 evidence statuses enforced | Per-field evidence tracking (not per-entity) | P3 | — |
| §5.7 Review Loop | ReviewOutcome, RevisionPlan, VenueMemory | Planned | — | — | Not implemented | P3 | Review loop |
| §5.8 Integration Context | Litops/WhiteCrow/External boundaries | Implemented | `integrations/litops_bridge.py`, `integrations/whitecrow_bridge.py` | JSONL export bridges functional | No live API connection | — | Done |

## Wave 2 — Entity Model (§6–11)

| Spec area | Required capability | Status | Evidence | Missing | Priority | Sprint |
|-----------|-------------------|--------|----------|---------|----------|--------|
| §6.1 Evidence Status Taxonomy | 11 evidence statuses | Implemented | `enums.py::EvidenceStatus` | — | — | Done |
| §6.2 EvidenceItem | Atomic evidence fragment | Implemented | `schema.py::EvidenceItem`, `evidence.py` | `claim_supported`, `page_or_section` fields simplified | P3 | — |
| §6.2 SourceSnapshot | Source state at analysis time | Implemented | `schema.py::SourceSnapshot`, `adapters/source_intake.py` | `staleness_policy`, `used_in_context_packs` not tracked | P2 | — |
| §6.2 ContextPackRef | Reproducible evidence bundle | Stub | `integrations/litops.py::ContextPackRef` | No functional ContextPack creation | P2 | Litops bridge |
| §6.3 ArticleModel | Publication-facing article model | Partial | `schema.py::ArticleModel` (20+ fields) | Missing: `title_candidates`, `abstract_candidates`, `theoretical_shoulders`, `opponents_or_contrasts`, `audience_candidates`, `mutable_zones`, `high_risk_zones` | P1 | — |
| §6.4 ManuscriptModel | Structural text map | Partial | `schema.py::ManuscriptModel` | Missing: `section_blocks`, `figures`, `tables`, `supplementary_materials`, `block_mapping_status` | P2 | Doc intake |
| §6.5 FieldModelReference | WhiteCrow field pointer | Stub | `integrations/whitecrow.py::FieldModelRef` | No functional creation | P3 | WhiteCrow bridge |
| §6.6 ArticleVariant | Publication-oriented variant | Planned | — | Not implemented | P3 | — |
| §6.7 VenueModel | Publication container model | Partial | `schema.py::VenueModel` (15+ fields) | Missing: `journal_model_id`, `section_model_ids`, `issue_model_ids`, `editorial_board_profile_id`, `published_corpus_id`, `citation_expectation_profile_id`, `tacit_signal_ids`, `prior_outcome_ids` | P1 | Venue profile |
| §6.8 JournalModel | Serial journal entity | Planned | — | Not implemented (VenueModel covers basics) | P2 | Venue profile |
| §6.9 SectionModel | Journal section/article type | Planned | — | Not implemented | P2 | Venue profile |
| §6.10 IssueModel/SpecialIssueModel | Time-bound containers | Planned | — | Not implemented | P3 | — |
| §6.11 PublicationRegimeModel | How publication works | Partial | `schema.py::PublicationRegimeModel`, `enums.py::PublicationRegimeType` (13 types) | Only enum + description; no `fit_axes_modifier`, `compliance_modifier`, `risk_modifier` | P2 | — |
| §6.12 EditorialBoardProfile | Editorial structure | Planned | — | Not implemented | P3 | — |
| §6.13 PublishedArticleCorpus | Corpus for pattern inference | Planned | — | Not implemented | P2 | Venue profile |
| §6.14 PublishedArticlePattern | Corpus-derived observations | Planned | — | Not implemented | P2 | Venue profile |
| §6.15 CitationExpectationProfile | Venue citation expectations | Planned | — | Partially covered by CitationEcologyReport | P2 | Bibliography robustness |
| §6.16 TacitVenueSignal | Non-formal knowledge | Planned | — | Not implemented | P3 | — |
| §6.17 SubmissionScenario | User goal/constraints | Implemented | `schema.py::SubmissionScenario` (15+ fields) | Missing: `prestige_priority`, `speed_priority`, `acceptance_probability_priority`, `questions_asked`, `answers` | P2 | — |
| §6.18 FitAssessment | Multi-axis comparison | Implemented | `schema.py::FitAssessment`, `services/fit_assessment.py` | 12 axes implemented (topic, discipline, genre, argument_structure, method, citation_ecology, novelty_positioning, language_register, audience, formal_compliance, author_eligibility, publication_regime) | Missing: `rewrite_effort`, `citation_effort`, `compliance_effort`, `time_risk`, `strategic_value` | P2 | — |
| §6.19 MismatchMap | Where fit fails | Implemented | `schema.py::MismatchMap`, `services/mismatch_mapping.py` | Missing: `critical_mismatches` vs `actionable` vs `non_actionable` classification | P2 | — |
| §6.20 RewritePlan | Manuscript form changes | Implemented | `schema.py::RewritePlan`, `services/rewrite_planning.py` | Missing: `draft_text_optional`, detailed change types | P2 | — |
| §6.21 ReframePlan | Deep article variant | Planned | — | Not implemented | P3 | — |
| §6.22 CitationPlan | Citation work for fit | Partial | Merged into `CitationEcologyReport` | Separate CitationPlan entity not created | P2 | Bibliography |
| §6.23 RiskReport | Publication risks | Implemented | `schema.py::RiskReport`, `services/risk_reporting.py` | 18 risk types implemented | — | — | Done |
| §6.24 ComplianceChecklist | Venue-derived checklist | Implemented | `schema.py::ComplianceChecklist`, `services/compliance.py` | Generic + venue-derived; no guideline-selection engine | P2 | — |
| §6.25 SubmissionPack | Operational submission object | Implemented | `schema.py::SubmissionPack`, `services/submission_pack.py` | Readiness assessment, cover letter, statements | — | — | Done |
| §6.26 ReviewerSimulation | Controlled risk analysis | Deferred | ADR / spec: "not implemented; schema/prohibition only" | Explicitly deferred until evidence layer stable | P3 | — |
| §6.27 ReviewOutcome | Post-submission learning | Planned | — | Not implemented | P3 | Review loop |
| §6.28 RevisionPlan | Review outcome → actions | Planned | — | Not implemented | P3 | Review loop |
| §6.29 VenueMemory | Accumulated venue knowledge | Planned | — | Not implemented | P3 | Review loop |
| §7 Entity Lifecycles | Lifecycle states per entity | Partial | `enums.py::LifecycleStatus` (12 values) | Applied to models, but lifecycle transitions not enforced | P2 | — |
| §8 Entity Relations | Relation graph | Partial | IDs cross-reference between entities | No enforced referential integrity | P3 | — |
| §9 MVP Object Scope | MVP-0 schemas | Implemented | All MVP-0 required entities exist | — | — | Done |
| §10 Persistence | JSONL registries | Implemented | `registry.py`, `persistence.py`, 16+ registries | — | — | Done |

## Wave 3 — Integration Contracts (§12–23)

| Spec area | Required capability | Status | Evidence | Missing | Priority | Sprint |
|-----------|-------------------|--------|----------|---------|----------|--------|
| §12 Integration architecture | 4 boundaries defined | Implemented | Litops bridge + WhiteCrow bridge functional | JSONL export bridges | No live API | — | Done |
| §13 Litops integration | Source/Workset/ContextPack/Artifact/Vault exchange | Implemented | `integrations/litops_bridge.py` (source+artifact JSONL export) | CLI `export-litops-pack` | No live Litops API | — | Done |
| §14 WhiteCrow integration | Field/Manuscript/PatchQueue/ProtectedCore exchange | Implemented | `integrations/whitecrow_bridge.py` (patch queue from mismatches/rewrites/compliance/risks) | CLI `export-whitecrow-patches` | No live WhiteCrow API | — | Done |
| §15 Internal services | Service boundaries | Implemented | 11 service modules in `services/` | All deterministic, no LLM | — | Done |
| §16–23 Vault/External doc | Vault projections, External doc bridge | Partial | Vault cards + indexes + manifest | No external doc bridge (Google Docs/DOCX) | P3 | — |

## Wave 4 — Data Adapters (§24–37)

| Spec area | Required capability | Status | Evidence | Missing | Priority | Sprint |
|-----------|-------------------|--------|----------|---------|----------|--------|
| §24 Adapter layer purpose | Source → Snapshot → Evidence flow | Implemented | `adapters/base.py`, `adapters/bridge.py` | — | — | Done |
| §25 AdapterResult contract | Standardized adapter output | Implemented | `adapters/base.py::AdapterResult` | Simplified vs spec (no `rate_limit_info`, `cost_info`, `raw_response_ref`) | P2 | Real adapters |
| §26.1 Manual URL Snapshot | URL → Source/Snapshot/Evidence | Stub | `adapters/url_snapshot.py` (placeholder, no real fetch) | No HTTP fetch, no HTML extraction | P1 | Real adapters |
| §26.2 File Intake / PDF | PDF/DOCX text extraction | Implemented | `adapters/source_intake.py` (PDF via pypdf, DOCX via python-docx, MD/TXT/JSON/HTML) | 9 extraction statuses | No OCR | — | Done |
| §26.3 OpenAlex adapter | Work search, author lookup | Implemented | `adapters/openalex.py` (mock + real mode with HTTP caching) | Work search functional | No author lookup | — | Done |
| §26.4 Crossref adapter | DOI lookup, work search | Implemented | `adapters/crossref.py` (mock + real mode with HTTP caching) | DOI lookup + search functional | — | — | Done |
| §26.5 OpenCitations adapter | Citation links | Implemented | `adapters/opencitations.py` (mock + real mode with HTTP caching) | Citation query functional | — | — | Done |
| §26.6 DOAJ adapter | Directory of OA journals | Planned | — | Not implemented | P2 | Real adapters |
| §26.7 Sherpa/RoMEO adapter | OA policy lookup | Planned | — | Not implemented | P3 | — |
| §26.8 Semantic Scholar adapter | Full-text search, references | Planned | — | Not implemented | P3 | — |
| §26.9 Unpaywall adapter | OA availability | Planned | — | Not implemented | P3 | — |
| §26.10 GROBID adapter | PDF structured extraction | Planned | — | Not implemented | P2 | Doc intake |
| §27 Evidence bridge | Adapter → Evidence conversion | Implemented | `adapters/bridge.py` | Mock = VENDOR_CLAIM, never FACT_FROM_SOURCE | — | Done |
| §28–30 Freshness/staleness | Source freshness tracking | Implemented | `freshness.py` (FreshnessPolicy, 6 statuses) | No automatic refresh | — | Done |

## Wave 5 — Operational Pipelines (§38–67)

| Spec area | Required capability | Status | Evidence | Missing | Priority | Sprint |
|-----------|-------------------|--------|----------|---------|----------|--------|
| §38 Pipeline base | PipelineRun lifecycle | Implemented | `pipelines/base.py` | — | — | Done |
| §39 Manuscript × Venue pipeline | 18-step pipeline | Implemented | `pipelines/manuscript_venue_fit.py` | — | — | Done |
| §40 Venue deep profile pipeline | Deep venue profiling | Planned | — | Not implemented | P2 | Venue profile |
| §41 Venue pool discovery pipeline | Multi-venue scan | Planned | — | Not implemented | P3 | — |
| §42 Reverse design pipeline | Field → article variants | Planned | — | Not implemented | P3 | — |
| §43 Submission pack pipeline | Pack generation | Planned | — | Not implemented | P2 | Report quality |
| §44 Review/rebuttal pipeline | Post-review learning | Planned | — | Not implemented | P3 | Review loop |
| §45 Q3/conference fallback | Fallback venue selection | Planned | — | Not implemented | P3 | — |
| §46–67 Pipeline details | Step-level specs | Partial | 18 steps implemented for main pipeline | Other pipelines not started | P2 | — |

## Wave 6 — Agent Roles & Prompt Families (§68–93)

| Spec area | Required capability | Status | Evidence | Missing | Priority | Sprint |
|-----------|-------------------|--------|----------|---------|----------|--------|
| §68–93 Agent/prompt layer | LLM agent roles, prompt templates, orchestration | Deferred | All services are deterministic (no LLM) | No agent roles, no prompt families, no orchestration | P3 | LLM layer |

## Wave 7 — UI/UX (§94–115)

| Spec area | Required capability | Status | Evidence | Missing | Priority | Sprint |
|-----------|-------------------|--------|----------|---------|----------|--------|
| §94–115 UI surfaces | Telegram, Web, evidence panels, human decisions | Deferred | CLI only | No Telegram, no Web UI | P3 | Much later |

## Wave 8 — Evaluation & Quality Gates (§116–130)

| Spec area | Required capability | Status | Evidence | Missing | Priority | Sprint |
|-----------|-------------------|--------|----------|---------|----------|--------|
| §116 Quality gates | Fit gate, submission gate | Implemented | `quality.py` (fit_quality_gate, submission_quality_gate) | — | — | Done |
| §117 Evidence audit | Evidence coverage check | Implemented | `services/evidence_audit.py` | — | — | Done |
| §118–130 Evaluation details | Anti-hallucination, logging, audit | Partial | Operation traces, quality gates exist | No anti-hallucination controls (no LLM yet), no formal audit protocol | P3 | LLM layer |

## Wave 9 — Security, Legal, Privacy (§131–140)

| Spec area | Required capability | Status | Evidence | Missing | Priority | Sprint |
|-----------|-------------------|--------|----------|---------|----------|--------|
| §131–140 Security/privacy | Data handling, API key safety, privacy controls | Partial | No API keys stored, no network calls, `.env` in .gitignore | No formal security review, no privacy controls for VenueMemory | P3 | — |

## Wave 10 — MVP Roadmap & Implementation Slicing (§141–148)

| Spec area | Required capability | Status | Evidence | Missing | Priority | Sprint |
|-----------|-------------------|--------|----------|---------|----------|--------|
| §141–142 Implementation principles | Domain first, evidence before recommendation | Implemented | Architecture follows these principles | — | — | Done |
| §143 Repository placement | Separate repo (spec said Litops, ADR-01 overrides) | Implemented | Own repo at `Kairoskopion/` | — | — | Done |
| §144 Module structure | Organized by concern | Implemented | `schema`, `services/`, `adapters/`, `pipelines/`, `cards`, `artifacts`, `cli` | Namespace differs from spec (`kairoskopion` not `litops/journal_yuga`) — intentional | — | Done |
| §145 Persistence | JSONL registries | Implemented | `registry.py`, `persistence.py` | — | — | Done |
| §146 ID strategy | Prefixed IDs | Implemented | `ids.py` (19 prefixes: `art_`, `ven_`, `fit_`, etc.) | Prefixes differ from spec (`art_` not `jy-art-`) — intentional | — | Done |
| §147 MVP-0 Domain skeleton | All required schemas | Implemented | 18+ dataclasses, 23 enums, JSONL registries, tests | — | — | Done |
| §148 MVP-1 One manuscript × one venue | Full pipeline path | Implemented | `pipelines/manuscript_venue_fit.py`, `cli.py` (run-fixture, run-local) | — | — | Done |

---

## Coverage summary

| Status | Count | % of spec areas |
|--------|-------|-----------------|
| Implemented | 38 | 57% |
| Partial | 10 | 15% |
| Stub | 2 | 3% |
| Planned | 12 | 18% |
| Deferred | 3 | 4% |
| Rejected | 0 | 0% |
| **Total tracked** | **67** | — |

### What is solid

- Core formula pipeline (18 steps, 556 tests)
- Evidence status taxonomy (11 statuses)
- Multi-axis fit (12 axes, no single score)
- Risk report (18 risk types)
- SubmissionPack with readiness assessment
- PDF/DOCX extraction (pypdf, python-docx)
- Real adapters with HTTP caching and rate limiting
- Multi-source venue profiling
- Bibliography multi-style parsing
- Publication trajectory reports
- Litops-compatible JSONL export bridge
- WhiteCrow patch queue bridge
- JSONL persistence (17+ registries)
- Vault markdown cards with cross-links, indexes, manifest
- Export/import bundles, freshness tracking, quality gates
- CLI (14 commands)

### What is honestly missing

- **No LLM-assisted extraction**: P3, explicitly deferred
- **No UI beyond CLI**: P3, explicitly deferred
- **No ReviewLoop** entities (ReviewOutcome, RevisionPlan, VenueMemory): P3
- **No JournalModel/SectionModel/IssueModel** sub-entities: P2
- **No live Litops/WhiteCrow API** — export bridges only: P3
- **No OCR** for scanned PDFs: P3
- **No fuzzy title matching** for reference linking (DOI only): P2
