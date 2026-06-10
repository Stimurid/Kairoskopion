# Trial Logos: Evidence-Pack Rerun Report

## 1. Objective

Close D10: replace the conservative UNKNOWN venue seed with a real evidence pack
collected from official Logos journal sources, then rerun the full pipeline to test
whether Kairoskopion produces materially better positioning outputs when given
real venue evidence.

## 2. Evidence Collection Summary

10 source notes collected from official and external sources (2026-06-10):

| Source | Type | Reliability |
|--------|------|-------------|
| source_01: Official homepage (logosjournal.ru/about) | official | high |
| source_02: Publication requirements (logosjournal.ru/requirements) | official | high |
| source_03: Peer review policy (logosjournal.ru/reviewing) | official | high |
| source_04: Publication ethics (logosjournal.ru/ethics) | official | high |
| source_05: Editorial board (logosjournal.ru/board, /council) | official | high |
| source_06: RCSI submission portal (journals.rcsi.science) | official | medium |
| source_07: Indexing and metrics (researcher.life, ScimagoJR) | external | medium |
| source_08: Recent issue themes (logosjournal.ru/archive) | official | high |
| source_09: Wikipedia entry (ru.wikipedia.org) | third_party | medium |
| source_10: Language policy (assembled inference) | inference | medium |

Evidence pack: `private_inputs/logos_trial/venue_guidelines_logos_evidence_pack.md`

Evidence status categories used:
- FACT_FROM_OFFICIAL_SOURCE — 7 sources
- EXTERNAL_CLAIM — 1 source (metrics)
- INFERENCE — 2 (language policy, APC)
- UNKNOWN — 9 blocking items listed in pack

## 3. Seed Trial vs Evidence-Pack Trial: Side-by-Side

| Dimension | Seed Trial | Evidence-Pack Trial | Change |
|-----------|-----------|-------------------|--------|
| **Overall fit label** | possible_but_costly | **poor_fit** | downgrade |
| **Mismatches** | 9 (2 major, 7 informational) | **9 (1 blocking, 2 major, 6 informational)** | +blocking |
| **Risk items** | 8 (3 major, 5 minor) | **10 (1 blocking, 4 major, 5 minor)** | +blocking, +1 major |
| **Rewrite plan proposed** | 3 proposed + 10 conditional | **4 proposed + 8 conditional** | +1 proposed, -2 conditional |
| **Compliance missing** | 3 items | **5 items** | +2 (abstract, AI disclosure now detected) |
| **Submission pack status** | needs_file_update | **not_ready** (2 blocking) | downgrade |

### Axis-level comparison (12 axes)

| Axis | Seed | Evidence-Pack | Notes |
|------|------|---------------|-------|
| topic | weak | weak | unchanged |
| discipline | unknown | unknown | still unassessed |
| genre | weak | weak | unchanged |
| argument_structure | unknown | unknown | still unassessed |
| method | medium | medium | unchanged |
| citation_ecology | unknown | unknown | still unassessed |
| novelty_positioning | medium | medium | unchanged |
| **language_register** | **unknown** | **bad** | **KEY CHANGE — blocking** |
| audience | unknown | unknown | still unassessed |
| formal_compliance | unknown | unknown | deferred to checklist |
| author_eligibility | unknown | unknown | no author metadata |
| publication_regime | medium | medium | unchanged |

## 4. Key Finding: Language Policy Is Blocking

The single most important result of the evidence collection is the language policy finding.
The manuscript is in English. Logos is a Russian-language journal. This was invisible
in the seed trial (language_register = unknown). With real evidence:

- `language_register` → `bad`
- Mismatch severity → `blocking`
- Risk → `desk_reject_risk (blocking)`
- Submission pack → `not_ready`

This is exactly the kind of critical information that Kairoskopion is designed to surface:
a blocking constraint that would waste the author's time if not caught early.

## 5. Bug Found and Fixed: Language Policy Extraction (D11)

During the initial evidence-pack run, the venue profiler extracted `language_policy: "English"`
despite the evidence pack clearly stating the journal is Russian-language. Root cause:

**venue_profiling.py:171** — the old logic searched the "Submission Requirements" section
for the word "english". The evidence pack's Submission Requirements section mentions
"Metadata must be in BOTH Russian AND English" — so "english" was found, and the profiler
concluded the journal accepts English articles.

### Fix

Replaced naive detection with `_extract_language_policy()` which:

