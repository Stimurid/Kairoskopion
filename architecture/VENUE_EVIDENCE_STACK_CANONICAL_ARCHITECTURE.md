# Venue Evidence Stack — Canonical Architecture v1

**Date:** 2026-06-12
**Status:** Design document for implementation planning
**Input:** Venue Evidence Stack Brief v1, existing codebase audit, Litops storage pattern
**Scope:** How VenueModel is built layer by layer from 29 source categories

---

## 1. Core Principle

> Agents cannot follow one route "through journals."
> VenueModel is assembled from an evidence stack, not extracted from a single source.

The system builds venue knowledge progressively through 8 depth levels.
Each field of VenueModel carries its own `evidence_status`, `source_ref`, `confidence`, and `staleness`.
No field is "just a string" — it is a claim with provenance.

---

## 2. What Exists vs What This Document Adds

### Already implemented (code exists, tests pass)

| Component | Location | State |
|-----------|----------|-------|
| VenueModel (30 fields) | `schema.py:223-256` | Guidelines extraction + enrichment claims |
| VenueRecord/Source/Claim/EvidencePack | `schema.py`, `enums.py` | Full data model with conflict resolution |
| 11 evidence statuses | `enums.py` | FACT_FROM_SOURCE through CONFLICTING_EVIDENCE |
| Venue registry (seed import, evidence pack) | `services/venue_registry.py` | JSONL corpus, claim resolution, staleness |
| 3 adapters (OpenAlex, Crossref, OpenCitations) | `adapters/` | Mock + real mode, bridge to EvidenceItem |
| Adapter base contract | `adapters/base.py` | AdapterResult, AdapterRecord, AdapterConfig |
| Adapter→Evidence bridge | `adapters/bridge.py` | Never FACT_FROM_SOURCE from adapter |
| Source intake (local files) | `adapters/source_intake.py` | 14 source roles, hash, extraction |
| Litops export bridge | `litops_bridge.py` | Source/Artifact JSONL export |
| 5 venue agents | `agents/venue/` | 2 real (discovery, profiler), 3 stubs |
| venue_profiling service | `services/venue_profiling.py` | Regex/heuristic guideline parsing |
| venue_profile_builder service | `services/venue_profile_builder.py` | Multi-source merge, conflict flagging |
| Conflict resolution rules | `VENUE_REGISTRY_ARCHITECTURE.md` | 6 resolution rules documented |
| 7 generalized fit invariants | `GENERALIZED_VENUE_FIT_INVARIANTS.md` | Product-level correctness rules |

### What this document adds (new or substantially refined)

| Addition | Status | What changes |
|----------|--------|--------------|
| **8-level depth model** | NEW | Agents get explicit depth routing, not flat "get venue info" |
| **Evidence status expansion** (11→23) | REFINED | 12 new statuses for corpus/editorial/policy/community sources |
| **External artifact storage** | NEW | PDF/HTML/MD artifacts on Yandex Disk, not VPS; index stays local |
| **Corpus Profiler pipeline** | NEW | L3: genre moves, method expectations, citation expectations from articles |
| **Editorial Board Analyzer** | NEW | L4: disciplinary center of gravity from board composition |
| **Community/CFP layer** | NEW | L4: PhilPapers, PhilEvents, H-Net, association sites |
| **VenueModel field→source mapping** | NEW | Every field knows which level populates it and at what evidence status |
| **Adapter priority tiers** | REFINED | Core/Soon/Later with explicit degradation rules |
| **Storage architecture** | NEW | Litops-pattern: metadata local (JSONL), content remote (Yandex Disk/S3) |
| **CorpusAnalyzer agent** | NEW | Reads OpenAlex works + full text → PublishedArticlePattern |
| **VenueSnapshotCrawler** | NEW | Real HTTP fetch → HTML/PDF → SourceSnapshot (replaces url_snapshot.py stub) |
| **Freshness orchestrator** | NEW | Decides which levels need refresh based on staleness policies |

### What the brief says that was already in the architecture (confirmation, not change)

- `ArticleModel × VenueModel × SubmissionScenario → FitAssessment` formula — already in spec §2
- Evidence-first principle — already ADR-03
- Closed paid source must not block MVP — already ADR-06
- Publisher finders as VENDOR_CLAIM — already noted in quality review
- Sci-Hub excluded — already in spec
- Google Scholar not core — already implied by "no fragile scraping"
- VenueEvidencePack with conflict detection — already implemented
- Mock adapters as stable contracts — already ADR-13

---

## 3. Canonical VenueModel Field→Source Map

Each field has a **primary source level**, **evidence status**, and **fallback**.

