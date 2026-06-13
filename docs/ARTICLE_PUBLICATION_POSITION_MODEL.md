# Article Publication Position Model — Reference Exemplar

**Status:** historical draft. SUPERSEDED by
[PUBLICATION_INTEGRABILITY_MODEL_v1.md](PUBLICATION_INTEGRABILITY_MODEL_v1.md)
as the authoritative target. This file is retained as a layered reading
of the same idea, not as a code contract.
**Companion to:** [FIELD_POSITION_MODEL.md](FIELD_POSITION_MODEL.md).
**Relation:** this document is the **qualitative, narrative, evidence-anchored**
overlay; FieldPositionModel is the **quantitative coordinate** overlay.
Both sit above the canonical `ArticleModel` (spec §6.3) and complement —
not replace — it.

---

## 1. Why this document exists

The earlier "gold JSON" exemplar for ArticleModel was downgraded to
**ArticleModel-lite / linguistic extraction baseline v0.1**. It is fine
for checking that an agent can read an abstract and emit claims. It is
NOT a Kairon-grade reference for "what does this article do as an
academic move, and in which conversation can it enter as a native
voice?". This document fixes that gap by recording the corrected
seven-layer structure as a reference exemplar that future agents,
prompts, and tests can target.

The exemplar is reproduced verbatim in §2 so it is preserved as
written. The reconciliation against canon (spec) and code follows
in §3–§5.

---

## 2. The seven-layer model (reference exemplar)

ArticleModel for Kairon is not a linguistic model of the text, not a
summary card, not a bibliographic record, and not an arbitrary
ontological annotation. It is a **publication-integrability model**: a
structure that shows in which disciplinary conversation the work can
enter, whether it speaks there as a native voice, what kind of move it
makes, what citational and theoretical debts it acknowledges, which it
ignores, where it will be received as internal, where as translatable,
and where as foreign.

Master formula:

```
text-as-content
+ article-as-academic-move
+ position-in-the-disciplinary-field
+ stance-toward-schools-camps-authors-conflicts
+ citation-ecology
+ kind-of-publication-container
+ price-of-adaptation
+ risk-of-losing-protected-core
```

### Layer I — Source & Manuscript

```
title_current; abstract_current; language; article_stage; input_mode;
word_count; section_count; reference_count; abstract_length;
has_references_section; has_methods_section;
has_data_availability_statement; has_ai_disclosure
```

Document layer. Necessary but not the model.

### Layer II — Article-as-Move

```
problem_statement; research_question; object_of_inquiry; core_claims;
argument_move_type; argument_move_description; method_status;
method_description; genre_current; novelty_mode
```

`argument_move_type` is more decisive than `genre_current`. A journal
may accept a theoretical essay yet reject the specific move when it
does not match the field's norm.

### Layer III — Field Position

```
primary_discipline; disciplinary_registers; field_coordinates;
schools_and_traditions; tribes_or_camps; camp_alignment; camp_distance;
canonical_authors_present; canonical_authors_missing;
missing_citations_as_signal; field_core_nonnegotiables;
field_boundary_conditions
```

Position is not a topic list. "Philosophy of technology" is not a
position. Position begins when the camp is named: Simondonian line,
Stieglerian line, analytic philosophy of artifacts, STS/ANT,
poststructuralist media theory, phenomenology of technology, HCI/design
studies, or their conflictual assembly.

### Layer IV — Citation Ecology

```
citation_ecology_current; citation_ecology_expected_by_field;
citation_bridges_needed; citation_debt; citation_gap_by_pathway;
bibliography_size_fit; bibliography_language_fit;
bibliography_recency_fit; bibliography_camp_signal;
dangerous_missing_names; decorative_citations;
overclaiming_risk_from_citation_gap
```

Who is **not** cited is also evidence. Latour-absent in STS,
Simondon/Stiegler-absent in philosophy of technics,
Manovich/Galloway/Hui-absent in media/interface studies — different
signals for different venues.

### Layer V — Publication Pathway

For each pathway:

```
pathway_id; discipline_name; tribe_name; fit_strength; why_this_pathway;
required_reframe; required_citation_bridges; required_argument_change;
required_examples_or_cases; field_core_risk; rewrite_effort;
possible_venue_types; example_venue_names; language_options;
indexing_options; strategic_value_notes
```

A pathway is not a journal list. It is a possible way of becoming an
article inside a specific community.

### Layer VI — Fit / Mismatch / Adaptation

For each target venue or venue family:

```
topic_fit; discipline_fit; tribe_fit; school_fit; argument_move_fit;
genre_fit; method_fit; citation_ecology_fit; novelty_fit;
language_register_fit; formal_compliance_fit; author_eligibility_fit;
publication_regime_fit; reviewer_risk; rewrite_effort; field_core_risk;
strategic_value; unknowns; evidence_refs
```

`MismatchMap` should show **where friction arises**: topic native, move
foreign; school native, citation debt unpaid; argument strong, format
wrong; venue fits but adaptation destroys protected core.

### Layer VII — Protected Core / Transformation

