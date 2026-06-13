# Kairon / Kairoskopion — Publication Integrability Model v1.0

**Status:** authoritative reference document. Supersedes the seven-layer
draft in [ARTICLE_PUBLICATION_POSITION_MODEL.md](ARTICLE_PUBLICATION_POSITION_MODEL.md)
as the target shape; that earlier document remains useful as a layered
reading of the same idea.
**Companion to:** [FIELD_POSITION_MODEL.md](FIELD_POSITION_MODEL.md)
(quantitative coordinate overlay) and the master
[KAIRON_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md](KAIRON_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md)
(canonical contract).
**Not yet a code contract.** This is the reference exemplar that future
agents, prompts, fixtures, and benchmark assertions must satisfy.

---

## 0. Главный тезис модели

Публикуемость статьи определяется не тем, что она «похожа на журнал» по
словам из title/abstract, и не тем, что она формально соответствует
шаблону. Публикуемость определяется тем, может ли работа быть распознана
как осмысленный ход внутри некоторого дисциплинарного сообщества, школы,
лагеря, publication regime и конкретного venue.

Поэтому ArticleModel в Кайроне не должен быть summary-моделью текста. Он
должен быть минимальной моделью интегрируемости статьи в академический
разговор.

Формула:

```
Article as Text
  → Article as Academic Move
    → Article as Field Position
      → Article as Citation-Ecology Signal
        → Article as Publication Candidate
          → Fit / Mismatch / Adaptation / Core-Risk
```

Если модель не отвечает на вопрос «свой ли это ход для данного
сообщества?», она ещё не является ArticleModel Кайрона.

---

## 1. Общая объектная схема

Система должна хранить не один объект, а связанный пакет:

```yaml
KaironPublicationModel:
  source_packet: SourceEvidencePacket
  article_model: NativeArticleModel
  semantic_profile: ArticleSemanticProfile
  field_position: FieldPositionModel(article)
  submission_scenarios: list[SubmissionScenario]
  pathway_models: list[DisciplinaryPathway]
  venue_candidates: list[VenueModel]
  venue_field_positions: list[FieldPositionModel(venue)]
  fit_assessments: list[FitAssessment]
  mismatch_maps: list[MismatchMap]
  adaptation_plans: list[RewritePlan | ReframePlan | CitationPlan | RiskReport]
  protected_core_policy: ProtectedCorePolicy
  evidence_policy: EvidencePolicy
```

ArticleModel — только один слой. Публикационная работа начинается там,
где ArticleModel сопоставляется с VenueModel через FieldPositionModel и
SubmissionScenario.

---

## 2. SourceEvidencePacket

Этот слой фиксирует, откуда взялись данные и какой у них статус. Без
этого Кайрон превращается в уверенный LLM-чат.

```yaml
SourceEvidencePacket:
  input_sources:
    - source_id
    - source_type: manuscript | abstract | notes | journal_url | CFP | review_letter | corpus_snapshot | user_brief
    - provenance: uploaded_file | drive_doc | web_source | user_statement | inferred
    - access_status: full | partial | inaccessible | stale | unknown
    - extraction_status: parsed | partially_parsed | failed | manual
  evidence_granularity:
    - source_fact
    - text_extracted_claim
    - inferred_pattern
    - corpus_observation
    - user_tacit_note
    - vendor_claim
    - unknown
    - conflicting_evidence
  evidence_refs:
    - ref_id
```

Правило: unknown нельзя превращать в absent. Если система не нашла
политику AI disclosure — это не значит, что её нет; это значит
not verified.

---

## 3. NativeArticleModel

Базовая модель статьи как публикационного кандидата, но ещё не полная
модель поля.

