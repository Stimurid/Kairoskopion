# Venue Registry Architecture — v0

## 1. Purpose

The venue registry provides a **general venue evidence registry** for Kairoskopion:

- **Source-bound facts**: every claim about a venue traces to a specific source document with provenance metadata (URL, retrieval date, extraction method, evidence status).
- **Reusable venue profiles**: once evidence about a venue is collected, it can be assembled into evidence packs for arbitrary manuscript x venue trials without rebuilding from scratch.
- **Evidence-first discipline**: the registry distinguishes official facts from external claims, inferences, and unknowns. No field is populated without a source trail.

### What this is NOT

- Not a journal ranking system or quality assessor.
- Not a mass crawler or scraper.
- Not a recommendation engine (yet).
- Not an "all journals database" — it holds only venues the user has actively profiled.
- Not a submission automation layer.

## 2. Core Entities

### VenueRecord

Top-level venue identity record. One per venue.

| Field | Type | Description |
|-------|------|-------------|
| `venue_record_id` | str | Stable ID (`vrec_*`) |
| `canonical_name` | str | Primary name |
| `aliases` | list[str] | Alternative names, abbreviations |
| `issn` | str or None | Print ISSN |
| `eissn` | str or None | Electronic ISSN |
| `publisher` | str or None | Publisher or institution |
| `official_urls` | list[str] | Known official URLs |
| `created_at` | str | ISO timestamp |
| `updated_at` | str | ISO timestamp |

### VenueSource

A specific document or page used as evidence about a venue.

| Field | Type | Description |
|-------|------|-------------|
| `venue_source_id` | str | Stable ID (`vsrc_*`) |
| `venue_record_id` | str | FK to VenueRecord |
| `source_url` | str or None | URL (None for manual notes) |
| `source_title` | str | Human-readable title |
| `source_type` | str | See source type taxonomy |
| `retrieved_at` | str or None | ISO timestamp of retrieval |
| `freshness_window_days` | int or None | Expected validity period |
| `extracted_by` | str | Who/what extracted (human, heuristic, etc.) |
| `extraction_method` | str | How extracted (manual_note, regex_heuristic, etc.) |
| `notes` | str or None | Free-text notes |
| `created_at` | str | ISO timestamp |

### VenueClaim

A single factual claim about a venue, linked to a source.

| Field | Type | Description |
|-------|------|-------------|
| `venue_claim_id` | str | Stable ID (`vclm_*`) |
| `venue_record_id` | str | FK to VenueRecord |
| `venue_source_id` | str | FK to VenueSource |
| `claim_path` | str | Dot-path to profile field (e.g. `language_policy`, `word_limits.article_max`) |
| `claim_value` | any | The claimed value |
| `evidence_status` | str | See evidence status taxonomy |
| `confidence` | str | high / medium / low |
| `quote_or_summary` | str or None | Supporting quote or summary from source |
| `conflict_group` | str or None | Group ID for conflicting claims |
| `created_at` | str | ISO timestamp |

### VenueEvidencePack

Assembled profile from registry claims, ready for pipeline consumption.

| Field | Type | Description |
|-------|------|-------------|
| `evidence_pack_id` | str | Stable ID (`vpack_*`) |
| `venue_record_id` | str | FK to VenueRecord |
| `profile` | dict | Resolved venue profile fields |
| `official_facts` | list[str] | Claim IDs backed by official sources |
| `external_claims` | list[str] | Claim IDs from external/third-party sources |
| `inferences` | list[str] | Claim IDs marked as inference |
| `unknowns` | list[str] | Profile fields with no claims |
| `conflicts` | list[dict] | Unresolved conflicts (claim_path + competing claim IDs) |
| `stale_warnings` | list[str] | Claims from sources past freshness window |
| `build_log` | list[str] | Decisions made during profile assembly |
| `created_at` | str | ISO timestamp |

### VenueProfileBuildResult

Service output wrapping the evidence pack with build metadata.

| Field | Type | Description |
|-------|------|-------------|
| `venue_record_id` | str | Which venue was built |
| `evidence_pack` | VenueEvidencePack | The assembled pack |
| `markdown_text` | str | Venue guidelines Markdown for `run-local` |
| `source_count` | int | Sources used |
| `claim_count` | int | Claims processed |
| `conflict_count` | int | Unresolved conflicts |
| `unknown_count` | int | Fields with no evidence |

## 3. Evidence Status Taxonomy

| Status | Meaning |
|--------|---------|
| `official_fact` | Extracted from an official venue page (homepage, author guidelines, editorial policy) |
| `external_claim` | From a third-party source (indexer, publisher aggregator, summary site) |
| `inference` | Derived from patterns (e.g. "likely double-blind" from anonymization instructions) |
| `unknown` | No evidence available for this field |
| `conflicting` | Multiple sources disagree; not resolved |
| `stale` | Source is past its freshness window |
| `deprecated` | Claim replaced by newer evidence |

