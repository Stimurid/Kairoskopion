# Round III-P3: LLM Organ Requirements

**Date:** 2026-06-26
**Branch:** `feature/round3-six-phase-build-hardening`
**Scope:** Define contracts for 13 LLM organs to replace BLOCKED_NEEDS_LLM and DEFERRED deterministic semantic fallbacks.

## Zombie Inventory

| # | new/old | component | file/function | current behavior | semantic responsibility | needed organ | existing organ? | prompt path | schema path | implementation action |
|---|---------|-----------|---------------|------------------|------------------------|--------------|-----------------|-------------|-------------|----------------------|
| 1 | NEW | DisciplineIntentParser | `cases.py` / `set_discipline_intent()` | Stores raw text, returns `FUNNEL_BLOCKED_NEEDS_LLM` | Parse free-text intent → structured discipline model with field, subfield, tradition, method orientation | DisciplineIntentParser | NO (new) | `prompts/discipline_intent_parsing.py` | DisciplineIntentResult | Create new agent + prompt |
| 2 | NEW | VenueFunnelPlanner | `cases.py` / `set_discipline_intent()` | Returns empty `venue_families` | Discipline intent → venue family list (discipline zones, journal clusters, search strategies) | VenueFunnelPlanner | NO (new) | `prompts/venue_funnel_planning.py` | VenueFunnelPlan | Create new agent + prompt |
| 3 | NEW | VenueFamilyContextBuilder | `cases.py` / `_build_venue_family_from_venue()` | Stores venue name, returns `BLOCKED_NEEDS_LLM` | Given concrete venue → infer discipline family, sibling venues, venue cluster context | VenueFamilyContextBuilder | NO (new) | `prompts/venue_family_context.py` | VenueFamilyContext | Create new agent + prompt |
| 4 | NEW | VenueMatrixAssessor | `cases.py` / `get_venue_matrix()` | Returns `NOT_ASSESSED_NEEDS_LLM` for all candidates | Semantic assessment of venue candidates on fit axes: topic, discipline, genre, method, core risk | VenueMatrixAssessor | Partial: FitAssessorAgent exists but operates on full ArticleModel×VenueModel, not venue-pool candidates | `prompts/venue_matrix_assessment.py` | VenueMatrixRow | Create new lightweight prompt (reuse FitAssessor axis vocabulary) |
| 5 | NEW | DepthRecommendationAgent | `cases.py` / `get_cost_estimate()` | Pure arithmetic (OK_TECHNICAL for cost; but depth recommendation = semantic) | Recommend optimal depth mode given article complexity, venue requirements, user budget constraints | DepthRecommendationAgent | NO (new, optional) | `prompts/depth_recommendation.py` | DepthRecommendation | Create new agent + prompt (OPTIONAL — cost arithmetic stays deterministic) |
| 6 | OLD | FitAssessmentOrgan | `services/fit_assessment.py` / `assess_fit()` | 12-axis keyword rules, hardcoded thresholds | Compare ArticleModel × VenueModel × Scenario → 12-axis FitAssessment with semantic justification | FitAssessorAgent (LLM path) | YES: `agents/fit_assessor.py` + `prompts/fit_assessment.py` | `prompts/fit_assessment.py` | FitAssessment schema exists | Wire LLM path as default; deterministic becomes runtime-failure-only fallback |
| 7 | OLD | MismatchNarrativeOrgan | `services/mismatch_mapping.py` / `build_mismatch_map()` | Hardcoded severity + generic actions | Read fit axes, produce narrative: what is mismatched, why, venue-side expectation (from venue text), severity as semantic judgment | MismatchNarratorAgent | YES: `agents/mismatch_narrator.py` + `prompts/mismatch_narrative.py` | `prompts/mismatch_narrative.py` | MismatchMap schema exists | Wire LLM path as default; deterministic becomes runtime-failure-only fallback |
| 8 | OLD | RewritePlanOrgan | `services/rewrite_planning.py` / `build_rewrite_plan()` | axis→change_type map, conditional actions | Produce rewrite actions with semantic justification: what to change, why, field-core risk per change, difficulty as judgment | RewritePlannerAgent | NO (agent shell absent) | `prompts/rewrite_planning.py` | RewritePlan schema exists | Create new agent + prompt |
| 9 | OLD | CitationEcologyOrgan | `services/citation_ecology.py` / `build_citation_ecology_report()` | Threshold-based gap detection | Analyze bibliography × venue corpus: semantic gap identification, bridge strategies, canon alignment | CitationEcologyAgent | NO (agent shell absent) | `prompts/citation_ecology.py` | CitationEcologyReport schema exists | Create new agent + prompt |
| 10 | OLD | MavrinskySemantic | `services/mavrinsky_venue_selection.py` / `assess_fit_for_vpkg()` | Token hit counts on 6 token bags → 16-axis fit | Full semantic 16-axis fit assessment: article × VenueProfilePackage, using actual reading of corpus content, not token counting | FitAssessorAgent (generalized) | PARTIAL: `agents/fit_assessor.py` handles 12 axes; Mavrinsky has 16 | `prompts/fit_assessment.py` (extended) | Extended FitAssessment | Generalize FitAssessorAgent to accept VenueProfilePackage input and 16-axis schema |
| 11 | OLD | VenueRegimeDetector | `services/venue_profiling.py` / `_detect_regime()` | substring→RegimeType | Read venue text and classify publication regime: classic journal, special issue, conference proceedings, mega-journal, edited volume, etc. | VenueProfilerAgent (extended) | YES: `agents/venue_profiler.py` already extracts venue model from text | `prompts/venue_fact_extraction.py` | VenueModel.regime_type | Add regime classification to existing VenueProfilerAgent prompt |
| 12 | OLD | VenuePolicyExtractor | `services/venue_profiling.py` / `_extract_*()` | regex→policy claims | Extract structured policy facts from venue text: language policy, OA status, APC, review model, AI policy, data policy, ethics, word limits | VenueProfilerAgent (extended) | YES: `agents/venue_profiler.py` already has fact extraction prompt | `prompts/venue_fact_extraction.py` | VenueModel policy fields | Expand existing VenueProfilerAgent prompt to cover all policy fields |
| 13 | OLD | ComplianceSemanticOrgan | `services/compliance_checklist_minimal.py` / `build_minimal_compliance_checklist()` | field presence→status | Semantic compliance assessment: does this article's actual content satisfy this venue's actual requirements? Not just field-present/absent. | ComplianceAssessorAgent | NO (agent shell absent) | `prompts/compliance_assessment.py` | ComplianceChecklist (enhanced) | Create new agent + prompt; keep structural pre-check as input |