```yaml
NativeArticleModel:
  identity:
    title_current
    abstract_current
    language
    article_stage: abstract | draft | full_manuscript | revision | unknown
    input_mode: abstract_only | full_manuscript | mixed

  content_core:
    problem_statement
    research_question
    object_of_inquiry
    core_claims

  method_and_genre:
    method_status: conceptual_method | empirical_method | case_based | mixed | review_method | unknown
    method_description
    genre_current: research_article | theoretical_essay | systematic_review | commentary | conceptual_article | forum_piece | book_review | unknown

  first_order_positioning:
    disciplinary_register_current
    novelty_mode: new_theory | critique | extension | translation_between_fields | application | synthesis | unknown
    theoretical_shoulders
    citation_ecology_current

  core_protection:
    protected_core
    mutable_zones

  deterministic_diagnostics:
    word_count
    section_count
    reference_count
    abstract_length
    has_references_section
    has_methods_section
    has_data_availability_statement
    has_ai_disclosure

  meta:
    unknowns
    confidence
    lifecycle_status
    extraction_status
```

`disciplinary_register_current` — не позиция, а первичный адрес. Говорит
«где искать», но не говорит «свой ли ты там».

---

## 4. ArticleSemanticProfile

Надстройка над ArticleModel, извлекает то, что нужно для публикационной
диагностики.

```yaml
ArticleSemanticProfile:
  disciplinary_registers:
    - name
    - strength
    - evidence

  primary_discipline

  schools_and_traditions:
    - school
    - relation: internal | adjacent | borrowed | contrastive | decorative | absent_but_relevant
    - strength
    - evidence

  theoretical_shoulders:
    - author_or_school
    - function_in_argument: foundation | bridge | foil | analogy | decoration | missing_expected
    - evidence

  opponents_or_foils:
    explicit_opponents
    implicit_foils
    avoided_polemics

  argument_move:
    argument_move_type:
      problem_statement
      genealogy
      concept_reconstruction
      school_critique
      model_building
      comparative_analysis
      disciplinary_translation
      polemical_essay
      empirical_conceptual_hybrid
      systematic_review
      methodology_piece
      unknown
    argument_move_description

  citation_bridges_needed:
    - target_pathway
    - missing_bridge
    - why_needed
    - core_risk

  citation_ecology_description

  protected_core_candidates
  mutable_zones
  field_core_nonnegotiables

  intended_audience
  audience_expertise_level
```

Если ArticleModel говорит «статья по философии техники», SemanticProfile
должен сказать: «континентальная линия, Делёз/Агамбен, концептуальная
реконструкция, против лакановского желания-как-нехватки, не
STS-case-study».

---

## 5. FieldPositionModel

Центральный слой. Одна и та же модель описывает статью, журнал, секцию,
спецвыпуск, дисциплину, редколлегию и корпус.

Статья = точка или компактный регион. Журнал = envelope. Секция = подрегион.
Редколлегия = облако точек. Корпус = эмпирический hull.
Fit = containment + distance + core-risk.

```yaml
FieldPositionModel:
  entity_type: article | venue | section | issue | editor | discipline | corpus
  entity_id

  disciplinary_position:
    discipline_vector:
      philosophy_of_technology: float
      STS: float
      media_studies: float
      HCI: float
      analytic_philosophy: float
      continental_philosophy: float
      digital_culture: float
    discipline_envelope: null | dict[dimension, [min, max]]
    subdiscipline_address:
      primary
      niche
      working_area

  tribe_position:
    school_affiliation_vector:
      Simondon: float
      Stiegler: float
      Heidegger: float
      Deleuze_Guattari: float
      Foucault: float
      Agamben: float
      Latour_ANT: float
      analytic_artifact_theory: float
      HCI_design: float
      platform_studies: float
    school_envelope: null | dict[dimension, [min, max]]
    citation_network_signature:
      must_cite
      typically_cite
      never_cite
      conspicuous_absence
      decorative_citations
      dangerous_missing_names
    opponents_and_foils:
      explicit_opponents
      implicit_foils
      published_polemics
      avoided_polemics

  argument_position:
    argument_move_vector:
      problem_statement: float
      genealogy: float
      concept_reconstruction: float
      school_critique: float
      model_building: float
      comparative_analysis: float
      disciplinary_translation: float
      polemical_essay: float
      empirical_conceptual_hybrid: float
      systematic_review: float
      methodology_piece: float
    argument_move_envelope: null | dict[move, [min, max]]
    novelty_mode:
      mode
      novelty_claim_strength
      builds_on_or_opposes
    evidence_type_profile:
      theoretical_argument: float
      textual_analysis: float
      case_study: float
      quantitative_data: float
      experimental: float
      archival: float
      interview_ethnographic: float

  methodological_position:
    method_stance:
      explicit_method: bool
      method_family
      method_specificity: low | medium | high
      empirical_component: bool
    formalization_level: float

  audience_and_register:
    audience_level:
      expertise_required: general | educated | specialist | deep_specialist
      presupposed_knowledge
      accessibility_index: float
    language_register:
      language
      register: academic_formal | academic_accessible | semi_popular | popular
      jargon_density: float
      expected_word_count_range
    genre_position:
      genre
      genre_formality: float
      sections_expected

  geo_institutional_position:
    geographic_affinity:
      author_region
      intellectual_tradition_region
      target_audience_region
      language_of_publication
    institutional_signals:
      prestige_tier
      indexing
      open_access
      apc_range
      review_model
      typical_decision_weeks
      author_region_patterns
      board_region_patterns
      anglophone_hegemony_index

  temporal_position:
    recency_of_core_references
    median_reference_year
    reference_time_depth_years
    field_maturity

  readiness:
    manuscript_stage
    completeness
    formal_compliance_score

  meta:
    unknowns
    confidence
    evidence_refs
```

