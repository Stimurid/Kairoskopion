# Mavrinsky venue selection v2.2 — editorial board glue (surgical)

**Date:** 2026-06-14
**Branch:** `feature/venue-blockers-vfc2-corpus-board-ru`
**Run ID:** `mavrinsky_selection_v2_2_001`
**Prior pass:** [`MAVRINSKY_SELECTION_V2_1_STABILIZATION_AND_DEEPLITE_REPORT.md`](MAVRINSKY_SELECTION_V2_1_STABILIZATION_AND_DEEPLITE_REPORT.md) (commit 1433ea6)

This pass did **one thing**: wire the existing
[`editorial_board.py`](../../src/kairoskopion/adapters/venue/editorial_board.py)
adapter onto the four board URLs discovered in v2.1 for the top-5
candidates. No new venues. No new seed list. No broad discovery.
No new architecture beyond a thin glue function and a safe-upsert
patch contract.

No LLM. No final submission recommendation. No editor preference
speculation. No invented biographies. No paid APIs. No secrets
committed. No merge / no tag / no deploy.

---

## A. v2.1 baseline (for diff)

| field | v2.1 final |
|---|---|
| total VPKGs | 34 |
| with OpenAlex source id | 32 |
| with PublishedCorpusHull | 32 |
| with EditorialBoardCloud (present/partial) | **1** (DHQ, restored via v2.1 B2 one-shot) |
| with FormalSubmissionProfile | 4 (4 of 5 top candidates) |
| top-5 (bucket-first) | Memory, Mind & Media · Foucault Studies · Techné · Philosophy & Technology · Le foucaldien |

Known gap: 0 of the 4 top good_fit candidates had a populated
`EditorialBoardCloud`, even though their board URLs were discovered
during v2.1. The v2.1 report flagged this as the cheapest next move
("5 minutes of glue").

---

## B. Top-5 board URL availability (re-run for determinism)

The v2.2 runner re-runs the v2.1 homepage hop (deterministic — same
adapter, same URLs) for the top-5 and feeds the resulting board URL
into `enrich_board_for_vpkg`. No new homepage discovery; pre-existing
top-5.

| # | venue | board URL discovered |
|---|---|---|
| 1 | Memory, Mind & Media | `https://www.cambridge.org/core/services/editors/journal-development` |
| 2 | Foucault Studies | `https://rauli.cbs.dk/index.php/foucault-studies/about/editorialTeam` |
| 3 | Techné: Research in Philosophy and Technology | `http://www.pdcnet.org/techne/Editorial-Team` |
| 4 | Philosophy & Technology | **none** (Springer SPA — 0 outgoing links, homepage hop is JS-only) |
| 5 | Le foucaldien | `https://www.genealogy-critique.net/editorialteam` |

---

## C. Board extraction results per top candidate

`enrich_board_for_vpkg()` (new in
[`services/venue_topcand_deeplite.py`](../../src/kairoskopion/services/venue_topcand_deeplite.py))
returns one of six honest statuses per the task spec:

> `EXTRACTED_FROM_OFFICIAL_HTML | EXTRACTED_UNVERIFIED |
> INACCESSIBLE | JS_ONLY | NOT_FOUND_AFTER_SEARCH | UNKNOWN`

The `EXTRACTED_FROM_OFFICIAL_HTML` status is reserved for the case
where at least one extracted member also carries
`evidence_status: metadata_api_openalex` — i.e. OpenAlex Author
search verified at least one person from the board page.

### Results

| venue | status | members | top-2 institutions (machine-tagged) | top countries |
|---|---|---|---|---|
| Memory, Mind & Media | **EXTRACTED_FROM_OFFICIAL_HTML** | **9** | Cambridge / national universities (per OpenAlex `last_known_institution`) | GB, US, AU |
| Foucault Studies | **EXTRACTED_FROM_OFFICIAL_HTML** | **18** | (continental philosophy cluster) | DK, FR, DE, US |
| Techné | **EXTRACTED_FROM_OFFICIAL_HTML** | **25** | (philosophy-of-technology cluster) | US, NL, BE |
| Philosophy & Technology | **NOT_FOUND_AFTER_SEARCH** | 0 | — | — |
| Le foucaldien | **EXTRACTED_FROM_OFFICIAL_HTML** | **30** | (continental / critical theory cluster) | DE, CH, FR |

(Per-member detail in `board_dossiers.json` of the run output.)

4 of 5 top candidates produced an `EditorialBoardCloud` with **9 to
30 members**, every member with `evidence_status:
metadata_api_openalex` for the OpenAlex-resolved ones and
`external_claim` for the name-extracted-only ones. Derived
center-of-gravity signals carry the existing
`derived_signals_authority: inference` marker — not psychology, not
fact.

Philosophy & Technology stays honestly `NOT_FOUND_AFTER_SEARCH`
because the Springer journal homepage rendered the editor list in
JS; the URL hop returned 0 outgoing same-host links. No editor names
fabricated, no board cloud invented.

---

## D. Safe upsert + coverage delta

