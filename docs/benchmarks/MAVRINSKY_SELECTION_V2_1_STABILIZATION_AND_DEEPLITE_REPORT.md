# Mavrinsky venue selection v2.1 — stabilization + deep-lite

**Date:** 2026-06-14
**Branch:** `feature/venue-blockers-vfc2-corpus-board-ru`
**Run ID:** `mavrinsky_selection_v2_1_001`
**Prior pass:** [`MAVRINSKY_OPERATOR_SEEDED_VENUE_SELECTION_V2_REPORT.md`](MAVRINSKY_OPERATOR_SEEDED_VENUE_SELECTION_V2_REPORT.md) (commit 60e7822)

This pass DID NOT expand the pool. It:

- fixed the two named defects from v2 (bucket-first ranker, completeness
  merge regression) with reproduction tests;
- performed controlled homepage → guidelines/board/scope URL hops on
  the **top candidates only**, capped per venue;
- ran the existing FormalSubmissionProfile extractor on accessible
  guidelines pages;
- produced PublishedArticlePattern-light corpus summaries for the
  top candidates;
- re-ran selection v2.1 over the same 34 VPKGs and rebuilt the top
  candidate dossiers.

No LLM. No broad discovery. No new seed list. No final submission
recommendation. No paid APIs. No invented references / editor
preferences. No secrets. No merge / no tag / no deploy.

---

## A. v2 baseline (for diff)

From the v2 report:

| field | v2 final |
|---|---|
| total VPKGs | 34 |
| with OpenAlex source id | 32 |
| with PublishedCorpusHull | 32 |
| with EditorialBoardCloud (present/partial) | **0** (regression from v1) |
| with FormalSubmissionProfile | 0 |
| bucket distribution | 4 good_fit / 5 PBC / 0 sibling / 0 poor_fit / 25 insufficient_data |
| top-5 ranker | confidence-first (mixed buckets) |

The two named v2 defects:

1. **Ranker** sorted top-5 by `evidence_confidence` only, so a
   `possible_but_costly` venue could outrank a `good_fit` venue.
2. **Enricher upsert** overwrote the completeness dict, dropping
   `EditorialBoardCloud` from `partial` to `missing` for the one
   venue (Digital Humanities Quarterly) that had a board-cloud id —
   1 → 0 collapse.

---

## B. Fixes

### B1. Bucket-first ranker

`services/mavrinsky_venue_selection.py::rank_top_candidates` replaces
the prior inline sort in `run_selection_over_registry`. Sort key
(ascending = better):

| tier | criterion |
|---|---|
| 0 | bucket order: good_fit → possible_but_costly → sibling → poor_fit → insufficient_data |
| 1 | −evidence_confidence (strong > medium > weak > unknown) |
| 2 | −has_corpus (corpus-backed VPKGs preferred) |
| 3 | −has_formal_profile |
| 4 | −strategic_value |
| 5 | −field_core_risk preference (`strong` preservation preferred, `bad` dispreferred) |
| 6 | canonical_name (stable lexicographic tiebreaker) |

Verified by 5 regression tests in
`tests/test_selection_v2_1_fixes.py::TestBucketFirstRanker`:

- `test_good_fit_outranks_possible_but_costly` — even when the PBC
  venue has higher confidence;
- `test_high_confidence_insufficient_does_not_outrank_lower_conf_good_fit`
  — exact wording from the acceptance criterion;
- `test_sibling_separable_from_possible_but_costly` — proves sibling
  bucket is distinguishable;
- `test_within_bucket_confidence_dominates_then_corpus` — within-tier
  ordering exercised;
- `test_canonical_name_is_stable_tiebreaker` — no random sort.

### B2. Completeness merge must not downgrade existing subobjects

`services/venue_profile_registry.py::upsert` now:

- dict-typed fields (notably `completeness` and `confidence`) merge
  per-key instead of being wholesale-replaced;
- for `completeness` specifically: a new `"missing"` value never
  downgrades an existing `"present"` or `"partial"` for the same
  subobject;
- subobject id fields (`editorial_board_cloud_id`,
  `published_corpus_hull_id`, `venue_field_position_id`,
  `publication_regime_id`, `citation_expectation_profile_id`,
  `source_evidence_packet_id`) — never erased by a `None`-bearing
  upsert.