`schools_and_traditions: ["Simondon", "STS"]` ничего не вычисляет.
`school_affiliation_vector + citation_network_signature + venue_envelope`
позволяет видеть дистанцию, containment и цену адаптации.

---

## 6. VenueModel через ту же координатную систему

Журнал описывается в том же пространстве, что и статья.

```yaml
VenueModel:
  venue_identity:
    venue_name
    venue_type: journal | section | special_issue | proceedings | edited_volume | open_review | preprint_reviewed
    publisher
    issn
    url
    language_options

  source_basis:
    aims_scope_sources
    author_guidelines_sources
    editorial_board_sources
    published_corpus_sources
    indexing_sources
    policy_sources

  venue_field_position: FieldPositionModel(entity_type="venue")

  venue_envelope:
    discipline_envelope
    school_envelope
    argument_move_envelope
    evidence_type_envelope
    method_envelope
    language_register_envelope
    genre_envelope

  formal_requirements:
    word_count_range
    abstract_required
    reference_style
    section_structure
    article_types
    author_eligibility
    APC
    OA_policy
    AI_policy
    data_policy
    ethics_policy
    COI_policy
    review_model

  trust_and_compliance:
    peer_review_clarity
    indexing_archiving
    persistent_identifiers
    fee_transparency
    license_clarity
    COPE_DOAJ_OASPA_signals
    predatory_risk_signals
```

Формальные требования важны, но они ниже field fit. Журнал может
идеально подходить по теме и быть невозможен по формату; может идеально
подходить по формату и быть чужим по лагерю.

---

## 7. SubmissionScenario

Одна и та же статья имеет разные fit в зависимости от цели автора.

```yaml
SubmissionScenario:
  scenario_id
  user_goal:
    prestige
    speed
    Scopus_WoS
    VAK_RSCI
    international_visibility
    local_academic_credit
    special_issue_entry
    intellectual_network_entry
    PhD_or_tenure_requirement
    low_APC
    open_access
  allowed_transformations:
    translate_language: bool
    change_title: bool
    expand_bibliography: bool
    add_cases: bool
    change_argument_move: bool
    change_discipline: bool
    split_into_sibling_manuscript: bool
  forbidden_transformations:
    - remove_protected_core
    - fabricate_method
    - simulate_empirical_data
    - add_fake_citations
  constraints:
    time
    budget
    language
    coauthors
    author_affiliation
    country_or_sanction_risks
```

Без SubmissionScenario fit ложен.

---

## 8. FitAssessment

Не score. Многомерное отношение координат.

