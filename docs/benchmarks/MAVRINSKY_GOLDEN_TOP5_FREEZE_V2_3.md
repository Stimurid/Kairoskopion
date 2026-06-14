# Mavrinsky golden top-5 freeze (v2.3)

> **Lifecycle status: `GOLDEN_ANALYSIS_INPUT`**
> **This is NOT a submission recommendation.** It is a structured,
> evidence-traceable snapshot of the top-5 venues Kairoskopion has
> assembled, frozen for **manual methodological golden analysis** by
> the operator/research team. Do not act on this ordering without
> human review.

**Freeze date:** 2026-06-14
**Branch:** `feature/venue-blockers-vfc2-corpus-board-ru`
**Baseline commit:** 72aa3b1 (after v2.3 closure pass)
**Registry total VPKGs:** 34
**Bucket counts:** 4 good_fit · 5 possible_but_costly · 0 sibling · 0 poor_fit · 25 insufficient_data
**Machine-readable companion:** `private_inputs/runs/mavrinsky_selection_v2_3_001/GOLDEN_TOP5_FREEZE_V2_3.json`

---

## Top-5 (bucket-first ranker, B1 from v2.1; honest reordering after board attach)

The v2.3 board attach moved Foucault Studies's `evidence_confidence`
from medium → strong (board=`present` lifted completeness), tying
with Memory, Mind & Media. The deterministic alphabetical tiebreak
puts F before M. This is correct behaviour — not a regression.

### 1. Foucault Studies — `good_fit`

| field | value | evidence |
|---|---|---|
| publisher | University of Copenhagen | operator_seed_canonical |
| ISSNs | 1832-5203 | operator_seed_canonical |
| OpenAlex source id | `S2735408488` (verified) | metadata_api_openalex |
| homepage | `https://rauli.cbs.dk/index.php/foucault-studies` | metadata_api_openalex |
| corpus hull | **present** (25 works, 13 abstracts) | openalex_corpus_observation |
| top corpus terms | foucault · critique · critical · michel · criticism | openalex_corpus_observation |
| formal submission profile | **partial** (5 fields) | external_claim_html, source: `rauli.cbs.dk/.../about/submissions` |
| editorial board cloud | **present** (18 members, EXTRACTED_FROM_OFFICIAL_HTML) | source: `rauli.cbs.dk/.../about/editorialTeam` |
| fit axes (summary) | topic=medium · disc=medium · arg_form=medium · fcr=strong · rewrite=strong · cite_ecology=medium · confidence=strong | mixed (per-axis evidence in JSON) |
| mismatches | 0 | — |
| label reasons | "topic=medium, rewrite=strong, fcr=strong, citation_ecology=medium, confidence=strong" | — |

### 2. Memory, Mind & Media — `good_fit`

| field | value | evidence |
|---|---|---|
| publisher | Cambridge University Press | metadata_api_openalex |
| ISSNs | 2635-0238 | metadata_api_openalex |
| OpenAlex source id | attached | metadata_api_openalex |
| corpus hull | **present** (25/25 abstracts) | openalex_corpus_observation |
| top corpus terms | memory · collective · anxiety · media · social | openalex_corpus_observation |
| formal submission profile | **partial** (article_types, open_access) | external_claim_html, source: cambridge.org/.../author-information-form-faqs |
| editorial board cloud | **present** (9 members, EXTRACTED_FROM_OFFICIAL_HTML) | source: cambridge.org/.../editors/journal-development |
| fit axes (summary) | topic=medium · arg_form=medium · fcr=strong · rewrite=strong · cite_ecology=medium · confidence=strong |  |
| mismatches | 0 | — |
| label reasons | "topic=medium, rewrite=strong, fcr=strong, citation_ecology=medium, confidence=strong" | — |

### 3. Techné: Research in Philosophy and Technology — `good_fit`

| field | value | evidence |
|---|---|---|
| publisher | Philosophy Documentation Center | operator_seed_canonical |
| ISSNs | 1091-8264 | operator_seed_canonical |
| OpenAlex source id | attached | metadata_api_openalex |
| corpus hull | **present** (25 works) | openalex_corpus_observation |
| top corpus terms | technology · philosophy · technological · theory · media | openalex_corpus_observation |
| formal submission profile | **partial** (6 fields: word_limit, abstract_word_limit, reference_style, article_types, open_access, ai_policy_mentioned) | external_claim_html, source: pdcnet.org/techne/Submission-Guidelines |
| editorial board cloud | **present** (25 members, EXTRACTED_FROM_OFFICIAL_HTML) | source: pdcnet.org/techne/Editorial-Team |
| fit axes (summary) | topic=medium · fcr=strong · rewrite=strong · cite_ecology=medium · confidence=medium |  |
| mismatches | 0 | — |
| label reasons | "topic=medium, rewrite=strong, fcr=strong, citation_ecology=medium, confidence=medium" | — |

### 4. Philosophy & Technology — `good_fit`

