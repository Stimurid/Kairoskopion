# Venue source layer map — operational rubric

**Status:** golden rubric. Operational complement to
[docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md](../../docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md)
(canon).

This file answers one question: **for each FPM axis of a venue
envelope, which source category (A–J) is authoritative, which are
corroborating, which are weak / forbidden?**

It does NOT redefine the canon — it operationalises it for the
runtime, the scorer, and the human reviewer. If this file disagrees
with the canon, the canon wins.

---

## 0. Inputs

- Funnel layers 1–8: canon §1.
- Source categories A–J: canon §3 (A = journal site, B = publisher, C
  = indexers, D = corpus, E = editorial board, F = authors-of-corpus,
  G = OpenAlex/Crossref/Scholar/SemanticScholar/OpenCitations, H =
  full-text resolvers, I = CFP/society channels, J = tacit signals).
- Authority levels (canon §3 + SOURCE_ADAPTER_AUTHORITY_CONTRACT.md):
  `formal_page`, `official_claim`, `vendor_policy`,
  `registry_card`, `metadata_api`, `corpus_observation`,
  `external_claim`, `inference`, `tacit_signal`,
  `UNKNOWN_NOT_VERIFIED`.

---

## 1. Authoritative-source matrix per FPM axis

Each axis of `venue_field_position` / `venue_envelope`. **One**
authoritative source per axis. Others corroborate or are advisory.

| FPM axis | Authoritative | Corroborating | Weak / advisory only |
|---|---|---|---|
| `discipline_envelope` | **D** corpus topic distribution (`corpus_observation`) | C OpenAlex Sources concepts, C DOAJ subject classification | A scope claim (`official_claim`), I CFP topics |
| `school_envelope` | **E** editor publications (school commitments) + **D** top-cited authors in corpus refs | G OpenCitations cited-author distribution | A scope, B publisher portfolio |
| `argument_move_envelope` | **D** structural analysis of 20–50 articles (`corpus_observation`) | A declared article_types in guidelines (`formal_page`) | B platform article_types (publisher-level) |
| `evidence_type_envelope` | **D** corpus method classification | A method-section requirement (`formal_page`) | A scope |
| `method_envelope` (requires_explicit_method, accepted/rejected method families) | **A** author guidelines (`formal_page`) | D corpus reality check (does the corpus match what guidelines demand?) | B publisher rules |
| `genre_envelope` / `language_register` envelope | **A** guidelines (word count, structure, language) (`formal_page`) | D actual length / register distribution in corpus | B template requirements |
| `citation_expectation_profile` (canonical_must_cite, bridge_traditions, absent_traditions_risk) | **G** OpenCitations + corpus references aggregation | E editor's own must-cite (from their publications) | F author overlap |
| `geographic_affinity` envelope (editorial_board_regions, author_regions_published, anglophone_hegemony_index) | **E** editor institutional affiliation distribution | **F** author affiliation distribution in last-50 corpus, C Crossref affiliations | B publisher HQ (low signal) |
| `institutional_signals` (prestige_tier, indexing, OA, APC, review_model, decision_weeks) | **C** DOAJ + Sherpa + Scopus/WoS registry cards (`registry_card`) | A OA/APC claim on site, B platform terms | none below registry |
| `temporal_position` (median_ref_year, field_maturity in this venue) | **D** corpus reference-age distribution + **G** OpenCitations year distribution | none above | C "established" claim |
| `publication_regime_model` (peer review clarity, decision time, desk-rejection patterns, special-issue logic, author_eligibility, compliance burden) | **A** policies + **B** publisher platform rules (both `formal_page`/`vendor_policy`) | J tacit signals from prior submissions (`tacit_signal`, low confidence) | scope text |
| `trust_compliance_profile` (peer review clarity, indexing/archiving, persistent IDs, fee transparency, license clarity, COPE/DOAJ/OASPA, predatory risk) | **C** DOAJ + COPE + OASPA membership lookups | A self-claim on site | publisher marketing |
| `section_models[*].article_types` / requirements | **A** section page on journal site | D recent articles in that section (corpus_observation) | scope claim |
| `issue_or_special_issue_models[*]` (theme, deadline, editors, article_types, target_disciplines) | **A** CFP page on journal site + **I** society / aggregator listing | C OpenAlex/Crossref of past special issues from same editors | publisher marketing |
| `tacit_venue_signals[*]` | **J** explicit user-supplied note (`tacit_signal`, with date + scope + confidence) | none — tacit is its own authority level | nothing |

