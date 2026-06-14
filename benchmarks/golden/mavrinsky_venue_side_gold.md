# Mavrinsky venue-side gold (v2)

**Status:** golden rubric. Mirror of
[`mavrinsky_article_side_gold.md`](mavrinsky_article_side_gold.md) on
the venue side.

**Supersedes:** v1 (same path, prior commit). v1 fixed three clusters
(CPT / STS / HCI) and rolled Russian-language venues out of scope under
an international-only scenario. v2 (this file) makes the cluster set
explicit at **five envelopes** so the rubric can score against either
the international scenario or a Russian-language scenario, and treats
"Russian philosophy venue" as a separate cluster whose fit depends on
language-and-regime rather than field-and-tribe.

**Inputs:**
- Article-side gold: [mavrinsky_article_side_gold.md](mavrinsky_article_side_gold.md).
- Canon: [docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md](../../docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md).
- Source layer rubric: [venue_source_layer_map.md](venue_source_layer_map.md).
- Funnel doc: [source_acquisition_funnel.md](source_acquisition_funnel.md).
- Manuscript: stays under `private_inputs/`, never committed.

This file does **not** name "correct" journals. It defines **the
topology of envelopes** the funnel must produce when run on Mavrinsky's
article, the **expected core-risk under adaptation** per cluster, and
the **Mavrinsky-specific anti-patterns** the scorer must hard-fail on.

---

## 0. Article point summary

From article-side gold, repeated for self-containment:

- Discipline: continental philosophy / philosophy of technology / media philosophy.
- Tribe: Deleuze-Guattari / Foucault / Agamben constructive; Lacan as foil.
- Argument move: concept_reconstruction + concept_introduction (greedy/generous interface).
- Evidence type: theoretical_argument 0.85.
- Method: not explicit, philosophical analysis.
- Audience: deep_specialist.
- Geographic: author in Russia, intellectual tradition France/Germany.
- Language: ru, English abstract.
- Protected core: desire-as-excess, interface as dispositif/capture, greedy/generous distinction.

Submission scenario (international visibility, Scopus or WoS, low APC,
medium rewrite allowed, NO removal of protected core, author in
Russia). A second scenario (Russian-language regime) is overlaid for
cluster 5.

---

## 1. Five target envelopes

These are not five journals. They are five **regions in the FPM
space** the venue side must produce envelopes for. Each region is
populated by some set of real venues; the rubric scores on envelope
topology, not on which specific journal lands inside.

| # | cluster | what it is | fit class for this article | core-risk under adaptation |
|---|---|---|---|---|
| 1 | **continental / media philosophy** | venues that publish theoretical essays on technology, interface, subjectivity in continental register; Deleuze/Foucault/Agamben canonical | **near-native fit** | **low** — protected core stays |
| 2 | **philosophy of technology** | philtech-mainstream; Simondon/Stiegler/Heidegger-on-technology/Hui canonical | **citation-bridge fit** | **medium** — protected core preserved iff bridge added without erasing Deleuze/Agamben line |
| 3 | **STS / platform studies** | sociotechnical empirical / ANT / platform studies; Latour canonical; case material required | **sibling-manuscript / high-rewrite fit** | **high** — empirical_conceptual_hybrid move required; protected core can be preserved only as a derivative manuscript |
| 4 | **HCI / design theory** | HCI empirical, dark patterns, persuasive technology, design intervention | **high-core-risk / sibling-only fit** | **destructive** — adapting to UX framing eliminates desire-as-excess pivot |
| 5 | **Russian philosophy** (RU-language scenario) | ВАК / РИНЦ / КиберЛенинка-listed Russian humanities/philosophy journals | **language-and-regime fit, NOT automatically field fit** | **low on language; medium-to-high on field** — varies by specific journal's editorial line; cannot be reduced to "Russian = friendly" |

These are the five envelopes whose topology the rubric checks.

---

## 2. Envelope shapes per cluster