## Counts

- **New (P2-BLOCKED):** 5 (#1–#5)
- **Old (P2-DEFERRED):** 8 (#6–#13)
- **Total:** 13

## Track 2: Contract Blocks

---

### Organ #1: DisciplineIntentParser

```
Organ: DisciplineIntentParser
Semantic responsibility: Parse free-text discipline intent ("philosophy of technology, STS, with continental register") into structured fields: primary discipline, subfields, intellectual tradition, method orientation, regional affinity, constraints.
Inputs: raw text string (user-typed discipline intent), region hint, user constraints list
Technical preprocessing allowed: string normalization, locale detection, constraint list parsing
Forbidden deterministic decisions: discipline classification, tradition identification, method orientation inference, subfield hierarchy
Output JSON schema:
  {
    "primary_discipline": str,
    "subfields": [str],
    "intellectual_tradition": str | null,
    "method_orientation": str | null,
    "regional_affinity": str | null,
    "parsed_constraints": [str],
    "confidence": "high" | "medium" | "low",
    "unknowns": [str],
    "reasoning": str
  }
Provenance policy: output.evidence_status = "llm_inference"; trace LLM model, tokens, latency
Uncertainty policy: if text is too vague or ambiguous, return confidence="low" with unknowns listing what's unclear; ask questions_for_user
Provider role: single-turn chat completion; system prompt defines discipline taxonomy awareness; user prompt contains raw text
Prompt file: src/kairoskopion/prompts/discipline_intent_parsing.py
Parser/repair: JSON parse → schema validate → repair (normalize field names, coerce types) → fail to needs_llm
Failure behavior: on provider error or parse failure → return intent_parse_status="needs_llm" (current behavior preserved as runtime failure only)
Tests: (a) LLM mock returns valid parse → families populated; (b) LLM raises → needs_llm preserved; (c) LLM returns malformed → repair attempted → fail → needs_llm
Implementation action: CREATE new prompt family + agent (no existing agent matches)
```

---

### Organ #2: VenueFunnelPlanner

```
Organ: VenueFunnelPlanner
Semantic responsibility: Given parsed discipline intent → produce venue family plan: discipline zones to search, journal family clusters, search strategy recommendations, expected venue types.
Inputs: DisciplineIntentResult (from organ #1), region hint, user constraints, existing pathways
Technical preprocessing allowed: region code normalization, constraint deduplication
Forbidden deterministic decisions: venue family identification, discipline→venue mapping, search strategy selection
Output JSON schema:
  {
    "venue_families": [
      {
        "family_name": str,
        "discipline_zone": str,
        "representative_venues": [str],
        "search_strategy": str,
        "expected_fit": "high" | "medium" | "exploratory",
        "notes": str
      }
    ],
    "search_priorities": [str],
    "confidence": "high" | "medium" | "low",
    "unknowns": [str],
    "reasoning": str
  }
Provenance policy: output.evidence_status = "llm_inference"; each family traces to LLM reasoning, not keyword match
Uncertainty policy: if discipline is niche or cross-disciplinary, return fewer families with lower confidence; never fabricate venue names that don't exist
Provider role: single-turn chat completion; system prompt has venue-family taxonomy; user prompt has parsed intent
Prompt file: src/kairoskopion/prompts/venue_funnel_planning.py
Parser/repair: JSON parse → schema validate → filter out families with fabricated venue names → fail to blocked
Failure behavior: on provider error or parse failure → return venue_families_status="FUNNEL_BLOCKED_NEEDS_LLM" (current behavior preserved as runtime failure only)
Tests: (a) LLM mock returns families → populated; (b) LLM fails → BLOCKED preserved; (c) venue names in output are marked as LLM suggestions, not facts
Implementation action: CREATE new prompt family + agent; depends on organ #1 output; can run sequentially in same call flow
```

---

### Organ #3: VenueFamilyContextBuilder

```
Organ: VenueFamilyContextBuilder
Semantic responsibility: Given a concrete investigated venue → infer its discipline family, sibling/competitor venues, venue cluster context.
Inputs: VenueModel (from investigation), venue text snippet, venue canonical name
Technical preprocessing allowed: venue name normalization, ISSN lookup (technical)
Forbidden deterministic decisions: discipline family classification, sibling venue identification, venue cluster assignment
Output JSON schema:
  {
    "source_venue": str,
    "families": [
      {
        "family_name": str,
        "discipline_zone": str,
        "venue_role_in_family": str,
        "sibling_venues": [str]
      }
    ],
    "families_status": "assessed",
    "confidence": "high" | "medium" | "low",
    "unknowns": [str],
    "reasoning": str
  }
Provenance policy: output.evidence_status = "llm_inference"; sibling_venues are LLM-suggested, not verified
Uncertainty policy: if venue is obscure or multi-disciplinary, return confidence="low" with explicit unknowns
Provider role: single-turn chat completion; system prompt has venue landscape knowledge; user prompt has venue model JSON
Prompt file: src/kairoskopion/prompts/venue_family_context.py
Parser/repair: JSON parse → schema validate → fail to blocked
Failure behavior: on provider error or parse failure → return families_status="BLOCKED_NEEDS_LLM" (current behavior preserved as runtime failure only)
Tests: (a) LLM mock returns families → populated; (b) LLM fails → BLOCKED preserved; (c) sibling venues marked as LLM inference not facts
Implementation action: CREATE new prompt family + agent
```

---

### Organ #4: VenueMatrixAssessor

```
Organ: VenueMatrixAssessor
Semantic responsibility: Given venue candidate pool + article context → produce per-candidate semantic assessment on fit axes (topic, discipline, genre, method, core risk).
Inputs: list of VenueCandidate dicts (from pool), article summary (discipline intent or article model), depth mode
Technical preprocessing allowed: candidate list filtering, deduplication, field extraction from candidate dicts
Forbidden deterministic decisions: fit value assignment (strong/medium/weak/bad), risk assessment, topic alignment judgment
Output JSON schema:
  {
    "assessments": [
      {
        "venue_candidate_id": str,
        "canonical_name": str,
        "semantic_assessment": {
          "topic_fit": "strong" | "medium" | "weak" | "bad" | "unknown",
          "discipline_fit": "strong" | "medium" | "weak" | "bad" | "unknown",
          "core_risk": "strong" | "medium" | "weak" | "bad" | "unknown",
          "overall_impression": str,
          "confidence": "high" | "medium" | "low"
        }
      }
    ],
    "unknowns": [str]
  }
Provenance policy: output.evidence_status = "llm_inference"; each assessment traces to LLM reasoning
Uncertainty policy: candidates with insufficient data → return "unknown" per axis, not "medium" or "weak"
Provider role: single-turn chat completion; batch all candidates in one call for consistency; system prompt defines axis vocabulary
Prompt file: src/kairoskopion/prompts/venue_matrix_assessment.py
Parser/repair: JSON parse → schema validate → per-candidate fallback to NOT_ASSESSED if individual parse fails
Failure behavior: on provider error → all candidates get semantic_assessment="NOT_ASSESSED_NEEDS_LLM" (current behavior preserved as runtime failure only)
Tests: (a) LLM mock returns assessments → matrix populated; (b) LLM fails → NOT_ASSESSED preserved; (c) no fake confidence scores
Implementation action: CREATE new prompt family; reuse FitAssessor axis vocabulary
```

---

### Organ #5: DepthRecommendationAgent (OPTIONAL)

```
Organ: DepthRecommendationAgent
Semantic responsibility: Given article complexity signals, venue investigation state, and user budget constraints → recommend optimal depth mode (quick/standard/deep/exhaustive) with reasoning.
Inputs: article_model summary, venue_model summary, current_depth_mode, budget_constraints, investigation_state
Technical preprocessing allowed: cost arithmetic (stays deterministic), budget limit checks
Forbidden deterministic decisions: depth recommendation based on content analysis, complexity assessment
Output JSON schema:
  {
    "recommended_depth": "quick" | "standard" | "deep" | "exhaustive",
    "reasoning": str,
    "cost_tradeoff": str,
    "confidence": "high" | "medium" | "low",
    "warnings": [str]
  }
Provenance policy: output.evidence_status = "llm_inference"
Uncertainty policy: if article/venue data insufficient → return current mode with low confidence
Provider role: single-turn chat completion; system prompt defines depth mode semantics
Prompt file: src/kairoskopion/prompts/depth_recommendation.py
Parser/repair: JSON parse → validate → default to current mode on failure
Failure behavior: on provider error → return current depth_mode with no recommendation (cost arithmetic continues to work deterministically)
Tests: (a) LLM mock returns recommendation → populated; (b) LLM fails → current mode unchanged; (c) cost estimate remains deterministic regardless
Implementation action: CREATE new agent + prompt; OPTIONAL — cost arithmetic is OK_TECHNICAL and stays deterministic; only the recommendation text requires LLM
```

---

### Organ #6: FitAssessmentOrgan (existing: wire as default)

```
Organ: FitAssessmentOrgan
Semantic responsibility: 12-axis semantic fit assessment: ArticleModel × VenueModel × SubmissionScenario → FitAssessment with narrative justification per axis.
Inputs: ArticleModel dict, VenueModel dict, SubmissionScenario dict
Technical preprocessing allowed: field extraction, null-coalescing, evidence_ref compilation
Forbidden deterministic decisions: axis value assignment (strong/medium/weak/bad), overall label selection, recommendation text generation
Output JSON schema: existing FitAssessment schema in prompts/fit_assessment.py
Provenance policy: existing — extraction_attempt metadata, LLM model/tokens/latency trace
Uncertainty policy: existing — unknown axes honest, not_enough_data label when > half unknown
Provider role: existing — single-turn chat completion via FitAssessorAgent.execute()
Prompt file: src/kairoskopion/prompts/fit_assessment.py (EXISTS)
Parser/repair: existing — classify_llm_response + validate_fit_assessment + repair
Failure behavior: CHANGE — on provider error → return FitAssessment with all axes="unknown", overall_label="not_enough_data", confidence="none", with extraction_attempt showing failure reason. DO NOT use deterministic keyword-rule fallback as semantic substitute.
Tests: (a) LLM mock returns valid → full assessment; (b) LLM raises → all-unknown assessment with failure metadata; (c) verify deterministic fallback is NOT used for semantic values
Implementation action: MODIFY FitAssessorAgent._fallback_deterministic → return all-unknown assessment instead of calling services/fit_assessment.py keyword rules
```

---

### Organ #7: MismatchNarrativeOrgan (existing: wire as default)

```
Organ: MismatchNarrativeOrgan
Semantic responsibility: Read FitAssessment weak/bad axes + ArticleModel + VenueModel → produce narrative: what is mismatched, venue-side expectation from actual venue text, severity as semantic judgment, adaptation actions.
Inputs: FitAssessment, ArticleModel dict, VenueModel dict
Technical preprocessing allowed: axis filtering (only weak/bad/unknown), evidence_ref assembly
Forbidden deterministic decisions: severity classification, venue_side narrative, action recommendation
Output JSON schema: existing MismatchMap schema + venue_side narrative field
Provenance policy: existing — llm_usage metadata
Uncertainty policy: if venue text insufficient to infer venue expectation → venue_side="" with unknown marker (current honest behavior)
Provider role: existing — single-turn chat completion via MismatchNarratorAgent
Prompt file: src/kairoskopion/prompts/mismatch_narrative.py (EXISTS)
Parser/repair: existing
Failure behavior: CHANGE — on provider error → return MismatchMap with structural mismatches (axes marked weak/bad) but venue_side="" and narrative_status="needs_llm". DO NOT use hardcoded severity/actions from services/mismatch_mapping.py
Tests: (a) LLM mock → full narrative; (b) LLM fails → structural-only map with needs_llm markers
Implementation action: MODIFY — ensure MismatchNarratorAgent is wired as default path; structural-only fallback replaces deterministic semantic fallback
```

---

### Organ #8: RewritePlanOrgan

```
Organ: RewritePlanOrgan
Semantic responsibility: Given MismatchMap → produce RewritePlan with semantic justification: what to change, why, field-core risk per change, difficulty judgment, conditional vs proposed.
Inputs: MismatchMap, ArticleModel dict, VenueModel dict
Technical preprocessing allowed: mismatch list iteration, change_id generation, field_core_risk enum lookup
Forbidden deterministic decisions: change_type selection, difficulty assessment, desired_state formulation, conditional/proposed classification based on content
Output JSON schema: existing RewritePlan schema
Provenance policy: output.evidence_status = "llm_inference"
Uncertainty policy: unknown axes → conditional changes with explicit "needs venue evidence" notes
Provider role: single-turn chat completion; system prompt defines change_type taxonomy and field_core_risk semantics
Prompt file: src/kairoskopion/prompts/rewrite_planning.py (CREATE)
Parser/repair: JSON parse → schema validate → fail to needs_llm
Failure behavior: on provider error → return RewritePlan with 0 changes, summary="needs_llm_rewrite_planner", lifecycle_status="blocked"
Tests: (a) LLM mock → rewrite plan with changes; (b) LLM fails → blocked plan; (c) field_core_risk correctly propagated from LLM judgment
Implementation action: CREATE new agent + prompt; RewritePlan schema already exists
```

---

### Organ #9: CitationEcologyOrgan

```
Organ: CitationEcologyOrgan
Semantic responsibility: Analyze bibliography × venue context → semantic gap identification, bridge reference strategies, canon alignment assessment, citation ecology health.
Inputs: BibliographyProfile, ArticleModel dict, VenueModel dict, venue_guidelines_text
Technical preprocessing allowed: reference count arithmetic, DOI presence check, year statistics
Forbidden deterministic decisions: gap severity assessment, bridge reference suggestion, canon alignment judgment, recency adequacy determination
Output JSON schema: existing CitationEcologyReport schema
Provenance policy: output.evidence_status = "llm_inference"; bridge references are LLM-suggested, not fabricated citations
Uncertainty policy: if bibliography is empty or venue corpus unknown → return report with honest unknowns, not threshold-based risk
Provider role: single-turn chat completion; system prompt defines citation ecology framework; user prompt has bibliography data + venue context
Prompt file: src/kairoskopion/prompts/citation_ecology_analysis.py (CREATE)
Parser/repair: JSON parse → schema validate → fail to needs_llm
Failure behavior: on provider error → return CitationEcologyReport with unknowns=["LLM citation ecology analysis unavailable"], summary="needs_llm"
Tests: (a) LLM mock → gaps and tasks; (b) LLM fails → unknown report; (c) no fabricated citations
Implementation action: CREATE new agent + prompt; CitationEcologyReport schema already exists
```

---

### Organ #10: MavrinskySemantic (generalize FitAssessor)

```
Organ: MavrinskySemantic (extended FitAssessorAgent)
Semantic responsibility: 16-axis semantic fit assessment for ArticleModel × VenueProfilePackage with corpus evidence. Token-bag counting is NOT semantic assessment.
Inputs: article_model dict, VenueProfilePackage dict, corpus_titles, corpus metadata
Technical preprocessing allowed: corpus_titles list compilation, VenueProfilePackage field extraction, completeness scoring (arithmetic)
Forbidden deterministic decisions: all 16 axis values, bucket assignment, rewrite/citation effort, field_core_risk, strategic_value
Output JSON schema: Extended FitAssessment (16 axes) — same axis structure as organ #6 but with 4 additional axes (argument_form_fit, rewrite_effort, citation_effort, strategic_value, evidence_confidence, unknowns_axis)
Provenance policy: output.evidence_status = "llm_inference"; each axis notes evidence source (corpus_observation vs vpkg_evidence vs inference)
Uncertainty policy: axes without corpus data → "unknown" with honest evidence source, not token-count-based guesses
Provider role: single-turn chat completion; system prompt includes 16-axis rubric; user prompt has article model + VPKG JSON + corpus titles
Prompt file: src/kairoskopion/prompts/fit_assessment.py (EXTEND with 16-axis variant)
Parser/repair: JSON parse → per-axis validation → normalize values → fail individual axes to "unknown" on parse error
Failure behavior: on provider error → return all-unknown 16-axis assessment with lifecycle_status="BLOCKED_NEEDS_LLM"
Tests: (a) LLM mock → 16-axis assessment; (b) LLM fails → all-unknown; (c) no token-bag counting in output; (d) bucket assignment uses LLM axis values, not hardcoded rules
Implementation action: EXTEND FitAssessorAgent to accept VenueProfilePackage input format; add 16-axis prompt variant; keep 12-axis variant for standard pipeline
```

---

### Organ #11: VenueRegimeDetector (extend VenueProfiler)

```
Organ: VenueRegimeDetector (inside VenueProfilerAgent)
Semantic responsibility: Classify publication regime from venue text: classic_journal_article, special_issue_article, conference_proceedings, mega_journal, edited_volume, or null.
Inputs: venue guidelines text (same as VenueProfilerAgent input)
Technical preprocessing allowed: text normalization
Forbidden deterministic decisions: regime classification (substring matching is NOT classification)
Output JSON schema: regime_type field in existing VenueModel extraction output
Provenance policy: extracted by LLM as part of venue fact extraction
Uncertainty policy: if no clear regime signal → return null with unknown, not default to classic_journal
Provider role: already handled by VenueProfilerAgent prompt — ensure regime_type is in the output schema
Prompt file: src/kairoskopion/prompts/venue_fact_extraction.py (EXTEND)
Parser/repair: existing
Failure behavior: on LLM failure → regime_type=null with unknown (current honest behavior already correct)
Tests: (a) LLM mock returns regime → populated; (b) verify _detect_regime() substring matcher is not used as semantic authority
Implementation action: EXTEND venue_fact_extraction prompt to explicitly ask for regime classification; verify VenueProfilerAgent output maps regime_type into VenueModel
```

---

### Organ #12: VenuePolicyExtractor (extend VenueProfiler)

```
Organ: VenuePolicyExtractor (inside VenueProfilerAgent)
Semantic responsibility: Extract structured policy facts from venue text: language policy, open_access_status, apc_policy, review_process_claims, anonymization_policy, ai_policy, data_policy, ethics_policy, word_limits, indexing_claims.
Inputs: venue guidelines text (same as VenueProfilerAgent input)
Technical preprocessing allowed: text normalization
Forbidden deterministic decisions: policy presence/absence judgment from regex (regex finds tokens, not meaning); negation interpretation; policy interpretation
Output JSON schema: policy fields in existing VenueModel extraction output
Provenance policy: each policy field traces to LLM extraction from venue text
Uncertainty policy: if policy text is ambiguous → return null with unknown, not regex-guessed value
Provider role: already handled by VenueProfilerAgent prompt
Prompt file: src/kairoskopion/prompts/venue_fact_extraction.py (EXTEND)
Parser/repair: existing
Failure behavior: on LLM failure → all policy fields null with unknowns (honest)
Tests: (a) LLM mock returns policies → populated; (b) verify _extract_*() regex functions not used as semantic authority; (c) negation correctly handled by LLM, not regex window
Implementation action: EXTEND venue_fact_extraction prompt to explicitly cover all policy fields; verify VenueProfilerAgent maps them into VenueModel
```

---

### Organ #13: ComplianceSemanticOrgan

```
Organ: ComplianceSemanticOrgan
Semantic responsibility: Semantic compliance assessment: does this article's actual CONTENT satisfy this venue's actual REQUIREMENTS? Not just field-present/absent structural matching.
Inputs: ArticleModel, VenueModel, SubmissionScenario, RiskReport, BibliographyProfile, structural pre-check (from build_minimal_compliance_checklist)
Technical preprocessing allowed: structural pre-check (field presence/absence is technical); structural item compilation; deduplication of missing/blocking/warning lists
Forbidden deterministic decisions: compliance satisfaction judgment based on content reading, severity of non-compliance, venue requirement interpretation from text
Output JSON schema: existing ComplianceChecklist schema (enhanced with semantic_status per item)
Provenance policy: structural items retain structural provenance; semantic items get llm_inference provenance
Uncertainty policy: items where venue requirement is unknown → remain "unknown_not_verified", not upgraded to "satisfied" or "not_required"
Provider role: two-phase: (1) structural pre-check (deterministic, OK_TECHNICAL); (2) LLM semantic pass over structural results + article content + venue text → semantic refinement
Prompt file: src/kairoskopion/prompts/compliance_assessment.py (CREATE)
Parser/repair: JSON parse → merge with structural checklist → validate → fail semantic items to "unknown_not_verified" on parse error
Failure behavior: on provider error → return structural-only checklist (current build_minimal_compliance_checklist output) with confidence="structural_only", semantic_status="needs_llm"
Tests: (a) LLM mock → semantic refinement of structural items; (b) LLM fails → structural-only checklist preserved; (c) structural items never downgraded by LLM failure
Implementation action: CREATE new agent + prompt; keep build_minimal_compliance_checklist as structural pre-check input; LLM refines, not replaces
```

---

## Implementation Grouping

### Group A: New organs for P2-blocked branches (Cockpit Track A/B)
- #1 DisciplineIntentParser — new agent + prompt
- #2 VenueFunnelPlanner — new agent + prompt (depends on #1)
- #3 VenueFamilyContextBuilder — new agent + prompt
- #4 VenueMatrixAssessor — new prompt (reuses FitAssessor vocabulary)
- #5 DepthRecommendationAgent — new agent + prompt (OPTIONAL)

### Group B: Rewire existing agents as default path
- #6 FitAssessmentOrgan — modify fallback behavior only
- #7 MismatchNarrativeOrgan — modify fallback behavior only

### Group C: New agents for pipeline services
- #8 RewritePlanOrgan — new agent + prompt
- #9 CitationEcologyOrgan — new agent + prompt
- #10 MavrinskySemantic — extend FitAssessor to 16-axis

### Group D: Extend existing VenueProfiler
- #11 VenueRegimeDetector — extend prompt
- #12 VenuePolicyExtractor — extend prompt

### Group E: Compliance semantic pass
- #13 ComplianceSemanticOrgan — new agent + prompt

## Dependency Order

```
#11, #12 — standalone (extend VenueProfiler prompt)
#1 → #2 — sequential (parse intent, then plan funnel)
#3 — standalone (venue→family context)
#4 — standalone (matrix assessment)
#5 — standalone (optional)
#6 — standalone (modify fallback)
#7 — standalone (modify fallback)
#8 — depends on #7 output (MismatchMap)
#9 — depends on #6 output (FitAssessment)
#10 — extends #6 (16-axis variant)
#13 — depends on #6, #7, #9 outputs
```

## RESULT

`P3_REQUIREMENTS_READY`