```yaml
FitAssessment:
  article_id
  venue_id
  scenario_id

  fit_vector:
    topic_fit:
      status: contained | adjacent | outside | unknown
      distance
      evidence_refs
    discipline_fit
    tribe_fit
    school_fit
    argument_move_fit
    method_fit
    evidence_type_fit
    citation_ecology_fit
    novelty_fit
    audience_fit
    language_register_fit
    genre_fit
    formal_compliance_fit
    author_eligibility_fit
    publication_regime_fit
    trust_compliance_fit

  core_risk_vector:
    discipline_shift_core_risk
    citation_bridge_core_risk
    argument_change_core_risk
    method_change_core_risk
    genre_change_core_risk
    language_register_core_risk

  effort_vector:
    bibliography_effort
    argument_rewrite_effort
    method_rewrite_effort
    example_case_effort
    formal_formatting_effort
    translation_effort

  strategic_value:
    field_entry_value
    citation_network_value
    prestige_value
    speed_value
    career_value
    community_fit_value

  verdict:
    label: strong_candidate | possible_but_costly | adjacent_with_reframe | poor_fit | high_core_risk | unknown
    explanation
    confidence
    unknowns
```

Нельзя выводить один процент. Число — только display artifact,
производный от осей.

---

## 9. MismatchMap

```yaml
MismatchMap:
  mismatches:
    - axis: school_fit
      mismatch_type: missing_canonical_citations
      description
      evidence
      adaptation_possible: true
      required_action
      core_risk: low | medium | high

    - axis: argument_move_fit
      mismatch_type: wrong_argument_norm
      description
      adaptation_possible
      required_action
      core_risk

    - axis: method_fit
      mismatch_type: venue_requires_explicit_method
      description
      adaptation_possible
      required_action
      core_risk

    - axis: genre_fit
      mismatch_type: essay_vs_research_article
      description
      adaptation_possible
      required_action
      core_risk

  unknowns_not_absences:
    - field
    - why_unknown
    - how_to_verify
```

Mismatch — не ошибка текста. Отношение между текстом и контейнером.

---

## 10. AdaptationPlan (Rewrite / Reframe / Citation / Risk / Sibling)

```yaml
AdaptationPlan:
  plan_type: rewrite | reframe | citation | risk | sibling_manuscript
  target_pathway_or_venue
  actions:
    - action_id
      target: title | abstract | introduction | literature_review | method | argument | examples | conclusion | references
      action_type: add | remove | rewrite | reframe | split | translate | verify
      reason
      expected_fit_gain
      core_risk
      evidence_refs

  forbidden_moves:
    - move
    - reason

  sibling_options:
    - sibling_title
    - target_field
    - what_changes
    - what_core_is_preserved
    - what_core_is_lost
```

Если адаптация разрушает объект, тезис, школу или novelty mode, это не
«улучшение fit», а high field-core risk.

---

## 11. Как модель работает на практике

1. **Intake** — `SourceEvidencePacket + NativeArticleModel`.
2. **Semantic profiling** — `ArticleSemanticProfile` (школы, лагеря, тип
   хода, оппоненты, citation bridges).
3. **Field positioning** — `FieldPositionModel(article)` (координаты, не
   теги).
4. **Venue profiling** — `VenueModel + FieldPositionModel(venue)` из
   aims/scope, author guidelines, editorial board, corpus, indexing,
   policies, CFP, special-issue page.
5. **Coordinate comparison** —
   `FitAssessment = compare(article_FPM, venue_FPM, SubmissionScenario)`.
6. **Mismatch extraction** — `MismatchMap`.
7. **Adaptation** — `RewritePlan / ReframePlan / CitationPlan / RiskReport`.
8. **Human decision** — target venue / другой pathway / sibling
   manuscript / отказ от venue / углубление WhiteCrow/Field reduction.

---

## 12. Опорный пример (Мавринский)

