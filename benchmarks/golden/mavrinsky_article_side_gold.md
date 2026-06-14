# Mavrinsky article-side golden benchmark

**Benchmark ID:** `mavrinsky_baseline_2026_06_14`
**Scope:** Article-side model only (no journal selection, no final fit).
**Purpose:** Verify that Kairoskopion can build the
*Publication Integrability Model* of a real Russian-language
philosophical draft well enough that downstream fit/mismatch/adaptation
agents can run against it.

> This file is the **rubric**, not the source manuscript. The source
> draft (Мавринский И.И., «Желание, виртуальность и интерфейс: к онтологии
> технических форм») stays under `private_inputs/` and is **never
> committed**. The operator supplies the local path via
> `KAIROSKOPION_BENCHMARK_ARTICLE` (see `benchmarks/README.md`).

The rubric below is derived from a hand-authored golden discussion of
the same draft, kept by the project author privately. Quotes are
limited to short conceptual phrases needed to describe the rubric;
no manuscript paragraphs are included.

---

## What the article actually does

- **Genre:** short theoretical paper / Russian-language conference-style
  draft (≈ 1500 words), not a peer-reviewed empirical study.
- **Stage:** `draft` (lifecycle), not submission-ready.
- **Master move:** **concept reconstruction + concept introduction +
  problematization**, in that weighting order. The article is NOT a
  systematic review, NOT an empirical case study, NOT a methodology
  piece.
- **Authorial product:** the distinction `жадный интерфейс` vs.
  `щедрый интерфейс` (greedy interface vs generous interface), framed
  as two ontological regimes of technology.

---

## Field position — what the rubric expects

### Disciplinary vector (article = point)

| dimension | rough magnitude | reason |
|---|---|---|
| `continental_philosophy` | high (≈ 0.78) | poststructuralist register and sources |
| `media_philosophy` | mid-high (≈ 0.58) | interface as mediating technical form |
| `philosophy_of_technology` | mid (≈ 0.55) | technology is explicit, but canon under-cited |
| `interface_theory` | mid (≈ 0.45) | central object, no full interface-studies apparatus |
| `digital_culture` | low-mid (≈ 0.30) | applicable, no digital-culture corpus drawn |
| `STS` | low (≈ 0.15) | translatable, but neither method nor evidence STS |
| `HCI / design` | very low (≈ 0.10) | "interface" is a false cognate; not HCI |
| `analytic_philosophy` | near zero (≈ 0.05) | wrong argument register |

The benchmark scorer checks **topology**, not exact decimals — a run
that produces `philosophy_of_technology > STS > HCI` and includes any
of {continental, media, philtech, interface_theory} as the top
discipline passes check 3.

### School / tribe affiliation

Internal-positive shoulders (must surface):

- Deleuze & Guattari (capture apparatus, desire-production)
- Agamben (apparatus, profanation, return-to-use)
- Foucault (subject critique, dispositif, governmentality)
- Heidegger (modern subjectivity, *not* `Gestell`-flavored
  philosophy-of-technology)
- Leibniz (analogy of possible worlds — supporting, not foundation)

Contrastive / foil (must be distinguished from shoulders):

- **Lacan** = `foil`, not `shoulder`. Desire-as-lack is what the
  article *moves away from*. A run that places Lacan as
  `theoretical_shoulder` without a `relation: contrastive` / `foil`
  marker is wrong on tribe-recognition.

Absent-but-relevant by pathway (must surface as *signals*, not as
hallucinated shoulders):

| pathway | absent-but-relevant authors / streams |
|---|---|
| philosophy_of_technology | Simondon, Stiegler, Yuk Hui |
| media / interface theory | Manovich, Galloway, software/interface studies |
| STS | Latour, ANT, platform studies |
| HCI / design | affordances, dark patterns, persuasive technology |

A run that lists Simondon among `theoretical_shoulders` is
**hallucinating** (Simondon is not cited in the draft).

### Argument move vector

| move | rough share | note |
|---|---|---|
| concept_reconstruction | dominant (≈ 0.45) | desire, dispositif, capture reassembled |
| concept_introduction | secondary (≈ 0.30) | greedy / generous interface |
| problem_statement | tertiary (≈ 0.15) | classical subject of will |
| genealogy | minor (≈ 0.10) | weak, not historiographic |
| empirical_conceptual_hybrid | 0 | no cases as evidence |
| systematic_review | 0 | not a survey |
| methodology_piece | 0 | not a methods paper |