### Identity fields (L0)

| Field | Primary source | Evidence status | Fallback |
|-------|---------------|-----------------|----------|
| `canonical_name` | OpenAlex / Crossref / official site | FACT_FROM_API_METADATA | User input |
| `venue_type` | Official site / OpenAlex | FACT_FROM_SOURCE | INFERENCE from corpus |
| `ISSN / eISSN` | Crossref / OpenAlex / DOAJ | FACT_FROM_API_METADATA | Official site |
| `publisher_or_owner` | Crossref member / OpenAlex | FACT_FROM_API_METADATA | Official site |
| `official_urls` | Official site | FACT_FROM_SOURCE | OpenAlex homepage |
| `aliases` | OpenAlex / ISSN Portal | FACT_FROM_API_METADATA | Manual |

### Formal requirements (L1)

| Field | Primary source | Evidence status | Fallback |
|-------|---------------|-----------------|----------|
| `scope_summary` | Official aims/scope page | FACT_FROM_SOURCE | OpenAlex topics |
| `article_types_supported` | Author guidelines | FACT_FROM_SOURCE | CORPUS_OBSERVATION |
| `language_policy` | Author guidelines | FACT_FROM_SOURCE | CORPUS_OBSERVATION |
| `word_limits` | Author guidelines | FACT_FROM_SOURCE | UNKNOWN |
| `reference_style` | Author guidelines | FACT_FROM_SOURCE | CORPUS_OBSERVATION |
| `submission_system` | Submission page | FACT_FROM_SOURCE | UNKNOWN |
| `ethics_policy` | Policy page | FACT_FROM_SOURCE | UNKNOWN |
| `ai_policy` | Policy page | FACT_FROM_SOURCE | UNKNOWN |
| `data_policy` | Policy page | FACT_FROM_SOURCE | UNKNOWN |
| `anonymization_policy` | Author guidelines | FACT_FROM_SOURCE | VENDOR_CLAIM |

### Publication model (L1 + L2)

| Field | Primary source | Evidence status | Fallback |
|-------|---------------|-----------------|----------|
| `review_process_claims` | Official site | VENDOR_CLAIM | OpenReview traces |
| `apc_policy` | Official site / DOAJ | FACT_FROM_SOURCE | VENDOR_CLAIM |
| `open_access_status` | DOAJ / Unpaywall / official | FACT_FROM_API_METADATA | VENDOR_CLAIM |
| `indexing_claims` | Official site | VENDOR_CLAIM | Scopus/WoS snapshot |
| `metrics_claims` | Official site | VENDOR_CLAIM | JCR/Scimago snapshot |
| `publication_regime` | Classifier agent | INFERENCE | L3 corpus evidence |

### Corpus-derived fields (L3) — NEW

| Field | Primary source | Evidence status | Fallback |
|-------|---------------|-----------------|----------|
| `genre_move_distribution` | Recent article corpus | CORPUS_OBSERVATION | UNKNOWN |
| `method_expectation_profile` | Recent article corpus | CORPUS_OBSERVATION | UNKNOWN |
| `empirical_conceptual_balance` | Recent article corpus | CORPUS_OBSERVATION | INFERENCE |
| `citation_density_norm` | OpenCitations + corpus | CORPUS_OBSERVATION | UNKNOWN |
| `theoretical_shoulders` | Citation ecology | CORPUS_OBSERVATION | UNKNOWN |
| `accepted_novelty_modes` | Corpus patterns | INFERENCE | UNKNOWN |
| `local_canon` | Most-cited in venue | CORPUS_OBSERVATION | UNKNOWN |
| `debate_streams` | Special issues + corpus | CORPUS_OBSERVATION | UNKNOWN |

### Editorial intelligence (L4) — NEW

| Field | Primary source | Evidence status | Fallback |
|-------|---------------|-----------------|----------|
| `editorial_board_profile` | Board page + OpenAlex authors | EDITORIAL_BOARD_INFERENCE | UNKNOWN |
| `disciplinary_center_of_gravity` | Board + corpus | EDITORIAL_BOARD_INFERENCE | CORPUS_OBSERVATION |
| `regional_institutional_ecology` | Board affiliations | EDITORIAL_BOARD_INFERENCE | UNKNOWN |
| `community_venue_signals` | PhilPapers/H-Net/associations | SCENE_FIT_INFERENCE | UNKNOWN |
| `special_issue_history` | Official site + CFP sources | FACT_FROM_SOURCE | UNKNOWN |

### User/memory fields (L7)