```yaml
article_field_position:
  discipline_vector:
    continental_philosophy: 0.75
    philosophy_of_technology: 0.55
    media_philosophy: 0.55
    interface_theory: 0.45
    digital_culture: 0.30
    STS: 0.15
    HCI_design: 0.10
    analytic_philosophy: 0.05

  school_affiliation_vector:
    Deleuze_Guattari: 0.80
    Agamben: 0.70
    Foucault: 0.65
    Leibniz: 0.25
    Heidegger: 0.20
    Lacan: -0.35
    Simondon: 0.00
    Stiegler: 0.00
    Latour_ANT: 0.00
    HCI_affordance_dark_patterns: 0.00

  citation_network_signature:
    must_cite_for_current_article:
      - Foucault
      - Deleuze
      - Guattari
      - Agamben
    currently_cited:
      - Foucault
      - Deleuze
      - Guattari
      - Agamben
      - Leibniz
      - Heidegger
      - Chernyakov
    conspicuous_absence_by_pathway:
      philosophy_of_technology:
        - Simondon
        - Stiegler
        - Hui
      media_interface_theory:
        - Manovich
        - Galloway
        - media interface studies
      STS:
        - Latour
        - platform studies
      HCI_design:
        - dark patterns
        - affordances
        - persuasive technology
      psychoanalytic_contrast:
        - Lacan

  argument_move_vector:
    concept_reconstruction: 0.45
    concept_introduction: 0.30
    problem_statement: 0.15
    genealogy: 0.10
    empirical_conceptual_hybrid: 0.00
    systematic_review: 0.00

  evidence_type_profile:
    theoretical_argument: 0.85
    textual_analysis: 0.10
    case_study: 0.05
    quantitative_data: 0.00
    experimental: 0.00
    interview_ethnographic: 0.00

  method_stance:
    explicit_method: false
    method_family: philosophical_analysis
    method_specificity: low
    empirical_component: false

  novelty_mode:
    mode: concept_introduction_plus_synthesis
    novelty_claim_strength: 0.65
    builds_on_or_opposes: both

  protected_core:
    - desire-as-excess shift
    - interface as apparatus/capture/dispositive
    - greedy/generous interface distinction
    - non-classical subjectivity
    - generous interface as return to use/profanation/possibility
```

---

## 13. Pathway matrix (для того же текста)

```yaml
pathways:
  continental_media_philosophy:
    fit_strength: strong
    required_adaptations:
      - clarify Lacan-Deleuze transition
      - sharpen Foucault/Agamben distinction
      - define interface ontologically
    core_risk: low
    citation_effort: medium
    likely_article_identity: conceptual_theoretical_essay

  philosophy_of_technology:
    fit_strength: medium_strong
    required_adaptations:
      - add technics bridge
      - decide whether Simondon/Stiegler/Hui are bridges or sibling-frame
      - explain interface as technical form
    core_risk: medium
    citation_effort: high
    likely_article_identity: philosophy_of_technics_conceptual_article

  media_interface_theory:
    fit_strength: medium
    required_adaptations:
      - add media/interface canon
      - add concrete interface classes
      - connect to platform mediation
    core_risk: medium_high
    citation_effort: high
    likely_article_identity: media_theory_article

  STS_platform_studies:
    fit_strength: weak_medium
    required_adaptations:
      - add cases
      - add STS/platform corpus
      - change move to empirical_conceptual_hybrid
    core_risk: high
    citation_effort: very_high
    likely_article_identity: sibling_manuscript

  HCI_design_theory:
    fit_strength: weak_medium
    required_adaptations:
      - operationalize greedy/generous interface
      - add HCI/design literature
      - avoid reducing generous interface to good UX
    core_risk: high
    citation_effort: very_high
    likely_article_identity: sibling_manuscript
```

---

## 14. Benchmark expectations

Кайрон должен проходить benchmark не по совпадению красивого JSON, а по
следующим проверкам:

1. **Native extraction:** title, abstract, language, references, basic claims.
2. **Academic move:** видит ли система, что это concept reconstruction +
   concept introduction, а не review и не empirical article.
3. **Field coordinates:** строит ли `discipline_vector` и
   `school_affiliation_vector`.
4. **Tribe recognition:** отличает ли Deleuze/Agamben/Foucault
   внутреннюю линию от Lacan-as-foil и Simondon-as-missing-bridge.
5. **Citation ecology:** видит ли отсутствия как pathway-specific
   signals.
6. **Venue logic:** понимает ли, что разные журналы требуют разных
   article identities.
7. **Core risk:** запрещает ли адаптации, которые превращают онтологию
   интерфейса в банальный UX.
8. **Evidence discipline:** различает ли extracted fact, inferred
   pattern, external venue evidence, unknown.