> H (full-text resolvers) is **never authoritative for venue
> metadata**. It is authoritative only for the *body of the article*
> when feeding D corpus mining. See canon §3.H.

---

## 2. Source ↔ funnel-layer activation

Which source categories light up at which funnel depth. Hot path
should not pay for sources that the layer does not need.

| Funnel layer | Active source categories | Active VenueProfilePackage subobjects |
|---|---|---|
| 1 — Venue universe | C (OpenAlex topics, DOAJ subject), B (publisher portfolios) | none — discovery only |
| 2 — Disciplinary regime | C, G (OpenAlex concepts) | `venue_identity`, `venue_field_position` (partial) |
| 3 — Tribe / school | E (lightweight editor sampling), G (OpenCitations cited-author network) | `school_envelope`, `editorial_board_profile` (partial), `citation_expectation_profile` (partial) |
| 4 — Venue class | A (site article_types), B (publisher class) | `journal_model`, `venue_envelope` (genre, regime) |
| 5 — Journal as envelope | A + B + C + initial D sample (5–10 articles) | `journal_model` (full), `formal_submission_profile`, `publication_regime_model`, `indexing_and_metrics_profile`, `trust_compliance_profile`, `venue_field_position` (most axes) |
| 6 — Section / special issue | A (section + CFP pages), I (society channels) | `section_models[*]`, `issue_or_special_issue_models[*]` |
| 7 — Editorial board cloud | E (full) + G (editor author records) | `editorial_board_profile` (full) — center of gravity, geographic, methodological, theoretical |
| 8 — Published corpus hull | D (20/35/50/80) + F (author profiles from corpus) + H (selective full-text) + G (references → OpenCitations) | `published_article_corpus`, `published_article_patterns`, `citation_expectation_profile` (full), `method_expectation_profile`, `genre_move_profile`, `style_register_profile`, `author_eligibility_profile`, `time_review_profile`, `apc_access_profile` (corpus-corroborated) |

**Activation rule.** A subobject at layer N must NOT be populated from
sources beyond category-level allowlist of N. If layer 5 produces
`editorial_board_profile`, that profile is *seed-only* (names from A);
the *full cloud* is layer 7 work.

---

## 3. Anti-patterns

The four ways a venue model goes wrong in practice. Each one is a
gate the scorer and reviewer must enforce.

### AP1 — `aims_scope` upgraded to `FACT`

Scope text is `official_claim` at best — venue's self-description.
The corpus (D) tells you what it actually publishes. If
`discipline_envelope` reads only from A, the envelope is a fiction.

**Rule:** any axis whose authoritative source is D, E, F, or G but
which was filled from A alone must be marked `evidence_status:
INFERENCE`, confidence `low`. The scorer flags this.

### AP2 — `indexing_claim` treated as fit

Scopus / WoS quartile is `institutional_signals`, not
`discipline_fit`. A Q1 journal in `philosophy_of_technology` is still
a poor fit for an HCI empirical study; Q1 says only that the **regime**
is prestigious.

**Rule:** `indexing_and_metrics_profile` never enters `fit_vector`
arithmetic. It enters `publication_regime_fit` and
`trust_compliance_fit`, no further.

### AP3 — Editorial board as psychology

E gives a **cloud**, not a psychology of individuals. Statements like
"editor X dislikes continental theory" are forbidden. Allowed: "board
publication record shows ≤ 1 continental theory contribution out of
20 sampled; confidence low; sample bias possible."

**Rule:** every `editorial_board_profile.derived_signal.*` must carry
`evidence_status: inference` and `confidence: low|medium` with a
non-empty `unknowns_and_caveats` field.

### AP4 — Full-text source confused with metadata source

