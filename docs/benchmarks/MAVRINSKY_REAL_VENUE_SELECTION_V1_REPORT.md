# Mavrinsky real venue selection v1 — report

**Date:** 2026-06-14
**Branch:** `feature/venue-blockers-vfc2-corpus-board-ru`
**Run ID:** `mavrinsky_selection_v1_001`

This pass:

- audited the four-blocker slice from pass #002 against actual code;
- enriched the 15 durable VPKGs from pass #002 (ISSN → OpenAlex
  identity + per-venue corpus mining);
- built a structured PRELIMINARY Mavrinsky `ArticleModel` from the
  committed golden rubric (not from memory);
- produced a 16-axis `FitAssessment` for every VPKG in the durable
  registry;
- bucketed all 15 into `good_fit / possible_but_costly /
  sibling_manuscript / poor_fit / insufficient_data`;
- built preliminary `MismatchMap` for the top 5;
- emitted `RewritePlan / CitationPlan / RiskReport` stubs for the top 5;
- shipped a side document `docs/AUTH_AND_PROXY_API_LANDSCAPE.md`
  answering "auth-shaped TODOs + AI-aggregator proxy question".

No LLM. No broad discovery. No invented references. No editor
biographies beyond adapter-supported evidence. No merge / no tag /
no deploy.

---

## A. Acceptance audit of prior slice (pass #002)

Verified at code/file level, not on report-text:

| check | result | evidence |
|---|---|---|
| B1. `VenueProfilePackage` is real aggregate, 28 fields | **PASS** | `schema.py::VenueProfilePackage` enumerated via `dataclasses.fields` |
| B1. `VenueProfileRegistry` is real durable JSONL with by-name/ISSN/OpenAlex index + cross-session reuse | **PASS** | tests `test_venue_blockers.py::TestVPKGRegistry`; live reopen confirms 15 records |
| B1. Merge-upsert preserves subobjects, no duplicates | **PASS** | `VenueProfileRegistry.upsert` line-by-line implementation; passing test |
| B2. HTTP only in adapters layer | **PASS** | `grep urllib src/kairoskopion/services/` → 0 hits (now and after this pass) |
| B2. `test_no_network_imports_in_services` invariant | **PASS** | preserved through this pass (new `venue_profile_enricher.py` lazy-imports HTTP layer from adapters at call time) |
| B2. `abstract_inverted_index` → text reconstruction works on real responses | **PASS** | 10 corpus hulls built this pass with `abstracts_available > 0` |
| B2. Corpus stores title / year / DOI / authors / concepts / abstract | **PASS** | `works_to_article_texts` in `venue_corpus_miner.py` |
| B3. Board derived_signals carry `authority: inference` + sample-size confidence | **PASS** | `EditorialBoardCloud.derived_signals_authority='inference'` enforced in dataclass default + adapter |
| B3. ORCID/OpenAlex Author lookup carries source refs and `evidence_status` per member | **PASS** | `EditorialBoardMember.evidence_status='metadata_api_openalex'` on enrich success |
| B3. No invented biographies | **PASS** | adapter only attaches `last_known_institution` when OpenAlex returned one; otherwise UNKNOWN |
| B3. Honest partial status when only homepage_url | **PASS** | builder marks `EditorialBoardCloud: partial` if `members_sampled < 6` |
| B4. CyberLeninka article-level hits ≠ verified journal facts | **PASS** | adapter result carries `evidence_status: external_claim_cyberleninka`; new mining function carries `CYBERLENINKA_SEARCH_DERIVED` |
| B4. ВАК / eLibrary / РИНЦ remain `UNKNOWN_NOT_VERIFIED` | **PASS** | adapter `unknowns` list says so verbatim |

**Audit verdict:** prior slice accepted, no fixes needed. This pass
builds on it.

---

## B. Coverage enrichment (C1–C5)

Coverage before vs after:

| field | pass #002 | this pass |
|---|---|---|
| total VPKGs in durable registry | 15 | **15** (same set, no broad discovery) |
| with `openalex_source_id` | 3 | **13** |
| with `PublishedCorpusHull` (`present` or `partial`) | 3 | **13** |
| with `homepage_url` | 1 | **9** (auto-attached from OpenAlex Source records) |
| with `cyberleninka_source_id` | 2 | 2 (no new RU discovery in this pass) |
| `EditorialBoardCloud` `present`/`partial` | 1 | 1 (board scraping not re-run on the enriched ids — separate sprint) |
| `FormalSubmissionProfile` `present`/`partial` | 0 | 0 (extractor exists in code; not invoked on this run because no guidelines URL discovery sprint yet) |