| field | value | evidence |
|---|---|---|
| publisher | Springer | operator_seed_canonical |
| ISSNs | 2210-5433, 2210-5441 | operator_seed_canonical |
| OpenAlex source id | `S23735784` | metadata_api_openalex |
| homepage | `https://www.springer.com/journal/13347` | metadata_api_openalex |
| corpus hull | **present** (25 works, 18 abstracts) | openalex_corpus_observation |
| top corpus terms | reply · beyond · philosophy · technology · epistemic | openalex_corpus_observation |
| formal submission profile | **missing** — Springer SPA returned 0 outgoing links on homepage hop | INACCESSIBLE / JS_ONLY |
| editorial board cloud | **missing** — `SPRINGER_BOARD_INACCESSIBLE_SPA_OR_NOT_FOUND` after v2.3 fallback (tried `/editors`, `/editorial-board`, `/editorial-team` — all returned HTTP error) | stable honest failure tag |
| fit axes (summary) | topic=medium · fcr=strong · rewrite=strong · cite_ecology=medium · confidence=medium |  |
| mismatches | 0 | — |
| label reasons | "topic=medium, rewrite=strong, fcr=strong, citation_ecology=medium, confidence=medium" | — |

### 5. Le foucaldien — `possible_but_costly`

| field | value | evidence |
|---|---|---|
| canonical_name | Le foucaldien (now: Genealogy + Critique) | metadata_api_openalex |
| corpus hull | **present** (25 works, 20 abstracts) | openalex_corpus_observation |
| top corpus terms | foucault · truth · savoir · lieux · michel | openalex_corpus_observation |
| formal submission profile | **partial** (4 fields: reference_style, article_types, open_access, ai_policy_mentioned) | external_claim_html, source: genealogy-critique.net/submissions |
| editorial board cloud | **present** (30 members, EXTRACTED_FROM_OFFICIAL_HTML) | source: genealogy-critique.net/editorialteam |
| fit axes (summary) | topic=weak · fcr=strong · rewrite=strong · cite_effort=strong · confidence=strong |  |
| mismatches | 1 (language_register_fit: RU article → EN/FR venue) | vpkg_evidence |
| label reasons | "topic=weak, rewrite=strong, fcr=strong, citation_effort=strong, confidence=strong" | — |

---

## How to read this freeze for manual analysis

This snapshot is the **evidence-traceable input** for a methodological
golden analysis. For each of the five venues:

1. **Identity** is anchored to OpenAlex Source IDs and (where
   high-confidence) ISSNs — never invented.
2. **Corpus hull** terms come from the latest 25 OpenAlex Works and
   reconstructed abstracts — not a hand-picked sample.
3. **Formal submission profile** is regex-extracted from the
   publisher's own author-guidelines page. Every absent field appears
   as `UNKNOWN_NOT_FOUND` in the JSON, never inferred as "NO".
4. **Editorial board cloud** comes from the publisher's editorial
   team page. Members carry per-member `evidence_status:
   external_claim` (HTML regex) upgraded to `metadata_api_openalex`
   for those resolved via OpenAlex Author. Derived center-of-gravity
   signals (top institutions/countries/concepts) carry the rubric v2
   §3.4 mandated `authority: inference` marker — they are NOT
   psychology, NOT editor preferences.
5. **Fit axes** come from the deterministic 16-axis v1 assessor
   running over the article's gold rubric and venue corpus signals.
   `_bucket_v2` (calibrated) assigns the label with `label_reasons`.

**What this freeze does NOT contain:**

- editor biographies;
- editor preferences ("this editor likes Deleuze");
- Q1/Q2/JCR claims (no Scopus / WoS / Dimensions data);
- ВАК / РИНЦ status (no eLibrary auth);
- final submission recommendation.

**What the next step should be:**

A human (operator or research team) reads this freeze, applies
domain knowledge that Kairoskopion does NOT have — the article's
exact protected core, the author's career considerations, the
language/time-budget constraints — and reaches a submission decision.
The freeze is the **input** to that decision, not the decision.

---

## Honest gaps in this freeze

- **Philosophy & Technology** has no board cloud and no formal
  profile because Springer renders both in JavaScript. Recorded as
  `SPRINGER_BOARD_INACCESSIBLE_SPA_OR_NOT_FOUND`. Next move: either
  a one-shot manual paste of the editor list (not in scope here),
  or a JS-rendering headless-browser adapter (separate sprint).
- **citation ecology** axis is `medium` for the philtech venues but
  the underlying corpus references are not yet wired into the
  citation plan stubs — they name bridge CATEGORIES only, not
  specific anchors. Operator must cross-check the article's
  bibliography against each venue's reference distribution manually.
- **ВАК / РИНЦ tier** for Le foucaldien is irrelevant (it's not a
  Russian-state-indexed journal). For the Russian-language
  candidates (Логос, Вопросы философии, Философские науки) which
  sit in possible_but_costly (positions 6+, not in the top-5),
  ВАК status is `AUTH_REQUIRED` — see
  [`AUTH_AND_PROXY_API_LANDSCAPE.md`](../AUTH_AND_PROXY_API_LANDSCAPE.md) §3.5.

End of freeze.