| Field | Primary source | Evidence status | Fallback |
|-------|---------------|-----------------|----------|
| `prior_outcomes` | User input | PRIOR_OUTCOME | none |
| `tacit_signals` | User notes | TACIT_SIGNAL | none |
| `reviewer_objection_memory` | OpenReview / user | PUBLIC_REVIEW_CORPUS | PRIOR_OUTCOME |

---

## 4. Storage Architecture

### The problem

VPS has limited disk. Article PDFs, HTML snapshots, venue guideline files, and
Markdown venue cards accumulate fast (50 venues × 20 articles × 500KB = 500MB;
1000 venues = 10GB). This cannot live on the application server.

### The pattern (from Litops)

Litops already separates **index** (local JSONL registries) from **content**
(Yandex Disk vault). Kairoskopion must follow the same pattern:

```
┌─────────────────────────────────────────────────────┐
│  VPS (application server)                           │
│                                                     │
│  .kairoskopion/registries/     ← metadata index     │
│    source_snapshots.jsonl      (IDs, hashes, refs)  │
│    evidence_items.jsonl                              │
│    venue_records.jsonl                               │
│    venue_claims.jsonl                                │
│    article_models.jsonl                              │
│                                                     │
│  .kairoskopion/cache/          ← ephemeral          │
│    api_responses/              (HTTP cache, TTL)    │
│    extraction_temp/            (GROBID output)      │
│                                                     │
└──────────────┬──────────────────────────────────────┘
               │ reference by content_hash + path
               ▼
┌─────────────────────────────────────────────────────┐
│  Yandex Disk / S3-compatible (content vault)        │
│                                                     │
│  kairoskopion-vault/                                │
│    articles/                                        │
│      {content_hash[:8]}/{content_hash}.pdf          │
│      {content_hash[:8]}/{content_hash}.md           │
│    venue-snapshots/                                 │
│      {venue_record_id}/                             │
│        homepage_{date}.html                         │
│        guidelines_{date}.md                         │
│        board_{date}.json                            │
│        corpus_sample_{date}.jsonl                   │
│    venue-cards/                                     │
│      {venue_record_id}_card.md                      │
│    litops-export/                                   │
│      sources.jsonl                                  │
│      artifacts.jsonl                                │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Storage contract

```python
@dataclass
class VaultRef:
    """Reference to content in external vault."""
    vault_path: str          # relative path inside vault root
    content_hash: str        # SHA256[:16] for integrity check
    content_type: str        # MIME type
    size_bytes: int | None
    uploaded_at: str | None  # ISO timestamp
    vault_backend: str       # "yandex_disk" | "s3" | "local_fs"

class VaultBackend(ABC):
    """Abstract vault interface — same API for local dev and production."""
    def upload(self, local_path: Path, vault_path: str) -> VaultRef: ...
    def download(self, vault_path: str, local_path: Path) -> Path: ...
    def exists(self, vault_path: str) -> bool: ...
    def list_dir(self, vault_prefix: str) -> list[str]: ...