Verified by 4 regression tests in
`tests/test_selection_v2_1_fixes.py::TestUpsertPreservesSubobjects`:

- `test_completeness_present_not_downgraded_to_missing` — exact
  reproduction of the v2 board=1 → 0 collapse, now blocked;
- `test_completeness_upgrade_path_still_works` — partial → present
  upgrade still applies (not over-fixed);
- `test_new_completeness_keys_get_added` — new subobject categories
  appear when added;
- `test_subobject_ids_not_erased_by_none` — orphan subobject ids
  survive.

### B2 one-shot restoration

Beyond the prospective fix, the v2.1 runner scans every VPKG for
**orphaned subobject ids** (id present, completeness `missing`) and
restores completeness to `"partial"` for the affected key — without
re-running the adapter. This recovers state lost during v2's bug
window.

- Digital Humanities Quarterly carried `editorial_board_cloud_id =
  ebc_b176ef2366e9` but completeness `EditorialBoardCloud=missing`.
- Restoration marked it `"partial"` (we know the subobject existed;
  we cannot re-verify its original status level without re-running
  the board adapter — `"partial"` is the honest claim).

Persisted as `b2_restoration.json` in the run output.

---

## C. Controlled homepage → guidelines/board/scope URL hop

New adapter
[`adapters/venue/venue_url_hop.py`](../../src/kairoskopion/adapters/venue/venue_url_hop.py).
Scope:

- 1 homepage fetch + up to 4 follow-up fetches per venue (cap);
- **same-domain only** (publisher-internal navigation, no external
  hops);
- 15s timeout per request;
- explicit `access_status` per category (`opened`, `http_<code>`,
  `network_<class>`, `js_only`, `not_found_after_search`, `unknown`);
- absent policy never inferred as `"NO"` — always `UNKNOWN_NOT_FOUND`.

Five required categories with per-category regex bag:
`guidelines`, `submission_info`, `editorial_board`, `aims_scope`,
`policy_oa_apc`.

Verified by 8 unit + fixture tests in
`tests/test_venue_url_hop.py` (no network — fixture HTML).

### Discovery results for the v2.1 top-5

| venue | homepage status | links scanned | guidelines URL? | board URL? |
|---|---|---|---|---|
| Memory, Mind & Media | opened | 372 | ✅ Cambridge author-information | ✅ Cambridge editors page |
| Foucault Studies | opened | 26 | ✅ rauli.cbs.dk submissions | ✅ rauli.cbs.dk editorial team |
| Techné | opened | 59 | ✅ pdcnet.org submission guidelines | ✅ pdcnet.org editorial team |
| Philosophy & Technology | opened, 0 links | 0 | ❌ Springer SPA — JS-only | ❌ |
| Le foucaldien | opened | 68 | ✅ genealogy-critique.net submissions | ✅ genealogy-critique.net editorial team |

Philosophy & Technology homepage returned an opened response but with
0 outgoing same-host links — recorded honestly as `INACCESSIBLE` for
hop purposes (Springer renders that page in JS). No fabricated
guidelines URL invented.

---

## D. Minimal FormalSubmissionProfile coverage

`adapters/venue/guidelines_extractor.py` was called on the four
discovered guidelines URLs (P&T excluded — no URL to hop to).
Extracted fields per venue:

| venue | guidelines page | fields extracted |
|---|---|---|
| Memory, Mind & Media | author-information-form-faqs | `article_types`, `open_access` |
| Foucault Studies | about/submissions | `abstract_word_limit`, `reference_style`, `article_types`, `language`, `open_access` |
| Techné | Submission-Guidelines | `word_limit`, `abstract_word_limit`, `reference_style`, `article_types`, `open_access`, `ai_policy_mentioned` |
| Le foucaldien | submissions | `reference_style`, `article_types`, `open_access`, `ai_policy_mentioned` |

Every extracted field carries `evidence: external_claim_html` and a
source `source_url`. Each FSP carries `discovery_method:
homepage_link_hop` and an overall `extraction_confidence` (`medium`
when ≥3 fields, `low` otherwise). All absent fields appear in
`unknowns` as `UNKNOWN_NOT_FOUND`. No generic requirements were
inferred.