### C1. ISSN/title → OpenAlex Sources resolver — `services/venue_profile_enricher.py`
- For each VPKG missing `openalex_source_id`:
  - tries `lookup_source_by_issn` for every ISSN it carries;
  - falls back to `search_source_by_title` and only attaches when
    the OpenAlex `display_name` matches the VPKG `canonical_name`
    case-insensitively (no silent guess);
  - if multiple title-search candidates and no exact match → marks
    `ambiguous`, attaches nothing, surfaces in VPKG `unknowns`.
- Result on run #1: **10 new `openalex_source_id` attached, 0
  ambiguous**.

### C2. Homepage discovery
- `OpenAlex Sources` record carries `homepage_url`. Resolver attaches
  it during C1 when present. **9 homepages newly attached** in this
  run.
- Guidelines / editorial-board URL discovery is **not** done here —
  that requires per-publisher heuristics out of scope. Honest
  `unknowns` left in VPKGs.

### C3. Corpus hull build
- For every VPKG now carrying an `openalex_source_id` whose
  `PublishedCorpusHull` was `missing`, the enricher runs
  `mine_venue_corpus` end-to-end:
  - up to 30 latest OpenAlex Works fetched, abstracts reconstructed;
  - `corpus_analyzer.analyze_venue_corpus` produces method/school/genre
    patterns;
  - `corpus_hull_builder.build_venue_corpus_hull` produces venue FPM;
  - `PublishedCorpusHull` records `works_fetched / abstracts_available /
    references_available / year_range_min / year_range_max`.
- Result on run #1: **10 new corpus hulls built**.

### C4. CyberLeninka corpus hull for Russian venues
- New `cyberleninka.mine_journal_articles(journal_name)` queries the
  CyberLeninka article search by journal name, filters to exact-name
  matches, returns:
  - per-article `{title, year, link, annotation}`;
  - year range;
  - top topic terms (bag-of-words from titles, RU+EN stopwords
    excluded);
  - **explicit `evidence_status: CYBERLENINKA_SEARCH_DERIVED`** —
    NOT a `corpus_observation`-grade fact;
  - explicit `unknowns` list: no abstracts, no references in this
    API tier.
- Not invoked on the 2 RU candidates in this run pending operator
  decision on whether CyberLeninka corpus signal is worth wiring
  into the auto-enrichment loop. Fixture mode and live mode both
  work; covered by tests.

### C5. Minimal `FormalSubmissionProfile` extractor
- `adapters/venue/guidelines_extractor.py::extract_formal_submission_profile`:
  - takes a guidelines URL or pre-fetched HTML;
  - extracts word_limit / abstract_word_limit / reference_style /
    article_types / language / open_access / APC / ai_policy via
    regex;
  - returns per-field `{value, evidence: external_claim_html}` plus
    explicit `UNKNOWN_NOT_FOUND` for every field absent from the page;
  - returns `access_status: js_only_or_thin / http_<code> /
    network_<class> / opened` honestly.
- **Not auto-invoked** on the 15 VPKGs because we don't yet have
  guidelines URLs for them (only `homepage_url` is in OpenAlex; the
  guidelines page is one click deeper, per-publisher). Wiring the
  homepage → guidelines hop is a follow-up sprint. The extractor
  itself works on supplied HTML — has tests.

---

## C. Mavrinsky ArticleModel (Part D of the task)

Built from `benchmarks/golden/mavrinsky_article_side_gold.md` and
committed as a dict in
`services/mavrinsky_venue_selection.py::mavrinsky_article_model()`.
Marked `_lifecycle_status: PRELIMINARY_ARTICLE_MODEL`. Persisted
per-run as `01_article_model.json`.

Fields:

- `title_working`: «Желание, виртуальность и интерфейс: к онтологии технических форм»
- `object_of_inquiry`: interface as ontological technical form in continental register;
- `central_problem`: how interface mediates technicity-of-subject under post-structuralist desire and capture;
- `core_claims` (3): desire-as-excess displaces Lacanian desire-as-lack; greedy = dispositif of capture, generous = opening; distinction is ontological not ergonomic;
- `genre: theoretical_essay`;
- `disciplinary_registers: [continental_philosophy, philosophy_of_technology, media_philosophy]`;
- `novelty_mode: concept_introduction_with_reconstruction`;
- `method_status: no_method_continental_argument`;
- `argument_form: concept_reconstruction_plus_concept_introduction`;
- `evidence_type_profile: theoretical_argument 0.85, …`;
- `tribes_present`:
  - constructive: Deleuze_Guattari, Foucault, Agamben;
  - foil: Lacan;
  - absent: Simondon, Stiegler, Latour_ANT, HCI_dark_patterns;
- `protected_core`: desire-as-excess shift; interface as dispositif/capture; greedy/generous as ontology not UX;
- `language_register`: ru + EN abstract, academic_dense, jargon_density 0.78;
- `geographic_affinity`: Russia / France-Germany tradition.

