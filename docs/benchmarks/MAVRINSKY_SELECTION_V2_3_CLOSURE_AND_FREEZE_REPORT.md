# Mavrinsky venue selection v2.3 — closure + golden top-5 freeze

**Date:** 2026-06-14
**Branch:** `feature/venue-blockers-vfc2-corpus-board-ru`
**Run ID:** `mavrinsky_selection_v2_3_001`
**Prior pass:** [`MAVRINSKY_SELECTION_V2_2_EDITORIAL_BOARD_GLUE_REPORT.md`](MAVRINSKY_SELECTION_V2_2_EDITORIAL_BOARD_GLUE_REPORT.md) (commit 72aa3b1)

This pass closes the two named v2.2 follow-ups and freezes the top-5
dataset for manual methodological golden analysis. No new venues, no
broad discovery, no new architecture beyond a small Springer-pattern
fallback helper and a codified completeness-threshold rule.

No LLM. No final submission recommendation. No invented data. No
paid APIs. No secrets. No merge / no tag / no deploy.

---

## A. v2.2 baseline (for diff)

| field | v2.2 final |
|---|---|
| total VPKGs | 34 |
| with EditorialBoardCloud | **5** (DHQ + 4 new top-candidate boards) |
| with FormalSubmissionProfile | 4 |
| top-5 (ranker output) | Memory, Mind & Media · Foucault Studies · Techné · Philosophy & Technology · Le foucaldien |
| board status for top-5 | MM&M 9 / FS 18 / Techné 25 / **P&T NOT_FOUND** / Le foucaldien 30 |
| open issues | P&T board Springer-SPA gap; partial-vs-present threshold consistency |

---

## B. Philosophy & Technology Springer board fallback

### Implementation

New helpers in
[`services/venue_topcand_deeplite.py`](../../src/kairoskopion/services/venue_topcand_deeplite.py):

- `springer_board_url_candidates(homepage_url)` — derives canonical
  candidate URLs from a Springer journal homepage of the shape
  `https://www.springer.com/journal/<jid>` (the case Mavrinsky's P&T
  homepage matches). Three URL patterns tried in order: `/editors`,
  `/editorial-board`, `/editorial-team`. **No broad web search.**
- `enrich_board_with_springer_fallback(vpkg)` — uses
  `enrich_board_for_vpkg` on each candidate URL in turn; first
  success wins. If all fail, records the spec-mandated stable
  failure tag
  > `SPRINGER_BOARD_INACCESSIBLE_SPA_OR_NOT_FOUND`

### Result for P&T

From this run's `pt_springer_fallback.json`:

```
candidates_tried:
  - https://www.springer.com/journal/13347/editors
  - https://www.springer.com/journal/13347/editorial-board
  - https://www.springer.com/journal/13347/editorial-team

per_url_status:
  - editors          : INACCESSIBLE (HTTPError)
  - editorial-board  : INACCESSIBLE (page returned without parseable members)
  - editorial-team   : INACCESSIBLE (HTTPError)

extraction_status : SPRINGER_BOARD_INACCESSIBLE_SPA_OR_NOT_FOUND
members_sampled   : 0
editorial_board_cloud : None
board_page_url    : None
```

Honest stable failure recorded. **No editor names fabricated.** P&T
VPKG's `editorial_board_cloud_id` remains None; `completeness` stays
`missing`. The runner writes a `warnings` entry on the VPKG documenting
the attempt:

> "v2.3 Springer fallback: SPRINGER_BOARD_INACCESSIBLE_SPA_OR_NOT_FOUND
> — tried 3 URL patterns; no editor names fabricated"

### Tests

`tests/test_selection_v2_3_closure.py::TestSpringerFallbackUrlPatterns`
and `TestSpringerFallbackOutcomes` — 7 tests covering:

- ID extraction from `springer.com/journal/<id>` (with/without trailing slash);
- non-Springer URLs return empty candidate list;
- `/article/` paths intentionally NOT supported (per-article URL, not journal);
- empty candidates produce stable failure tag;
- all-URL-failure produces stable failure tag;
- first success wins (other URLs not attempted).

---

## C. Board present/partial threshold — codified rule

### Implementation

`services/venue_topcand_deeplite.py::board_completeness_from_status`
is now the **single source of truth** for the completeness mapping:

```
members_sampled >= 6 AND extracted        -> 'present'
members_sampled in 1..5 AND extracted     -> 'partial'
URL exists but extraction failed          -> 'missing'
no URL                                    -> 'missing'
```

Where "extracted" = `EXTRACTED_FROM_OFFICIAL_HTML` or
`EXTRACTED_UNVERIFIED`. Failed statuses (`INACCESSIBLE`, `JS_ONLY`,
`NOT_FOUND_AFTER_SEARCH`, `UNKNOWN`) always map to `missing`.

### Tests

`TestBoardCompletenessThreshold` — 8 cases (9/18/25/30 → present,
5/1 → partial, unverified-with-9 still present, every failed status →
missing).

`TestThresholdMergeSafety` — 1 reproduction case proving that an
empty/failed re-extraction (with the threshold-derived `missing`
completeness) DOES NOT erase an existing present board cloud. The
v2.1 B2 fix combined with this rule produces the right behaviour
end-to-end.