For each cluster, the rubric expects an envelope that overlaps the
ranges below. **Overlap** means the venue envelope's `[lo, hi]` for
that dimension intersects the rubric's `[lo, hi]`. Exact decimals are
not required; topology is.

### 2.1 Continental / media philosophy envelope

| axis | expected envelope range |
|---|---|
| `discipline_envelope` | `continental_philosophy: [0.3, 0.9]`, `philosophy_of_technology: [0.0, 0.5]`, `media_philosophy: [0.2, 0.8]`, `STS: [0.0, 0.3]`, `HCI: [0.0, 0.1]` |
| `school_envelope` | `Deleuze_Guattari: [0.2, 0.8]`, `Foucault: [0.2, 0.8]`, `Agamben: [0.1, 0.7]`, `Heidegger: [0.0, 0.5]`, `Simondon: [0.0, 0.4]`, `Stiegler: [0.0, 0.3]`, `Latour_ANT: [0.0, 0.3]`, `HCI_dark_patterns: [0.0, 0.1]` |
| `argument_move_envelope` | `concept_reconstruction: [0.3, 0.9]`, `concept_introduction: [0.2, 0.7]`, `genealogy: [0.0, 0.6]`, `empirical_conceptual_hybrid: [0.0, 0.3]`, `systematic_review: [0.0, 0.2]` |
| `evidence_type_envelope` | `theoretical_argument: [0.5, 1.0]`, `textual_analysis: [0.0, 0.6]`, `case_study: [0.0, 0.3]`, `quantitative_data: [0.0, 0.0]` |
| `method_envelope` | `requires_explicit_method: false`, `accepted: [philosophical_analysis, conceptual_reconstruction, textual, genealogy]`, `rejected: [experimental, RCT, computational]` |
| `citation_expectation` | canonical includes ≥ 2 of {Foucault, Deleuze, Guattari, Agamben}; Lacan as foil acceptable; Simondon/Stiegler optional |
| expected core-risk under adaptation | **low** — article enters as is, modulo minor rhetorical polish |

### 2.2 Philosophy of technology envelope

| axis | expected envelope range |
|---|---|
| `discipline_envelope` | `philosophy_of_technology: [0.4, 1.0]`, `continental_philosophy: [0.0, 0.5]`, `philosophy_of_science: [0.0, 0.5]`, `media_philosophy: [0.0, 0.4]`, `STS: [0.0, 0.4]`, `HCI: [0.0, 0.2]` |
| `school_envelope` | `Simondon: [0.1, 0.7]`, `Stiegler: [0.1, 0.7]`, `Yuk_Hui: [0.0, 0.6]`, `Heidegger_on_technology: [0.1, 0.7]`, `Verbeek: [0.0, 0.5]`, `Deleuze_Guattari: [0.0, 0.4]`, `Foucault: [0.0, 0.4]`, `Agamben: [0.0, 0.3]` |
| `argument_move_envelope` | `concept_reconstruction: [0.2, 0.7]`, `concept_introduction: [0.1, 0.6]`, `empirical_conceptual_hybrid: [0.0, 0.4]`, `genealogy: [0.0, 0.4]` |
| `evidence_type_envelope` | `theoretical_argument: [0.3, 0.9]`, `case_study: [0.0, 0.5]`, `textual_analysis: [0.0, 0.5]` |
| `method_envelope` | `requires_explicit_method: false`-tolerant; `accepted: [philosophical_analysis, conceptual_reconstruction, postphenomenology, mediation_theory]` |
| `citation_expectation` | canonical includes ≥ 1 of {Simondon, Stiegler, Yuk_Hui, Heidegger-on-technology}; Foucault/Deleuze welcome; Lacan as foil neutral; missing technics bridge = high risk |
| expected core-risk under adaptation | **medium** — requires citation bridge to Simondon/Stiegler/Hui; preserved iff that bridge is added without erasing the desire-as-excess pivot |

### 2.3 STS / platform studies envelope

