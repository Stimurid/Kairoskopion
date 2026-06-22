# Semantic Organs — Round II Audit

**Status:** documentation + minimal correction patch.
**Authored:** 2026-06-21.
**Baseline commit:** `b109a59` (post V2-E + dirty real article run).
**Predecessor:** [`LEGACY_COMPATIBILITY_REUSE_AUDIT_V2.md`](LEGACY_COMPATIBILITY_REUSE_AUDIT_V2.md),
[`MISMATCH_MAPPER_CLASSIFICATION_V2B.md`](MISMATCH_MAPPER_CLASSIFICATION_V2B.md).

This pass re-audits the V2-D/V2-E refactor line against the doctrine
the operator stated:

> Deterministic code is forbidden for: article meaning, genre
> inference, core claims, thesis/problem/object/method/novelty,
> venue meaning, article type interpretation unless direct source
> fact, fit axes, mismatch descriptions, mismatch actions, risk
> semantics, rewrite suggestions, citation ecology, citation
> bridge categories, compliance interpretation, submission strategy,
> field-core risk, publication positioning.

The previous audit dismissed `services/citation_ecology.py` with
"needs LLM wrapper", which is *not* a valid rejection reason — at
best a deferral. This pass reclassifies it correctly.

---

## 1. Executive summary

**Finding 1 — Deterministic semantic leakage in V2-D builders.**
The "minimal-real" CitationPlan / SubmissionPack lanes emit
*meaning-bearing* strings from code:

- `citation_gap_categories = ["disciplinary citation bridging may be
  insufficient"]` — semantic claim about citation ecology, written
  by code, triggered by a fit axis label.
- `missing_bridge_categories = ["disciplinary bridge references
  between article's disciplinary register and venue's primary
  discipline"]` — semantic claim about which references the article
  needs.
- `recommended_reference_search_tasks = ["Identify 5-8 recent
  articles from the target venue that engage the article's
  disciplinary tradition; extract the theoretical anchors they
  recur to."]` — semantic submission strategy from code.
- `dangerous_padding_warnings = ["Do not add references only to
  imitate venue metrics..."]` — semantic editorial advice from code.