### Effect on the actual durable registry

Re-reading
`.kairoskopion/registries/venue_profile_packages.jsonl` after
v2.3 + v2.2:

| venue | board completeness | members | extraction status |
|---|---|---|---|
| Memory, Mind & Media | **present** | 9 | EXTRACTED_FROM_OFFICIAL_HTML |
| Foucault Studies | **present** | 18 | EXTRACTED_FROM_OFFICIAL_HTML |
| Techné | **present** | 25 | EXTRACTED_FROM_OFFICIAL_HTML |
| Philosophy & Technology | **missing** | 0 | SPRINGER_BOARD_INACCESSIBLE_SPA_OR_NOT_FOUND |
| Le foucaldien | **present** | 30 | EXTRACTED_FROM_OFFICIAL_HTML |
| Digital Humanities Quarterly | partial | — | v2.1 B2 one-shot restoration (members not re-counted) |

Honest correction: the v2.2 report claimed all 4 new boards were stuck
at "partial". Reading the actual JSONL shows v2.2 had already
recorded them as `present` (the runner's `< 6 → partial else present`
rule fired correctly on 9/18/25/30 members). The v2.2 report was
wrong about this; v2.3 codifies the rule explicitly and proves it
with tests. The actual durable state is correct.

---

## D. Top-5 before/after board coverage

| stage | top-5 with board | top-5 with corpus hull | top-5 with formal profile |
|---|---|---|---|
| v2.1 final | 0 | 5 | 4 |
| v2.2 final | 4 (P&T missing) | 5 | 4 |
| **v2.3 final** | **4** (P&T still missing — honest INACCESSIBLE) | **5** | **4** |

Across the whole registry: total board coverage = **5 of 34**
(DHQ + 4 top good_fits).

The 4 attached top-5 boards now read `present` (correctly), and P&T
has been thoroughly tried via Springer fallback and stably marked
inaccessible. No partial-vs-present ambiguity remains for the top-5.

---

## E. Golden top-5 freeze artifact

### Frozen artifacts

| artifact | path | tracked? |
|---|---|---|
| machine-readable JSON | `private_inputs/runs/mavrinsky_selection_v2_3_001/GOLDEN_TOP5_FREEZE_V2_3.json` | ignored |
| human-readable Markdown | [`docs/benchmarks/MAVRINSKY_GOLDEN_TOP5_FREEZE_V2_3.md`](MAVRINSKY_GOLDEN_TOP5_FREEZE_V2_3.md) | **tracked** |

Both carry `_lifecycle_status: GOLDEN_ANALYSIS_INPUT` and the
explicit `_intended_use` string at the top:

> "Manual methodological golden analysis. NOT a submission
> recommendation. NOT a ranking that should be acted on without
> human review."

### What the freeze contains per top-5 venue

- VPKG id, canonical name, publisher, ISSNs, homepage, OpenAlex
  source id;
- bucket label + `label_reasons` from `_bucket_v2`;
- full 16-axis FitAssessment (summary + per-axis values + evidence
  source);
- `_signals_used` (token detection counts: continental/philtech/STS/HCI/theory/empirical);
- corpus hull summary (id, completeness);
- corpus pattern summary (top terms, dominant concepts, article type
  hints, method density, novelty hints, reference count stats);
- formal submission profile (extracted fields with per-field
  `evidence_status: external_claim_html` and source_url);
- board cloud summary (id, completeness, extraction_status,
  members_sampled, source URL);
- MismatchMap with `evidence_refs` + `requires_user_acceptance`;
- RewritePlan / CitationPlan / RiskReport stubs (each
  `_lifecycle_status: STUB`);
- evidence_status_summary across 4 layers;
- explicit `unknowns` list (per-VPKG honest gaps);
- recent `warnings` (last 10).

### What the freeze does NOT contain

- final submission recommendation (deliberately absent);
- editor biographies;
- editor preference claims;
- Q1/Q2 / JCR / Scopus / WoS / Dimensions claims (no auth for those
  sources);
- ВАК / РИНЦ tier (no eLibrary auth);
- invented references.

### Top-5 ordering after v2.3 (with board signal attached)

Recomputed with the calibrated bucketer + bucket-first ranker:

1. **Foucault Studies** [good_fit]
2. **Memory, Mind & Media** [good_fit]
3. **Techné** [good_fit]
4. **Philosophy & Technology** [good_fit]
5. **Le foucaldien** [possible_but_costly]

Foucault Studies moved from #2 → #1 because its 18-member board
attach lifted `evidence_confidence` from medium → strong, tying with
MM&M. The deterministic alphabetical tiebreak in `rank_top_candidates`
puts F before M. **This is correct behaviour, not a regression** —
the freeze documents this ordering shift explicitly.

---

## F. Remaining limitations