class LocalFsVault(VaultBackend): ...      # dev: just a local directory
class YandexDiskVault(VaultBackend): ...   # prod: yadisk API
class S3Vault(VaultBackend): ...           # future: any S3-compatible
```

### What goes where

| Content type | Storage | Why |
|-------------|---------|-----|
| JSONL registries (metadata) | VPS local | Fast read, small, append-only |
| API response cache | VPS local (ephemeral) | TTL-based, disposable |
| Article PDFs | Vault (Yandex Disk) | Large, archival, shared with Litops |
| HTML page snapshots | Vault (Yandex Disk) | Large, versioned by date |
| Venue MD cards | Vault (Yandex Disk) | Human-readable, shared |
| Corpus sample JSONL | Vault (Yandex Disk) | Large, versioned |
| Editorial board JSON | Vault (Yandex Disk) | Versioned snapshots |
| GROBID extraction output | VPS cache → Vault | Temp during processing, archive result |
| User-uploaded manuscripts | Vault (Yandex Disk) | User content, must persist |

### Configuration

```env
# Storage backends
KAIRON_VAULT_BACKEND=local_fs          # local_fs | yandex_disk | s3
KAIRON_VAULT_LOCAL_PATH=./vault        # for local_fs backend
KAIRON_VAULT_YADISK_TOKEN=             # for yandex_disk backend
KAIRON_VAULT_YADISK_ROOT=kairoskopion-vault
KAIRON_VAULT_S3_BUCKET=               # for s3 backend
KAIRON_VAULT_S3_PREFIX=kairoskopion-vault
```

### Interaction with Litops

Litops already uses Yandex Disk for its vault. If both Litops and Kairoskopion
use the same Yandex Disk account:

- Litops vault: `litops-vault/`
- Kairoskopion vault: `kairoskopion-vault/`
- Shared: articles that both systems reference get stored once, cross-linked by `content_hash`

The `litops_bridge.py` export already produces `sources.jsonl` and `artifacts.jsonl`.
With vault integration, these exports would include `vault_ref` fields pointing to
the same physical files.

---

## 5. Agent Architecture for Evidence Stack

### Current agents (venue layer)

| Agent | What it does now | What it should do |
|-------|-----------------|-------------------|
| `venue_identifier` | Returns stub "needs_sources" | L0: resolve via OpenAlex + Crossref + DOAJ |
| `venue_profiler` | Parses local guidelines text | L1: official snapshot extraction |
| `venue_discovery` | Matches against seed corpus | L0+L2: OpenAlex source search + seed corpus |
| `publication_regime_classifier` | Extracts fields from VenueModel | L2+L3: classify from guidelines + corpus evidence |
| `venue_publication_profile_builder` | Partial profile from evidence pack | L3+L4: full profile from corpus + board + community |

### New agents needed

| Agent | Level | Input | Output | Priority |
|-------|-------|-------|--------|----------|
| `venue_snapshot_crawler` | L1 | URL list | SourceSnapshot[] with vault refs | Core |
| `corpus_sampler` | L3 | venue ISSN/ID | OpenAlex works sample → vault | Core |
| `corpus_analyzer` | L3 | PublishedArticleCorpus | GenreMoveProfile, MethodExpectation, CitationExpectation | Core |
| `editorial_board_analyzer` | L4 | Board page snapshot | EditorialBoardProfile with disciplinary inference | Soon |
| `community_signal_collector` | L4 | Venue identity | PhilPapers/PhilEvents/H-Net signals | Soon (humanities) |
| `freshness_orchestrator` | Control | VenueEvidencePack | Refresh plan (which levels are stale) | Soon |

### Agent depth routing

The key architectural insight: agents don't all run for every venue.
Depth is progressive and demand-driven:

```
User says "check Nature Human Behaviour"
  → L0: Identity Resolver (OpenAlex + Crossref) → VenueRecord
  → L1: Snapshot Crawler (homepage, guidelines) → SourceSnapshots
  → L2: API Enrichment (OpenAlex works count, DOAJ, Unpaywall) → MetadataProfile
  → STOP here for "quick look"

User says "how well does my article fit?"
  → L3: Corpus Sampler (50 recent articles via OpenAlex) → PublishedArticleCorpus
  → L3: Corpus Analyzer → GenreMoveProfile, MethodExpectation
  → L4: Editorial Board Analyzer → EditorialBoardProfile
  → FitAssessment now has corpus-level evidence

User says "prepare submission"
  → L6: Compliance check (fresh guidelines, Sherpa, Unpaywall)
  → L7: Check prior outcomes, tacit signals
  → SubmissionPack with full evidence trail
```

This is controlled by a **VenueDepthPolicy**:

```python
@dataclass
class VenueDepthPolicy:
    """How deep to build VenueModel for a given use case."""
    target_depth: int          # 0-7
    required_levels: list[int] # must complete
    optional_levels: list[int] # run if time/budget allows
    max_api_calls: int         # budget limit
    max_articles_to_sample: int
    freshness_threshold_days: int