```
protected_core; mutable_zones; forbidden_reframes; allowed_reframes;
sibling_manuscript_options; acceptable_loss; unacceptable_loss;
questions_for_author
```

This layer protects the thought from "successful" publishing damage.
If a venue asks to remove desire, subject, dispositif and keep only UX
patterns, that adaptation may raise the HCI fit while destroying the
article. The system must see this.

### Worked example (anchor)

A worked anchor instance for the article *"Желание, виртуальность и
интерфейс"* by Маvrинский (greedy / generous interface ontology,
Foucault / Deleuze-Guattari / Agamben lineage) is held by the user
as **Article Publication Position Model — gold instance v1**. When we
codify §3.4 below into agent prompts, this instance becomes the
reference fixture.

---

## 3. Coverage map against existing code

| Layer | Already in `src/kairoskopion/schema.py` | Gap to fill |
|---|---|---|
| I Source & Manuscript | `ArticleModel.title_current`, `abstract_current`, `language`, `article_stage`, `input_mode`, `word_count`, `section_count`, `reference_count`, `abstract_length`, `has_*` flags; `FieldPositionModel.article_readiness` (manuscript_stage, completeness, formal_compliance_score) | None — full coverage |
| II Article-as-Move | `ArticleModel.problem_statement`, `research_question`, `object_of_inquiry`, `core_claims`, `genre_current`, `novelty_mode`, `method_status`, `method_description`; `ArticleSemanticProfile.argument_move_type`, `argument_move_description`; `FieldPositionModel.argument_move_vector`, `novelty_mode` | None — vectorized form already exists |
| III Field Position | `ArticleSemanticProfile.disciplinary_registers`, `primary_discipline`, `schools_and_traditions`, `theoretical_shoulders`, `opponents_or_foils`; `FieldPositionModel.discipline_vector`, `school_affiliation_vector`, `citation_network_signature`, `opponents_and_foils`, `subdiscipline_address` | `tribes_or_camps` as `list[{tribe, relation, reason}]` (qualitative), `camp_alignment`, `camp_distance`, `missing_citations_as_signal`, `field_core_nonnegotiables`, `field_boundary_conditions` |
| IV Citation Ecology | `ArticleModel.citation_ecology_current`; `CitationExpectationProfile` (typical_reference_count, dominant_traditions, expected_bridge_references, self_citation_rate, recency_bias, canonical_works_expected, absent_traditions_risk); `CitationPlan`; `FieldPositionModel.citation_network_signature` (must_cite, typically_cite, never_cite, conspicuous_absence, bridge_traditions) | `dangerous_missing_names`, `decorative_citations`, `overclaiming_risk_from_citation_gap`, `citation_gap_by_pathway`, `bibliography_size_fit`, `bibliography_language_fit`, `bibliography_recency_fit`, `bibliography_camp_signal` |
| V Publication Pathway | `DisciplinaryPathway` (10 fields including `required_adaptations`, `field_core_risk`, `language_options`, `indexing_options`, `strategic_value_notes`, `example_venue_names`, `rank`) | Decompose `required_adaptations` into `required_reframe`, `required_citation_bridges`, `required_argument_change`, `required_examples_or_cases`; add `tribe_name`, `why_this_pathway`, `rewrite_effort` (currently implicit) |
| VI Fit / Mismatch | `FitAssessment.axes` (12 axes, `list[dict]`); `MismatchMap`; `MismatchItem.field_core_risk`; `FieldPositionModel.compute_field_position_fit` (11 numeric axes with containment/distance) | Additional axis kinds: `tribe_fit`, `school_fit`, `reviewer_risk`, `strategic_value` — schema-compatible since `axes` is `list[dict]` |
| VII Protected Core / Transformation | `ArticleModel.protected_core`, `mutable_zones`, `protected_core_status`; `ArticleVariant` (sibling manuscripts) | `forbidden_reframes`, `allowed_reframes`, `acceptable_loss`, `unacceptable_loss`, `questions_for_author` |

**Verdict:** layers I, II, VI are fully covered. Layers III, IV, V, VII
have well-defined deltas, each small (1 dataclass or 3–8 new fields).
Nothing in the seven-layer model contradicts the existing schema; every
addition is purely additive.

---

## 4. Coverage map against canon (KAIRON_TECHNICAL_SPEC §6.3, §FitAssessment)

The master spec §6.3 lists the canonical ArticleModel fields. Cross-checking:

- `article_structure` (canon) → `argument_move_type` (proposed) is a
  strict refinement, compatible.
- `theoretical_shoulders`, `opponents_or_contrasts`, `key_terms`,
  `citation_ecology_current`, `bibliography_status`,
  `empirical_material_status`, `audience_current`, `audience_candidates`,
  `publication_intent`, `protected_core`, `mutable_zones`,
  `high_risk_zones` (canon) → all explicitly named in §6.3 of the spec
  and present in our `ArticleModel` (or in `ArticleSemanticProfile` for
  the semantic ones). The seven-layer model groups them into III–IV–VII
  without renaming.