9. **Fit vector:** выдаёт ли многомерную карту вместо одного числа.
10. **Adaptation:** предлагает ли Rewrite/Reframe/CitationPlan, а не
    просто «добавьте литературу».

---

## 15. Итоговая формула продукта

Kairon должен отвечать не «куда подать эту статью?», а:

> «Какой статьёй этот текст может стать для какого сообщества, каким
> ходом он туда входит, какие долги должен признать, какие мосты
> построить, какие элементы нельзя менять, где адаптация становится
> другой статьёй, и какой publication container способен принять этот
> ход без разрушения ядра?»

---

# Reconciliation appendix (added by reviewer)

This block is NOT part of the model itself. It records the gap analysis
against the existing codebase and the previous reconciliation
([ARTICLE_PUBLICATION_POSITION_MODEL.md](ARTICLE_PUBLICATION_POSITION_MODEL.md)).

## A. What's already in code (full coverage)

| v1.0 object | Implementation |
|---|---|
| `NativeArticleModel.identity / content_core / method_and_genre / first_order_positioning / core_protection / deterministic_diagnostics / meta` | `schema.ArticleModel` (covers all §3 fields, including word_count, section_count, has_methods_section, has_ai_disclosure, protected_core, mutable_zones, lifecycle_status, extraction_status) |
| `ArticleSemanticProfile.disciplinary_registers / primary_discipline / theoretical_shoulders / opponents_or_foils / argument_move / citation_bridges_needed / protected_core_candidates / mutable_zones / field_core_nonnegotiables / intended_audience / audience_expertise_level` | `schema.ArticleSemanticProfile` (all named fields present) |
| `FieldPositionModel.disciplinary_position / tribe_position / argument_position / methodological_position / audience_and_register / geo_institutional_position / temporal_position / readiness / meta` | `schema.FieldPositionModel` (all 7 groups + envelope shape) |
| `VenueModel.venue_identity / source_basis / formal_requirements / trust_and_compliance` | `schema.VenueModel` + `PublicationRegimeModel` + `VenueEvidencePack` (Source Authority Model v0) + 6 venue adapters |
| `SubmissionScenario.user_goal / constraints` | `schema.SubmissionScenario` |
| `FitAssessment.fit_vector` (12+ axes) + `verdict.label` | `schema.FitAssessment.axes: list[dict]` + `FitLabel` enum |
| `MismatchMap.mismatches[].axis / mismatch_type / description / required_action / core_risk` + `unknowns_not_absences` | `schema.MismatchMap` + `schema.MismatchItem.field_core_risk` |
| `AdaptationPlan` family | `schema.RewritePlan` + `CitationPlan` + `RiskReport` + `ComplianceChecklist` |
| Step 1–7 of §11 pipeline | Already wired through the `Case` orchestrator (see `api/cases.py`); FPM steps wired in commit `cb464f8` |

## B. v1.0 deltas — what's missing or needs structural change