| axis | expected envelope range |
|---|---|
| `discipline_envelope` | `STS: [0.5, 1.0]`, `sociology_of_science: [0.2, 0.7]`, `platform_studies: [0.1, 0.6]`, `continental_philosophy: [0.0, 0.2]`, `philosophy_of_technology: [0.0, 0.3]` |
| `school_envelope` | `Latour_ANT: [0.2, 0.8]`, `Callon: [0.0, 0.6]`, `STS_empirical: [0.3, 0.9]`, `Deleuze_Guattari: [0.0, 0.2]`, `Foucault: [0.0, 0.4]` |
| `argument_move_envelope` | `empirical_conceptual_hybrid: [0.3, 0.9]`, `case_study: [0.2, 0.8]`, `concept_reconstruction: [0.0, 0.3]`, `concept_introduction: [0.0, 0.3]` |
| `evidence_type_envelope` | `case_study: [0.3, 1.0]`, `interview_ethnographic: [0.0, 0.8]`, `archival: [0.0, 0.5]`, `theoretical_argument: [0.0, 0.3]` |
| `method_envelope` | `requires_explicit_method: true`, `accepted: [case_study, ethnography, ANT_method, qualitative_interview]`, `rejected: [pure_theoretical_essay, free_form_philosophy]` |
| `citation_expectation` | canonical includes Latour and at least one platform-studies marker; missing ANT bridge = high risk; Deleuze/Agamben acceptable as theoretical seasoning, not as method |
| expected core-risk under adaptation | **high** — argument move must shift to empirical_conceptual_hybrid; the article as-is is **outside method envelope**; protected core preserved only via **sibling manuscript**, not in-place adaptation |

### 2.4 HCI / design theory envelope

| axis | expected envelope range |
|---|---|
| `discipline_envelope` | `HCI: [0.5, 1.0]`, `design_studies: [0.1, 0.8]`, `psychology_HCI: [0.0, 0.6]`, `interaction_design: [0.2, 0.9]`, `continental_philosophy: [0.0, 0.1]`, `philosophy_of_technology: [0.0, 0.2]` |
| `school_envelope` | `HCI_affordances: [0.1, 0.7]`, `dark_patterns: [0.0, 0.6]`, `persuasive_technology: [0.0, 0.5]`, `interaction_design: [0.2, 0.9]`, `Deleuze_Guattari: [0.0, 0.05]`, `Foucault: [0.0, 0.1]`, `Agamben: [0.0, 0.05]` |
| `argument_move_envelope` | `empirical_study: [0.3, 0.9]`, `design_intervention: [0.1, 0.7]`, `concept_introduction: [0.0, 0.3]`, `concept_reconstruction: [0.0, 0.2]` |
| `evidence_type_envelope` | `experimental: [0.2, 0.9]`, `quantitative_data: [0.2, 0.9]`, `user_study: [0.2, 1.0]`, `theoretical_argument: [0.0, 0.2]` |
| `method_envelope` | `requires_explicit_method: true`, `accepted: [user_study, design_intervention, experimental, mixed_methods]`, `rejected: [free_form_philosophy, conceptual_reconstruction]` |
| `citation_expectation` | canonical: HCI/design references, affordances, dark patterns; the article's must-cite set (Foucault/Deleuze/Agamben) is here a `dangerous_missing_names` for HCI but irrelevant overall |
| expected core-risk under adaptation | **destructive** — "generous interface" reframed as "good UX" eliminates the desire-as-excess pivot; **only a derivative sibling manuscript with different core** is admissible; never an in-place adaptation |

### 2.5 Russian philosophy (RU-language regime) envelope