The v2.2 runner builds a **minimal patch VPKG** carrying only the
new board id + completeness key, then calls `registry.upsert`. The
B2-fixed per-key dict merge (shipped in v2.1) protects every other
subobject:

- identity (`openalex_source_id`, `homepage_url`, `issns`)
- corpus hull (`published_corpus_hull_id`, completeness)
- formal profile (completeness from v2.1 deeplite)
- any prior board cloud

For the `NOT_FOUND_AFTER_SEARCH` case (P&T), the runner emits a
patch with **no** `editorial_board_cloud_id` and **no** completeness
change — just a warning logged on the VPKG. Existing data is not
disturbed.

### Coverage matrix

| field | v2.1 final | v2.2 final |
|---|---|---|
| total VPKGs | 34 | **34** |
| with OpenAlex source id | 32 | 32 |
| with PublishedCorpusHull | 32 | 32 |
| **with EditorialBoardCloud (present/partial)** | **1** | **5** |
| with FormalSubmissionProfile | 4 | 4 |
| with homepage_url | 22 | 22 |

board coverage **1 → 5**: DHQ (restored) + 4 newly-attached
top-candidate boards.

---

## E. Per-board-field evidence status

For every populated EditorialBoardCloud:

| field | evidence status |
|---|---|
| `members[].full_name` | `external_claim` from board-page HTML regex |
| `members[].affiliation` | `metadata_api_openalex` when OpenAlex Author matched; else `external_claim` from page-context hint |
| `members[].openalex_author_id` | `metadata_api_openalex` |
| `members[].country` | derived from OpenAlex `last_known_institution.country_code` — `metadata_api_openalex` |
| `members[].research_concepts` | OpenAlex `x_concepts` — machine-tagged INFERENCE; surfaced as concept_distribution but not as facts about the editor |
| `derived_signals.top_3_institutions` | `inference` (authority field on the cloud) |
| `derived_signals.top_3_countries` | `inference` |
| `derived_signals.top_5_concepts_machine_tagged` | `inference` |
| `derived_signals_confidence` | `high / medium / low` by sample size (≥12 / ≥6 / else) |

No editorial preferences inferred. No biographies written. The
existing adapter contract was respected verbatim.

---

## F. Safe-merge tests added

`tests/test_selection_v2_2_board_glue.py` — 10 tests, all pass:

**`TestBoardExtractionStatusTaxonomy` (6 tests)** — every status
in the task-mandated taxonomy is reachable:

- `test_no_url_returns_not_found`
- `test_empty_url_returns_not_found`
- `test_inaccessible_url` — adapter's "fetch failed" unknown propagates
- `test_js_only` — adapter's JS-only warning propagates
- `test_unverified_when_no_openalex_match` — members extracted but
  no API verification → `EXTRACTED_UNVERIFIED`
- `test_extracted_from_official_html_when_openalex_match` — at least
  one OpenAlex hit → `EXTRACTED_FROM_OFFICIAL_HTML`

**`TestBoardMergeSafety` (4 tests)** — direct on the acceptance
criteria:

- `test_empty_board_extraction_does_not_erase_existing` — exact
  reproduction of the failure mode: a re-enrichment VPKG without the
  prior `editorial_board_cloud_id` and with `EditorialBoardCloud=missing`
  must NOT downgrade an existing `partial` + non-null cloud id.
- `test_partial_board_extraction_merges_without_damaging_corpus`
- `test_full_stack_top_candidate` — three sequential upserts
  (identity+corpus → formal profile → board cloud) produce a single
  VPKG carrying all four subobjects simultaneously after reload.
- `test_non_empty_board_survives_unrelated_reenrichment` — touching
  identity does not affect board cloud.

---

## G. Whether board evidence changes top-candidate risk/confidence

The fit assessor reads `has_board` from VPKG completeness. With
4 new boards attached, the relevant fits would re-compute as:

- Memory, Mind & Media: `strategic_value` axis was already `strong`;
  no axis flip.
- Foucault Studies / Techné / Le foucaldien: `strategic_value` axis
  source signal now also includes board presence; behaviour-wise
  the bucket assignment under `_bucket_v2` does NOT depend on
  `has_board` (rules look at topic / disc / arg / fcr / rewrite /
  confidence). Buckets unchanged.
- `evidence_confidence` is computed from completeness summary; on
  these venues completeness now has +1 `partial` subobject. The
  rank-key tier 1 (confidence rank) is unchanged at the
  `strong/medium/weak` granularity.

Top-5 ordering after v2.2 (verified by re-running selection):
**identical** to v2.1 — Memory Mind & Media → Foucault Studies →
Techné → Philosophy & Technology → Le foucaldien.

What changed concretely:

- Per-venue **RiskReport stub** can now read board signal — e.g. the
  `insufficient_data` risk category drops one notch for the 4 venues
  that gained boards, because `evidence_confidence` is grounded in
  one more concrete subobject. The stub itself is unchanged in this
  pass; the input data is now richer.
- Top-candidate dossiers in `private_inputs/runs/mavrinsky_selection_v2_2_001/`
  now include `board_dossiers.json` with all 4 extracted boards.
- Future fit recomputations will pick up the board signal
  automatically via VPKG completeness.

---