---

## D. Selection v1 — 16-axis FitAssessment over all 15 VPKGs

Axes per rubric v1 §8: `topic_fit, disciplinary_fit, genre_fit,
argument_form_fit, method_fit, novelty_mode_fit, citation_ecology_fit,
language_register_fit, formal_compliance_fit, publication_regime_fit,
rewrite_effort, citation_effort, field_core_risk, strategic_value,
evidence_confidence, unknowns_axis`.

Allowed values per axis: `strong / medium / weak / bad / unknown`.
Every axis records `evidence: article_evidence | vpkg_evidence |
corpus_observation | cyberleninka_observation | inference | unknown`.

No numeric black-box score.

### Bucket distribution after v1 run

| bucket | count |
|---|---|
| **good_fit** | 1 |
| **possible_but_costly** | 14 |
| **sibling_manuscript** | 0 |
| **poor_fit** | 0 |
| **insufficient_data** | 0 |

### Top-5 candidates

(Ranked by `field_core_risk + evidence_confidence`. These are NOT
"the right journals for Mavrinsky" — they are the top 5 by Kairoskopion
v1 evidence signal **on the existing 15 VPKGs**. Most of pass #002's
shortlist was DOAJ keyword noise, and that noise is still here; this
report is honest about it.)

| # | venue | topic | rewrite | field_core_risk | confidence | bucket |
|---|---|---|---|---|---|---|
| 1 | **Memory, Mind & Media** | medium | strong | strong | strong | good_fit |
| 2 | **Revista Textos y Contextos** | medium | strong | strong | medium | possible_but_costly |
| 3 | **Le foucaldien** | medium | strong | strong | medium | possible_but_costly |
| 4 | **Colloquy: Text, Theory, Critique** | unknown | strong | strong | medium | possible_but_costly |
| 5 | **Journal of Educational Research in Mathematics** | medium | unknown | unknown | strong | possible_but_costly |

**Honest reading:** the bucket distribution is skewed because v1
detection is biased by DOAJ keyword noise inherited from pass #002 —
shows up in *Journal of Educational Research in Mathematics* being
in the top 5. The good_fit pick (*Memory, Mind & Media*) is plausible
but still relies on shallow signal (continental token bag detection,
not corpus refs). **The known philtech canon names** (*Philosophy &
Technology*, *Techné*, *Foucault Studies*) **are not in the pool** —
pass #002 didn't discover them (DOAJ-thin coverage). The Russian
philtech canon (*Вопросы философии*, *Логос*) isn't in the
pool either because the CyberLeninka discovery in pass #002 surfaced
adjacent journals, not those two.

**Better selection requires either**:
- a one-shot operator-curated seed for these 5–8 named journals,
  then enrich-pass on them;
- or a separate sprint to discover them via OpenAlex Sources directly
  (out of scope here);
- or LLM-grade content matching (Agentum).

---

## E. MismatchMap (Part F)

For each top-5 venue, `services.mavrinsky_venue_selection.build_mismatch_map`
emits a `MismatchMap` with `{article_side, venue_side, mismatch_axis,
severity, evidence_refs, possible_actions, field_core_risk,
requires_user_acceptance}`. Output saved as `05_mismatch_maps.json`.

Common pattern across the top-5: 1 mismatch each, mostly on
`citation_ecology_fit` (article's continental canon vs venue's
unknown/different canon).

---

## F. Stubs (Part G)

Saved as `06_rewrite_plans.json`, `07_citation_plans.json`,
`08_risk_reports.json`. Each is `_lifecycle_status: STUB`.

- **RewritePlan stub**: actions tied to which axes failed in the fit;
  every action carries `protected_core_impact`;
- **CitationPlan stub**: `missing_bridge_categories` derived from
  corpus token distribution; `references_to_verify` placeholder
  reminding caller "do not fabricate" — actual references must come
  from VPKG corpus references when wired;
- **RiskReport stub**: 8 risk categories (`formal_risk, scope_risk,
  method_risk, citation_gap, ai_policy_unknowns, apc_oa_unknowns,
  field_core_loss_risk, insufficient_data`) populated per the axis
  values.

---

## G. Artifact inventory