DEPTH_QUICK_LOOK = VenueDepthPolicy(target_depth=2, ...)
DEPTH_FIT_ASSESSMENT = VenueDepthPolicy(target_depth=4, ...)
DEPTH_SUBMISSION_READY = VenueDepthPolicy(target_depth=7, ...)
```

---

## 6. Evidence Status Expansion

### Current (11 statuses in `enums.py`)

```
FACT_FROM_SOURCE, VENDOR_CLAIM, CORPUS_OBSERVATION, INFERENCE,
TACIT_SIGNAL, USER_NOTE, PRIOR_OUTCOME, UNKNOWN, INACCESSIBLE,
STALE, CONFLICTING_EVIDENCE
```

### Proposed additions (12 new)

| New status | Meaning | Source |
|-----------|---------|--------|
| `FACT_FROM_API_METADATA` | Structured data from open API | OpenAlex, Crossref, DOAJ |
| `INFERENCE_WITH_EVIDENCE` | RAG/QA answer backed by passages | PaperQA2 |
| `SCENE_FIT_INFERENCE` | Community/scene match, not core fit | PhilPapers, associations |
| `EDITORIAL_BOARD_INFERENCE` | Derived from board composition | Board analysis |
| `USER_LIBRARY_FACT` | From user's citation manager | Zotero/Mendeley |
| `EXTERNAL_SUGGESTER_RESULT` | From publisher finder / Trinka | Publisher tools |
| `EXTERNAL_COMPLIANCE_REPORT` | From plagiarism/similarity checker | iThenticate etc. |
| `SECONDARY_SIGNAL` | Fragile/scraping source | Google Scholar |
| `PUBLIC_REVIEW_CORPUS` | From OpenReview public traces | OpenReview |
| `POLICY_SOURCE` | From Sherpa/DOAJ policy records | Sherpa |
| `OFFICIAL_SERIAL_METADATA` | From ISSN Portal | ISSN |
| `PAID_INDEX_METADATA` | From Scopus/WoS/JCR (user-provided) | User snapshots |

### Implementation approach

Don't change the enum in one shot. Add statuses as adapters are implemented.
The existing 11 cover everything needed for L0-L2 with current adapters.
New statuses arrive with their adapter in the same sprint.

---

## 7. Adapter Implementation Priority

### Tier 1 — Core (Sprints 1-2)

| Adapter | API | Auth | Rate limit | What it gives |
|---------|-----|------|-----------|---------------|
| OpenAlex (upgrade from mock) | REST, free | Polite email header | 10 req/s | Sources, works, authors, topics |
| Crossref (upgrade from mock) | REST, free | Polite email header | 50 req/s | DOI, journals, members, licenses |
| OpenCitations (upgrade from mock) | REST, free, CC0 | None | Moderate | Citations, references, counts |
| VenueSnapshotCrawler | HTTP | None | Self-limited | HTML → SourceSnapshot → vault |
| GROBID integration | Local/Docker | None | N/A | PDF → structured document |

### Tier 2 — Soon (Sprints 3-4)

| Adapter | API | Auth | What it gives |
|---------|-----|------|---------------|
| DOAJ | REST, free | None | OA journal validation, predatory signal |
| Unpaywall | REST, free | Email | OA status, legal full-text locations |
| Semantic Scholar | REST, free | API key (free) | Embeddings, recommendations, citation context |
| Sherpa/Open Policy Finder | REST | API key | Self-archiving, funder compliance |
| PhilPapers | Web scraping / manual | None | Philosophy categories, journals, CFP |

### Tier 3 — Later (Sprint 5+, paid/optional)

| Adapter | Constraint | Degradation |
|---------|-----------|-------------|
| Scopus/WoS/JCR | Paid API, institutional access | UNKNOWN_NOT_VERIFIED or user snapshot |
| ISSN Portal | Paid | OpenAlex/Crossref ISSN suffices for MVP |
| Dimensions/Lens | Freemium/paid | OPTIONAL_ENRICHMENT |
| DataCite | Free but niche | Only for STEM data papers |

### Degradation rule

Every adapter must implement:
```python
def degrade_gracefully(self) -> AdapterResult:
    """Return result with evidence_status=UNKNOWN when adapter unavailable."""
```

No adapter failure blocks the pipeline. VenueModel gets built with what's available;
missing fields are explicitly `UNKNOWN` with `source_ref=None`.

---

## 8. New Schema Entities

### PublishedArticlePattern (L3 output)

```python
@dataclass
class PublishedArticlePattern(_DictMixin):
    pattern_id: str
    venue_record_id: str
    sample_size: int
    sample_period: str  # "2024-01 to 2026-06"
    genre_distribution: dict[str, float]  # {"empirical": 0.4, "theoretical": 0.3, ...}
    method_distribution: dict[str, float]
    median_word_count: int | None
    median_reference_count: int | None
    citation_density_per_1000_words: float | None
    theoretical_shoulders: list[str]  # most-cited authors/works in venue
    empirical_conceptual_ratio: float | None
    language_distribution: dict[str, float]
    article_type_distribution: dict[str, float]
    abstract_move_patterns: list[str]  # common rhetorical moves
    debate_streams: list[str]  # recurring topics/controversies
    evidence_status: str  # CORPUS_OBSERVATION
    unknowns: list[str]
    confidence: str
    created_at: str
```

### VenueDepthState (freshness tracking)

```python
@dataclass
class VenueDepthState(_DictMixin):
    venue_record_id: str
    level_states: dict[str, LevelState]  # "L0" → LevelState
    last_full_refresh: str | None
    next_refresh_due: str | None

@dataclass
class LevelState(_DictMixin):
    level: str  # "L0", "L1", etc.
    status: str  # "fresh", "stale", "never_run", "partial"
    last_run: str | None
    source_count: int
    claim_count: int
    unknown_count: int
    freshness_expires: str | None