1. Checks dedicated "Language Policy" section first (highest priority)
2. Detects Russian-language signals ("Russian-language journal", "русскоязычный")
3. Distinguishes metadata language from article body language
4. Checks "Aims and Scope" / "Scope" for language signals
5. Falls back to Submission Requirements only when no dedicated section exists
6. Returns None (unknown) when metadata mentions both languages but body language unclear

### Tests added

5 new tests in `TestLanguagePolicyExtraction`:
- `test_russian_language_section` — dedicated section → Russian
- `test_english_metadata_not_english_journal` — metadata bilingual → not English
- `test_russian_scope_signal` — "Russian-language journal" in scope → Russian
- `test_english_only_submission` — English in requirements (no Russian) → English
- `test_no_language_info_returns_none` — no signals → None

All 22 venue profiling tests pass. All 592+ tests pass (see Phase 8).

## 6. Rewrite Plan Comparison

### Seed trial: 3 proposed + 10 conditional = 13 total

Proposed: topic reframe, genre restructure, genre case component
Conditional: discipline, argument_structure, citation (×2), **language (×2)**, audience,
formal_compliance (×2), author_eligibility

### Evidence-pack trial: 4 proposed + 8 conditional = 12 total

Proposed: topic reframe, genre restructure, genre case component, **language register shift (high difficulty)**
Conditional: discipline, argument_structure, citation (×2), audience,
formal_compliance (×2), author_eligibility

**Net change:** language_register moved from conditional (investigate) to proposed (act),
with difficulty rated `high`. This is correct — with evidence confirming Russian-only policy,
the system correctly escalates from "investigate language policy" to "translate/adapt the article".

## 7. Evidence Propagation Assessment

| Pipeline Component | Evidence Reached? | Quality |
|--------------------|-------------------|---------|
| VenueModel | YES — scope, publisher, URLs, unknowns | Good |
| VenueModel language | YES — "Russian" (after D11 fix) | Correct |
| VenueModel indexing | YES — scopus, wos, ebsco, erih, ulrich | Complete |
| VenueModel anonymization | YES — single_blind | Correct |
| VenueModel APC | YES — no_apc | Correct |
| VenueModel word limits | PARTIAL — 200-250 extracted (abstract, not article) | Bug-adjacent |
| FitAssessment | YES — language_register = bad | Correct |
| MismatchMap | YES — language blocking | Correct |
| RiskReport | YES — desk_reject_risk blocking | Correct |
| RewritePlan | YES — language_register_shift proposed | Correct |
| SubmissionPack | YES — not_ready with blocking reasons | Correct |
| ComplianceChecklist | PARTIAL — abstract 200-250 correct, word_count 200-250 wrong | Bug |

### Known extraction issues (not fixed — out of scope)

1. **Word limit confusion:** The compliance checker extracted `word_count: 200-250` from
   the abstract limit, then flagged "Manuscript too long (10828 > 250)". The 200-250 is
   the abstract limit, not the article word limit (which is UNKNOWN). This is a pre-existing
   issue, not introduced by this change.

2. **Article types not extracted:** `article_types_supported: []` — the evidence pack lists
   research articles, book reviews, polemical contributions, but the extractor pattern
   (`**Name**`) didn't match the numbered list format. Pre-existing limitation.

## 8. Verdict

| Criterion | Verdict |
|-----------|---------|
| Evidence pack ingestible by pipeline | PASS |
| Language policy correctly surfaced | PASS (after D11 fix) |
| Fit label reflects language barrier | PASS (poor_fit) |
| Blocking mismatch surfaced | PASS (language_register: blocking) |
| Blocking risk surfaced | PASS (desk_reject_risk) |
| Submission pack correctly blocked | PASS (not_ready, 2 blocking items) |
| Rewrite plan escalated language action | PASS (conditional → proposed, high difficulty) |
| D11 fix has tests | PASS (5 tests) |
| No regressions | PASS (597+ tests pass) |
| Evidence pack does not hallucinate | PASS (all claims traced to sources) |

**Overall: PASS — D10 closed.**

The evidence-pack rerun demonstrates that Kairoskopion produces materially better
positioning outputs when given real venue evidence. The system correctly identified
the single most important barrier (language policy) and escalated it from unknown to
blocking, changing the overall recommendation from "possible but costly" to "poor fit."
This is exactly the kind of information-asymmetry reduction the system is designed to provide.