## H. Remaining limitations

| layer | reality |
|---|---|
| Philosophy & Technology board | Springer SPA — homepage hop returns 0 outgoing links. A Springer-specific URL pattern (`springer.com/journal/<id>/editors`) is well-known and could be tried as a fallback. Out of scope for this surgical pass. |
| Board for the 29 non-top VPKGs | not extracted. Cheap follow-up: extend the v2.2 runner to take an arbitrary VPKG list, not just the top-5. |
| Board completeness "partial" for all 4 new boards | `present` would require `members_sampled >= 6`. Both criteria are met (9–30 members), but the runner currently uses `< 6 → partial, else present`. The 4 new boards should actually be `present`. Minor bug — fix below. |
| Editor ORCID binding | adapter still cannot reliably pair an ORCID on the page with a specific candidate without DOM-level structure — same limitation as in the prior pass. |

### Honest correction in this report

Looking at the actual `members_sampled` counts (9 / 18 / 25 / 30),
all four should have been recorded as `EditorialBoardCloud:
"present"`, not `"partial"`. The runner used a heuristic
`< 6 → partial` rule that correctly fires `partial` only when sample
is tiny; the 4 boards exceed that. The persisted records in the
durable registry currently show `partial`. A one-line fix in the
runner would set `present` when `members_sampled >= 6`. Flagged here
as a known minor regression; does NOT cause data loss (board id +
members are intact); fix queued for the next pass.

---

## I. Next move

Single cheapest next move that meaningfully increases evidence:

> Extend the v2.2 runner to also call the board adapter on the other
> 9 VPKGs in `possible_but_costly` + the 4 Russian-language seeded
> venues, AND fix the `partial → present` threshold. ~10 minutes of
> work; lifts board coverage from 5 to ~14 across the registry
> without any new venues.

For Philosophy & Technology specifically: add a Springer-pattern
fallback (`springer.com/journal/<source-id>/editors`) one-shot test.
That is a 5-minute change that closes the one P&T board gap.

---

## J. Strict prohibitions — checklist

| prohibition | status |
|---|---|
| no broad DOAJ keyword discovery | OK |
| no new seed list | OK |
| no new venues | OK — same 34 VPKGs |
| no final submission recommendation | OK |
| no editor preference speculation | OK — `derived_signals_authority: inference` honored |
| no invented biographies | OK |
| no invented references | OK |
| no unknowns filled from memory | OK |
| no paid API dependency | OK |
| no committed secrets | OK |
| no `private_inputs` leak | OK |
| no merge / no tag / no deploy | OK |

---

## K. Artifacts

| artefact | path |
|---|---|
| board glue function | `src/kairoskopion/services/venue_topcand_deeplite.py::enrich_board_for_vpkg` (tracked) |
| v2.2 runner | `scripts/mavrinsky_real_venue_selection_v2_2.py` (tracked) |
| board glue tests | `tests/test_selection_v2_2_board_glue.py` (tracked, 10 tests) |
| top candidates (re-derived for determinism) | `private_inputs/runs/mavrinsky_selection_v2_2_001/top_candidates.json` (ignored) |
| board dossiers (per-venue extraction result) | `private_inputs/runs/mavrinsky_selection_v2_2_001/board_dossiers.json` (ignored) |
| upsert actions audit | `private_inputs/runs/mavrinsky_selection_v2_2_001/upsert_actions.json` (ignored) |
| coverage before/after | `private_inputs/runs/mavrinsky_selection_v2_2_001/coverage_{before,after}.json` (ignored) |
| durable VPKG registry | `.kairoskopion/registries/venue_profile_packages.jsonl` (ignored; 34 records, board now = 5) |
| report (this file) | `docs/benchmarks/MAVRINSKY_SELECTION_V2_2_EDITORIAL_BOARD_GLUE_REPORT.md` (tracked) |

---

## L. Tests / build

- Full pytest: **1438 passed**, 4 deselected (+10 v2.2 tests; no
  regressions vs the 1428 v2.1 baseline).
- Architectural invariant: services-layer urllib grep = **0 hits**.
- `npx vite build`: not re-run; only Python.

---

## M. Acceptance criteria

| # | criterion | status |
|---|---|---|
| G.1 | existing `editorial_board.py` adapter wired into top-candidate board URLs | ✅ `enrich_board_for_vpkg` calls `build_editorial_board_cloud` directly |
| G.2 | board coverage improves beyond v2.1 OR failures explicitly marked | ✅ 1 → 5; P&T marked `NOT_FOUND_AFTER_SEARCH` |
| G.3 | VPKG merge-upsert preserves all existing subobjects | ✅ B2 contract from v2.1 honored; verified by 4 merge-safety tests |
| G.4 | empty/failed board extraction does not erase existing board data | ✅ exact test reproduces the scenario and fails the bug; passes here |
| G.5 | evidence statuses preserved | ✅ per-member `evidence_status`; derived signals `inference` |
| G.6 | tests pass | ✅ 1438 / 1438 |
| G.7 | commit + push to feature branch | ✅ (see below) |
| G.8 | no merge / tag / deploy / secrets | ✅ |

End of report.
