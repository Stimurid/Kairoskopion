# Mavrinsky venue-side gold

**Status:** golden rubric. Mirror of
[`mavrinsky_article_side_gold.md`](mavrinsky_article_side_gold.md) on
the venue side.

**Inputs:**
- Article-side gold: same file as above.
- Canon: [docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md](../../docs/VENUE_FUNNEL_AND_PROFILE_PACKAGE_V1.md)
- Source layer rubric: [venue_source_layer_map.md](venue_source_layer_map.md)
- Manuscript: stays under `private_inputs/`, never committed.

This file says **what the venue-side pipeline must produce** when run
on Mavrinsky's article. It is not a list of "correct" journals. It is
a topology of expected envelopes per cluster + funnel-layer
expectations + anti-patterns to fail loudly on.

---

## 0. What we are running through the funnel

Article point summary (from article-side gold, repeated for self-containment):

- Discipline: continental philosophy / philosophy of technology / media philosophy.
- Tribe: Deleuze-Guattari / Foucault / Agamben constructive; Lacan as foil.
- Argument move: concept_reconstruction + concept_introduction (greedy/generous interface).
- Evidence type: theoretical_argument 0.85.
- Method: not explicit, philosophical analysis.
- Audience: deep_specialist.
- Geographic: author in Russia, intellectual tradition France/Germany.
- Language: ru, English abstract.
- Protected core: desire-as-excess, interface as dispositif/capture, greedy/generous distinction.

Submission scenario (also from gold): international visibility, Scopus
or WoS, low APC, allows medium rewrite, NO removal of protected core,
author in Russia (sanction-aware).

---

## 1. Three target clusters the funnel must surface

| cluster | what it is | why it matters for Mavrinsky |
|---|---|---|
| **CPT** — continental philtech / media philosophy | venues that publish theoretical essays on technology, interface, subjectivity in continental register; Deleuze/Foucault/Agamben canonical | the article's *native* home; fit expected `strong` or `possible` |
| **STS-platform** | STS / platform studies / sociotechnical; Latour/ANT/platform empirical | the article's *adjacent_with_reframe* zone; high rewrite cost, may require sibling manuscript |
| **HCI-design** | HCI, design theory, interaction ethics, dark patterns | the article's *high core risk* zone; risk of reducing generous interface to "good UX" |

A fourth cluster — **RU-humanities** (Russian VAK/RINTS philosophy
journals) — is in scope of the article-side scenario (`author in
Russia`) but is out of scope of this gold because the current
`SubmissionScenario` targets international Scopus/WoS visibility. A
follow-up gold under a different scenario can cover it.

---

## 2. Expected pool shape (funnel layers 1–2)

Pool must contain at least:

| cluster | expected count in pool | acceptable identity sources |
|---|---|---|
| CPT | ≥ 5 | C (OpenAlex Sources by concept), C (DOAJ subject), B (publisher portfolios) |
| STS-platform | ≥ 5 | same |
| HCI-design | ≥ 3 | same |
| transboundary (philtech ↔ STS, e.g., *Philosophy & Technology*) | ≥ 2 | same |

PASS: ≥ 15 distinct `VenueRecord` candidates with
`evidence_status: registry_card` or stronger for `venue_identity`.
PARTIAL: 8–14. FAIL: < 8 OR any cluster missing.

**Forbidden in pool:** LLM-invented venue names without identity
verification through C or G adapters (see venue_source_layer_map.md
§5).

---

## 3. Expected shortlist shape (funnel layers 3–5)

Shortlist = 8–12 candidates that survive a light envelope check
(layer 3 tribe + layer 4 venue_class + layer 5 light envelope from
A + B + 5–10 corpus articles).

For Mavrinsky the gold shortlist shape:

| cluster | expected venues in shortlist | required envelope hits |
|---|---|---|
| CPT | 3–5 | `discipline_envelope.continental_philosophy ∈ [0.3, 0.9]`, `school_envelope` includes any of {Deleuze, Foucault, Agamben} with hi ≥ 0.5 |
| philtech bridge (transboundary) | 2–3 | `discipline_envelope.philosophy_of_technology ∈ [0.3, 0.8]`, `school_envelope` includes any of {Simondon, Stiegler, Yuk_Hui} with hi ≥ 0.3 |
| STS-platform | 1–2 | shortlisted only with explicit `core_risk: high` flag for tribe mismatch |
| HCI-design | 0–1 | shortlisted only with `core_risk: destructive` flag and `requires_sibling_manuscript: true` |

PASS: 8–12 candidates with envelope hits as above. PARTIAL: 5–7 OR
clusters skewed (e.g., 8 CPT but no philtech bridge). FAIL: < 5.

**Required marker per shortlisted venue:** an explicit
`pathway_decision` field that names which of the 5 pathways from the
article-side gold the venue covers (`continental_media_philosophy`,
`philosophy_of_technology`, `media_interface_theory`,
`STS_platform_studies`, `HCI_design_theory`).

---

## 4. Expected deep dossiers (funnel layers 5–8)

For 3 deep dossiers, expected envelopes per axis. Numbers are **ranges
the envelope hi/lo must overlap**, not exact values.

### 4.1 Deep dossier — CPT representative

Concrete example: *Philosophy & Technology* (Springer) or *Techné:
Research in Philosophy and Technology* or *Foucault Studies* — any
one of these. Topology must hold regardless of which specific journal:

| axis | expected envelope shape | source per §1 of source layer map |
|---|---|---|
| `discipline_envelope` | `continental_philosophy: [0.3, 0.9]`, `philosophy_of_technology: [0.3, 0.8]`, `media_philosophy: [0.0, 0.7]`, `STS: [0.0, 0.5]`, `HCI: [0.0, 0.2]` | D corpus topic |
| `school_envelope` | `Deleuze_Guattari: [0.0, 0.7]`, `Agamben: [0.0, 0.6]`, `Foucault: [0.1, 0.7]`, `Simondon: [0.0, 0.7]`, `Stiegler: [0.0, 0.6]`, `Yuk_Hui: [0.0, 0.5]`, `Latour_ANT: [0.0, 0.4]`, `HCI_dark_patterns: [0.0, 0.1]` | E editor pubs + D top-cited |
| `argument_move_envelope` | `concept_reconstruction: [0.2, 0.8]`, `concept_introduction: [0.1, 0.6]`, `empirical_conceptual_hybrid: [0.0, 0.4]`, `systematic_review: [0.0, 0.2]` | D structural |
| `evidence_type_envelope` | `theoretical_argument: [0.4, 1.0]`, `textual_analysis: [0.0, 0.6]`, `case_study: [0.0, 0.4]`, `quantitative: [0.0, 0.1]` | D method classification |
| `method_envelope` | `requires_explicit_method: false`, `accepted: [philosophical_analysis, conceptual_reconstruction, genealogy, textual]`, `rejected: [experimental, RCT, computational]` | A guidelines + D check |
| `citation_expectation_profile.canonical_must_cite` | at least one of {Foucault, Deleuze, Guattari, Agamben, Heidegger, Simondon, Stiegler, Yuk_Hui} per article | G + D |
| `citation_expectation_profile.absent_traditions_risk` | "no Foucault" = high risk; "no Lacan" = low risk; "no HCI dark patterns" = no risk | E reasoning |
| `geographic_affinity` envelope | `editorial_board_regions`: ≥ 3 of {USA, UK, France, Germany, Netherlands, Italy}; `anglophone_hegemony_index ∈ [0.5, 0.9]` | E + F |
| `institutional_signals` | `prestige_tier: top` or `mid`; `OA: hybrid` typical; `review_model: double_blind` | C |

Expected `FitAssessment.overall_label`: **`possible`** or
**`possible_but_costly`** (never `strong_candidate` because article is
draft-stage; never `poor_fit` if cluster is correct).

### 4.2 Deep dossier — STS-platform representative

Concrete example: *Science, Technology, & Human Values* or *Social
Studies of Science*.

