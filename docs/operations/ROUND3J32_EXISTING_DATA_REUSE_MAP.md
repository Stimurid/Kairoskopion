# Round III-J3.2 — Existing Data Reuse Map

> **Date:** 2026-06-24
> **Branch:** `main` @ `905ec60`
> **Scope:** Data inventory. No code changes.

---

## 1. Data Locations Summary

| Location | Purpose | Format | Size |
|----------|---------|--------|------|
| `data/disciplinary_landscape/seeds/` | Discipline definitions | JSONL | 43 entries |
| `data/rubrics/` | Academic writing rubric | JSON | 1 file |
| `benchmarks/_operator_notes/mavrinsky_venue_research/seed_corpus/` | Venue seed corpus | JSONL | 17 venues, ~300 claims, ~100 sources |
| `private_inputs/logos_trial/` | Logos evidence pack | MD + JSON | 10 sources + scenario |
| `.kairoskopion/registries/` | Main app registries | JSONL | 15 registry files |
| `.kairoskopion_logos_trial_evidence/` | Logos trial environment | JSONL | 17 registry files |
| `.kairoskopion_validation_matrix/` | Validation test matrix | JSONL | 4 scenario subdirs |
| `tests/fixtures/uc1_demo_pack/corpus/` | Demo article corpora | JSON | 3 × 38 articles |
| `tests/fixtures/` | Test fixtures | MD + JSON | Various |

---

## 2. Discipline Data

### International Disciplines (`data/disciplinary_landscape/seeds/international_seed.jsonl`)

- **Entries:** 28
- **Freshness:** 2026-06-17
- **Provenance:** LLM draft (pretraining + schema v1.0.0)
- **Content per entry:** paradigm, epistemic regime, canonical questions, key authors, institutional forms, ontologies
- **Entry size:** 1500-3000 words each
- **Covers:** philosophy of technology, AI ethics, epistemology, cognitive science, pedagogy, STS, anthropology, etc.
- **Usable now?** YES

### Russian Disciplines (`data/disciplinary_landscape/seeds/ru_seed.jsonl`)

- **Entries:** 15
- **Freshness:** 2026-06-17
- **Provenance:** LLM draft (pretraining + schema v1.0.0)
- **Covers:** Russian philosophy of technology, activity theory, pedagogical psychology, SMD methodology, Elkonin-Davydov learning theory, etc.
- **Usable now?** YES

### Schema: `data/disciplinary_landscape/schema/discipline_model.schema.json`

- Canonical JSON schema for DisciplineModel
- Synced by hand to Python dataclass
- Spec reference

---

## 3. Venue Seed Corpus

### Main Corpus (`benchmarks/_operator_notes/mavrinsky_venue_research/seed_corpus/`)

| File | Entries | Content |
|------|---------|---------|
| `venues.jsonl` | 17 | Russian philosophical journals with ISSN, publisher, official URLs |
| `claims.jsonl` | ~200+ | Venue scope, article types, submission requirements, peer review policy |
| `sources.jsonl` | ~100+ | Evidence sources (URLs, publication dates) |

**Freshness:** 2026-06-14
**Provenance:** Operator-curated (Mavrinsky venue research)

**Venues in seed corpus include:**
- Логос / Logos (HSE / Anashvili)
- Stasis (EUSP)
- Sociological Review (Russia)
- Studia Culturae
- Chelovek (Institute of Philosophy RAS)
- Historiko-philosophical Yearbook
- 11+ additional Russian venues

### DOAJ Discovery (`/.kairoskopion/registries/venue_profile_packages.jsonl`)

- **Entries:** 167
- **Freshness:** 2026-06-14
- **Provenance:** DOAJ discovery clusters (philosophy of technology, STS, continental philosophy)
- **Content:** Venue identity (names, ISSNs), discovery metadata
- **Missing:** Corpus hulls, formal submission profiles (deferred)
- **Usable now?** PARTIAL — identity yes, full profiles no

---

## 4. Target Venue Assessment

### Логос (Logos)

| Field | Status | Source |
|-------|--------|--------|
| Found? | **YES** | Seed corpus + trial environment |
| Canonical name | Логос / Logos | venues.jsonl |
| ISSN | 0869-5377 (print), 2499-9628 (eISSN) | venues.jsonl |
| Publisher | HSE / Anashvili | venues.jsonl |
| Official URL | https://logosjournal.ru/ | venues.jsonl |
| Aims/scope | YES (comprehensive) | `private_inputs/logos_trial/venue_guidelines_logos_evidence_pack.md` |
| Article types | Research articles, book reviews, polemical contributions, thematic blocks | Evidence pack |
| Submission requirements | Abstract 200-250 words, keywords, metadata RU+EN, author affiliation | Evidence pack |
| Peer review | Single-blind, 2-4 months, 5-stage criteria | Evidence pack |
| Language policy | Russian-language journal | Evidence pack (inferred) |
| Indexing | Web of Science ESCI, Scopus (since 2016), EBSCO, eLibrary/RSCI | Evidence pack |
| APC | No fee | Evidence pack |
| VAK specialties | Listed | Evidence pack |
| **Usable for VenueModel?** | **YES — production-ready** | |
| Fields missing | Recent issue article lists (partial), editorial board turnover | |
| Source evidence quality | FACT_FROM_OFFICIAL_SOURCE (logosjournal.ru) + INFERENCE | |

