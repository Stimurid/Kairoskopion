# Venue-side deterministic benchmark #001

**Date:** 2026-06-14
**Branch:** `feature/venue-side-golden-baseline`
**Run ID:** `mavrinsky_venue_det_001`
**Goal:** prove the new venue-side rubric works internally on a
synthetic Mavrinsky venue pool — no live HTTP, no LLM, no
`EditorialBoardCloud` adapter, no new adapters.

---

## 1. Inputs

| input | path | committed? |
|---|---|---|
| article FPM (synthetic, gold-aligned) | `benchmarks/fixtures/mavrinsky_venue_side/article_fpm.json` | yes |
| venue pool (5 synthetic archetypes) | `benchmarks/fixtures/mavrinsky_venue_side/pool.json` | yes |
| rubric | `benchmarks/golden/venue_source_layer_map.md` | yes |
| topology gold | `benchmarks/golden/mavrinsky_venue_side_gold.md` | yes |
| funnel doc | `benchmarks/golden/source_acquisition_funnel.md` | yes |
| harness | `scripts/run_venue_side_benchmark.py` | yes |

The five fixture venues are clearly marked `[FIXTURE]` in
`canonical_name` and `publisher` and **do not impersonate real
journals**. Each carries `disciplinary_cluster` plus a
`fixture_corpus_summary` block (corpus_size + method_distribution +
school_distribution + genre_distribution + citation_stats) that the
harness materialises into a `CorpusAnalysisResult` for the hull
builder.

## 2. Command

```powershell
python scripts/run_venue_side_benchmark.py `
    --article-fpm  benchmarks/fixtures/mavrinsky_venue_side/article_fpm.json `
    --fixture-pool benchmarks/fixtures/mavrinsky_venue_side/pool.json `
    --output       private_inputs/runs/mavrinsky_venue_det_001