| axis | expected envelope shape |
|---|---|
| `discipline_envelope` | `STS: [0.6, 1.0]`, `sociology_of_science: [0.2, 0.7]`, `platform_studies: [0.0, 0.5]`, `continental_philosophy: [0.0, 0.3]`, `philosophy_of_technology: [0.0, 0.4]` |
| `school_envelope` | `Latour_ANT: [0.2, 0.8]`, `Callon: [0.0, 0.6]`, `STS_empirical: [0.3, 0.9]`, `Deleuze_Guattari: [0.0, 0.3]`, `Foucault: [0.0, 0.5]` |
| `argument_move_envelope` | `empirical_conceptual_hybrid: [0.3, 0.9]`, `case_study: [0.2, 0.8]`, `concept_reconstruction: [0.0, 0.4]`, `concept_introduction: [0.0, 0.3]` |
| `evidence_type_envelope` | `case_study: [0.3, 1.0]`, `ethnographic: [0.0, 0.8]`, `archival: [0.0, 0.5]`, `theoretical_argument: [0.0, 0.4]` |
| `method_envelope` | `requires_explicit_method: true`, `accepted: [case_study, ethnography, ANT_method, qualitative]`, `rejected: [pure_theoretical_essay]` |

Expected `FitAssessment.overall_label`: **`high_risk`** or
**`adjacent_with_reframe`** with explicit
`mismatch_map.mismatches[*].axis == method_fit | evidence_type_fit |
argument_move_fit` and
`mismatch_map.unknowns_not_absences[*].why_unknown` filled.

**Required:** `AdaptationPlan.sibling_options` must contain at least
one entry with `what_changes: ["add_case_layer",
"add_STS_corpus", "shift_argument_move_to_empirical_conceptual"]` and
`what_core_is_lost: ["pure_conceptual_register",
"theoretical_density"]`.

### 4.3 Deep dossier — HCI-design representative

Concrete example: *International Journal of Human-Computer Studies*
or *Design Issues* or *Interacting with Computers*.

| axis | expected envelope shape |
|---|---|
| `discipline_envelope` | `HCI: [0.6, 1.0]`, `design_studies: [0.2, 0.8]`, `psychology_HCI: [0.0, 0.6]`, `continental_philosophy: [0.0, 0.1]`, `philosophy_of_technology: [0.0, 0.2]` |
| `school_envelope` | `HCI_affordances: [0.2, 0.8]`, `HCI_dark_patterns: [0.0, 0.6]`, `persuasive_technology: [0.0, 0.6]`, `interaction_design: [0.3, 0.9]`, `Deleuze_Guattari: [0.0, 0.05]` |
| `argument_move_envelope` | `empirical_study: [0.3, 0.9]`, `design_intervention: [0.1, 0.7]`, `concept_introduction: [0.0, 0.4]`, `concept_reconstruction: [0.0, 0.2]` |
| `evidence_type_envelope` | `experimental: [0.2, 0.9]`, `quantitative_data: [0.2, 0.9]`, `user_study: [0.2, 1.0]`, `theoretical_argument: [0.0, 0.2]` |

Expected `FitAssessment.overall_label`: **`poor_fit`** with
**`high_core_risk`** flagged.

**Required:** `AdaptationPlan.sibling_options` must contain entry with
`what_core_is_lost: ["dispositif_apparatus_framing",
"desire_as_excess_pivot", "ontological_interface_register"]`. If this
entry is missing, the gold fails on anti-pattern AP3-equivalent for
adaptation (cost falsely understated).

---

## 5. Anti-patterns the run must NOT exhibit

Beyond §3 of [venue_source_layer_map.md](venue_source_layer_map.md),
the Mavrinsky-specific anti-patterns:

