# Round III-J3.2 — Baseline Scenario Status

> **Date:** 2026-06-24
> **Branch:** `main` @ `905ec60`
> **Scope:** Status assessment. No code changes.

---

## 1. Pipeline Stage Map

Full baseline scenario:

```
Upload article → ArticleModel → SemanticProfile → VenueModel → FitAssessment
    → MismatchMap → CitationPlan → RiskReport → RewritePlan
    → Human Dossier → SubmissionPack
```

| Stage | Implemented? | Live in API? | Data-backed? | LLM-backed? | Deterministic Fallback? | Current Blocker |
|-------|-------------|-------------|-------------|-------------|------------------------|-----------------|
| Article Upload | YES | YES (auto) | YES (text) | — | — | None |
| ArticleModel | YES | YES (auto on intake) | YES | YES (agent) | YES (service) | None |
| SemanticProfile | YES | YES (auto) | YES | YES (agent) | YES (service) | Requires ArticleModel |
| DisciplinaryPathways | YES | YES (on demand) | PARTIAL (registry) | YES (agent) | YES (heuristics) | Requires ArticleModel |
| VenueModel | YES | **OPTIONAL** (POST /investigate-venue) | YES (venue text) | YES (agent) | YES (regex) | **Not auto-wired to article flow** |
| PublicationRegimeModel | YES | OPTIONAL (via VenueProfiler) | YES | Via VenueProfiler | YES | Same as VenueModel |
| VenueCandidatePool | YES | On demand (POST /discover-venues) | PARTIAL (LLM gen) | YES (agent) | YES | Requires pathways |
| FitAssessment | YES | Via select-venue trigger | YES | YES (agent) | YES (service) | **Requires selected_venue** |
| MismatchMap | YES | Via fit_chain | YES | NO | YES | Requires FitAssessment |
| MismatchNarrator | YES | Via fit_chain | YES | YES (agent) | Honest empty | Requires MismatchMap |
| RiskReport | YES | Via fit_chain | PARTIAL | YES (try_llm_risk_officer) | YES (structural) | Requires FitAssessment; enum normalization gap |
| RewritePlan | YES | Via fit_chain | YES | YES (agent) | needs_llm placeholder | Requires FitAssessment + MismatchMap |
| CitationPlan | YES | Via fit_chain | YES | YES (upgrade) | YES (structural) | Requires article + bibliography |
| ComplianceChecklist | YES | Via fit_chain | YES | NO | YES | Requires FitAssessment |
| SubmissionPack | YES | Via fit_chain | YES | NO | YES | Requires all above |
| HumanDossier | YES | GET /human-dossier | YES (renders) | NO (presentation) | YES | Requires case dossier |

---

## 2. Venue Data Flow Trace

| Pipeline Edge | Expected | Actual | Status | Evidence |
|---------------|----------|--------|--------|----------|
| Article upload → auto VenueModel | Automatic venue investigation from article metadata | **Not automatic** — investigation is separate optional endpoint | BY DESIGN | `cases.py:276-294` (intake router is mutually exclusive) |
| Venue text → investigate_venue() | Runs on venue-type classification | Works IF operator calls POST /investigate-venue | WORKING | `cases.py:284-287` |
| investigate_venue() → VenueProfilerAgent | LLM extraction or deterministic fallback | Works — produces VenueModel with confidence | WORKING | `cases.py:784-808` |
| investigated_venue → selected_venue | Manual promotion via POST /select-venue | Works IF operator calls endpoint | BY DESIGN | `cases.py:1053-1096` (operator choice gate) |
| selected_venue + article → FitAssessment | Auto-run | Auto-triggers via fit_chain on select | WORKING | `cases.py:1081-1082` |
| FitAssessment → risk/rewrite/citation | Auto-run via fit_chain | Works — all downstream stages fire | WORKING | `cases.py:1218-1712` |
| All stages → HumanDossier | Render existing data honestly | Works — honest rendering of available data | WORKING | `human_dossier.py` |

### Root Cause: Why J3.2 Dossier Has Low-Confidence Venue

The J3.2 test cases were created via article intake. The operator:
1. Uploaded article text → ArticleModel built automatically
2. Provided venue text as input → stored but NOT investigated
3. Never called POST /investigate-venue → `investigated_venue = None`
4. Never called POST /select-venue → `selected_venue = None`
5. Fit chain never triggered → RiskReport/RewritePlan = placeholder
6. Human dossier renders this honestly

**This is not a data absence problem or a wiring bug.** It is an intentional UX flow where venue investigation is a separate operator action.

---

## 3. CLI vs API Coverage

