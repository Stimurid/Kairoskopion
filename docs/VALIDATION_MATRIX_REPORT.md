# Validation Matrix Report — Arbitrary Manuscript x Venue

**Date:** 2026-06-11
**Base:** `v0.2.0-alpha-rc4` at `b8a94bb`
**Branch:** `feature/arbitrary-manuscript-venue-validation-matrix`

## Fixture Cases

| # | Case | Manuscript | Venue |
|---|------|-----------|-------|
| 1 | Good fit | English theoretical (platform governance, 12 refs) | English philosophy venue (complete guidelines) |
| 2 | Language blocker | English theoretical | Russian-only humanities venue |
| 3 | Method/genre blocker | English theoretical | Empirical social science venue (requires data) |
| 3b | Method match | Empirical social science (mixed-methods, 12 refs) | Empirical social science venue |
| 4 | Missing evidence | English theoretical | Mostly-UNKNOWN venue (no guidelines) |
| 5 | Formal compliance | English theoretical | Education venue (abstract 200-250 + article 6000-12000) |
| 6 | Thin citation | Theoretical (3 refs only) | English philosophy venue |
| 6b | Robust citation | Theoretical (12 refs) | English philosophy venue |

All fixtures are synthetic and non-private. No Logos data used.

## Expected vs Observed Behavior

### Case 1 — Good fit

| Assertion | Expected | Observed | Result |
|-----------|----------|----------|--------|
| language_register | strong/medium | strong | PASS |
| discipline | not unknown | medium | PASS |
| genre | not weak | strong | PASS |
| no blocking language mismatch | no blocking | no blocking | PASS |
| overall | not poor_fit | possible_but_costly | PASS |

### Case 2 — Language blocker

| Assertion | Expected | Observed | Result |
|-----------|----------|----------|--------|
| language_register | bad | bad | PASS |
| blocking mismatch | present | present | PASS |
| critical list | language mentioned | yes | PASS |
| desk_reject risk | blocking present | present | PASS |
| submission readiness | not_ready | not_ready | PASS |
| rewrite plan language action | present | present | PASS |
| overall | poor_fit | poor_fit | PASS |

### Case 3 — Method/genre blocker

| Assertion | Expected | Observed | Result |
|-----------|----------|----------|--------|
| theoretical at empirical: method | weak/bad | weak | PASS (after D16 fix) |
| empirical at empirical: method | strong/medium | strong | PASS |
| language OK both | strong/medium | strong/strong | PASS |
| method mismatch entry | present | present | PASS |

### Case 4 — Missing evidence

| Assertion | Expected | Observed | Result |
|-----------|----------|----------|--------|
| unknown axes >= 3 | yes | yes | PASS |
| unknowns in fit | non-empty | non-empty | PASS |
| cautious overall | not_enough_data/possible_but_costly/poor_fit | not_enough_data | PASS |
| conditional actions | present | present | PASS |
| no invented word limit | no non_compliant word_count | correct | PASS |

### Case 5 — Formal compliance

| Assertion | Expected | Observed | Result |
|-----------|----------|----------|--------|
| abstract limit not applied to body | correct | correct | PASS |
| article word limit present | compliance item exists | exists | PASS |
| language OK | strong/medium | strong | PASS |

### Case 6 — Citation ecology

| Assertion | Expected | Observed | Result |
|-----------|----------|----------|--------|
| thin (3 refs) citation_ecology | weak | weak | PASS |
| robust (12 refs) citation_ecology | not weak | medium | PASS (after D17 fix) |
| thin has citation_gap risk | present | present | PASS (after D17 fix) |
| thin vs robust different | different values | weak vs medium | PASS (after D17 fix) |

## CLI Smoke Test

All 6 cases pass via `kairoskopion run-local` with per-case storage roots.
Script: `scripts/run_validation_matrix.ps1`.
Storage: `.kairoskopion_validation_matrix/` (gitignored).

## What Generalized Correctly After the Logos Trial

1. **Language policy detection** — correctly identifies English-only, Russian-only,
   and bilingual-metadata policies. Generic, not Logos-specific.
2. **Discipline matching** — 13-discipline keyword taxonomy with adjacency graph
   correctly matches philosophy, social theory, education, and distinguishes them.
3. **Genre assessment** — theoretical essays rated strong at philosophy venues,
   not penalized. Empirical venues correctly distinguish genre expectations.
4. **Unknown propagation** — mostly-UNKNOWN venue produces cautious verdict with
   conditional evidence-collection actions. No invented requirements.
5. **Word limit distinction** — abstract limits (200-250) correctly separated
   from article body limits (6000-12000). No cross-contamination.
6. **Mismatch map and risk report** — blocking language mismatch produces
   desk_reject_risk, submission not_ready. Method mismatch produces methodology
   mismatch risk.

## Defects Found and Fixed (Phase 7)

### D16 — Method detection too narrow

**Symptom:** Theoretical article on platform governance returned `method_status: unknown`
instead of `conceptual_method`. The conceptual marker list missed common signals
like "normative framework", "we argue that", "this paper argues".

**Fix:** Added markers to `_detect_method()`: `normative framework`, `normative theory`,
`theoretical framework`, `conceptual framework`, `critical analysis`, `deliberative`,
`we argue that`, `this paper argues`, `this essay argues`. Also expanded empirical
markers: `mixed-methods`, `quantitative`, `qualitative data`, `thematic analysis`,
`participants`.

**File:** `src/kairoskopion/services/article_modeling.py`

### D17 — Citation ecology thresholds too coarse + missing risk

**Symptom:** Both 3-ref and 12-ref articles got `citation_ecology: weak`. The threshold
for `medium` was 20 refs, which is too high for theoretical disciplines where 10-15
references is normal. Also, `citation_gap` risk only fired for `unknown`, not `weak`.

**Fix:** Added intermediate threshold: 8-14 refs = `medium` (was all `weak` below 20).
15+ refs = `medium` (was 20+). Added `citation_gap` risk for `weak` citation ecology.

**Files:** `src/kairoskopion/services/fit_assessment.py`, `src/kairoskopion/services/risk_reporting.py`

## Where Behavior Is Still Weak/Noisy

1. **argument_structure** — always `unknown` for new fixtures (no extraction of
   problem_statement/research_question from arbitrary manuscript formats).
2. **formal_compliance** — always `unknown` (deferred to compliance checklist,
   not assessed at fit level).
3. **author_eligibility** — always `unknown` (no author metadata extraction).
4. **novelty_positioning** — depends on narrow keyword matching; may miss subtle
   novelty signals.
5. **Overall fit label** — `possible_but_costly` for good-fit case; ideally could
   be `possible` or `strong_candidate`, but currently cautious due to unknowns.

## Remaining Product Risks

1. Method/genre detection relies on keyword matching — will fail for articles
   using uncommon terminology for conceptual or empirical work.
2. Citation ecology doesn't profile against venue citation expectations —
   only counts total references.
3. No real venue evidence beyond author guidelines text — all venue knowledge
   comes from a single guidelines document.
4. No LLM-assisted extraction — all heuristic regex, which limits accuracy.

## Overfitting Assessment

**Is Kairon now safer against Logos/article overfitting?** YES.

- No production code contains "Logos", "Логос", or any reference to the trial venue.
- All 6 validation matrix cases use completely different manuscripts and venues.
- The two defects found (D16, D17) were generic weaknesses, not Logos artifacts.
- Both fixes expand general-purpose detection (more markers, better thresholds),
  not Logos-specific behavior.
- 641 tests pass across all fixtures (original + trial + validation matrix).