H (full-text resolvers — including Sci-Hub-likes, Academia,
ResearchGate, personal library, user-uploaded ZIPs) is the **body of
the article**. It is not the source of truth about which venue the
article belongs to, what the venue's policies are, or whether the
indexing claim is valid.

**Rule:** all metadata (`venue_identity`, `journal_model`, policies,
indexing, board, requirements) must trace to A / B / C / E / G. H is
allowed only as `corpus_observation` feeder for D-derived patterns.

---

## 4. Cache-miss authority map

When the two-stage `DB → network` search (canon §7) decides to fetch
fresh data, which adapter calls for which subobject and which cost.

| Cache-miss state | What we fetch | From category | Cost |
|---|---|---|---|
| `absent` (no `VenueRecord`) | identity → journal_model → quick D sample (5–10) | A + B + C + G + small D | medium (5–10 HTTP requests, no LLM) |
| `stale` on `formal_submission_profile` | re-fetch A + B + author guidelines + policies | A + B | low |
| `stale` on `published_article_corpus` | refresh latest N articles in corpus | G + small D | medium |
| `weak_evidence` on `editorial_board_profile` | sample more editors, fetch ORCID + OpenAlex Author | E + G | medium-high (per-editor ORCID lookup) |
| `weak_evidence` on `citation_expectation_profile` | enlarge corpus refs to 50; query OpenCitations | D (corpus) + G (OpenCitations) | high (each ref needs API call) |
| `weak_evidence` on `geographic_affinity` envelope | aggregate F (author affiliations from corpus) + E (editor affiliations) | E + F | medium |
| `fresh_sufficient` | nothing — composition from registry | none | zero |

> No LLM calls are required for any of these refreshes. LLM is for
> **interpretation** (e.g., classifying a method family from an abstract),
> not for **fetching**. Adapters fetch; the registry stores; the LLM (when
> Agentum is wired) interprets at fit-time.

---

## 5. Forbidden source uses

For belt-and-suspenders. The scorer and reviewer must reject these.

- A `discipline_envelope` populated only from A `aims/scope` — forbidden,
  must include D corroboration or be marked `partial`.
- An `indexing_and_metrics_profile` populated only from A `claims of
  being indexed` — forbidden, must include C `registry_card`
  corroboration, else `UNKNOWN_NOT_VERIFIED`.
- An `editorial_board_profile.derived_signal` populated from < 4 editors
  in a board of ≥ 10 — forbidden, must be `partial` with explicit
  sample size.
- Any subobject populated from H without independent A/B/C/G
  metadata — forbidden, the subobject is metadata not body.
- Any `tacit_venue_signal` without a source-and-date stamp —
  forbidden, drops `evidence_status` to `UNKNOWN_NOT_VERIFIED`.

---

## 6. Per-axis golden expectations (Mavrinsky-side)

Concrete numbers / shapes the rubric expects to see when the funnel
runs on Mavrinsky's article. These are NOT predictions for any single
journal — they describe what a correctly-built envelope for a
**continental-philosophy-of-technology** venue should look like.