4 of 5 top-candidate VPKGs got FormalSubmissionProfile=`partial` after
this pass (the 5th = P&T, recorded as INACCESSIBLE).

---

## E. Selection v2.1 — corrected top-5

### Coverage matrix

| field | v2 final | v2.1 BEFORE | v2.1 AFTER reenrich+restore | v2.1 FINAL (post-deeplite) |
|---|---|---|---|---|
| total VPKGs | 34 | 34 | 34 | **34** |
| with OpenAlex source id | 32 | 32 | 32 | **32** |
| with PublishedCorpusHull | 32 | 32 | 32 | **32** |
| with EditorialBoardCloud | 0 | 0 | **1** (B2 restoration) | **1** |
| with FormalSubmissionProfile | 0 | 0 | 0 | **4** (deeplite extraction) |
| with homepage_url | 22 | 22 | 22 | **22** |
| with cyberleninka_source_id | 2 | 2 | 2 | **2** |

### Buckets v2.1 (calibrated rules unchanged from v2)

`good_fit: 4 · possible_but_costly: 5 · sibling_manuscript: 0 ·
poor_fit: 0 · insufficient_data: 25` (total = 34).

Bucket counts are unchanged from v2 (same calibrated `_bucket_v2`).
What changed is the **top-5 ordering**, which is now bucket-consistent.

### Top-5 (bucket-first ranker, B1)

| # | venue | bucket | topic | rewrite | fcr | confidence |
|---|---|---|---|---|---|---|
| 1 | Memory, Mind & Media | **good_fit** | medium | strong | strong | strong |
| 2 | Foucault Studies | **good_fit** | medium | strong | strong | medium |
| 3 | Techné: Research in Philosophy and Technology | **good_fit** | medium | strong | strong | medium |
| 4 | Philosophy & Technology | **good_fit** | medium | strong | strong | medium |
| 5 | Le foucaldien | possible_but_costly | weak | strong | strong | strong |

All four `good_fit` venues now rank above any `possible_but_costly`,
which directly satisfies the acceptance criterion I.5.

The remaining `possible_but_costly` set (positions 6+) is unchanged
from v2: Revista Textos y Contextos, Логос, Философские науки, RJPS.

---

## F. Top-candidate dossier summaries

### MismatchMap (E1)

Per-venue mismatch count (full data in
`05_mismatch_maps.json`):

| venue | # mismatches | dominant axis |
|---|---|---|
| Memory, Mind & Media | 0 | — (continental-friendly corpus, language fit) |
| Foucault Studies | 0 | — (Foucault canon native) |
| Techné | 0 | — (philtech canon native) |
| Philosophy & Technology | 0 | — (philtech canon native) |
| Le foucaldien | 1 | language_register_fit (RU article → EN/FR venue) |

Every mismatch carries `evidence_refs`, `severity`, `possible_actions`,
`field_core_risk`, `requires_user_acceptance`, and `confidence` (via
the underlying axis evidence_source field).

### RewritePlan stub (E2)

Per `06_rewrite_plans.json`, each top-5 venue has actions targeting:
title/abstract positioning, intro framing, citation bridge,
method-status clarification. Each action carries
`protected_core_impact ∈ {minimal, low, high}` so a future
user-acceptance step can detect protected-core-touching changes.

### CitationPlan stub (E3)

Per `07_citation_plans.json`:

- bridge categories named only when corpus token distribution
  supports it (philtech for Techné/P&T, foucauldian for Foucault
  Studies / Le foucaldien);
- `likely_anchors` are CATEGORY NAMES, not specific bibliographic
  references — no DOI / author tuple invented;
- `references_to_verify` carries the explicit
  > "exact references must come from VPKG corpus reference data —
  > not yet wired (deferred); do not fabricate"
  reminder;
- `dangerous_padding_warnings` flags decorative citing.

### RiskReport stub (E4)

Per `08_risk_reports.json`, eight risk categories per venue:
`formal_risk`, `scope_risk`, `method_risk`, `citation_gap`,
`ai_policy_unknowns`, `apc_oa_unknowns`, `field_core_loss_risk`,
`insufficient_data`. Each carries `level ∈ {strong, medium, weak, bad,
unknown}` derived from the corresponding axis, plus a `note` that
quotes the axis evidence.