| axis | expected envelope range |
|---|---|
| `discipline_envelope` | `philosophy_general: [0.3, 0.9]`, `media_philosophy: [0.0, 0.5]`, `continental_philosophy: [0.1, 0.7]`, `philosophy_of_technology: [0.0, 0.4]`, `Russian_humanities_methodology: [0.1, 0.6]` |
| `school_envelope` | extremely wide and journal-specific; **cannot be reduced to a single profile**. Possible: `Russian_metaphysical_tradition`, `continental_post-Soviet`, `analytical_Russian_school`, `phenomenological_tradition` — each is its own cluster within the cluster |
| `argument_move_envelope` | `concept_reconstruction: [0.2, 0.8]`, `concept_introduction: [0.1, 0.6]`, `commentary: [0.1, 0.5]`, `theoretical_essay: [0.2, 0.8]` |
| `evidence_type_envelope` | `theoretical_argument: [0.4, 0.9]`, `textual_analysis: [0.1, 0.7]` |
| `method_envelope` | `requires_explicit_method: false`, broad acceptance |
| `language_register` | `language: ru` (primary), bilingual abstract often required |
| `institutional_signals` | `prestige_tier`: ВАК-perechen + РИНЦ + кибериленинка — **strategic, not field-fit**; some journals indexed in Scopus or WoS, most are not |
| expected core-risk under adaptation | **low on language and regime** (article is already ru); **field fit varies per specific journal**. The rubric must NOT assume "Russian = friendly". It must enforce: pick the venue whose editorial line actually matches continental media philosophy register; otherwise core fit is undetermined. |

> **Critical note:** the Russian-philosophy cluster is the only one
> where indexing claims (ВАК-perechen, РИНЦ inclusion) materially
> determine value, because the strategic value of publication for a
> Russian author is partially regime-defined. This is **not field
> fit**; it is `publication_regime_fit`. Conflating the two is anti-
> pattern VAP7 below.

---

## 3. Funnel-layer expectations

How each funnel layer maps to the five clusters.

| funnel layer | layer 1 (universe) | layer 2 (regime) | layer 3 (tribe) | layer 4 (class) | layer 5 (journal) | layer 6 (section/SI) | layer 7 (board) | layer 8 (corpus) |
|---|---|---|---|---|---|---|---|---|
| cluster 1 (cont/media phil) | YES — broad disc | YES — continental regime | YES — Deleuze/Foucault/Agamben | journal / forum essay | YES — full identity | optional SI | needed for confidence | needed for hull |
| cluster 2 (philtech) | YES | YES — philtech regime | YES — Simondon/Stiegler/Hui | journal | YES | optional | needed | needed |
| cluster 3 (STS) | YES | YES — STS regime | YES — Latour/ANT | journal / proceedings | YES | maybe SI | needed | needed |
| cluster 4 (HCI) | YES | YES — HCI regime | YES — affordances/dark patterns | journal / proceedings | YES | maybe SI | optional (the field is well-bounded) | needed |
| cluster 5 (RU phil) | YES — broad | **CRITICAL** — regime varies wildly | per-journal | per-journal | YES | per-journal SI | **CRITICAL** for field fit (board defines line) | needed if Scopus/WoS regime |

The takeaway: cluster 5 cannot be served by `discipline` + `tribe` +
`identity` alone. It requires `EditorialBoardCloud` to determine field
fit, because Russian journals' editorial lines vary inside the same
nominal discipline.

---

## 4. Mavrinsky-specific anti-patterns (VAP1–VAP7)

Beyond the general AP1–AP4 in
[venue_source_layer_map.md §5](venue_source_layer_map.md), the
Mavrinsky-specific anti-patterns:

- **VAP1** Lacan-as-shoulder. Any deep dossier listing Lacan in
  `citation_expectation_profile.canonical_must_cite` for clusters 1–4
  is a bug (Lacan is the article's foil, not canonical here).
- **VAP2** Simondon-hallucination. Any dossier claiming Simondon
  appears in the article's current citation network is a bug. Simondon
  is `absent_but_relevant` for cluster 2 only.
- **VAP3** HCI fit upgraded. If `overall_label` for cluster 4 returns
  `strong_candidate` or `possible`, that is a bug — `protected_core`
  gating is missing.
- **VAP4** Generic STS reframe. If `AdaptationPlan.sibling_options` for
  cluster 3 reduces to "add cases" without naming what protected_core
  is preserved or lost, that is a bug — cost is understated.
- **VAP5** "Q1 = strong" for cluster 1 or 2. *Philosophy & Technology*
  in cluster 1 may legitimately come back `possible_but_costly` if the
  Simondon/Stiegler bridge is required. Treating it as automatically
  `strong` because of Q1 is AP2 (indexing as fit) from the source layer
  map.
- **VAP6** Wrong scenario pool. If the pool under the international
  scenario contains cluster 5 (Russian VAK), that is a scenario-
  violation. If the pool under the Russian scenario contains
  cluster 4 (HCI proceedings), that is also a scenario-violation. The
  pool must respect scenario constraints.
- **VAP7** "Russian = friendly". Treating cluster 5 as automatically a
  field fit because the article is in Russian is wrong. Cluster 5 is
  a language-and-regime fit; field fit varies per journal and must be
  established from `EditorialBoardCloud` and `PublishedCorpusHull`.

---

## 5. Acceptance criteria

Median of 3 same-config runs. PASS iff:

**A. Cluster coverage.** All 5 clusters surface ≥ 1 candidate each
under the union of the two scenarios (international + Russian).
**B. Envelope topology.** For each of the 5 clusters, ≥ 1 deep dossier
produces an envelope that overlaps the §2 ranges on **at least 4 of
6 axes** (discipline, school, argument_move, evidence_type, method,
citation_expectation).
**C. Label topology.** Cluster 1 → `possible` or
`possible_but_costly`. Cluster 2 → `possible_but_costly` or
`adjacent_with_reframe`. Cluster 3 → `adjacent_with_reframe` or
`high_risk`. Cluster 4 → `poor_fit` or `high_core_risk`. Cluster 5 →
varies by specific journal but `publication_regime_fit` must be
distinguished from `discipline_fit`.

PARTIAL: A and B PASS, C produces correct labels for 3 of 5 clusters.
FAIL: any inversion in C (e.g., cluster 4 → `strong_candidate`); or
A FAIL; or B fails for ≥ 2 clusters.

---

## 6. What this gold deliberately does NOT cover

- Selecting a specific journal as "the right one". The rubric scores
  topology, not picks.
- Live editorial board adapter outputs. The cluster-5 board-determines-
  fit observation is a contract for the future live adapter, not a
  demand for this baseline.
- Cost / latency per fetch. Belongs to Agentum.
- Cross-cluster `MismatchMap` arithmetic and `RewritePlan` action
  shapes. Those belong to `FitAssessment` per PIM v1 §8 and to a
  separate adaptation rubric.
- Scope handling for clusters that are valid for other articles
  (e.g., digital humanities, education, AI ethics). They are not
  Mavrinsky-cluster.

---

## 7. Scoring hooks

The venue-side scorer (in `scripts/run_venue_side_benchmark.py`) reads
this file and the source layer map, then for each completed run checks:

1. cluster coverage per §1,
2. envelope topology per §2 (axis-by-axis overlap),
3. label topology per §5 C,
4. anti-pattern violations per §4,
5. forbidden source uses per source layer map §5.

Score JSON shape mirrors the article-side scorecard. The scorer is
deterministic; it does not call the LLM.

---

## 8. Open questions flagged for next gold revision

These do not block acceptance:

1. **Cluster 5 sub-clusters.** Russian philosophy splits into
   `metaphysical / phenomenological / continental-post-Soviet /
   analytical`. Should each be its own envelope in v3, or does the
   current "varies per journal" pattern stay?
2. **Editorial board weighting.** Senior editor (200 papers, 30y) vs
   junior (10 papers, 5y) — equal vote? Current rubric: equal. May
   need career-stage normalisation.
3. **Publisher portfolio cross-reference.** Springer's *Philosophy &
   Technology* portfolio neighbours STS and analytic philtech;
   weak corroboration to `school_envelope`. Not in v2 matrix.
4. **SI venues as separate cluster.** A topic-bounded special issue
   may legitimately cross cluster 1 ↔ cluster 2. Today the rubric
   collapses SI into the host journal. v3 may promote
   `SpecialIssueModel` to first-class.

End of gold v2.