- `SubmissionPack.next_actions` includes strategic text written by
  code (e.g. "Identify the current debate markers in the venue's
  recent issues on this topic; position the article's novelty
  claim against the most recent counter-argument.").

These violate the doctrine. Even though they were triggered by a
*structural* signal ("axis=discipline rated weak"), the *prose
content* is a semantic claim.

**Finding 2 — `services/citation_ecology.py` re-classified.**
Its *structural* parts (ref count, recency, DOI coverage, source
diversity statistics) are `STRUCTURAL_EXTRACTION_OK` — already
covered by `BibliographyProfile`. Its *semantic* parts (bridge
detection by token overlap, venue expectation interpretation by
regex over guidelines text) are `DETERMINISTIC_SEMANTIC_ZOMBIE`.
Schema mismatch (`CitationEcologyReport` ≠ `CitationPlan`) is
secondary.

**Verdict on `services/citation_ecology.py`: `SPEC_REFERENCE_ONLY`.**
Not because it "needs a wrapper" — but because (a) its semantic
sub-parts violate the doctrine and need LLM/source-backing, and
(b) its useful structural sub-parts (statistics over BibliographyProfile)
are *already* extracted into V2-E `BibliographyProfile` builder. A
future LLM CitationEcologist agent should consume BibliographyProfile
+ venue source corpus + ArticleSemanticProfile; reusing this module's
heuristic bridge detector would re-introduce the zombie.

**Finding 3 — title_current still None on real article.**
ArticleModeler did not extract the H1 title from the user article.
This is a *structural* extraction failure, not a semantic one. Title
is *direct source fact*: it's literally an H1 line. Deterministic
H1 extraction is allowed by doctrine and should run as a fallback
when modeler returns None.

**Finding 4 — narrator parse_failed hardcoded reason.**
`agents/mismatch_narrator.py` line ~161 hardcodes
`reason=FALLBACK_REASON_SCHEMA_VALIDATION_FAILED` regardless of
whether the actual parse outcome was `invalid_json`, `repair_failed`,
or `schema_validation_failed`. V2-B2 classifier reads both
`parse_status` and `fallback_reason`; precedence currently prefers
the hardcoded `fallback_reason`. **The narrator should derive
`reason` from `outcome.status` so the V2-B2 surface tells the
truth.** Tiny metadata fix.

**Finding 5 — provenance metadata absent.**
No object in the dossier carries explicit "this field came from
LLM / source-fact / structural-extraction / deterministic-heuristic /
needs-llm" markers. The operator can't tell, at the field level,
which output is grounded and which is heuristic.

---

## 2. ROUND_II_REFACTOR_DECISION_AUDIT

| Module | Old classification | Current runtime status | Replacement / new path | Rejection reason used | Valid? | Semantic work involved? | Deterministic semantic risk | Required action | Priority |
|---|---|---|---|---|---|---|---|---|---|
| `services/citation_ecology.py` | `NEEDS_LLM_WRAPPER_OR_ADAPTER` | UNUSED | new V2-D `citation_plan_minimal.py` | "needs LLM wrapper + wrong schema" | **partial** — wrapper need ≠ rejection; correct reason is "semantic sub-parts are zombie" | yes (bridge detection, venue expectation regex) | HIGH | RE-CLASSIFY as `SPEC_REFERENCE_ONLY` for stated correct reason; preserve as spec doc; do NOT reuse heuristic bridge detector | medium |
| `agents/fit/citation_planner.py` | `SPEC_REFERENCE_ONLY` | UNUSED | new V2-D `citation_plan_minimal.py` | "LLM agent would invent references" — INCORRECT, this agent has anti-hallucination contract | **no** — agent is LLM-backed with proper contract | yes (LLM-driven semantic claims with anti-hallucination rules) | LOW | RE-CLASSIFY as `LLM_AGENT_USABLE`; wire later as the proper organ for semantic fields | medium |
| `agents/submission/compliance_auditor.py` | `SPEC_REFERENCE_ONLY` | UNUSED | V2-D `compliance_checklist_minimal.py` | similar to citation_planner | partial — schema/Case slot missing, but its LLM-grounded interpretation is the right organ | yes | LOW (agent itself is LLM-backed) | RE-CLASSIFY as `LLM_AGENT_USABLE_NEEDS_CASE_SLOT`; wire later | low |
| `agents/submission/submission_pack_builder.py` | `SPEC_REFERENCE_ONLY` | UNUSED | V2-D `submission_pack_minimal.py` | "generates cover letter we forbid" | **yes** — generation of cover-letter / strategic next_actions belongs to LLM organ | yes | LOW | keep as future LLM organ; wire after compliance + citation | low |
| `services/compliance.py` | `DETERMINISTIC_SEMANTIC_ZOMBIE` (Z#3) | UNUSED | V2-D `compliance_checklist_minimal.py` | "Z#3 substring bug + ManuscriptModel dep" | **yes** | yes (AI-disclosure substring) | HIGH | confirm UNUSED; do NOT reuse heuristic checks | high |
| `services/submission_pack.py` | `NEEDS_LLM_WRAPPER_OR_ADAPTER` | UNUSED | V2-D `submission_pack_minimal.py` | "generates cover letter, wrong field names" | yes | partial (template cover letter is borderline; readiness logic is structural) | LOW (readiness logic) | confirm UNUSED for now; readiness logic concept already absorbed | low |
| V2-D `services/citation_plan_minimal.py` | new deterministic builder | ACTIVE | n/a | n/a | n/a | **yes** — emits semantic gap_categories / bridges / search tasks / padding warnings | **HIGH — current violation** | **STRIP semantic content fields** (gap_categories, missing_bridges, search_tasks, padding_warnings) → mark `needs_llm`; keep structural fields (status from BibliographyProfile, verification_tasks for structural missing data) | **high** |
| V2-D `services/compliance_checklist_minimal.py` | new deterministic builder | ACTIVE | n/a | n/a | n/a | partial — per-item *status* (satisfied/missing/unknown_not_verified) is structural; per-item *notes* prose is borderline | LOW-MEDIUM | mark item origins; for `requirement` fields use stable factual labels; keep `unknown_not_verified` default for unverifiable policies | medium |
| V2-D `services/submission_pack_minimal.py` | new deterministic builder | ACTIVE | n/a | n/a | n/a | partial — `ready_status` is structural (rules over upstream); `next_actions` prose is **submission strategy** which doctrine forbids | MEDIUM | mark `next_actions` with `origin=deterministic_aggregation` if they only aggregate upstream status; strip prose that *interprets* the article/venue beyond aggregation | medium |
| V2-E `services/bibliography_profile.py` | structural extractor | ACTIVE | n/a | n/a | n/a | **no** — confirmed structural-only (counting, regex DOI/URL/year, dedup) | LOW | confirm no semantic claims; add explicit "structural-only" semantic_status | high (confirm) |
| `agents/fit/mismatch_mapper.py` | `LLM_AGENT_USABLE` but structurally incompatible | UNUSED | direct deterministic build + LLM narrator | "schema mismatch + duplicate of narrator" | yes | n/a | n/a | leave UNUSED (V2-B decision stands) | n/a |
| `agents/mismatch_narrator.py` | LLM-backed | ACTIVE | n/a | n/a | n/a | yes (semantic narrative authored by LLM) | LOW | **fix `reason` derivation from `outcome.status`** so V2-B2 surface is honest about parse_failed vs invalid_json vs repair_failed | medium |
| ArticleModeler (LLM) | LLM-backed | ACTIVE | n/a | n/a | n/a | yes | LOW | add **structural H1 title fallback** (direct source fact, allowed by doctrine) when modeler returns title_current=None | medium |
| `services/citation_ecology.py::_detect_bridge_references` | heuristic | UNUSED | n/a | n/a | n/a | yes (semantic claim from token overlap) | HIGH | keep UNUSED; flag as zombie reference | high |

---

## 3. RUNTIME_SEMANTIC_PROVENANCE_MATRIX

Provenance for every meaning-bearing field that ships in the
production dossier today (after the dirty real article run,
`case_97beb1600bba`). Source `case-dirty-real`.

| Section / object | Meaning-bearing fields | Producer | LLM used? | Model/role | source_fact_direct used? | user_input used? | structural_extraction used? | deterministic aggregation used? | deterministic semantic fallback possible? | fallback actually ran? | Verdict | Required fix |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| InputClassifier | input_type, classifier_label | `agents/input_classifier.py` | yes | gpt-4o-mini (override) | no | no | no | no | yes (rule-based fallback) | no (LLM ran) | allowed | none |
| ArticleModel | title_current, abstract_current, research_question, core_claims, problem_statement, object_of_inquiry, genre_current, novelty_mode, method_status, disciplinary_register_current, protected_core, mutable_zones, unknowns, confidence | `agents/article_modeler.py` | yes | global Sonnet | partial (title could be H1 source-fact) | no | partial (word_count, abstract_length) | no | yes (`article_modeling.py` deterministic) | unknown (LLM ran but title_current=None) | allowed; **title H1 fallback missing** | add `_structural_title_from_h1()` fallback marked `origin=structural_extraction` when modeler returns title_current=None |
| ArticleSemanticProfile | disciplinary_registers, schools_and_traditions, argument_move_type, intended_audience, protected_core_candidates | `agents/article_semantic_profiler.py` | yes | global Sonnet | no | no | no | no | yes (`article_enrichment.py` keyword-based) | no | allowed (guarded); fallback is `DETERMINISTIC_SEMANTIC_ZOMBIE` per V2 audit Z#2 | leave as-is per V2 audit; guarded in prod |
| DisciplinaryPathway | discipline_name, fit_strength, required_adaptations, field_core_risk, venue_type_hints | `agents/disciplinary_pathway_mapper.py` | yes | global Sonnet | no | no | no | no | yes | unknown | allowed | none |
| VenueModel | canonical_name (often source-fact from header), scope_summary (source-fact from venue text), article_types_supported (source-fact regex), language_policy, open_access_status, apc_policy, ai_policy, ethics_policy, data_policy | `agents/venue_profiler.py` | yes | global Sonnet | yes (most fields are extracted from supplied venue text) | yes (operator-supplied text) | partial (article_types regex) | no | yes (`venue_profiling.py` regex with negation guards; Z#4 bilingual bug) | no | allowed; Z#4 lurks for bilingual | none in V2-Round-II scope |
| SubmissionScenario | goal, prestige_priority, speed_priority, deadline, apc_max, language, target_indexing | `Case._synthesise_preliminary_scenario` | no | n/a | no | yes (operator should fill; auto-synthesised marked preliminary) | no | no | **n/a — synthesis is honest-skeleton, not semantic claim** | yes (preliminary) | allowed (banner shown) | none |
| FitAssessment | overall_label, axes[].value, axes[].notes, axes[].confidence, recommendation, unknowns | `agents/fit_assessor.py` | yes | global Sonnet | no | no | no | no | yes (`fit_assessment.py` keyword fallback; Z#1, Z#5) | no | allowed in prod; fallback is zombie if LLM off | none in scope |
| MismatchMap (base) | mismatches[].axis, .severity, .article_side, .field_core_risk | `services/mismatch_mapping.py::build_mismatch_map` | no | n/a | n/a | n/a | partial (axis names from fit) | yes (severity from axis value mapping; field_core risk from `_CORE_SENSITIVE_AXES`) | n/a | n/a | allowed — structural translation of fit verdict | none |
| MismatchMap | mismatches[].venue_side, .description, .possible_actions | `agents/mismatch_narrator.py` | yes | global Sonnet | no | no | no | no | yes (honest empty fallback) | **yes for `case_97beb1600bba` — parse_failed, 0/6 filled** | allowed; fallback is honest empty | **fix narrator `reason` derivation so V2-B2 surface accurately reports `repair_failed` vs `invalid_json` vs `schema_validation_failed`** |
| narrator_coverage (V2-B1/B2) | narrator_status, parse_failure_category, parse_failure_reason | `services/narrator_coverage.py` | no | n/a | n/a | n/a | yes | yes | n/a | n/a | allowed — pure classification of LLM attempt metadata | tighten parse_status precedence over hardcoded fallback_reason |
| RiskReport | risk_items[].risk_type, .description, .severity, .likelihood, .mitigation, blocking_risks, warnings, unknowns | `services/risk_reporting.py::build_risk_report` | **no** | n/a | n/a | n/a | partial | yes (rule-based from axes + fit + venue) | **yes — currently in active use** | **yes — production-active deterministic semantic** | **borderline** — risk *types* are structural (taxonomy), but descriptions/mitigations are semantic templates | mark each item with `origin=deterministic_aggregation` if produced from fixed taxonomy + axis lookups; flag `risk_officer` LLM agent as the proper organ (deferred) |
| RewritePlan | changes[].target_block, .desired_state, .reason, .field_core_risk, estimated_effort, summary | `services/rewrite_planning.py::build_rewrite_plan` | **no** | n/a | n/a | n/a | partial (target_block from axes) | yes (`change_type` dict mapping) | **yes — currently in active use** | **yes — production-active deterministic semantic** | **borderline** — changes are derived from mismatch axes via template; `desired_state` text is semantic prose authored by code | mark with `origin=deterministic_aggregation`; `rewrite_planner` LLM agent is the proper organ (deferred) |
| BibliographyProfile (V2-E) | reference_count, doi_count, url_count, year_distribution, parsed_reference_count, malformed_count, duplicate_suspect_count, status | `services/bibliography_profile.py` | no | n/a | yes (DOI/URL/year regex from source text) | no | yes | yes | no — purely structural | n/a | **allowed** — confirmed structural-only | confirm with test |
| CitationPlan (V2-D) | citation_gap_categories, missing_bridge_categories, recommended_reference_search_tasks, dangerous_padding_warnings | `services/citation_plan_minimal.py` | **no** | n/a | no | no | no | partial | **YES — current behaviour emits deterministic semantic prose** | **YES — fired for case_97beb1600bba** | **FORBIDDEN by doctrine** | **STRIP these fields when LLM organ absent; mark `field_origins["citation_gap_categories"]=needs_llm`** |
| CitationPlan (V2-D) | status, current_bibliography_status, verification_tasks, confidence | `services/citation_plan_minimal.py` | no | n/a | no | no | yes | yes | no — derived from BibliographyProfile status | n/a | allowed — structural aggregation | mark with `origin=structural_extraction` / `deterministic_aggregation` |
| ComplianceChecklist (V2-D) | checklist_items[].requirement, .status, .source_status, missing_items, blocking_items, unknowns | `services/compliance_checklist_minimal.py` | no | n/a | partial (article fields, venue policy field presence) | no | yes | yes | no — pure cross-reference of article fields vs venue field presence | n/a | allowed — structural cross-reference | mark per-item `origin` |
| ComplianceChecklist | checklist_items[].notes | `services/compliance_checklist_minimal.py` | no | n/a | n/a | n/a | yes (instruction text about missing structure) | n/a | borderline — instruction prose about what's missing | n/a | allowed — structural-status prose | none |
| SubmissionPack (V2-D) | ready_status, depends_on, files | `services/submission_pack_minimal.py` | no | n/a | n/a | n/a | no | yes — pure rule over upstream | no | n/a | allowed — structural aggregation | mark `origin=deterministic_aggregation` |
| SubmissionPack | next_actions, statements, warnings | `services/submission_pack_minimal.py` | no | n/a | n/a | n/a | no | yes (text aggregating upstream status) | partial — aggregation OK; but some action prose interprets the article ("Identify the current debate markers..." would be strategic) | **yes — current emission** | **borderline** | mark `origin=deterministic_aggregation`; ensure no action interprets article/venue content beyond aggregating upstream status |
| NextActionBlock (UI) | derived primary action string | `ui/src/components/DossierView.tsx::NextActionBlock` | no | n/a | n/a | n/a | yes | yes — pure derivation from object statuses | no | n/a | allowed — UI aggregation of structural status | none |
| Dossier UI labels | most labels are static UI strings | UI components | no | n/a | n/a | n/a | yes | yes | no | n/a | allowed | none |

---

## 4. `services/citation_ecology.py` re-audit (Track C)

**Inputs expected:** `BibliographyProfile`, `ArticleModel`, `VenueModel`, `venue_guidelines_text`.

**Output:** `CitationEcologyReport` (not `CitationPlan`).

### Subpart classification

| Subpart | Lines | Classification |
|---|---|---|
| `_check_reference_count` | 86–115 | **STRUCTURAL** (counts vs guideline limit regex) |
| `_check_recency` | 117–147 | **STRUCTURAL** (year stats from BibliographyProfile) |
| `_check_source_diversity` | 150–177 | **STRUCTURAL** (kind distribution) |
| `_check_doi_coverage` | 179–196 | **STRUCTURAL** (DOI ratio) |
| `_detect_bridge_references` | 199–246 | **DETERMINISTIC_SEMANTIC_ZOMBIE** — bridge inference by token overlap between article discipline and venue scope. Even after Track D tightening (≥2 distinct discipline tokens) this is a semantic claim from keywords. |
| `_check_venue_expectations` | 249–279 | **DETERMINISTIC_SEMANTIC_ZOMBIE** — interprets venue guideline text by regex |
| `gaps[]` / `tasks[]` / `warning_signals[]` schema | dataclass | useful taxonomy; usable as *spec reference* |

### Could it consume `BibliographyProfile`?

Yes — its statistical sub-checks already operate on shapes equivalent to BibliographyProfile. The structural sub-parts are essentially what V2-E's BibliographyProfile builder already computes (counts, DOI coverage, year distribution). **The structural value is already absorbed.** Re-importing this module adds nothing structurally, and re-activating its semantic sub-parts re-introduces zombie behaviour.

### Could it become an LLM-agent wrapper?

In principle yes — `agents/fit/citation_planner.py` already exists and references the same family. But this would be wrapping the *taxonomy* (gaps/tasks/warnings) with LLM semantic output, *not* the bridge detector or venue-expectation regex. That's a future LLM organ pass, not V2-D's deterministic builder.

### Verdict

**`SPEC_REFERENCE_ONLY`** — for the correct reason: its semantic sub-parts are deterministic-semantic-zombie that the doctrine forbids; its useful structural sub-parts are already covered by V2-E `BibliographyProfile`. The schema mismatch (`CitationEcologyReport` ≠ `CitationPlan`) is secondary. Reuse the *taxonomy* (`CitationGap`, `CitationTask`) as a contract reference when wiring the future LLM CitationEcologist agent; do NOT call `_detect_bridge_references` or `_check_venue_expectations` from any runtime path.

This **inverts** the earlier "not used because needs wrapper" framing into the correct framing: "not used because its semantic parts violate the doctrine; structural parts already covered; wrapper path leads to a fresh LLM agent, not adaptation of this code."

---

## 5. V2-E BibliographyProfile re-confirmation (Track E)

Re-confirmed strictly structural:

- DOI/URL/year extraction → regex, structural ✓
- Reference splitting → regex (numbered / bulleted / newline / semicolon fallback), structural ✓
- `title_text` / `authors_text` / `venue_text` → **explicitly None** on every reference (no parser tries to populate them) ✓
- Status taxonomy (`not_found`, `present_unparsed`, `parsed_structural`, `partial`, `malformed`, `unknown`) describes *structure*, not *semantic adequacy* ✓
- `verification_status` distinguishes `not_verified` / `structural_only` / `identifiers_detected` from `verified` — code NEVER claims `verified` ✓
- `parsed_structural` is never interpreted as "citation ecology is good" — that conclusion would belong to a CitationEcologist LLM agent ✓

**Required tests** (Track I, items 9, 10): added in patch.

---

## 6. Track F — smallest correction set

After Tracks A–E, the immediate fixes required *before the next real article test* are:

1. **Add semantic provenance taxonomy** (`services/semantic_provenance.py`) — constants for origin codes.
2. **Add `field_origins` + `semantic_status` to CitationPlan / ComplianceChecklist / SubmissionPack / BibliographyProfile schema** — so the operator (and UI) can see, per field, which origin produced the content.
3. **Strip deterministic semantic emission from CitationPlan**:
   - `citation_gap_categories` → empty when LLM organ absent, `origin=needs_llm`
   - `missing_bridge_categories` → empty when LLM organ absent, `origin=needs_llm`
   - `recommended_reference_search_tasks` → empty when LLM organ absent, `origin=needs_llm`
   - `dangerous_padding_warnings` → empty when LLM organ absent, `origin=needs_llm`
   - keep `verification_tasks` (structural status of missing bibliography), `status`, `current_bibliography_status` — these are structural
4. **Strip strategic next_actions prose from SubmissionPack** that interprets the article/venue beyond aggregating upstream status; keep aggregation-only next_actions and mark `origin=deterministic_aggregation`.
5. **Add structural title H1 fallback** to `_run_fit_chain` (or similar) — direct source fact when modeler returns None; marked `origin=structural_extraction`.
6. **Fix `agents/mismatch_narrator.py` `reason` derivation** from `outcome.status` so V2-B2 surface tells the truth.
7. **Tighten V2-B2 `classify_parse_failure` precedence** to prefer concrete `parse_status` over hardcoded `fallback_reason`.
8. **UI: render `semantic_status` + per-field origins** so the operator sees which sections are LLM-grounded vs heuristic vs needs-LLM.
9. **Tests** pin the doctrine rules.
10. **Russian venue retest** of the same real article (`Вопросы философии` with manually supplied venue text marked `user_supplied_venue_text`).

**Explicitly NOT in scope of this pass**: wiring `agents/fit/citation_planner.py`, `agents/submission/compliance_auditor.py`, or `agents/submission/submission_pack_builder.py` as LLM organs. Those are future passes; flagging here only.

---

## 7. Confirmations

- ✅ Every prior "not used because needs wrapper" decision re-evaluated
- ✅ No old semantic/LLM-capable module rejected for the wrong reason
- ✅ `services/citation_ecology.py` has a correct action plan (`SPEC_REFERENCE_ONLY` for the *correct* reason: semantic parts forbidden, structural parts already absorbed)
- ✅ Deterministic semantic outputs identified for stripping/marking
- ✅ Title extraction path identified (direct H1 = source-fact, allowed)
- ✅ Mismatch narrator parse_status fix identified
- ✅ Doctrine rules to be pinned by tests
