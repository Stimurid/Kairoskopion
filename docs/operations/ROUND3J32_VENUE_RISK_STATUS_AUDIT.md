# Round III-J3.2 — Venue & Risk Status Audit

> **Date:** 2026-06-24
> **Branch:** `main` @ `905ec60`
> **Scope:** Pre-implementation audit. No code changes.

---

## 1. Repository Inventory: Venue/Journal/Discipline Assets

### Live Runtime Models

| Artifact | Path | Status | Tests | Reuse Classification |
|----------|------|--------|-------|---------------------|
| VenueModel | `schema.py` | live_runtime | 38+ | deterministic formal extraction OK |
| ArticleModel | `schema.py` | live_runtime | 10+ | LLM-agent already usable |
| PublicationRegimeModel | `schema.py` | live_runtime | 4+ | deterministic formal extraction OK |
| FitAssessment | `schema.py` | live_runtime | 8+ | LLM-agent already usable |
| MismatchMap | `schema.py` | live_runtime | 6+ | LLM-agent already usable |
| RiskReport | `schema.py` | live_runtime | 3+ | LLM-agent already usable |
| CitationEcologyReport | `schema.py` | live_runtime | 3+ | LLM-agent already usable |
| DisciplineModel | `services/discipline_registry/model.py` | live_runtime | 4+ | deterministic formal extraction OK |
| DisciplineSourcePacket | `services/discipline_registry/source_packet.py` | live_runtime | 2 | deterministic formal extraction OK |

### Schema-Only / Dormant Models

| Artifact | Path | Status | Notes |
|----------|------|--------|-------|
| JournalModel (§6.8) | `schema.py` | schema_only | Superseded by VenueModel per canon §2.2. Not populated. |
| SectionModel (§6.9) | `schema.py` | schema_only | Journal section/article type. Unfilled. |
| IssueModel | — | does not exist | No explicit IssueModel. VenueModel covers journal-level. |
| FieldModelReference | `integrations/whitecrow.py` | schema_only | WhiteCrow projection. Not active. |
| VenueMemoryKeeperAgent | `agents/review/venue_memory_keeper.py` | dormant_agent | Shell exists; update logic unimplemented. |
| venue_publication_profile_builder | `agents/venue/` | broken | References removed corpus hull builder. Not callable. |

### Live Agents

| Agent | Path | LLM? | Deterministic Fallback? | Tests |
|-------|------|------|------------------------|-------|
| VenueProfilerAgent | `agents/venue_profiler.py` | YES | YES (regex heuristics) | 2+ |
| VenueFieldPositionerAgent | `agents/venue_field_positioner.py` | YES | YES (institutional fallback) | 4+ |
| VenueDiscoveryAgent | `agents/venue/venue_discovery.py` | YES | YES | 2+ |
| DisciplineSeederAgent | `agents/discipline_seeder.py` | YES | YES | 3+ |
| DisciplineSourceAcquisitionAgent | `agents/discipline_source_acquisition.py` | YES | YES | 2+ |
| RiskOfficerAgent | `agents/submission/risk_officer.py` | YES | YES (build_risk_report) | 4+ |
| CorpusSamplerAgent | `agents/venue/corpus_sampler_agent.py` | YES | YES | 2+ |
| ArticleModelerAgent | `services/article_modeler.py` | YES | YES | 2+ |

### Live Services

| Service | Path | Purpose |
|---------|------|---------|
| build_venue_model() | `services/venue_profiling.py` | Deterministic VenueModel from text (regex) |
| venue_registry | `services/venue_registry.py` | Pool CRUD, JSONL persistence |
| venue_pool_discovery | `services/venue_pool_discovery.py` | Candidate synthesis + ranking |
| venue_evidence_stack | `services/venue_evidence_stack.py` | Evidence pack from adapters |
| venue_candidate_screening | `services/venue_candidate_screening.py` | Filter candidates by fit |
| mavrinsky_venue_selection | `services/mavrinsky_venue_selection.py` | Ranking algorithm |
| risk_reporting | `services/risk_reporting.py` | Deterministic risk heuristics |
| try_llm_risk_officer | `services/llm_semantic_organs.py` | LLM risk path with envelope |
| compliance | `services/compliance.py` | Compliance checklist builder |
| source_authority | `services/source_authority.py` | Evidence credibility ranking |
| venue_cache_policy | `services/venue_cache_policy.py` | TTL cache invalidation |
| venue_operator_seed | `services/venue_operator_seed.py` | Fixture seed data (Logos, etc.) |

### Venue Adapters

| Adapter | Path | Status | Tests |
|---------|------|--------|-------|
| Crossref | `adapters/venue/crossref.py` | live_runtime | 2+ |
| OpenAlex | `adapters/venue/openalex.py` | live_runtime | 1 |
| DOAJ | `adapters/venue/doaj.py` | live_runtime | 1 |
| OpenCitations | `adapters/venue/opencitations.py` | live_runtime | 2+ |
| Unpaywall | `adapters/venue/unpaywall.py` | live_runtime | 0 |
| SnapshotCrawler | `adapters/venue/snapshot_crawler.py` | live_runtime | 0 |
| CyberLeninka | `adapters/venue/cyberleninka.py` | live_runtime | 0 |

### CLI Commands (Venue-Related)