- Canon §FitAssessment requires the assessment to include "topic fit,
  discipline fit, genre fit, argument fit, method fit, citation ecology
  fit, novelty fit, language/register fit, formal compliance fit, author
  eligibility, publication regime fit, effort, risk, time, strategic
  value, confidence, evidence refs and unknowns." Our `FitAssessment`
  currently models 12 of these as `axes[]`; the seven-layer model
  proposes adding `tribe_fit`, `school_fit`, `reviewer_risk`,
  `strategic_value` as additional axes — strictly **expanding** the
  canon, not contradicting it.
- Canon rule: no single fit score; preserve unknowns; protected core is
  a first-class field; sibling manuscripts via `ArticleVariant`;
  evidence trail for every claim — all preserved by the seven-layer
  model. No rules are broken.

**Verdict:** the seven-layer model is canon-compatible. It is in fact a
faithful elaboration of what the spec describes as "publication-facing
semantic model of the article" + "Fit and Adaptation Context" + "field
core risk" + "sibling trajectories", rendered into named, agent-extractable
slots.

---

## 5. Decision

This model **complements** the existing implementation. It is **not** a
replacement for `ArticleModel`, `ArticleSemanticProfile`,
`FieldPositionModel`, `DisciplinaryPathway`, or `FitAssessment`.

### Division of labour

- `ArticleModel` (canon §6.3) → Layer I (document) and Layer II
  (article-as-move) — already largely covered.
- `ArticleSemanticProfile` → Layer III base (disciplines, schools,
  theoretical shoulders, argument move) — already covered.
- `FieldPositionModel` → Layer III as coordinates + Layers IV (citation
  network signature) and V (envelopes for venues) — quantitative.
- `DisciplinaryPathway` → Layer V (pathways) — covered, needs field
  decomposition.
- `FitAssessment` + `MismatchMap` → Layer VI — covered, needs new axis
  kinds.
- New dataclasses (proposed below) → Layers III-qualitative,
  IV-diagnostics, VII-transformation policy.

### What "go further" means

If the user confirms, the next session should implement **only the
deltas**, one dataclass at a time, each with a deterministic builder,
an LLM prompt family, an agent, and tests:

1. **`IntegrabilityModel`** — qualitative companion to FPM. Fields:
   `tribes_or_camps: list[{tribe_name, relation, reason}]`,
   `missing_citations_as_signal: dict[pathway_id, str]`,
   `field_core_nonnegotiables: list[str]`,
   `field_boundary_conditions: list[str]`,
   `integrability_verdict: str` (strongest_home / nearest_transformable
   / high_risk_zones).
   Built by a new agent `IntegrabilityAuditor` over
   `ArticleModel + ArticleSemanticProfile + FieldPositionModel`.
2. **Extend `DisciplinaryPathway`** — split `required_adaptations` into
   `required_reframe`, `required_citation_bridges`,
   `required_argument_change`, `required_examples_or_cases`; add
   `tribe_name`, `why_this_pathway`, `rewrite_effort`. Keep the
   aggregate field for back-compat.
3. **`CitationEcologyDiagnostics`** — extend `CitationEcologyReport`:
   `dangerous_missing_names: list[str]`,
   `decorative_citations: list[str]`,
   `overclaiming_risk_from_citation_gap: str | None`,
   `bibliography_size_fit`, `_language_fit`, `_recency_fit`,
   `_camp_signal`.
4. **`TransformationPolicy`** — new dataclass guarding `RewritePlanner`
   output: `forbidden_reframes`, `allowed_reframes`, `acceptable_loss`,
   `unacceptable_loss`, `questions_for_author`. The planner must
   refuse to emit changes intersecting `forbidden_reframes`.
5. **Add axes to `FitAssessment.axes`** — `tribe_fit`, `school_fit`,
   `reviewer_risk`, `strategic_value`, `field_core_risk` — no schema
   change required (axes are already `list[dict]`).

Total cost estimate: one focused sprint per dataclass plus one extra
sprint to wire them through `Case` (similar in shape to the
just-completed `FieldPositionModel` wiring), with corresponding tests.

### Non-goals

- Do not hardcode camp names (Simondon, Stiegler, Latour) in enums or
  schema. They are data, not structure.
- Do not introduce a single integrability score. Verdict is a label
  plus a structured breakdown.
- Do not invent a separate "Mavrinsky-specific" type. The worked
  example in §2 is a fixture instance, not a schema.
- Do not bundle all five deltas into one mega-commit; one dataclass
  per branch.

---

## 6. Final verdict

The seven-layer Article Publication Position Model **fits the codebase
and the canon as a complement**. There is no overlap that requires
deletion, no contradiction that requires migration. The path forward is
five small additive deltas, each prepared by the wiring patterns
already validated by the FPM integration (commit `cb464f8` on
`feature/wire-fpm-pipeline`).

**Recommendation:** treat this document as the reference exemplar going
forward. Use the §2 layer descriptions to author LLM prompts; use the
§3–§4 coverage maps to scope each follow-up sprint; use the §5
decisions as the ordered backlog.