**10 evidence source files in `private_inputs/logos_trial/`:**
- Logos_official_home, about_page, publication_requirements, peer_review, publication_ethics, editorial_board, indexing_metrics, recent_issues, Wikipedia, language_policy_inference

### Вопросы философии (Voprosy Filosofii)

| Field | Status |
|-------|--------|
| Found? | **NO** |
| In seed corpus? | NO |
| In registries? | NO |
| In evidence packs? | NO |
| In test fixtures? | Referenced in test code but no data |
| In operator seeds? | Referenced in `venue_operator_seed.py` (fixture) |
| **Usable for VenueModel?** | **NO — requires enrichment** |

**To add Вопросы философии would require:**
- Web source acquisition (vphil.ru / RAS website)
- ISSN verification (0042-8744)
- Evidence pack assembly matching Logos pattern
- No mass scraping needed — single targeted venue

---

## 5. Pipeline Registry State

### Main Registry (`.kairoskopion/registries/`)

| Registry | Entries | Size | Date |
|----------|---------|------|------|
| venue_profile_packages.jsonl | 167 | 253 KB | 2026-06-14 |
| venue_models.jsonl | 1 | 2.4 KB | 2026-06-09 |
| publication_regimes.jsonl | 1 | 424 B | 2026-06-09 |
| article_models.jsonl | 1 | 2.1 KB | 2026-06-09 |
| manuscripts.jsonl | 1 | — | 2026-06-09 |
| fit_assessments.jsonl | 1 | — | 2026-06-09 |
| rewrite_plans.jsonl | 1 | — | 2026-06-09 |
| risk_reports.jsonl | 1 | — | 2026-06-09 |
| mismatch_maps.jsonl | 1 | — | 2026-06-09 |
| bibliography_profiles.jsonl | 1 | — | 2026-06-09 |
| citation_ecology_reports.jsonl | 1 | — | 2026-06-09 |
| compliance_checklists.jsonl | 1 | — | 2026-06-09 |
| quality_gates.jsonl | 2 | — | 2026-06-09 |
| operation_traces.jsonl | 1 | — | 2026-06-09 |
| pipeline_runs.jsonl | 1 | — | 2026-06-09 |

### Logos Trial Registry (`.kairoskopion_logos_trial_evidence/`)

- Full pipeline registry set (17 files)
- Dedicated Logos trial environment
- Date: 2026-06-10
- Contains complete working example of full pipeline on real journal

### Validation Matrix (`.kairoskopion_validation_matrix/`)

- 4 scenario subdirs: good_fit, language_block, method_block, scope_block
- Test matrix for validation scenarios
- Usable for regression testing

---

## 6. Demo Corpora

| Corpus | Location | Articles | Content |
|--------|----------|----------|---------|
| Philosophy & Technology | `tests/fixtures/uc1_demo_pack/corpus/philosophy_and_technology_corpus.json` | 38 | Simondon, AI ethics, epistemic injustice |
| Social Studies of Science | `tests/fixtures/uc1_demo_pack/corpus/social_studies_of_science_corpus.json` | 38 | STS-oriented research |
| Techne | `tests/fixtures/uc1_demo_pack/corpus/techne_corpus.json` | 38 | Technology philosophy |

Each entry: article_id, title, authors, year, venue, keywords, word_count, methodology, citation_count_synthetic, abstract_snippet. Synthetic but realistic.

---

## 7. Academic Writing Rubric

`data/rubrics/russian_philosophy_academic_writing_rubric_v0_1.json`
- Source: HSE Practical Philosophy course-paper guidelines (PDF → JSON)
- 8 rubric categories: AI use policy, research purpose, literature work, structure, goal/tasks/thesis, philosophical problem, argument and style, references
- Usable for Russian philosophical manuscript readiness scoring
- NOT connected to runtime pipeline

---

## 8. Critical Gaps

| Missing | Impact | Effort to Fill |
|---------|--------|----------------|
| Вопросы философии venue data | HIGH — benchmark venue has no data | Single targeted enrichment |
| Issue-level metadata for journals | MEDIUM — VPKGs lack recent issue/article lists | Per-venue acquisition |
| Formal submission profiles for 167 DOAJ VPKGs | HIGH — only Logos has full profile | Bulk acquisition (out of scope) |
| Adapter integration in API case flow | MEDIUM — adapters work in CLI but not wired to API | Code wiring |
| Writing rubric → pipeline integration | LOW — standalone data | Service adapter |

---

## 9. Reuse Summary

| Dataset | Can Be Reused Now? | For What? |
|---------|-------------------|-----------|
| 43 discipline seeds | YES | Venue-discipline mapping, field positioner input |
| Logos evidence pack | YES | Full VenueModel construction for Logos |
| 17-venue seed corpus | YES | Bootstrap venue discovery for Russian philosophy |
| 167 DOAJ VPKGs | PARTIAL | Identity resolution; not full profiles |
| 3 demo corpora | YES | Testing, corpus hull development |
| Writing rubric | YES | Manuscript readiness pre-check |
| Logos trial registries | YES | Reference implementation |