```

### VaultRef (storage reference)

Already described in §4 above.

---

## 9. Implementation Plan

### Sprint V1: Adapter Reality + Vault Foundation (2-3 days)

**Goal:** Make existing adapters real (not mock), add vault storage layer.

Tasks:
1. **VaultBackend ABC + LocalFsVault** — abstract storage interface, local implementation
2. **OpenAlex adapter → real mode** — remove mock default, add proper error handling, pagination
3. **Crossref adapter → real mode** — same
4. **OpenCitations adapter → real mode** — same
5. **VenueSnapshotCrawler** — real HTTP fetch → HTML → text extraction → vault storage
6. **SourceSnapshot gains vault_ref** — schema migration
7. **CLI: `--vault-backend` flag** for all commands
8. **Tests:** adapter integration tests with VCR/cassette pattern (recorded HTTP)
9. **Update venue_identifier agent** — wire to OpenAlex source lookup + Crossref journal lookup

**Deliverable:** `kairon run-agent-workflow uc1_draft_to_venue_pool_positioning --manuscript paper.md`
produces real OpenAlex/Crossref data, stores snapshots in local vault.

**Evidence status used:** FACT_FROM_SOURCE, FACT_FROM_API_METADATA, VENDOR_CLAIM, UNKNOWN.

### Sprint V2: Corpus Profiler (2-3 days)

**Goal:** Build PublishedArticlePattern from real article data.

Tasks:
1. **corpus_sampler agent** — fetch 30-50 recent works via OpenAlex by source ISSN
2. **GROBID integration** — Docker-based PDF → structured document (optional, degrade to metadata-only)
3. **corpus_analyzer agent** — compute distributions from article metadata:
   - genre/method from titles+abstracts (keyword/heuristic, not LLM)
   - citation density from reference counts
   - language distribution
   - article type distribution
   - theoretical shoulders from most-cited references
4. **PublishedArticlePattern schema** — add to schema.py
5. **VenuePublicationProfile enrichment** — feed corpus patterns into existing profile builder
6. **Vault: corpus samples** — store sampled article metadata as JSONL in vault

---

## 9. Source Authority and Access Separation

**Added:** 2026-06-13 (GPT-16 alignment, point 7)

### Architectural rule

> Full-text access is not metadata authority.
> Metadata authority is not publication-pattern authority.
> Official venue claim is not independent verification.
> Corpus evidence is not formal policy.
> User memory is not public fact.

### SourceAccessMode (how we accessed the source)

`metadata_api` | `full_text_pdf` | `full_text_html` | `official_webpage` | `submission_system_page` | `editorial_board_page` | `corpus_sample` | `citation_graph` | `index_registry` | `user_memory` | `review_history` | `manual_note`

### SourceAuthorityScope (what the source can legitimately claim)

`venue_identity` | `issn_identity` | `publisher_identity` | `formal_requirements` | `submission_policy` | `publication_regime` | `indexing_status` | `article_metadata` | `article_full_text` | `citation_relations` | `corpus_pattern` | `editorial_board_signal` | `community_signal` | `author_identity` | `affiliation_identity` | `funding_statement` | `ai_disclosure_policy` | `reporting_guideline` | `prior_outcome` | `tacit_signal`

### Authority rules (examples)

| Access mode | Can support | Cannot support |
|-------------|------------|----------------|
| metadata_api (OpenAlex, Crossref) | venue_identity, ISSN, publisher, article_metadata, citation_relations | corpus_pattern, formal_requirements, editorial taste |
| full_text_pdf/html | article_full_text, corpus_pattern, citation_relations | ISSN, indexing, formal policy, submission policy |
| official_webpage | venue_identity, formal_requirements, submission_policy, AI disclosure | independent indexing verification, corpus pattern |
| corpus_sample | corpus_pattern, citation_relations | submission eligibility, formal policy, indexing |
| user_memory | prior_outcome, tacit_signal | venue identity, public venue fact |
| index_registry | indexing_status, venue_identity, ISSN | corpus pattern, editorial taste |

### Implementation

- Enums: `src/kairoskopion/enums.py` — `SourceAccessMode`, `SourceAuthorityScope`, `AuthorityStrength`
- Models: `src/kairoskopion/source_authority.py` — `SourceAuthorityClaim`, `SourceAuthorityAssessment`, `EvidenceConflict`, `EvidenceReconciliationResult`, `PublicationHistoryModel`, `CitationIntegrityCheck`, `ReportingGuidelineSelection`
- Service: `src/kairoskopion/services/source_authority.py` — authority matrix, claim checking, conflict detection, reconciliation
- Integration: `src/kairoskopion/services/evidence_audit.py` — optional `authority_assessments` and `evidence_conflicts` parameters
- Tests: `tests/test_source_authority.py` — 53 tests covering all models, authority rules, and auditor integration

### Limitations (v0)

- Authority matrix is deterministic; no confidence scoring
- No live retraction/PubPeer integration (models are placeholders)
- PublicationHistoryModel requires user or source input
- FullTextAccess/MetadataAuthority separation is rule-based, not enforced at adapter level yet

**Deliverable:** `kairon venue-deep-profile --venue-issn 1234-5678` builds profile
from real corpus, not just guidelines.

**Evidence status used:** CORPUS_OBSERVATION, INFERENCE.

### Sprint V3: DOAJ + Unpaywall + Sherpa (1-2 days)

**Goal:** Policy/compliance layer becomes real.

Tasks:
1. **DOAJAdapter** — journal lookup by ISSN, OA validation
2. **UnpaywallAdapter** — OA status for articles, legal full-text discovery
3. **SherpaAdapter** — self-archiving permissions, funder compliance
4. **fulltext_access_status field** — LEGAL_OA | USER_PROVIDED | SUBSCRIPTION_REQUIRED | INACCESSIBLE | UNKNOWN
5. **Predatory signal** — DOAJ inclusion as positive signal, absence as UNKNOWN (not verdict)
6. **ComplianceChecklist enrichment** — feed policy data into compliance agent

**Deliverable:** RiskReport and ComplianceChecklist use real policy data.

**Evidence status used:** POLICY_SOURCE, FACT_FROM_API_METADATA.

### Sprint V4: Editorial Board + Community (2-3 days)

**Goal:** L4 intelligence — who runs the journal, what community it serves.

Tasks:
1. **editorial_board_analyzer agent** — parse board page (from L1 snapshot), cross-reference with OpenAlex author profiles
2. **EditorialBoardProfile population** — disciplinary center, institutional ecology, regional distribution
3. **PhilPapers adapter** (scrape/manual) — philosophy journal categories, topic taxonomy
4. **community_signal_collector agent** — PhilPapers + manual CFP sources
5. **CommunityVenueSignal schema** — new entity for scene/community fit
6. **Special issue history extraction** — from official site snapshots

**Deliverable:** FitAssessment can say "this journal's board is centered on X tradition,
your article comes from Y — adaptation cost is Z."

**Evidence status used:** EDITORIAL_BOARD_INFERENCE, SCENE_FIT_INFERENCE.

### Sprint V5: Semantic Scholar + Freshness + YandexDisk Vault (2 days)

**Goal:** Semantic neighborhood + production storage + staleness management.

Tasks:
1. **SemanticScholarAdapter** — paper search, recommendations, SPECTER2 embeddings
2. **Citation bridge enrichment** — S2 recommendations feed into CitationPlan
3. **YandexDiskVault backend** — implement VaultBackend for Yandex Disk API
4. **Freshness orchestrator** — VenueDepthState tracking, refresh planning
5. **CLI: `kairon venue-refresh`** — check staleness, re-run stale levels
6. **VenueDepthPolicy** — quick_look / fit_assessment / submission_ready presets

**Deliverable:** Production deployment stores artifacts on Yandex Disk.
Staleness tracking prevents serving expired venue data.

### Sprint V6: External Suggesters + Review Memory (1-2 days)

**Goal:** L5 weak suggesters + L7 user memory.

Tasks:
1. **PublisherFinderAdapter** — at least one publisher finder (Springer or Elsevier) as candidate generator
2. **JANE/Trinka adapter** (if API available) — abstract-to-journal matching
3. **PriorOutcome schema + CLI** — user records submission results
4. **TacitVenueSignal schema + CLI** — user records informal knowledge
5. **VenueMemory integration** — prior outcomes feed into RiskReport and FitAssessment
6. **OpenReviewAdapter** (for CS/AI venues) — public reviews, decisions

**Deliverable:** System remembers past submissions and uses them in future assessments.

---

## 10. What the Brief Describes More Precisely Than Existing Docs

| Topic | Existing docs say | Brief adds |
|-------|------------------|------------|
| **Source categories** | "OpenAlex, Crossref, manual snapshots" (3-5 named) | 29 specific sources with exact data yields per source |
| **Evidence status per source** | 11 generic statuses | Specific mapping: which source produces which status |
| **Corpus analysis** | "PublishedArticleCorpus schema exists" | Exact reconstruction targets: genre moves, method expectations, theoretical shoulders, debate streams, empirical/conceptual balance |
| **Editorial board** | "EditorialBoardProfile schema exists" | Reconstruction method: cross-reference with OpenAlex, compute disciplinary center of gravity |
| **Publisher finders** | Not mentioned | 4 specific finders analyzed (Springer, T&F, Wiley, Elsevier) with bias assessment |
| **Humanities sources** | PhilPapers mentioned once | PhilPapers + PhilEvents + H-Net + 4S/STHV as mandatory for non-STEM |
| **Degradation paths** | "degrade to UNKNOWN" | Specific degradation chain: OpenAlex → Crossref → DOAJ → publisher → user → UNKNOWN |
| **Full-text access** | Not addressed | Explicit policy: LEGAL_OA → USER_PROVIDED → SUBSCRIPTION_REQUIRED → metadata-only |
| **Storage** | "Litops manages files" | Concrete vault architecture with hash-based paths, Yandex Disk backend |
| **Agent depth routing** | All agents run every time | Progressive depth: L0→L7, demand-driven, budget-aware |
| **Russian sources** | Not mentioned | eLIBRARY/РИНЦ, КиберЛенинка, ВАК as separate adapter tier |

## 11. What Differs From Existing Architecture (Not Just "More Detail")

| Aspect | Existing architecture | Brief's position | Resolution |
|--------|----------------------|------------------|------------|
| **Adapter→Evidence bridge** | All adapter results are VENDOR_CLAIM | Brief proposes FACT_FROM_API_METADATA for OpenAlex/Crossref | **Accept brief**: structured API metadata from authoritative open registries is stronger than vendor claim. Reserve VENDOR_CLAIM for publisher finders and journal self-reports. Update bridge.py. |
| **VenueModel structure** | Flat model, 30 fields | Brief implies sub-entities (EditorialBoardProfile, PublishedArticlePattern, CitationExpectationProfile) as separate objects linked to VenueModel | **Accept brief**: VenueModel stays as identity+formal shell; deep profiles are separate entities in VenueEvidencePack. Already partially this way. |
| **Evidence status count** | 11 statuses, treated as sufficient | Brief proposes 23 | **Partial accept**: add FACT_FROM_API_METADATA now (distinguishes API facts from page facts). Add others as their adapters land. Don't pre-create unused statuses. |
| **Depth routing** | Sequential workflow, all steps run | Brief proposes demand-driven depth with budget | **Accept brief**: add VenueDepthPolicy. Quick look stops at L2; full fit goes to L4; submission prep goes to L7. |
| **Storage** | "Files stay at source" (no vault) | Brief requires explicit vault with hash-based paths | **Accept brief**: implement VaultBackend ABC in Sprint V1. LocalFsVault for dev, YandexDiskVault for prod. |
| **Corpus as primary source** | Corpus schema exists but no population | Brief makes corpus analysis a first-class pipeline step | **Accept brief**: CorpusSampler + CorpusAnalyzer agents in Sprint V2. This is the biggest functional gap. |

---

## 12. Decision Record

**ADR-15: Venue Evidence Stack Depth Model**

- Context: VenueModel quality depends on source diversity. Current implementation
  only uses L0-L1 (identity + guidelines). Brief demonstrates 8 levels of evidence.
- Decision: Adopt 8-level depth model. Agents are assigned to levels. Depth is
  demand-driven via VenueDepthPolicy. Each level produces typed evidence with
  explicit status.
- Consequences: More adapter code, but clearer provenance. FitAssessment accuracy
  improves proportionally to depth achieved.

**ADR-16: External Content Vault**

- Context: Article PDFs, HTML snapshots, and venue cards cannot live on VPS.
  Litops already uses Yandex Disk for source vault.
- Decision: Implement VaultBackend ABC with LocalFsVault (dev) and
  YandexDiskVault (prod). Content referenced by hash. Metadata stays in
  local JSONL registries.
- Consequences: Requires Yandex Disk API integration. Adds ~200 lines of
  vault code. All existing SourceSnapshot/EvidenceItem gain optional vault_ref.

**ADR-17: FACT_FROM_API_METADATA as Distinct Evidence Status**

- Context: OpenAlex/Crossref/DOAJ data is more authoritative than publisher
  claims but less authoritative than official journal pages.
- Decision: Add FACT_FROM_API_METADATA between FACT_FROM_SOURCE and VENDOR_CLAIM.
  Adapter bridge marks OpenAlex/Crossref/DOAJ results as FACT_FROM_API_METADATA,
  not VENDOR_CLAIM.
- Consequences: Conflict resolution rules updated: FACT_FROM_SOURCE > FACT_FROM_API_METADATA > VENDOR_CLAIM.