| Axis | Expected shape of envelope (for continental-philtech cluster) | Expected source category |
|---|---|---|
| `discipline_envelope` | `continental_philosophy: [0.3, 0.9]`, `philosophy_of_technology: [0.3, 0.8]`, `media_philosophy: [0.0, 0.7]`, `STS: [0.0, 0.5]`, `HCI: [0.0, 0.2]` | D + C |
| `school_envelope` | `Deleuze/Guattari: [0.0, 0.7]`, `Agamben: [0.0, 0.6]`, `Foucault: [0.1, 0.7]`, `Simondon: [0.0, 0.7]`, `Stiegler: [0.0, 0.7]`, `Yuk_Hui: [0.0, 0.5]`, `Latour_ANT: [0.0, 0.4]`, `HCI_dark_patterns: [0.0, 0.1]` | E + D top-cited |
| `argument_move_envelope` | `concept_reconstruction: [0.2, 0.8]`, `concept_introduction: [0.1, 0.6]`, `genealogy: [0.0, 0.5]`, `empirical_conceptual_hybrid: [0.0, 0.4]`, `systematic_review: [0.0, 0.2]`, `methodology_piece: [0.0, 0.1]` | D structural |
| `evidence_type_envelope` | `theoretical_argument: [0.4, 1.0]`, `textual_analysis: [0.0, 0.6]`, `case_study: [0.0, 0.4]`, `quantitative_data: [0.0, 0.1]`, `experimental: [0.0, 0.0]` | D method classification |
| `method_envelope` | `explicit_method: false`-tolerant; `accepted_method_families: [philosophical_analysis, conceptual_reconstruction, textual]`; `rejected: [experimental, RCT, computational]` | A + D check |
| `citation_expectation_profile.canonical_must_cite` | at least one of {Foucault, Deleuze, Guattari, Agamben, Heidegger, Simondon, Stiegler, Yuk_Hui} expected per article | G + D |
| `citation_expectation_profile.absent_traditions_risk` | journal's cluster determines risk: in this cluster, "no Lacan engagement" is low risk; "no Foucault" is high risk | E reasoning |
| `geographic_affinity` envelope | `editorial_board_regions`: at least 3 of {USA, UK, France, Germany, Netherlands, Italy} represented; `anglophone_hegemony_index: [0.5, 0.9]` | E (board) + F (corpus) |
| `institutional_signals` | `prestige_tier: top` for the cluster's top 2 (e.g., *Philosophy & Technology*, *Techné*); `OA: hybrid` typical; `APC_range: $1500–$3500` typical; `review_model: double_blind` typical | C registry cards |
| `temporal_position` | `median_reference_year ≈ 1985–2005` for continental philtech (Foucault/Deleuze era); `field_maturity: established` | D + G |

Equivalent shapes for **STS-platform cluster** and **HCI-design
cluster** live in [`mavrinsky_venue_side_gold.md`](mavrinsky_venue_side_gold.md)
because those are venue-side expectations for the article, not
general per-axis source-layer expectations.

---

## 7. How this rubric is consumed

- **Scorer (`scripts/score_against_gold.py`):** §3 anti-patterns become
  per-axis FAIL checks. §5 forbidden uses become hard-FAIL gates.
  §6 ranges become PARTIAL/PASS thresholds for shape match.
- **Operator review:** for any venue profile with `evidence_status:
  INFERENCE` on an axis whose authoritative source per §1 is D / E /
  G, the reviewer must check whether the run actually hit D / E / G
  or only A. If only A, the axis is downgraded to `partial`.
- **Adapter authors:** new adapters declare which source category
  (A–J) they belong to. The authority enforced is determined by §1.

---

## 8. What this rubric does NOT cover

- Cross-cluster fit (e.g., should an article move from continental
  philtech to HCI?) — that's `FitAssessment` arithmetic per
  [PUBLICATION_INTEGRABILITY_MODEL_v1.md §8](../../docs/PUBLICATION_INTEGRABILITY_MODEL_v1.md).
- Timeline / decision-time profiling — moves to a separate rubric
  once we have enough `J` tacit signals to compare.
- Cost modelling per fetch — belongs to Agentum (no local LLM tuning,
  see project memory).

---

## 9. Open questions for the next pass

These do not block use of this rubric. They are flagged for the next
venue-side review:

1. **What is the minimum corpus size for an "honest" `discipline_envelope`?**
   Canon §6 says 5–10 for quick, 20–35 for standard. The rubric
   currently defaults to 20 for envelope construction. If corpus < 20,
   envelope must be marked `partial`. Threshold may need
   per-discipline calibration (philosophy journals are slower than
   AI venues).
2. **How is editor publication count weighted in `school_envelope`?**
   A senior editor with 200 papers vs a junior with 10 — equal vote?
   Current rubric: equal. May need career-stage normalisation.
3. **Are we cross-referencing publisher portfolios for cluster
   inference?** Springer's *Philosophy & Technology* sits in a portfolio
   with STS journals; this may legitimately corroborate
   `school_envelope` weakly. Not yet in the matrix.

End of rubric.
