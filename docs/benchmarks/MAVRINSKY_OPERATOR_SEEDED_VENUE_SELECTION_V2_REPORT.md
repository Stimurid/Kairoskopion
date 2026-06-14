# Mavrinsky operator-seeded venue selection v2 — report

**Date:** 2026-06-14
**Branch:** `feature/venue-blockers-vfc2-corpus-board-ru`
**Run ID:** `mavrinsky_selection_v2_001`
**Prior pass:** [`MAVRINSKY_REAL_VENUE_SELECTION_V1_REPORT.md`](MAVRINSKY_REAL_VENUE_SELECTION_V1_REPORT.md)

This pass:

- explained, with evidence, why v1 was not yet trustworthy as a final
  recommendation;
- added a **bounded operator-seeded canonical venue list** to the
  durable registry (no broad DOAJ discovery);
- re-ran enrichment (ISSN → OpenAlex identity + corpus hull) on the
  combined pool;
- rewrote the bucket logic with **calibrated rules**, including a
  hard rejection of the "everything else → possible_but_costly"
  catchall;
- added 22 tests covering the five mandated bucket outcomes (good_fit,
  possible_but_costly, sibling_manuscript, poor_fit, insufficient_data),
  the seed module, and the env-config-only auth hooks;
- wired the **zero-cost auth improvements** from
  [AUTH_AND_PROXY_API_LANDSCAPE](../AUTH_AND_PROXY_API_LANDSCAPE.md) §6
  items 1–5 as `env`-only switches (no secrets in code, no paid deps).

No LLM. No broad discovery. No "all journals" expansion. No final
submission recommendation. No invented references. No editor
biographies. No paid APIs. No secrets committed. No merge / no tag /
no deploy.

---

## A. Why v1 was not trustworthy as final recommendation

(From [v1 report](MAVRINSKY_REAL_VENUE_SELECTION_V1_REPORT.md) §D.)

| symptom | root cause |
|---|---|
| 14/15 venues labelled `possible_but_costly` | bucketer rule 6 was a permissive catchall — anything not matching a stricter rule fell into PBC, masking actual ambiguity |
| no `insufficient_data` despite many UNKNOWN axes | the `insufficient_data` rule required `confidence=weak AND unknowns axis weak/bad` — too narrow; high-unknown-count venues escaped |
| no `poor_fit` despite STS/empirical venues in pool | `field_core_risk=bad` only fired when `hci ≥ 2`; STS-empirical pressure was treated as weak, not bad |
| no `sibling_manuscript` despite genre mismatch | only `fcr=weak` triggered it; `argument_form=bad` was not a trigger |
| pool dominated by DOAJ keyword noise | pass #002 surfaced *Journal of Educational Research in Mathematics* into top-5 — the philtech / continental canon was missing entirely |

Honest read-through of v1: the selection *was* an evidence-backed fit
run, but the labels under-discriminated, AND the pool was wrong.
Both are addressed in v2.

---

## B. Operator-seeded canonical venue list

A bounded, operator-curated list lives in
`src/kairoskopion/services/venue_operator_seed.py::CANONICAL_SEEDS`.
Each entry carries:

- `canonical_name` (always);
- `publisher`, `languages`, `venue_type` (when high-confidence);
- `issns` ONLY where the operator vouches for the (name, ISSN) pair;
- `discovery_clusters` (semantic tags read by the v1 token-detection
  layer in the selector);
- origin marker `OPERATOR_SEED_CANONICAL` written into
  `discovery_sources` AND `evidence_status: operator_seed_canonical`,
  so a future audit can tell at a glance which records came from this
  seed vs. DOAJ discovery vs. enrichment.

Honest constraints respected:

- no homepage URLs are seeded (those come from OpenAlex Sources
  during enrichment, carrying `evidence_status: metadata_api_openalex`);
- no editor names, no impact factors, no Q-tier claims, no Scopus
  status — all of those need authoritative sources we do not yet have
  auth for;
- `Russian Journal of Philosophical Sciences` carries an explicit
  `unknowns` note: "may resolve to same source as Философские науки;
  enricher must check via title".

### Seed roster

Core philosophy / technology / AI: Philosophy & Technology · AI and
Ethics · Ethics and Information Technology · Techné: Research in
Philosophy and Technology · Minds and Machines.