## 4. Source Types

| Type | Description | Freshness window |
|------|-------------|-----------------|
| `official_homepage` | Venue's main page | 180 days |
| `official_author_guidelines` | Author instructions page | 90 days |
| `official_editorial_policy` | Editorial/ethics policy page | 180 days |
| `official_archive` | Issue archive or TOC | 365 days |
| `official_contacts` | Editorial board / contact page | 60 days |
| `registry_card` | ISSN portal, DOAJ, Ulrichsweb entry | 365 days |
| `indexer_page` | Scopus, WoS, OpenAlex entry | 365 days |
| `publisher_page` | Publisher's venue listing | 180 days |
| `third_party_summary` | Blog, wiki, review site | 90 days |
| `manual_note` | User-entered note | None (no expiry) |

## 5. Required Provenance Fields (per claim)

Every VenueClaim carries:

- `source_url` — where the evidence came from (None for manual notes)
- `source_title` — human-readable source label
- `source_type` — from the source type taxonomy
- `retrieved_at` — when the source was accessed
- `evidence_status` — from the evidence status taxonomy
- `freshness_window` — how long the source is considered valid (via source type defaults)
- `extracted_by` — who/what produced the claim (human, heuristic, etc.)
- `extraction_method` — how the value was obtained (manual_note, regex_heuristic, seed_corpus_import, etc.)
- `confidence` — high / medium / low
- `quote_or_summary` — supporting text from the source
- `claim_path` — which profile field this claim populates
- `conflict_group` — optional group ID linking competing claims

## 6. Venue Profile Fields

The evidence pack resolves these profile fields from claims:

| Field | Description |
|-------|-------------|
| `name` | Canonical venue name |
| `aliases` | Alternative names |
| `issn` / `eissn` | Standard identifiers |
| `publisher` | Publisher or institution |
| `official_urls` | Known official URLs |
| `aims_scope` | Aims and scope summary |
| `accepted_article_types` | List of accepted article types |
| `accepted_languages` | Language policy |
| `submission_route` | How to submit (e.g. OJS, ScholarOne, email) |
| `author_guidelines_summary` | Key requirements from author guidelines |
| `word_limits` | Word/page limits (article, abstract) |
| `abstract_limits` | Abstract word limits |
| `citation_style` | Required citation style |
| `review_model` | Review type (double-blind, open, etc.) |
| `anonymization_policy` | Anonymization requirements |
| `apc_oa` | APC and open access status |
| `indexing_claims` | Claimed indexing (Scopus, WoS, DOAJ, etc.) |
| `ethics_policy` | Ethics requirements |
| `ai_policy` | AI usage disclosure policy |
| `data_policy` | Data availability requirements |
| `conflict_policy` | Conflict of interest policy |
| `editorial_board_signal` | Editorial board presence/size signal |
| `recent_issue_signal` | Recent publication activity signal |
| `unknowns` | Fields with no evidence |

## 7. Freshness Policy

- **Official pages** (homepage, guidelines, editorial policy) expire slower than third-party pages.
- **Indexer claims** (Scopus, WoS) require a retrieval date; claims without dates are treated as stale.
- **Editorial board** information is volatile — 60-day freshness window.
- **Author guidelines** must be refreshed before real submission decisions — 90-day window.
- **Manual notes** have no automatic expiry (user-entered, user-maintained).
- **Stale sources** are flagged but not deleted — they remain as evidence with `stale` status.

## 8. Integration

### Import path
- `import_venue_seed_corpus(corpus_dir)` reads JSONL files (venues, sources, claims) and writes to registry storage.
- Seed corpus is synthetic/public only. No private data.

### Build path
- `build_venue_evidence_pack(venue_id_or_alias, registry_storage)` assembles claims into a resolved profile.
- Output includes Markdown text compatible with `run-local --venue-guidelines`.

### Pipeline integration
- Generated evidence pack Markdown feeds directly into the existing `run-local` pipeline.
- Reports distinguish official facts vs. external claims vs. unknowns.
- SubmissionPack blocks when critical evidence (language policy, article types, word limits) is stale or unknown.

### Conflict handling
- If two claims target the same `claim_path`, the resolver checks:
  1. If one is `official_fact` and the other is not, official wins (no conflict marker).
  2. If both are `official_fact` or both are `external_claim` and values differ, the field is marked `conflicting` with both claim IDs reported.
  3. Conflicts are never silently resolved — they appear in the evidence pack and build log.

## 9. Non-Goals

- **Mass crawling**: no automated web fetching of venue pages.
- **Automatic truth verification**: claims are not cross-checked against external databases.
- **Journal ranking**: no quality scores, quartile assignments, or prestige metrics.
- **Reviewer prediction**: no modeling of likely reviewers or review outcomes.
- **Acceptance probability**: no statistical acceptance rate modeling.
- **Automatic submission**: no submission portal automation.