| Delta | What to add | Where |
|---|---|---|
| **B1. `SourceEvidencePacket` as a first-class object** | New dataclass aggregating `input_sources[]` with `provenance` / `access_status` / `extraction_status` + `evidence_granularity` taxonomy as enum. Currently distributed across `SourceSnapshot`, `EvidenceItem`, `AdapterResult`. | new `schema.SourceEvidencePacket` + `enums.EvidenceGranularity` (8 values) |
| **B2. `KaironPublicationModel` packet** | Top-level aggregate that bundles source_packet + article_model + semantic_profile + field_position + scenarios + pathways + venue_candidates + fit_assessments + mismatch_maps + adaptation_plans + `protected_core_policy` + `evidence_policy`. Currently approximated by `Case` (runtime) but not serialized as a domain object. | new `schema.KaironPublicationModel` for export/dossier; `Case` remains the in-memory orchestrator |
| **B3. `ProtectedCorePolicy` + `EvidencePolicy`** | Explicit policy objects with `forbidden_transformations`, `allowed_transformations` (already in v1.0 §7), `acceptable_loss`, `unacceptable_loss`, `questions_for_author`; evidence policy = how UNKNOWN/INACCESSIBLE/CONFLICT are surfaced. | new `schema.ProtectedCorePolicy` and `schema.EvidencePolicy` |
| **B4. `ArticleSemanticProfile.schools_and_traditions[]` enriched** | Currently `list[str]`. v1.0 wants `list[{school, relation, strength, evidence}]` with `relation` ∈ {internal, adjacent, borrowed, contrastive, decorative, absent_but_relevant}. | extend `ArticleSemanticProfile`; add `enums.SchoolRelation` |
| **B5. `theoretical_shoulders[]` enriched** | Currently `list[str]`. v1.0 wants `list[{author_or_school, function_in_argument, evidence}]` with `function_in_argument` ∈ {foundation, bridge, foil, analogy, decoration, missing_expected}. | extend `ArticleSemanticProfile`; add `enums.ShoulderFunction` |
| **B6. `citation_bridges_needed[]` structured** | Currently `list[str]`. v1.0 wants `list[{target_pathway, missing_bridge, why_needed, core_risk}]`. | extend `ArticleSemanticProfile`; reuses `FieldCoreImpact` enum for `core_risk` |
| **B7. `FieldPositionModel.citation_network_signature` extension** | Add `decorative_citations: list[str]` and `dangerous_missing_names: list[str]`. Match v1.0 §5 tribe_position. | extend the existing field (it's `dict[str, Any]`, schema-compatible) |
| **B8. `VenueModel.venue_envelope` as a named substructure** | v1.0 §6 lists explicit envelopes per axis (discipline / school / argument_move / evidence_type / method / language_register / genre). Currently we have only `discipline_envelope`, `school_envelope`, `argument_move_envelope` in FPM. | extend FPM (or `VenueModel`) with `evidence_type_envelope`, `method_envelope`, `language_register_envelope`, `genre_envelope` |
| **B9. `SubmissionScenario.allowed_transformations / forbidden_transformations`** | New structured fields. Currently scenario has `language_constraints`, `APC_constraints`, `target_indexing` and free-form `goal` — missing the transformation lattice. | extend `schema.SubmissionScenario` |
| **B10. `FitAssessment` split into 4 vectors** | Currently a single `axes: list[dict]`. v1.0 §8 separates `fit_vector` + `core_risk_vector` + `effort_vector` + `strategic_value` + `verdict`. The current 12-axis FitAssessment maps to `fit_vector` only. | extend `FitAssessment` with 3 sibling vectors; `axes` becomes `fit_vector`; preserve back-compat via property |
| **B11. `MismatchMap.mismatches[].mismatch_type`** | Need a closed taxonomy: `missing_canonical_citations`, `wrong_argument_norm`, `venue_requires_explicit_method`, `essay_vs_research_article`, … | add `enums.MismatchType` (initial seed of ~10 values; extensible) |
| **B12. `MismatchMap.unknowns_not_absences[]`** | New structured field: `[{field, why_unknown, how_to_verify}]`. Already implicit in our UNKNOWN handling but not surfaced as a typed list. | extend `schema.MismatchMap` |
| **B13. `AdaptationPlan.actions[].target/action_type` taxonomy + `forbidden_moves[]` + `sibling_options[]`** | Currently `RewritePlan.changes`, `CitationPlan.recommendations`, `RiskReport.risks`, `ArticleVariant`. Need a unified `AdaptationAction` shape with `target` enum + `action_type` enum + `forbidden_moves[]` cross-checked against `ProtectedCorePolicy`. | new `schema.AdaptationAction` + enums `AdaptationTarget`, `AdaptationActionType`; refactor plans to share it; cross-link `ArticleVariant` as sibling option |
| **B14. Benchmark harness for the 10 v1.0 checks** | Translate §14 (1–10) into pytest fixtures + assertions. The Mavrinsky exemplar (§12) becomes the gold fixture. | new `tests/test_publication_integrability_v1.py` + `tests/fixtures/integrability_v1/` |

## C. Conflicts with code or canon

None. v1.0 is purely additive. Every new field maps to an existing
location or to a new sibling object that doesn't disturb the canonical
contract. Key invariants preserved:

- No single fit score (§8 `verdict.label` is categorical).
- UNKNOWN ≠ absent (§9 `unknowns_not_absences` makes it explicit).
- Protected core as first-class (§7 `forbidden_transformations`).
- Evidence trail required (§2 `SourceEvidencePacket`).
- LLM-optional pipeline (none of B1–B14 requires LLM; all have
  deterministic fallback path).
- No external API dependency (B1, B11–B13 are pure schema work).

## D. Relation to the previous five-delta plan

[ARTICLE_PUBLICATION_POSITION_MODEL.md §5](ARTICLE_PUBLICATION_POSITION_MODEL.md)
listed five deltas (IntegrabilityModel, DisciplinaryPathway expansion,
CitationEcologyDiagnostics, TransformationPolicy, new FitAssessment
axes). v1.0 reorganises these around 14 named deltas (B1–B14). The
mapping:

- Previous *IntegrabilityModel* → v1.0 B4 + B5 + B6 (enriched
  `ArticleSemanticProfile` substructures, no separate top-level object).
- Previous *DisciplinaryPathway expansion* → still valid, now under
  the umbrella of v1.0 `pathway_models` in `KaironPublicationModel` (B2).
- Previous *CitationEcologyDiagnostics* → v1.0 B6 + B7 (split between
  SemanticProfile and FPM signature).
- Previous *TransformationPolicy* → v1.0 B3 (`ProtectedCorePolicy`) +
  B9 (`SubmissionScenario.forbidden_transformations`) + B13
  (`AdaptationPlan.forbidden_moves`).
- Previous *new FitAssessment axes* → v1.0 B10 (4-vector decomposition;
  the new axes become entries inside `fit_vector` or `core_risk_vector`).

v1.0 is sharper. Use B1–B14 as the authoritative backlog.

## E. Decision and recommended next step

The model **complements and supersedes** the prior draft. Nothing must
be deleted; 14 additive deltas remain. They naturally split into four
sprints:

- **Sprint α — Evidence & Policy substrate (B1, B3).**
  `SourceEvidencePacket` + `EvidenceGranularity` enum +
  `ProtectedCorePolicy` + `EvidencePolicy`. These two unlock everything
  else (every adaptation plan reads the policy; every fit reads the
  evidence packet).
- **Sprint β — SemanticProfile enrichment (B4, B5, B6, B7, B11, B12).**
  Structured schools / shoulders / bridges, mismatch type taxonomy,
  unknowns_not_absences. Most of these are list-of-string → list-of-dict
  migrations with deterministic builders.
- **Sprint γ — FitAssessment 4-vector decomposition (B10).** Split
  `axes` into `fit_vector` / `core_risk_vector` / `effort_vector` /
  `strategic_value`. Keep `axes` as a back-compat property. Update
  `FitAssessorAgent` prompt and the FPM-based fit path to populate all
  four.
- **Sprint δ — AdaptationPlan unification + Scenario lattice + Venue
  envelope completion (B8, B9, B13).** `AdaptationAction` shape +
  `SubmissionScenario.{allowed,forbidden}_transformations` +
  remaining envelopes (`evidence_type_envelope`, `method_envelope`,
  `language_register_envelope`, `genre_envelope`).
- **Sprint ε — Benchmark harness (B14).** Gold fixture from §12 +
  pytest assertions for §14 (1)–(10). Becomes the regression suite
  guarding everything above.
- **Sprint ζ — Aggregate `KaironPublicationModel` (B2).** Last, because
  it's just a packaging dataclass on top of everything else; built once
  the pieces stabilise. Used for dossier export and inter-system
  transport (Litops / WhiteCrow bridges).

**Recommendation:** start with **Sprint α**, because B1 and B3 are
preconditions for the rest. Order inside α: B1 first (SourceEvidencePacket
+ EvidenceGranularity enum, deterministic builder, persistence in
`Case`), B3 second (ProtectedCorePolicy + EvidencePolicy, plus a
hook in `RewritePlanner` that consults `ProtectedCorePolicy.forbidden_moves`).
Each delta gets its own feature branch following the pattern of
`feature/wire-fpm-pipeline`.

**Status quo verdict:** confirmed complement; go further.