| artefact | path | tracked? |
|---|---|---|
| article model | `private_inputs/runs/mavrinsky_selection_v1_001/01_article_model.json` | ignored |
| per-venue fits (15) | `private_inputs/runs/mavrinsky_selection_v1_001/02_fits.json` | ignored |
| shortlist buckets | `private_inputs/runs/mavrinsky_selection_v1_001/03_shortlist_buckets.json` | ignored |
| top-5 | `private_inputs/runs/mavrinsky_selection_v1_001/04_top_candidates.json` | ignored |
| mismatch maps (5) | `private_inputs/runs/mavrinsky_selection_v1_001/05_mismatch_maps.json` | ignored |
| rewrite plans (5) | `private_inputs/runs/mavrinsky_selection_v1_001/06_rewrite_plans.json` | ignored |
| citation plans (5) | `private_inputs/runs/mavrinsky_selection_v1_001/07_citation_plans.json` | ignored |
| risk reports (5) | `private_inputs/runs/mavrinsky_selection_v1_001/08_risk_reports.json` | ignored |
| enrich summary | `private_inputs/runs/mavrinsky_selection_v1_001/enrich_summary.json` | ignored |
| durable registry (post-enrichment) | `.kairoskopion/registries/venue_profile_packages.jsonl` | ignored (15 records, persists cross-session) |
| this report | `docs/benchmarks/MAVRINSKY_REAL_VENUE_SELECTION_V1_REPORT.md` | tracked |
| auth landscape side doc | `docs/AUTH_AND_PROXY_API_LANDSCAPE.md` | tracked |

---

## H. Tests / build

- `pytest tests/test_venue_blockers.py`: **19/19 passed**
- full `pytest`: **1389 passed**, 4 deselected (no regressions vs
  previous head; new modules backwards-compatible).
- `npx vite build`: clean.
- `services/` layer urllib hits: **0** (architectural invariant preserved
  — services lazy-import HTTP adapters at call time).
- `private_inputs/` and `.kairoskopion/` gitignored; nothing leaks.

---

## I. What's now reusable cross-session

A fresh `VenueProfileRegistry(storage_root='.kairoskopion')`
instantiated on a clean process reads back **all 15 VPKGs** with their
post-enrichment fields:

- 13 carry `openalex_source_id` (was 3 before enrichment);
- 13 carry `PublishedCorpusHull` references with `works_fetched ≥ 1`;
- 9 carry `homepage_url`;
- 2 carry `cyberleninka_source_id`.

A second article submitted next session that surfaces any of these
canonical_names or ISSNs will hit the by-name / by-ISSN / by-OpenAlex
index in `O(1)` and reuse the corpus hull + identity without
re-discovering. **The user's "не всё нужно искать заново" property is
mechanically guaranteed for these 15 venues from this point on.**

---

## J. What remains partial / deferred

| layer | reality | next step |
|---|---|---|
| FormalSubmissionProfile coverage | 0 / 15 | guidelines-URL discovery sprint (homepage → guidelines hop) |
| EditorialBoardCloud coverage | 1 / 15 | board-URL discovery sprint (same hop); then re-run board adapter |
| CyberLeninka corpus hulls for RU venues | 0 / 2 | wire `cyberleninka.mine_journal_articles` into enricher |
| Russian philtech canon journals (Вопросы философии, Логос, …) | not in pool | one-shot operator seed; OR a dedicated OpenAlex+CyberLeninka discovery sprint targeted at these names |
| International philtech canon (Philosophy & Technology, Techné, Foucault Studies) | not in pool | one-shot operator seed; pass #002 missed them because DOAJ-only discovery is keyword-noisy |
| Authoritative ВАК/РИНЦ status | absent | requires eLibrary auth — operator decision (see `docs/AUTH_AND_PROXY_API_LANDSCAPE.md` §3.5 + §6 row 11) |
| Scopus / WoS authority on `institutional_signals` | absent | paid auth — see `AUTH_AND_PROXY_API_LANDSCAPE.md` §3.1 / §3.2 / §6 rows 8–9 |
| Article-side LLM-grade extraction (for richer ArticleModel than the rubric-derived one) | not used here | Agentum runtime contract pending |

---

## K. Companion document

`docs/AUTH_AND_PROXY_API_LANDSCAPE.md` answers the user's broader
question about "what auth do we need on what sources, and would going
through aggregators (incl. AI aggregators like Consensus / Elicit /
SciSpace / Scite) be cheaper than going direct".

Short version of the recommendation in that doc: **wire 5 free items
right now** (OpenAlex mailto, Crossref mailto, Semantic Scholar API
key, ORCID developer credentials, CORE API key). They close ~80% of
the actual gaps from pass #002 at zero cost and ~30 minutes of
sign-up time. Defer Scopus / WoS / eLibrary auth until a concrete
case fails without them. **AI aggregators are not the right proxy
for venue-side queries** — they're useful at fit-time, not
profile-build-time, and SciSpace specifically is a competitor whose
output we should not adopt.

---

## L. No merge / no tag / no deploy

Same feature branch (`feature/venue-blockers-vfc2-corpus-board-ru`).
Single follow-up commit on top of the prior `ba14292`. Pushed.

End of report.