### Evidence type profile

- `theoretical_argument` ≈ 0.85
- `textual_analysis` ≈ 0.10
- `case_study` ≈ 0.05
- empirical / experimental / interview-ethnographic / archival: 0

### Method stance

- `explicit_method` = false
- `method_family` = `philosophical_analysis`
- `method_specificity` = low
- `empirical_component` = false

### Audience and register

- `expertise_required` = `specialist` or `deep_specialist`
- `register` = `academic_formal` / `academic_dense`
- `jargon_density` ≈ 0.7 – 0.8

### Geographic affinity

- `author_region` = Russia
- `intellectual_tradition_region` = France / Germany (continental)
- `language_of_publication` = `ru` (translation needed for
  international submission)

---

## Protected core (must NOT be lost in any adaptation)

These items, in some form, must be present in the model's
`protected_core` field (as list or as multi-sentence string the
benchmark coerces to list):

1. shift from desire-as-lack to desire-as-excess
2. interface as apparatus / capture / dispositif
3. greedy / generous interface distinction
4. non-classical subjectivity
5. generous interface as return-to-use / profanation / possibility-expansion

The scorer counts a run as PASS on check 7 (`core_risk`) if at least
two of {desire, interface, apparatus/capture/dispositif} appear in the
core text.

---

## Pathways

The article-side model should produce at least:

- **continental media philosophy** — fit `strong`, core risk `low`
- **philosophy of technology** — fit `medium_strong`, core risk
  `medium` (requires technics canon bridge)
- **media / interface theory** — fit `medium`, core risk `medium_high`
- **STS / platform studies** — fit `weak_medium`, core risk `high`,
  realistically a sibling manuscript
- **HCI / design theory** — fit `weak_medium`, core risk `high`,
  sibling manuscript

The scorer requires ≥ 2 pathways for PARTIAL and ≥ pathways AND ≥ 1
venue candidate for PASS.

---

## Scoring (10 checks, §14 of the underlying rubric)

| # | check | PASS rule (informal) |
|---|---|---|
| 1 | native_extraction | title + abstract + language=`ru*` + ref_count > 0 + claims |
| 2 | academic_move | `concept_reconstruction` and `concept_introduction` both surface, no `systematic_review` / `empirical_conceptual_hybrid` label |
| 3 | field_coordinates | discipline_vector and school_affiliation_vector each ≥ 4 dims; floats; gold disciplines/schools matched |
| 4 | tribe_recognition | ≥ 2 internal hits + Lacan present AND marked foil + at least one missing-bridge author surfaced |
| 5 | citation_ecology | `must_cite` present + `conspicuous_absence` present + pathway-keyed absences |
| 6 | venue_logic | ≥ 2 pathways + ≥ 1 venue candidate |
| 7 | core_risk | ≥ 3 protected_core items AND ≥ 2 of {desire, interface, apparatus} present |
| 8 | evidence_discipline | `SourceEvidencePacket.input_sources` with `provenance` + `access_status` + `granularity_summary` |
| 9 | fit_vector | `FitAssessment.axes` non-empty + `overall_label` set + no single score + FPM-based axes present |
| 10 | adaptation | rewrite_plan with ≥ 2 changes + summary + citation_plan |

PARTIAL is awarded when the structural signal is present but
incomplete. FAIL is when the signal is absent or wrong.

---

## Reproducibility envelope

Live-LLM scoring is **stochastic**. The benchmark does not chase a
single deterministic score. Acceptance is:

- median of 3 consecutive runs ≥ baseline,
- no check that previously PASSED drops to FAIL more than once in
  3 runs.

The current baseline is `mavrinsky_baseline_2026_06_14`:

> 4 PASS / 3 PARTIAL / 3 FAIL on best run (`mavrinsky_006`), with
> known FAILs concentrated on (1) title extraction, (9) fit.axes
> empty in some runs, (10) rewrite_plan empty when mismatches is
> empty.

Future baselines must be named and dated; do not overwrite this one
when introducing new runs.

---

## What this benchmark deliberately does NOT measure

- aesthetic / stylistic quality of the LLM prose;
- whether venue suggestions are *good* ones — only that the
  pipeline produces a structured set with the right shape;
- adaptation correctness — only structural presence and
  protected-core gating;
- per-token cost or latency.

These belong in separate harnesses if needed.