```

No `--allow-live`. No LLM env. Pure deterministic.

## 3. Outputs

Under `private_inputs/runs/mavrinsky_venue_det_001/venue/` (gitignored):

| file | bytes | what |
|---|---|---|
| `01_pool.json` | ~6 KB | 5 candidates after pool stage |
| `02_shortlist.json` | ~7 KB | 5 candidates with `pathway_decision` |
| `03_deep_dossiers.json` | ~16 KB | 5 dossiers with venue FPM + `field_position_fit` |
| `04_scorecard.json` | ~3 KB | per-cluster envelope + label checks |

## 4. Scorecard summary

| metric | value |
|---|---|
| deep_dossier_count | 5 |
| clusters_covered | 5 / 5 |
| **PASS** | **4** |
| **PARTIAL** | **1** |
| **FAIL** | **0** |
| UNDETERMINED | 0 |

Per-cluster (combined / envelope / label):

| cluster | combined | envelope | label |
|---|---|---|---|
| continental_media_philosophy | **PASS** | PASS (Deleuze_Guattari, Foucault, Agamben hits; method `theoretical` accepted) | UNDETERMINED (hull-only FPM → `not_enough_data`) |
| philosophy_of_technology | **PASS** | PASS (Simondon, Stiegler, Yuk_Hui hits; method `theoretical` accepted) | UNDETERMINED |
| STS_platform_studies | **PASS** | PASS (Latour_ANT hit; method `case_study` accepted) | UNDETERMINED |
| HCI_design_theory | **PASS** | PASS (HCI_affordances hit; method `experimental` accepted) | UNDETERMINED |
| RU_philosophy_regime | **PARTIAL** | PARTIAL (required dims empty by cluster gold — manual review required per §2.5) | UNDETERMINED |

Label `UNDETERMINED` for all five clusters is **the correct outcome**.
The corpus-hull-only venue FPM covers 5 of the 11 axes
`compute_field_position_fit` checks (school, argument_move,
evidence_type, method, formalization). The remaining 6
(formalization_level, accessibility_index, jargon_density, language,
genre_formality, geographic_affinity) require A guidelines + C
registry sources, which are deliberately out of scope for this
baseline. Per rubric §3.5 (Unknown ≠ absent), the harness treats
this as honest unknown, not failure.

## 5. What the hull builder successfully computed

For each cluster, the builder produced a usable `school_envelope`,
`argument_move_envelope`, `evidence_type_profile`, and `method_stance`
from the synthetic corpus alone:

| cluster | top schools in envelope | accepted methods | rejected methods |
|---|---|---|---|
| continental | Deleuze_Guattari, Foucault, Agamben, Heidegger | theoretical | case_study, experimental |
| philtech | Simondon, Stiegler, Yuk_Hui, Heidegger_on_technology, Verbeek | theoretical, case_study | experimental |
| STS | Latour_ANT, Callon, STS_empirical, Foucault | case_study, interview_ethnographic | experimental |
| HCI | HCI_affordances, dark_patterns, persuasive_technology, interaction_design, Foucault | experimental, user_study, quantitative_data, design_intervention | — |
| RU | Russian_metaphysical_tradition, continental_post_Soviet, phenomenological_tradition, Foucault, Deleuze_Guattari | theoretical, textual | — |

For Mavrinsky's article point (DG 0.80, Agamben 0.70, Foucault 0.65,
concept_reconstruction 0.45, concept_introduction 0.30,
theoretical_argument 0.85), `compute_field_position_fit` flagged:

- **continental:** `school_fit=outside dist=0.33, method_fit=adjacent` —
  article is slightly above the continental envelope's upper edge on
  DG (article 0.80 vs envelope `[0.26, 0.66]`). Reads as "more
  continental than the average article in this cluster", consistent
  with the gold's "near-native fit" + minor rhetorical polish.
- **philtech:** `school_fit=outside dist=0.55, method_fit=adjacent` —
  envelope wants Simondon/Stiegler/Yuk_Hui dominantly; article has 0
  for all three. This is the "missing citation bridge" signal from
  the gold §2.2. Correct.
- **STS:** `school_fit=outside, method_fit=adjacent` — envelope
  accepts `case_study` and `interview_ethnographic`; article method is
  `philosophical_analysis`. This is the method/evidence mismatch the
  gold §2.3 names as the sibling-manuscript trigger. Correct.
- **HCI:** `school_fit=outside, method_fit=adjacent` — envelope
  dominated by HCI_affordances + dark_patterns + interaction_design;
  article carries 0 on those and 0.80 on DG (envelope ~0.05 ceiling for
  DG). This is the UX-reduction danger the gold §2.4 names. Correct.
- **RU:** `school_fit=outside, method_fit=adjacent` — envelope has
  Russian_metaphysical/continental_post_Soviet dominant; article
  carries 0.10 on continental_post_Soviet and 0.80 on DG. Method
  `theoretical` is accepted. Cluster acceptance per gold §2.5 is
  per-journal; the harness correctly emits PARTIAL with "manual
  review".

## 6. What remained unknown (correctly)

- `discipline_envelope` for every venue FPM — left empty with explicit
  `unknowns` marker. Builder docstring: requires OpenAlex concepts
  (G corroborator) at harness level, not at builder level.
- `geographic_affinity` for every venue FPM — empty. Requires E
  editorial board + F authors-of-corpus.
- `institutional_signals` for every venue FPM — empty. Requires C
  registry cards.
- `language_register` (`jargon_density`, `language`) for every venue
  FPM — empty. Requires A guidelines.
- `formalization_level`, `audience_level`, `genre_position.genre_formality`
  — empty for the same reason.

Every empty axis carries a non-silent explanation in
`venue_fpm.unknowns`. None of them was coerced to a default, null,
or fabricated value. **Caveat §3.5 holds.**

## 7. Source-layer authority rules — verification

Six fundamental caveats from `venue_source_layer_map.md` §3:

| caveat | held in this run? | check |
|---|---|---|
| §3.1 official scope ≠ corpus fact | **yes** | `scope_summary` in pool data was never read by the builder; only `fixture_corpus_summary` was. `tests/test_corpus_hull_builder.py::TestOfficialScopeNotCorpusFact` asserts the builder signature does not accept any scope parameter. |
| §3.2 indexing ≠ fit | **yes** | RU fixture carried `_vendor_indexing_claim: "ВАК-перечень, РИНЦ"` inside `citation_stats`; the builder did not promote it to `institutional_signals` or to any fit axis. `tests/test_corpus_hull_builder.py::TestIndexingNotFit` confirms. |
| §3.3 full text ≠ metadata authority | **yes** | The builder reads only the analyzer's pattern outputs; nothing about full text reaches `venue_identity` / `institutional_signals`. Tests confirm. |
| §3.4 editorial board = inference | **yes** | No `EditorialBoardCloud` was produced. `geographic_affinity` is empty for all five dossiers. The harness does not synthesise a board signal. |
| §3.5 unknown ≠ absent | **yes** | Five-of-six unknown axes carry non-silent `unknowns` markers in the venue FPM. The label `UNDETERMINED` for all five clusters is honest unknown, not silent failure. |
| §3.6 incomplete graph ≠ absence of tradition | **yes** | School entries below the noise floor (e.g., `Latour_ANT: 0.03` in the continental fixture) are filtered from the envelope but not asserted as "Latour is taboo". They simply do not appear; the gold §3.6 + scorer treat their absence as undetermined. |

## 8. PASS by cluster vs gold expectations

| cluster | gold expectation | observed | verdict |
|---|---|---|---|
| continental/media philosophy | near-native fit; DG/Foucault/Agamben canonical | envelope contains all three; method `theoretical` accepted; article at upper edge | **PASS** |
| philosophy of technology | citation-bridge fit; Simondon/Stiegler/Hui canonical; article missing bridge | envelope dominated by Simondon/Stiegler/Yuk_Hui; article has 0 for all three → mismatch correctly visible | **PASS** |
| STS/platform studies | sibling/high-rewrite; method/evidence mismatch expected | envelope accepts case_study; article is theoretical only → method_fit `adjacent`, school distant | **PASS** |
| HCI/design theory | destructive/sibling-only; UX-reduction danger | envelope is HCI_affordances + dark_patterns + interaction_design; no DG; article has 0 on those; method requires experimental | **PASS** |
| Russian philosophy | language-and-regime fit, not automatically field fit | envelope contains Russian_metaphysical / continental_post_Soviet / phenomenological dominantly; harness emits PARTIAL with "manual review" per gold §2.5 | **PARTIAL** (per gold's own acceptance shape) |

## 9. Tests / build

- `pytest` 1322 passed, 4 deselected.
- `npx tsc --noEmit` clean.
- `npx vite build` clean.
- `git status` clean after the run (the run output lands under
  `private_inputs/runs/` which is `.gitignore`'d).

## 10. Whether the branch is merge-ready

**A: `feature/venue-side-golden-baseline` is internally consistent.**
Rubric ↔ fixture ↔ harness ↔ scorer cohere. The five-cluster
topology gold predicts the observed envelope contents and the
observed fit-axis distances.

**B: A still HOLDS — do not merge to main until article-side rc17
lands.** This branch is doctrine baseline + deterministic builder +
synthetic harness proof. Merging it to `main` ahead of rc17 would
recreate the rc16-vs-main drift the audit just closed. The right
order is:

1. close `fix/llm-agent-tolerance-mavrinsky` → main → tag rc17;
2. merge `feature/venue-funnel-v1-canon` (doctrine) → main → rc18;
3. merge `feature/venue-side-golden-baseline` (this branch, with this
   benchmark proof) → main → rc19.

**C remains deferred.** No `EditorialBoardCloud` live adapter in this
branch. Contract is defined; sprint is the next venue-side milestone.

## 11. Caveats and limits of this proof

- **Synthetic pool only.** Five archetypes, not 30–80 candidates. The
  pool stage's expected access_status distribution (rubric §1 of the
  funnel doc) is untested at scale; it will be exercised by the live
  discovery sprint.
- **No `EditorialBoardCloud`.** Geographic envelope absent across all
  five dossiers. Cluster 5 (RU) is therefore PARTIAL by construction:
  cluster gold §2.5 says field fit varies per journal's editorial
  line, and editor line isn't observable from corpus alone.
- **`compute_field_position_fit` is partial by design here.** Six of
  11 axes return UNKNOWN. The `not_enough_data` label is a
  consequence, not a bug; expanding source-layer coverage closes it.
- **No prompt engineering, no LLM, no temperature work** — that is
  Agentum territory by project memory.

## 12. Recommendation

B (this benchmark proof) **passed.** A (merge to main) **remains held**
until article-side rc17 closes. C (live `EditorialBoardCloud`) **remains
deferred**.

Next single milestone: close article-side rc17 (a separate branch),
then unblock the merge train per §10.

End of report.