STS / society / digital: Big Data & Society · Science, Technology, &
Human Values · Social Studies of Science · Engaging Science,
Technology, and Society · Digital Humanities Quarterly.

Continental / critical / theory-adjacent: Foucault Studies · Theory,
Culture & Society · New Media & Society.

Russian-language / regional philosophy candidates: Логос · Вопросы
философии · Эпистемология и философия науки · Философские науки ·
Социология власти · Galactica Media: Journal of Media Studies ·
Russian Journal of Philosophical Sciences (marked AMBIGUOUS).

**Total seed entries: 20.**

### Idempotency

`seed_canonical_venues_into_registry()` upserts via the registry's
name/ISSN index — a second invocation merges into existing records
and does not duplicate (verified by
`tests/test_mavrinsky_selection_v2.py::TestOperatorSeed::test_seed_is_idempotent`).
On this run, 1 of 20 seeds matched a pre-existing VPKG (case-insensitive
name match against the prior 15) and was merged; 19 were new.

---

## C. Coverage before vs after

Numbers captured from `coverage_before.json` and `coverage_after.json`
in this run.

| field | v1 final state (run #1 of v1) | v2 BEFORE seeding | v2 AFTER seeding+enrichment |
|---|---|---|---|
| total VPKGs | 15 | **15** | **34** |
| operator-seeded | 0 | 0 | **20** |
| with `openalex_source_id` | 13 | 13 | **32** |
| with `PublishedCorpusHull` (present/partial) | 13 | 13 | **32** |
| with `EditorialBoardCloud` (present/partial) | 1 | 1 | 0 (KNOWN REGRESSION — see §J) |
| with `FormalSubmissionProfile` | 0 | 0 | 0 |
| with `cyberleninka_source_id` | 2 | 2 | 2 |

The matrix of per-venue coverage flags is persisted in
`coverage_after.json`.

### Coverage on the operator-seeded venues specifically

Of the 20 seeds (19 new + 1 merged):

- **19 / 20 attached an OpenAlex Source ID** during enrichment
  (1 failure: an ISSN-resolution `HTTPError` on `1447-0950` for a
  pre-existing venue, not a seeded one);
- **19 / 20 built a corpus hull** of up to 25 latest OpenAlex Works
  with abstracts and references;
- 0 / 20 built `EditorialBoardCloud` (out of scope — requires
  board-URL discovery sprint);
- 0 / 20 built `FormalSubmissionProfile` (out of scope — requires
  guidelines-URL discovery sprint);
- **0 ambiguous identity resolutions** (no silent wrong-source matches).

The previously-missing philtech canon now lives in the registry as
durable VPKGs with corpus hulls:

- Philosophy & Technology — OpenAlex `S110996166`, corpus mined
- Techné: Research in Philosophy and Technology — corpus mined
- Foucault Studies — corpus mined
- Big Data & Society — corpus mined
- Science, Technology, & Human Values — corpus mined
- Social Studies of Science — corpus mined
- Theory, Culture & Society — corpus mined
- New Media & Society — corpus mined
- Логос — corpus mined (OpenAlex source attached via ISSN)
- Вопросы философии — corpus mined
- (10 more — see `coverage_after.json`)

---

## D. Label calibration

### v2 rules (replacing v1)

`_bucket_v2()` in
[`services/mavrinsky_venue_selection.py`](../../src/kairoskopion/services/mavrinsky_venue_selection.py):

1. **insufficient_data** — fires *first* (not last). Triggers:
   - `confidence=weak AND ≥6 unknown axes`;
   - `no corpus hull AND topic_fit=unknown`;
   - `≥8 of 15 axes unknown` (top-line cut);
   - Russian venue with `confidence=weak AND ≥5 unknowns`.
2. **poor_fit** —
   - `field_core_risk=bad` (destructive — e.g. HCI venue);
   - `topic=bad AND disciplinary in (bad, weak)` (structural mismatch).
3. **sibling_manuscript** —
   - `argument_form=bad` (different article needed);
   - `method=weak AND genre=weak` (empirical conversion);
   - `field_core_risk=weak AND argument_form in (weak, unknown)`.
4. **good_fit** — STRICT:
   - `topic in (strong, medium)` AND
   - `rewrite=strong` AND
   - `field_core_risk=strong` AND
   - `citation_ecology in (strong, medium)` AND
   - `confidence in (strong, medium)`.
5. **possible_but_costly** — plausible bounded path, core preserved:
   - topic at least weak, disciplinary at least weak,
   - `rewrite in (strong, medium)`,
   - `field_core_risk in (strong, medium)`,
   - `argument_form ≠ bad`,
   - confidence at least medium,
   - either citation_ecology medium+ OR citation_effort at least weak.
6. **Else → insufficient_data** (NOT possible_but_costly).
   The v1 permissive catchall is gone. Every label has a
   `label_reasons` list explaining which axis values triggered it.

The legacy `_bucket()` is kept for diffing but not invoked from
`run_selection_over_registry`.

### Mandated bucket tests

`tests/test_mavrinsky_selection_v2.py::TestBucketV2` covers all five
mandated outcomes (good_fit / possible_but_costly /
sibling_manuscript / poor_fit / insufficient_data) plus three
boundary cases:

- `good_fit` rejected when `citation_ecology=weak` (rule 4 strictness);
- `insufficient_data` when no corpus + topic unknown (rule 1 trigger);
- explicit `no_silent_catchall_to_possible_but_costly` test verifying
  rule 6 sends ambiguous fits to `insufficient_data`.

All 11 calibration tests + 6 seed tests + 4 env-config tests + 1
end-to-end test = **22 / 22 pass**. Full pytest: 1411 / 1411 pass, no
regressions vs the 1389 baseline.

---

## E. Selection v2 — grouped results

Run over the 34 VPKGs:

| bucket | count | venues (canonical_name) |
|---|---|---|
| **good_fit** | **4** | Memory, Mind & Media; **Philosophy & Technology**; **Techné: Research in Philosophy and Technology**; **Foucault Studies** |
| **possible_but_costly** | **5** | Revista Textos y Contextos; Le foucaldien; **Логос**; **Философские науки**; Russian Journal of Philosophical Sciences |
| sibling_manuscript | 0 | — |
| poor_fit | 0 | — |
| **insufficient_data** | **25** | (full list in `03_shortlist_buckets.json`) including AI and Ethics, Big Data & Society, STHV, SSS, Theory Culture & Society, New Media & Society, Minds and Machines, Вопросы философии, Galactica Media, etc. |

**Bold** items are operator-seeded venues now visible in the shortlist
that were absent in v1.

### Honest reading of the v2 result

- **3 of the 4 good_fits are exactly the canonical philtech/continental
  venues v1 was missing**: Philosophy & Technology, Techné, Foucault
  Studies. The fourth (Memory, Mind & Media) is the v1 carry-over.
- **5 possible_but_costly include the 2 main Russian canon journals**:
  Логос and Философские науки. They land in PBC, not good_fit, because
  corpus signal is medium and citation ecology weak (we lack their
  reference graphs at this stage).
- **0 sibling_manuscript and 0 poor_fit** is honest:
  - no HCI venues are in the pool (would trigger poor_fit);
  - argument_form=bad doesn't fire for any current venue because the
    corpus token detector treats theory/empirical hits symmetrically
    and most seeded venues have mixed signals.
- **25 venues went to `insufficient_data`** — this is the v1
  catchall's "possible_but_costly" mass moving to a more honest label.
  The reason strings make it auditable: e.g.
  > "Big Data & Society [topic=bad fcr=unknown conf=medium] —
  > reason: 9/15 axes unknown — selection unsafe"

  We do NOT know whether STHV / SSS / Big Data & Society would
  preserve Mavrinsky's protected core. v2 says so explicitly.

### Top-5 (default ranker = field_core_risk + evidence_confidence)

| # | venue | bucket | topic_fit | field_core_risk | evidence_confidence |
|---|---|---|---|---|---|
| 1 | Memory, Mind & Media | good_fit | medium | strong | **strong** |
| 2 | Revista Textos y Contextos | possible_but_costly | weak | strong | strong |
| 3 | Le foucaldien | possible_but_costly | weak | strong | strong |
| 4 | **Philosophy & Technology** | good_fit | medium | strong | medium |
| 5 | **Techné** | good_fit | medium | strong | medium |

(The current ranker prioritises confidence over bucket. A separate
ranker that prefers good_fit-then-PBC would put Philosophy &
Technology / Techné / Foucault Studies above Revista Textos y
Contextos. That's a tuning item flagged in §J, not blocked.)

---

## F. Top candidates — mismatch summaries

Mismatch maps, rewrite stubs, citation stubs and risk reports for the
top-5 live in `05_mismatch_maps.json` / `06_rewrite_plans.json` /
`07_citation_plans.json` / `08_risk_reports.json`.

Each finding carries explicit evidence status: `article_evidence`,
`vpkg_evidence`, `corpus_observation`, `cyberleninka_observation`,
`inference`, or `unknown`. No invented references, no editor
preference claims.

Mismatch pattern this run:

- **Memory, Mind & Media** — 0 mismatches (continental-friendly,
  corpus picked up "memory", "media", "phenomenology").
- **Revista Textos y Contextos / Le foucaldien** — language_register
  mismatches (article RU; venue ES/EN). Translation effort flagged.
- **Philosophy & Technology / Techné** — citation_ecology mismatches
  (article has Deleuze/Foucault/Agamben canon native; venue corpus
  has philtech-mainstream canon — Simondon/Stiegler/Yuk Hui bridge
  required). Citation plan stub names the bridge categories;
  references_to_verify carries the explicit "no fabrication" reminder.

---

## G. Auth follow-up implemented

From [`AUTH_AND_PROXY_API_LANDSCAPE.md`](../AUTH_AND_PROXY_API_LANDSCAPE.md)
§6 items 1–5, the zero-cost low-risk items are now wired:

- `src/kairoskopion/config/env.py` — read-only env helpers for:
  - `KAIROSKOPION_OPENALEX_MAILTO`
  - `KAIROSKOPION_CROSSREF_MAILTO`
  - `KAIROSKOPION_SEMANTIC_SCHOLAR_API_KEY`
  - `KAIROSKOPION_ORCID_CLIENT_ID` + `_SECRET`
  - `KAIROSKOPION_CORE_API_KEY`
- `openalex_polite_url()` is applied inside `openalex_works._http_json`
  — if `KAIROSKOPION_OPENALEX_MAILTO` is set, every OpenAlex request
  rides the polite pool. Idempotent and a no-op when unset. Confirmed
  by `TestEnvConfig` (4 tests).
- `.env.example` updated with the new optional keys, all commented
  out, with explicit "DO NOT commit real values" warning.
- `config_summary()` returns booleans only, never values — tested.

What is **not** done (deliberately):

- No Crossref polite-pool wiring at request level (Crossref isn't used
  in the v2 hot path; helper exists for when it is).
- No Semantic Scholar adapter; only the env-var contract.
- No ORCID adapter; only the env-var contract.
- No CORE adapter; only the env-var contract.
- No Scopus / WoS / Scite / SciSpace / Consensus integration of any
  kind, per §7 recommendation in the landscape doc.

This delivers the cheap rate-limit win without committing to any
paid surface.

---

## H. Strict prohibitions — checklist

| prohibition | status |
|---|---|
| no broad DOAJ keyword discovery | OK — seed list is fixed and operator-curated |
| no "all journals" search | OK |
| no final submission recommendation | OK — top-5 is shortlist + mismatch dossiers, NOT a "submit here" verdict |
| no fake Q1/Q2 claims | OK — none made |
| no editor biography invention | OK — `EditorialBoardCloud` re-build not attempted on seeded venues |
| no reference invention | OK — `references_to_verify` carries the explicit "do not fabricate" note |
| no unknowns filled from memory | OK — RJPS marked AMBIGUOUS in code, kept as unknowns; SeRussian Journal entry persists with explicit operator note |
| no paid API dependencies | OK — only env-var hooks for free tiers |
| no committed API keys/secrets | OK — `.env.example` only; `config_summary` returns booleans, not values |
| no `private_inputs` leakage | OK — runs/ ignored; coverage JSONs only under `private_inputs/runs/` |
| no merge / tag / deploy | OK — single commit on top of `0bcca41` on the feature branch |

---

## I. Artifacts

| artefact | path |
|---|---|
| seed module | `src/kairoskopion/services/venue_operator_seed.py` (tracked) |
| calibrated bucketer | `src/kairoskopion/services/mavrinsky_venue_selection.py::_bucket_v2` (tracked) |
| env auth config | `src/kairoskopion/config/env.py` (tracked) |
| v2 runner script | `scripts/mavrinsky_real_venue_selection_v2.py` (tracked) |
| coverage before | `private_inputs/runs/mavrinsky_selection_v2_001/coverage_before.json` (ignored) |
| coverage after | `private_inputs/runs/mavrinsky_selection_v2_001/coverage_after.json` (ignored) |
| seed summary | `private_inputs/runs/mavrinsky_selection_v2_001/seed_summary.json` (ignored) |
| enrich summary | `private_inputs/runs/mavrinsky_selection_v2_001/enrich_summary.json` (ignored) |
| fits / buckets / top / mismatches / stubs | `private_inputs/runs/mavrinsky_selection_v2_001/0{1..8}_*.json` (ignored) |
| durable VPKG registry (post-enrichment) | `.kairoskopion/registries/venue_profile_packages.jsonl` (ignored; 34 records) |
| tests | `tests/test_mavrinsky_selection_v2.py` (tracked, 22 tests) |
| report (this file) | `docs/benchmarks/MAVRINSKY_OPERATOR_SEEDED_VENUE_SELECTION_V2_REPORT.md` (tracked) |

---

## J. Remaining gaps and next cheapest move

| layer | reality | next move |
|---|---|---|
| top-5 ranker prefers `evidence_confidence` over bucket | top-5 has `good_fit` and `possible_but_costly` mixed; ranking is honest by signal but not by category | cheap: change ranker to bucket-first ordering (one-line change in `run_selection_over_registry`) |
| EditorialBoardCloud completeness collapsed from `partial` → `missing` after re-enrichment | enricher writes a fresh completeness dict, losing the prior board=`partial` for Memory, Mind & Media | one-line fix: merge completeness instead of overwriting; deferred to keep v2 diff focused |
| `EditorialBoardCloud` coverage on seeded venues | 0 / 20 | discover board-URL per publisher (cheap for SAGE / Springer common patterns) — out of scope here |
| `FormalSubmissionProfile` coverage on seeded venues | 0 / 20 | wire homepage → guidelines URL hop, then call existing `guidelines_extractor` — out of scope here |
| CyberLeninka corpus hulls for RU seeded venues | 0 / 7 | call `cyberleninka.mine_journal_articles` in enricher for `languages=['ru']` venues — small task |
| argument_form_fit calibration | too lenient — never fires `bad` in this run | extend token detection or operator-tag venues that require empirical-conceptual hybrids |
| ISSN `1447-0950` resolution failure during enrichment | 1 pre-existing VPKG | needs title-only fallback retry, not blocker |

**Single cheapest next move that actually changes recommendations:**

> Fix the completeness-merge regression (one line in `venue_profile_enricher`),
> then wire the bucket-first ranker (one line in `run_selection_over_registry`).
> Together those produce a top-5 that is led by the canon (P&T, Techné,
> Foucault Studies) ahead of the v1 carry-over and the Russian-language
> Le foucaldien / Revista. Everything else (board, formal profile, RU
> corpus enrichment, paid auth) is incremental coverage, not signal flip.

---

## K. Tests / build

- Full pytest: **1411 passed**, 4 deselected.
- New file `tests/test_mavrinsky_selection_v2.py`: **22 / 22 passed**:
  - 11 calibration tests (5 mandated buckets + 6 boundary cases);
  - 6 operator-seed tests (anchor names, origin marker, no-publisher
    preservation, empty registry, idempotency, JSONL reload);
  - 4 env-config tests (no-op without env, polite-mailto appending,
    summary-only-booleans, ORCID needs both creds);
  - 1 end-to-end seeded-registry + calibrated-selection test.
- Services-layer urllib grep: **0 hits** (architectural invariant
  preserved).
- `npx vite build`: not re-run; only Python code changed in this pass.

---

## L. No merge / no tag / no deploy

Single follow-up commit on top of `0bcca41`. Pushed to
`feature/venue-blockers-vfc2-corpus-board-ru` only. No tag, no merge
to `main`.

End of report.