| Capability | CLI Pipeline | API Case Flow |
|-----------|-------------|---------------|
| ArticleModel extraction | YES (auto) | YES (auto) |
| VenueModel extraction | YES (auto, step 4-6) | OPTIONAL (separate endpoint) |
| Venue adapter calls (Crossref, OpenAlex, DOAJ) | YES (evidence stack) | NO |
| Venue discovery pool | YES | YES (on demand) |
| FitAssessment | YES (auto) | YES (after select-venue) |
| MismatchMap | YES (auto) | YES (fit_chain) |
| RiskReport | YES (auto) | YES (fit_chain) |
| CitationEcologyReport | YES | CLI only |
| Evidence audit | YES | CLI only |
| Artifact markdown | YES | CLI only (dossier via API) |
| Human dossier | NO (CLI has markdown vault) | YES |

**Key difference:** CLI pipeline runs all 18 steps sequentially. API is event-driven with operator gates.

---

## 4. RiskOfficer Status

### Production Path

The case orchestrator calls `try_llm_risk_officer()` (in `llm_semantic_organs.py`), NOT the agent shell. This path:

1. Uses `try_llm_call_with_outcome` envelope
2. Has alias resolution (`"risks"` → `"risk_items"`)
3. Returns `needs_llm` placeholder on parse failure
4. **Missing:** enum normalization (risk_type, severity not case-normalized)

### Failure Modes

| Scenario | Outcome | Quality |
|----------|---------|---------|
| LLM returns valid JSON with correct enums | risk_items extracted, semantic_status=llm_grounded | GOOD |
| LLM returns valid JSON with capitalized enums | Items extracted but risk_type="Scope Mismatch" instead of "scope_mismatch" | DEGRADED — works but wrong enum |
| LLM returns malformed JSON, repairable | Repair succeeds, items extracted | OK |
| LLM returns garbage | repair_failed → needs_llm placeholder | FALLBACK |
| No LLM provider | Deterministic build_risk_report() | STRUCTURAL_ONLY |

### Comparison with Working Agents

| Feature | CitationPlanner | RiskOfficer | Gap |
|---------|----------------|-------------|-----|
| Enum normalization | YES (`_normalize_enum_like_fields`) | NO | RiskOfficer missing |
| Alias resolution | YES | YES | OK |
| Deterministic fallback | Complete | Complete | OK |
| Agent shell used? | YES (old API) | NO (dead code) | Agent shell obsolete |

---

## 5. Recommended Next Steps (Options, Not Implementation)

### Option 1: Wire Venue Investigation into Existing Cases

**What:** For the two existing J3.2 cases on prod, manually call the venue investigation endpoints to populate VenueModel and trigger the full fit chain.

**Steps:**
1. POST `/cases/{case_id}/investigate-venue` with venue text for each case
2. POST `/cases/{case_id}/select-venue/investigated` to promote
3. Fit chain runs automatically → FitAssessment, MismatchMap, RiskReport, etc.
4. Regenerate human dossier

**Effort:** ~30 minutes (API calls + verification)
**Risk:** LOW — no code changes, existing pipeline
**Success criteria:** Both cases have populated VenueModel, FitAssessment, RiskReport in dossier
**Why now:** Proves the pipeline works end-to-end without any code changes
**Why not now:** Venue text quality may be insufficient for good VenueModel without Logos evidence pack

### Option 2: Fill VenueModel for Two Target Venues

**What:** Bounded data acquisition for Вопросы философии (missing) and connect existing Logos evidence pack.

**For Logos:**
- Evidence pack already exists in `private_inputs/logos_trial/`
- Need: resolver to load this into case flow
- Effort: Small — data exists, needs wiring

**For Вопросы философии:**
- No data exists in repository
- Need: targeted web acquisition (vphil.ru, eLibrary, Scopus listing)
- Evidence pack assembly matching Logos pattern
- ISSN: 0042-8744
- No mass scraping — single venue

**Effort:** 2-4 hours (Logos wiring: 30 min; Вопросы философии acquisition: 2-3 hours)
**Risk:** MEDIUM — web acquisition depends on site accessibility
**Success criteria:** Both venues have VenueModel with confidence ≥ medium, evidence-backed
**Why now:** These are the benchmark venues for the product
**Why not now:** May be premature before proving pipeline works with Option 1

### Option 3: RiskOfficer Enum Normalization Fix

**What:** Add enum normalization to `try_llm_risk_officer()` in `llm_semantic_organs.py`.

**Exact fix:**
- After extracting `raw.get("risk_type")`, normalize: `.lower().replace(" ", "_").replace("-", "_")`
- Validate against `RISK_TYPES` tuple from `risk_reporting.py`
- Same for `severity`
- ~15 lines in 1 file

**Effort:** 15-30 minutes
**Risk:** LOW — same pattern as Citation normalizer
**Success criteria:** LLM responses with capitalized enums produce valid risk_items
**Why now:** Smallest fix with highest signal improvement
**Why not now:** Only matters when LLM is available and returns parseable-but-misformatted JSON; does not help with garbage responses

### Recommended Sequence

1. **Option 1 first** — prove pipeline works without code changes
2. **Option 3** — fix the enum gap (smallest code change, highest reliability improvement)
3. **Option 2** — fill venue data (depends on whether Option 1 proves the flow)
