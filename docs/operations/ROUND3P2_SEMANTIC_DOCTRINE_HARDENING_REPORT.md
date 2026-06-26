# Round III-P2: Semantic Zombie Purge & LLM-Only Doctrine Enforcement

**Date:** 2026-06-26
**Branch:** `feature/round3-six-phase-build-hardening`
**Scope:** Harden 6-phase build (Round III-O) against semantic deterministic zombies.

## 1. Summary of Removed/Neutralized Zombies

### Removed: `_infer_venue_families()` keyword→discipline map
- **Before:** Hardcoded 5-entry keyword→venue-family map (philosophy, sts, sociology, media, technology) with fixed venue lists and `confidence: "medium"`.
- **After:** Method deleted. `set_discipline_intent()` stores raw text, marks `intent_parse_status = "needs_llm"`, returns `venue_families_status: "FUNNEL_BLOCKED_NEEDS_LLM"` with empty families list.

### Neutralized: `_build_venue_family_from_venue()` cross-track
- **Before:** Called `_infer_venue_families()` on venue name+scope to produce fake family context.
- **After:** Stores venue identity, sets `families_status: "BLOCKED_NEEDS_LLM"`, empty families. No semantic inference without LLM.

### Neutralized: `get_venue_matrix()` semantic fields
- **Before:** Included `confidence` field (copied from candidate, often "low" default — looks like semantic assessment).
- **After:** Removed `confidence`. Added explicit `semantic_assessment: "NOT_ASSESSED_NEEDS_LLM"`. Only technical/structural fields remain: evidence count, sources count, unknowns count, status, next_action.

### Pre-existing zombies (documented, NOT removed in this pass)
These exist in services predating the 6-phase build. They are the deterministic fallback paths of the existing agent architecture. Removing them requires LLM organ contracts (Track 7 — deferred):
- `fit_assessment.py::assess_fit()` — 12-axis keyword rules
- `mismatch_mapping.py::build_mismatch_map()` — hardcoded severity/action
- `rewrite_planning.py::build_rewrite_plan()` — axis→change_type map
- `citation_ecology.py::build_citation_ecology_report()` — threshold-based
- `mavrinsky_venue_selection.py::assess_fit_for_vpkg()` — token hit counts
- `venue_profiling.py::_detect_regime()`, `_extract_*()` — regex extraction

These remain but are clearly documented as deterministic fallback, not LLM-equivalent. The cockpit UI already marks them with `"deterministic_fallback"` warnings where applicable.

## 2. LLM-Only Semantic Doctrine Enforcement Table

| Component | Before | After | Semantic Engine | Status |
|-----------|--------|-------|-----------------|--------|
| discipline intent | keyword→families | stores raw text, blocks | LLM required / FUNNEL_BLOCKED | ENFORCED |
| venue families | keyword map | removed entirely | LLM required / BLOCKED_NEEDS_LLM | ENFORCED |
| venue matrix | confidence field visible | semantic_assessment = NOT_ASSESSED | LLM required for semantic axes | ENFORCED |
| venue family context | keyword→family from venue | stores identity, blocks | LLM required / BLOCKED_NEEDS_LLM | ENFORCED |
| cost estimate | mechanical arithmetic | unchanged | N/A (technical determinism OK) | OK_TECHNICAL |
| depth mode | mode selection | unchanged | N/A (technical determinism OK) | OK_TECHNICAL |
| compliance | minimal checklist | unchanged label | Labeled `mechanical_compliance` | DOCUMENTED |
| fit assessment | deterministic 12-axis | unchanged (agent fallback) | Agent fallback documented | DEFERRED_TO_LLM_ORGAN |

## 3. URL/Security Gate Status

### SSRF Protection: ENFORCED
- `Case._is_safe_url()` validates all URLs before fetch:
  - Scheme allowlist: `http`, `https` only
  - Blocked: `file://`, `ftp://`, `data:`, `gopher://`, etc.
  - Blocked hosts: `localhost`, `127.0.0.1`, `::1`, `0.0.0.0`
  - DNS resolution check: blocks private/reserved/loopback/link-local IPs
  - Cloud metadata IP `169.254.169.254` explicitly blocked
