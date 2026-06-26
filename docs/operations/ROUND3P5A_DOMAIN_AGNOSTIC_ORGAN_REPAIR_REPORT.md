# Round III-P5A: Domain-Agnostic Prompt Organ Repair Report

## Objective

Make all 13 LLM organ prompts domain-agnostic. Remove model-memory risks. Expand thin schemas. Add universal epistemic regime awareness.

## Scope

- 11 prompt files rewritten/patched (2 NO_CHANGE)
- 8 agent files updated to match new templates
- 27 new domain-agnostic tests added
- All existing tests updated for schema renames

## Key Changes

### Shared Domain-Agnostic Doctrine

`_DOMAIN_AGNOSTIC_DOCTRINE` constant defined in `discipline_intent_parsing.py`, imported by all 9 modified prompt families. Contains 15 epistemic regimes: mathematical proof, experimental measurement, simulation/modeling, clinical trial, field observation, archival/historical, legal analysis, textual/hermeneutic, design-based, computational/algorithmic, survey/statistical, ethnographic, philosophical/conceptual, engineering validation, meta-analysis/systematic review.

### Model-Memory Blockers Resolved

- Organ #2 (VenueFunnelPlanning): Schema requires `source_ref` + `evidence_status` on every corpus candidate. Validator flags missing source_ref.
- Organ #3 (VenueFamilyContext): Explicit prohibition on sibling/competitor suggestions from LLM training memory. Validator checks neighbors without source_ref.

### Expanded Schemas

- Organ #4 (VenueMatrix): 3 axes to 16 axes, each with evidence_marker (source_evidence/corpus_evidence/user_input/llm_inference/unknown). `semantic_assessment` renamed to `preliminary_assessment`.
- Organ #5 (Depth): 4 generic modes to 5 canonical: quick_scan, light_profile, deep_profile, submission_ready, post_review. Default changed from "standard" to "light_profile".
- Organ #9 (CitationEcology): Replaced humanities-centric roles with 12 domain-agnostic citation roles. 7 gap categories. `key_thinkers` renamed to `reference_anchors`. `venue_canon_alignment` renamed to `venue_alignment_assessment`.
- Organ #8 (Rewrite): Added reframe_candidates, variant_suggestions, patch_queue_readiness. User approval invariant: field_core_risk >= moderate requires requires_user_approval.
- Organ #13 (Compliance): Added submission pack lifecycle: source_freshness_status, missing_policy_areas, privacy_warnings, export_safety_warnings, submission_pack_readiness, user_decisions_required.

### Agent Updates (8 agents)

All 8 agents updated to pass new template variables using `_safe_json()` helper pattern. Output entities updated to match new schema field names.

### Test Results

- Before: 2461 tests passing
- After: 2488 tests passing (+27 new P5A tests)
- 0 failures, 0 errors

## Forbidden List Compliance

All items from the P5A forbidden list verified:

- No hardcoded STS/philosophy/continental theory as default
- No philosophy-specific examples as structural logic
- No humanities article genre assumptions
- No citation ecology = "add thinkers/traditions"
- No empirical/conceptual as only method axis
- No venue family suggestions from model memory
- No "known prestigious journals" from LLM memory
- No candidate venues built from training memory
- No real journal names as candidate facts unless in registered corpus
- No domain-specific examples as product behavior

## Files Changed

### Prompts (src/kairoskopion/prompts/)

- discipline_intent_parsing.py (Organ #1) — full rewrite, doctrine source
- venue_funnel_planning.py (Organ #2) — full rewrite, no-model-memory
- venue_family_context.py (Organ #3) — full rewrite, no-model-memory
- venue_matrix_assessment.py (Organ #4) — full rewrite, 16 axes
- depth_recommendation.py (Organ #5) — full rewrite, canonical modes
- fit_assessment.py (Organ #6) — light patch, doctrine injection
- mismatch_narrative.py (Organ #7) — light patch, multi-domain examples
- rewrite_planning.py (Organ #8) — full rewrite, user approval
- citation_ecology_analysis.py (Organ #9) — full rewrite, 12 roles
- venue_fact_extraction.py (Organs #11/#12) — NO CHANGE
- compliance_assessment.py (Organ #13) — full rewrite, lifecycle

### Agents (src/kairoskopion/agents/)

- discipline_intent_parser.py
- venue_funnel_planner.py
- venue_family_context_builder.py
- venue_matrix_assessor.py
- depth_recommendation.py
- rewrite_planner.py
- citation_ecology.py
- compliance_assessor.py

### API

- src/kairoskopion/api/cases.py — semantic_assessment renamed to preliminary_assessment

### Tests

- tests/test_p5a_domain_agnostic.py — 27 new tests
- tests/test_p4_llm_organs.py — updated for schema renames
- tests/test_phase3_track_a_funnel.py — updated for schema renames

## Verdict

PASS. All 13 organs are domain-agnostic. Model-memory blockers resolved. Thin schemas expanded. 2488 tests green.