- **VAP1** Lacan-as-shoulder. Any deep dossier listing Lacan in
  `citation_expectation_profile.canonical_must_cite` for the **CPT
  cluster** is a bug (Lacan is the article's foil, not a CPT canonical).
  Lacanian psychoanalysis journals are not in scope for this article.
- **VAP2** Simondon-hallucination. Any deep dossier claiming Simondon
  appears in the article's current citation network is a bug. Simondon
  is `absent_but_relevant` for the philtech pathway only.
- **VAP3** HCI fit upgraded. If `FitAssessment.overall_label` for a HCI
  venue comes back `strong_candidate` or `possible`, that is a bug —
  the system is missing protected_core gating.
- **VAP4** Generic STS reframe. If `AdaptationPlan.sibling_options`
  for STS reduces to "add_cases" without naming what protected_core
  is preserved or lost, that is a bug — the adaptation
  understates cost.
- **VAP5** "Philosophy & Technology" as Q1 = strong. Springer's
  *Philosophy & Technology* sits in the CPT cluster but its envelope
  also leans toward philtech-mainstream; the fit may legitimately be
  `possible_but_costly` because Simondon/Stiegler/Yuk_Hui bridge is
  required. Treating it as automatically `strong` because of Q1 is
  AP2 (indexing claim as fit) from the source layer map.
- **VAP6** Russian-language pool. If the pool contains Russian VAK
  journals despite the international Scopus/WoS scenario, that is a
  scenario-violation, not a discovery success — pool must respect
  scenario constraints.

---

## 6. Acceptance criteria (3 PASS, all-or-nothing)

The Mavrinsky venue-side run is accepted when **all three** hold,
median of 3 same-config runs:

**A. Pool topology.** §2 PASS.
**B. Shortlist coverage.** §3 PASS with all 5 pathways from the
article-side gold represented at least once in `pathway_decision`.
**C. Deep dossier overall_label.** §4.1 returns `possible` or
`possible_but_costly`; §4.2 returns `high_risk` or
`adjacent_with_reframe`; §4.3 returns `poor_fit` with
`high_core_risk` flag.

If A and B PASS but C produces a wrong label (CPT goes to `poor_fit`,
or HCI goes to `possible`), that is a **structural failure** and the
run fails — not because the score is low but because the model has
inverted the fit topology.

PARTIAL: A or B PASS, C produces correct labels for 2 of 3 clusters.
FAIL: any single inversion in C, or A/B FAIL.

---

## 7. What this gold deliberately does NOT cover

- **Russian-language pool under a different scenario.** Belongs to a
  separate `mavrinsky_ru_scenario_gold.md`.
- **Section / special issue depth (canon §1 layer 6).** The current
  scenario does not target a specific SI. If a follow-up SI scenario
  is supplied, the gold extends.
- **Tacit signals (canon §1 layer J).** Operator's prior submissions
  to these venues are not available at gold-construction time. If
  they exist, they enter as `tacit_venue_signals[*]` with explicit
  source-and-date stamp, not as overrides to envelope topology.
- **LLM stochasticity envelope.** Acceptance is over median-of-3
  runs. Single-run variance is expected and is not a structural
  failure.

---

## 8. Scoring hooks

The venue-side scorer (to be added as a follow-up commit in
`scripts/score_venue_side_against_gold.py`) reads this file and the
canon, then for each completed run checks:

1. pool count per cluster against §2,
2. shortlist count and pathway coverage against §3,
3. per-deep-dossier envelope axis overlap against §4,
4. anti-pattern violation per §5,
5. overall PASS/PARTIAL/FAIL per §6.

Score JSON shape mirrors the article-side scorecard. The scorer is
deterministic; it does not call the LLM.

---

## 9. Open questions flagged for next gold revision

1. **Are these three clusters exhaustive for Mavrinsky?** Possibly
   also: digital_culture journals, media_archaeology journals, art &
   science / experimental humanities. Not added yet because the
   article does not strongly indicate digital-culture register; if a
   later run surfaces strong digital-culture envelope hits, fold in.
2. **Should `editorial_board_regions` per cluster be normative?**
   E.g., CPT cluster strongly biased toward EU; STS toward US/UK;
   HCI toward US. Currently the gold accepts wide ranges. May tighten
   after first 3 real runs.
3. **Special-issue venues.** Springer / De Gruyter / Brill / Sage often
   host philosophy-of-technology special issues. The current pool gold
   does not require these as separate `issue_or_special_issue_models`;
   that may be a separate cluster after canon §1 layer 6 lands in code.

These do not block acceptance. They are flagged for the second pass.

End of gold.