- **8 new SSRF tests** in `test_phase1_source_acquisition.py::TestURLSecurityGate`

## 4. Adapter Mode Gate Status

### LIVE_API Env-Gated: ENFORCED
- `set_adapter_mode("live_api")` now requires `KAIROSKOPION_ALLOW_LIVE_API=1` in server environment
- Without env var: returns `status: "forbidden"`
- Offline modes (offline_stub, fixture, cached) always allowed
- **3 new tests**: blocked without env, allowed with env, audit logged

## 5. VenueMemory Review Gate Status

### Review-Gated: ENFORCED
New fields on `VenueMemoryRecord`:
- `review_status`: provisional | candidate | accepted | rejected | superseded
- `record_type`: case_investigation (default)
- `created_from_case_id`: provenance
- `source_refs`: evidence trail
- `is_canonical` property: only True when `review_status == "accepted"`

Rules enforced:
- All new records start as `provisional`
- `upsert_from_venue()` creates provisional records
- Tacit notes remain notes, never auto-promote to facts
- Outcomes remain outcomes, never auto-generalize
- Promotion requires explicit `POST /venue-memory/{id}/review` with valid status
- **6 new review gate invariant tests** in `test_phase4_venue_memory.py::TestVenueMemoryReviewGate`

## 6. Tests Rewritten/Added

| Test file | Before | After | Key changes |
|-----------|--------|-------|-------------|
| test_phase1_source_acquisition.py | 13 | 21 | +8 SSRF tests, +3 adapter mode gate tests |
| test_phase3_track_a_funnel.py | 14 | 15 | Rewritten: no keyword→family assertions; assert BLOCKED states |
| test_phase4_venue_memory.py | 17 | 25 | +6 review gate invariants, +2 provenance tests |
| test_phase5_budget_depth.py | 13 | 13 | Unchanged (already technical-only) |
| test_phase6_ui_integration.py | 16 | 16 | Unchanged (file/import checks) |
| **Total new tests** | 73 | 90 | **+17 net new** |

### Doctrine invariant tests added:
- `test_no_deterministic_fallback_for_venue_families` — families always empty without LLM
- `test_venue_matrix_no_fake_semantic_scores` — no fit_score, risk_score, overall_fit
- `test_new_record_is_provisional` — VenueMemory starts provisional
- `test_tacit_notes_do_not_become_facts` — notes ≠ facts
- `test_outcomes_do_not_become_facts` — outcomes ≠ facts

## 7. Full Regression Results

```
2390 passed, 4 deselected, 1 warning, 5 subtests passed in 46.47s
TypeScript: clean (tsc --noEmit)
Vite build: clean (352 KB JS, 99 KB CSS)
```

## 8. Remaining Blockers

### DEFERRED: LLM organ contracts (Track 7)
The following LLM organ contracts are defined but not implemented. Without them, the existing agent deterministic fallbacks (pre-dating the 6-phase build) remain active:
1. `DisciplineIntentParser` — parse free-text intent into structured discipline model
2. `VenueFunnelPlanner` — discipline→venue family→candidate pool
3. `VenueMatrixAssessor` — semantic axes for venue comparison
4. `VenueFamilyContextBuilder` — venue→discipline context
5. `DepthRecommendationAgent` (optional) — semantic depth recommendation

These are the next implementation target, not a blocker for the P2 hardening pass.

### NOT BLOCKING:
- Pre-existing deterministic services (fit_assessment, mismatch_mapping, rewrite_planning, citation_ecology) — these are agent fallback paths, not 6-phase zombies. They are clearly labeled and return `confidence=low` with explicit warnings.

## RESULT

**`SIX_PHASE_BUILD_HARDENED_READY_FOR_MAIN_REVIEW`**

All semantic zombies from the 6-phase build are neutralized. Security gates enforced. VenueMemory review-gated. Tests doctrine-compliant. No new feature expansion.