For the four venues where FormalSubmissionProfile was extracted, the
`ai_policy_unknowns` and `apc_oa_unknowns` risk reports already
benefit — e.g. Techné's `ai_policy_mentioned=True` was caught by the
extractor.

### Corpus pattern light summary (F)

`10_corpus_pattern_summaries.json` per top-5:

| venue | works | abstracts | top terms (top-5) |
|---|---|---|---|
| Memory, Mind & Media | 25 | 25 | memory · collective · anxiety · media · social |
| Foucault Studies | 25 | 13 | foucault · critique · critical · michel · criticism |
| Techné | 25 | 9 | technology · philosophy · technological · theory · media |
| Philosophy & Technology | 25 | 18 | reply · beyond · philosophy · technology · epistemic |
| Le foucaldien | 25 | 20 | foucault · truth · savoir · lieux · michel |

Each summary also records `dominant_concepts` (OpenAlex concept ids
with counts), `article_type_hints`, `method_token_density`,
`novelty_claim_hints`, `reference_count_stats`, and
`evidence_status: openalex_corpus_observation`. Every venue has
`_lifecycle_status: PRELIMINARY` (none were under-sampled).

The corpus token distributions confirm that the v2.1 top-5 are
the canonical continental / philtech / media-philosophy venues for a
Mavrinsky-class article. No HCI noise survived; no DOAJ-keyword
educational-mathematics venues in the top.

---

## G. What remains partial / next cheapest move

| layer | reality after v2.1 | next cheapest move |
|---|---|---|
| EditorialBoardCloud population on top candidates | board URLs discovered for 4 of 5; adapter scrape NOT re-run on them in this pass | run the existing `editorial_board.py` adapter on the discovered URLs (no new code; just wire it into the deeplite step) |
| FormalSubmissionProfile coverage | 4 of 34 venues (4 of 5 top candidates) | extend hop to non-top VPKGs — cheap; just remove the top-N gate in the runner |
| Philosophy & Technology guidelines | inaccessible (Springer SPA renders in JS) | a Springer-specific URL pattern (springer.com/journal/xxxxx/submission-guidelines) is well-known and could be tried as a fallback — small effort |
| Bucket distribution still 4 / 5 / 0 / 0 / 25 | no `sibling_manuscript` or `poor_fit` fired this run | the seed pool does not contain HCI venues; either add a couple of HCI canon names (e.g. CHI Letters, TOCHI) to exercise the rules in the real pool, or accept the result is honest given pool composition |
| 1 OpenAlex ISSN failure (`1447-0950`) | pre-existing VPKG that the resolver could not match via ISSN | title-only fallback retry — small task |
| corpus references not yet flowing into CitationPlan stubs | OpenAlex `referenced_works` aren't surfaced in the stub | wire `corpus_pattern_light_summary` data into stub_citation_plan — small task |
| `EditorialBoardCloud` adapter still gated by board-URL discovery | URLs now discovered for 4 of 5 top — adapter not yet wired | one-line extension in deeplite to call the existing board adapter |

**Single cheapest next move that actually changes evidence quality:**

> Wire `editorial_board.py` adapter onto the 4 board URLs discovered
> in this pass. Existing adapter + existing service + 5 minutes of
> glue. Lifts top-candidate EditorialBoardCloud completeness from 0
> (4 unattached URLs) to 4 partial in one pass, and unblocks
> `Editorial board's recent publications match article canon?` for
> the Mavrinsky case.

---

## H. Tests / build

- Full pytest: **1428 passed**, 4 deselected (+17 vs the 1411 v2
  baseline; no regressions).
- New file `tests/test_selection_v2_1_fixes.py`: 9 tests, all pass.
- New file `tests/test_venue_url_hop.py`: 8 tests, all pass (no
  network — fixture HTML).
- Architectural invariant: services-layer urllib grep = **0 hits**
  (URL hop adapter lives in `adapters/venue/`; deeplite service
  lazy-imports it).
- `npx vite build`: not re-run; only Python code changed in this pass.

---

## I. Artifacts