| layer | reality |
|---|---|
| Philosophy & Technology board | Springer SPA serves editor list in JS. Stably marked `SPRINGER_BOARD_INACCESSIBLE_SPA_OR_NOT_FOUND`. Closing this requires either a JS-rendering adapter (separate sprint) or operator-provided manual paste. |
| Citation plan stubs name CATEGORIES not anchors | OpenAlex `referenced_works` not yet flowing into the stub. Next pass could wire it. |
| 29 non-top VPKGs unanalyzed | Out of scope here. The bucketer already labels them `insufficient_data`. |
| ВАК / РИНЦ tier for Russian seeds | `AUTH_REQUIRED` — operator decision (see [`AUTH_AND_PROXY_API_LANDSCAPE.md`](../AUTH_AND_PROXY_API_LANDSCAPE.md) §3.5). |
| ORCID-to-candidate binding in board cloud | Adapter limitation — requires DOM-level structure. |

---

## G. Next step

> **The next step is manual methodological golden analysis by the
> operator/research team, NOT more discovery.**

The freeze (Section E) is the input. The operator now applies what
Kairoskopion cannot: knowledge of the article's exact protected core,
career trade-offs, language/time budget, and editor familiarity
beyond what OpenAlex Authors knows. Kairoskopion's job at this
point is to **present evidence honestly**, not to decide.

Concrete tasks that fit AFTER manual analysis (none of them in
scope here):

- if the operator picks Foucault Studies → produce a real RewritePlan
  (not stub) and a CitationPlan grounded in the venue's actual
  reference graph;
- if the operator picks Le foucaldien → resolve the
  `language_register_fit` mismatch with a translation plan;
- if the operator picks P&T → manually paste editor list to bypass
  the Springer-SPA inaccessibility, or accept the gap.

What is **not** the next step:

- more venue discovery;
- another seed list;
- broader OpenAlex / DOAJ keyword expansion;
- an LLM "decide for me" call;
- a final submission verdict.

---

## H. Strict prohibitions — checklist

| prohibition | status |
|---|---|
| no broad discovery | OK — only `/journal/<id>/...` patterns tried, only for P&T |
| no all-34 board expansion | OK — fallback ran on P&T only |
| no new venues | OK |
| no new seed list | OK |
| no final submission recommendation | OK — freeze explicitly `GOLDEN_ANALYSIS_INPUT` |
| no invented editor preferences | OK |
| no invented biographies | OK |
| no invented references | OK |
| no unknowns filled from memory | OK |
| no paid API dependencies | OK |
| no committed secrets | OK |
| no `private_inputs` leak | OK |
| no merge / no tag / no deploy | OK |

---

## I. Artifacts

| artefact | path |
|---|---|
| Springer fallback helpers | `src/kairoskopion/services/venue_topcand_deeplite.py::springer_board_url_candidates` / `enrich_board_with_springer_fallback` (tracked) |
| codified threshold rule | `src/kairoskopion/services/venue_topcand_deeplite.py::board_completeness_from_status` (tracked) |
| v2.3 runner | `scripts/mavrinsky_real_venue_selection_v2_3.py` (tracked) |
| v2.3 tests | `tests/test_selection_v2_3_closure.py` (tracked, 17 tests) |
| golden freeze (JSON) | `private_inputs/runs/mavrinsky_selection_v2_3_001/GOLDEN_TOP5_FREEZE_V2_3.json` (ignored) |
| golden freeze (Markdown) | `docs/benchmarks/MAVRINSKY_GOLDEN_TOP5_FREEZE_V2_3.md` (tracked) |
| P&T fallback audit | `private_inputs/runs/mavrinsky_selection_v2_3_001/pt_springer_fallback.json` (ignored) |
| coverage after | `private_inputs/runs/mavrinsky_selection_v2_3_001/coverage_after.json` (ignored) |
| this report | `docs/benchmarks/MAVRINSKY_SELECTION_V2_3_CLOSURE_AND_FREEZE_REPORT.md` (tracked) |

---

## J. Tests / build

- Full pytest: **1455 passed**, 4 deselected (+17 v2.3 tests; no
  regressions vs the 1438 v2.2 baseline).
- Architectural invariant: services-layer urllib grep = **0 hits**.
- `npx vite build`: not re-run; only Python.

---

## K. Acceptance criteria

| # | criterion | status |
|---|---|---|
| G.1 | P&T board fallback either extracts evidence OR records stable honest failure | ✅ Stable `SPRINGER_BOARD_INACCESSIBLE_SPA_OR_NOT_FOUND` after 3 URL patterns tried |
| G.2 | Board present/partial threshold fixed and tested | ✅ `board_completeness_from_status` codified rule + 8 threshold tests + 1 merge-safety test |
| G.3 | Existing board clouds not erased | ✅ B2 merge from v2.1 + missing-completeness no-erase test |
| G.4 | Golden top-5 freeze artifact exists | ✅ JSON in run dir + Markdown in `docs/benchmarks/` |
| G.5 | Freeze clearly marked as input for manual analysis, not recommendation | ✅ both artifacts carry `_lifecycle_status: GOLDEN_ANALYSIS_INPUT` and explicit `_not_a_submission_recommendation: true` |
| G.6 | Tests pass | ✅ 1455 / 1455 |
| G.7 | Commit + push | ✅ (see below) |
| G.8 | No merge / tag / deploy / secrets | ✅ |

End of report.