| Command | Status |
|---------|--------|
| `cmd_build_venue_profile` | live_runtime |
| `cmd_build_venue_evidence_pack` | live_runtime |
| `cmd_discover_venue_pool` (if exists) | live_runtime |
| `cmd_import_venue_seed` | live_runtime |

### Prompt Families

| Family | Path | Agent |
|--------|------|-------|
| VENUE_FACT_EXTRACTION_FAMILY | `prompts/venue_fact_extraction.py` | VenueProfiler |
| RISK_REPORTING_FAMILY | `agents/prompt_families/risk_reporting.py` | RiskOfficer |
| discipline_source_acquisition | `prompts/discipline_source_acquisition.py` | DisciplineSourceAcquisition |
| discipline_seeding | `prompts/discipline_seeding.py` | DisciplineSeeder |
| field_positioning | `prompts/field_positioning.py` | VenueFieldPositioner |

---

## 2. RiskOfficer Failure Analysis

### Architecture

Two code paths exist:

1. **Agent shell** (`RiskOfficerAgent.execute` in `agents/submission/risk_officer.py`):
   - Uses old `try_llm_call` API (returns `None` on failure)
   - **NOT called by case orchestrator** — dead code in production flow

2. **Semantic organs path** (`try_llm_risk_officer` in `services/llm_semantic_organs.py`):
   - Uses `try_llm_call_with_outcome` envelope
   - **This is the actual production path** (called from `cases.py:1478`)
   - Has alias resolution (`find_list_under_aliases` for `"risks"` vs `"risk_items"`)

### Failure Mode: "called_ok but repair_failed"

| Step | What Happens | Status |
|------|-------------|--------|
| 1. Provider call | LLM responds | called_ok |
| 2. Strict parse | Provider doesn't enforce schema strictly | parsed=None |
| 3. Loose parse | json.loads on content | SUCCESS or FAIL |
| 4a. If parseable | loose_parsed populated | Works — items extracted |
| 4b. If garbage | repair_and_parse exhausts all strategies | repair_failed |
| 5. Adapter | parsed=None, loose_parsed=None | Returns needs_llm placeholder |

### Enum Normalization Gap

**RiskOfficer** does NOT normalize enum values:
- LLM produces: `"Scope Mismatch"`, `"HIGH"`
- Schema expects: `"scope_mismatch"`, `"high"`
- `try_llm_risk_officer` (line 183): just does `raw.get("risk_type").strip()` — no case/underscore normalization

**CitationPlanner** DOES normalize (different code path, `_normalize_enum_like_fields`).

### Fix Assessment

| Issue | Fix | Effort | Risk |
|-------|-----|--------|------|
| Enum normalization missing | Add `.lower().replace(" ", "_")` in try_llm_risk_officer | 1 file, ~15 lines | LOW |
| Agent shell dead code | Deprecate or wire to outcome API | Optional cleanup | LOW |
| Schema too lax (`required: []`) | Add field validation post-normalization | 1 file, ~20 lines | LOW |

### Deterministic Fallback Quality

`build_risk_report()` in `services/risk_reporting.py`:
- Generates risk items from fit axes + mismatch map
- Covers: desk_reject_risk, scope_mismatch, method_gap, etc.
- Confidence: medium; semantic_status: structural_only
- **Quality is acceptable for fallback** — covers major risk categories
- **Gap**: Cannot capture nuanced publication risks (LLM-only)

---

## 3. Runtime Reachability: Venue Data Flow

### The Break Point

The J3.2 dossier shows empty/low-confidence venue data because:

```
Article upload (POST /intake/text, input_type=article)
    → _build_article_model()           ← runs automatically
    → investigate_venue()              ← NOT called (separate endpoint)
    → selected_venue = None            ← nothing to select
    → fit_chain SKIPPED                ← guard: requires selected_venue
    → RiskReport = needs_llm placeholder
    → Dossier renders honestly
```

**This is by design**, not a bug. The case orchestrator decouples article intake from venue investigation. The operator must:

1. `POST /cases/{id}/investigate-venue` with venue text
2. `POST /cases/{id}/select-venue/investigated` to promote
3. Fit chain runs automatically after selection

### Venue Investigation Flow (cases.py:752-827)

1. Validates minimum 200 chars
2. If LLM provider available → VenueProfilerAgent
3. Else → deterministic `build_venue_model()` (regex)
4. Stores on `self.investigated_venue`
5. Does NOT auto-call adapters (Crossref, OpenAlex, DOAJ)
6. Adapter-based evidence is CLI/pipeline only, not in API case flow

### What's Connected vs Disconnected

| Component | Connected to API? | Connected to CLI? | Notes |
|-----------|------------------|-------------------|-------|
| VenueProfilerAgent | YES (via investigate_venue) | YES | Both paths work |
| Venue adapters (Crossref, OpenAlex, DOAJ) | NO | YES (evidence stack) | API has no adapter calls |
| VenueFieldPositioner | YES (after venue investigation) | YES | Runs post-investigation |
| Venue discovery pool | YES (POST /discover-venues) | YES | Requires pathways |
| Seed corpus (17 venues) | NO (CLI import only) | YES | Not auto-loaded by API |
| Discipline seeds (43) | YES (registry loaded) | YES | Available for positioner |
| Writing rubric | NO | NO | Standalone data |