| artefact | path |
|---|---|
| ranker | `src/kairoskopion/services/mavrinsky_venue_selection.py::rank_top_candidates` (tracked) |
| upsert merge fix | `src/kairoskopion/services/venue_profile_registry.py::upsert` (tracked) |
| URL hop adapter | `src/kairoskopion/adapters/venue/venue_url_hop.py` (tracked) |
| deeplite service | `src/kairoskopion/services/venue_topcand_deeplite.py` (tracked) |
| v2.1 runner | `scripts/mavrinsky_real_venue_selection_v2_1.py` (tracked) |
| coverage before/after/final | `private_inputs/runs/mavrinsky_selection_v2_1_001/coverage_{before,after,final}.json` (ignored) |
| B2 restoration audit | `private_inputs/runs/mavrinsky_selection_v2_1_001/b2_restoration.json` (ignored) |
| re-enrich summary | `private_inputs/runs/mavrinsky_selection_v2_1_001/reenrich_summary.json` (ignored) |
| article model / fits / buckets / top / dossiers | `private_inputs/runs/mavrinsky_selection_v2_1_001/{01..08}_*.json` (ignored) |
| discovery dossiers | `private_inputs/runs/mavrinsky_selection_v2_1_001/09_discovery_dossiers.json` (ignored) |
| corpus pattern summaries | `private_inputs/runs/mavrinsky_selection_v2_1_001/10_corpus_pattern_summaries.json` (ignored) |
| durable VPKG registry | `.kairoskopion/registries/venue_profile_packages.jsonl` (ignored; 34 records, board=1 restored, formal=4 attached) |
| tests | `tests/test_selection_v2_1_fixes.py`, `tests/test_venue_url_hop.py` (tracked) |
| report (this file) | `docs/benchmarks/MAVRINSKY_SELECTION_V2_1_STABILIZATION_AND_DEEPLITE_REPORT.md` (tracked) |

---

## J. Strict prohibitions — checklist

| prohibition | status |
|---|---|
| no broad DOAJ keyword discovery | OK — no DOAJ call this pass |
| no new all-journals expansion | OK — pool unchanged at 34 |
| no new seed list | OK |
| no final submission recommendation | OK — top-5 is shortlist + dossiers |
| no fake Q1/Q2 claims | OK |
| no invented editor preferences | OK — board URL discovered but adapter not re-run |
| no invented references | OK — citation stubs name CATEGORIES only |
| no unknowns filled from memory | OK |
| no paid API dependency | OK |
| no committed secrets | OK — env-only config |
| no `private_inputs` leak | OK |
| no merge / no tag / no deploy | OK |

---

## K. Acceptance criteria

| # | criterion | status |
|---|---|---|
| 1 | Ranker sorts by bucket before confidence + tests prove it | ✅ `rank_top_candidates` + 5 regression tests |
| 2 | EditorialBoardCloud / VPKG merge-upsert no longer erases existing subobjects + tests prove it | ✅ `upsert` per-key merge + 4 regression tests; board=1 restored |
| 3 | Controlled URL discovery improves guidelines/board/formal profile coverage OR explicitly documents inaccessible cases | ✅ 4 of 5 top venues hopped successfully; P&T marked inaccessible |
| 4 | Selection v2.1 reruns over the same 34 VPKGs | ✅ 34 fits, 34 = sum(buckets) |
| 5 | Corrected top candidates are bucket-consistent | ✅ 4 good_fit then 1 PBC; no PBC outranks good_fit |
| 6 | Top candidates have MismatchMap + Rewrite/Citation/Risk stubs | ✅ files 05–08 in run dir |
| 7 | Corpus pattern light summaries exist for top candidates with enough data | ✅ all 5 = PRELIMINARY; none INSUFFICIENT_CORPUS_FOR_PATTERN |
| 8 | All outputs preserve evidence status and unknowns | ✅ FSP `evidence: external_claim_html`; corpus pattern `openalex_corpus_observation`; mismatch `evidence_refs`; absent fields `UNKNOWN_NOT_FOUND` |
| 9 | Tests pass | ✅ 1428 / 1428 |
| 10 | Commit + push to feature branch | ✅ (see below) |
| 11 | No merge / tag / deploy / secrets | ✅ |

End of report.
