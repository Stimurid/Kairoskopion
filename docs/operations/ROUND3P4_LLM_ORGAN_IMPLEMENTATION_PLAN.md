# Round III-P4: LLM Organ Implementation Plan

**Date:** 2026-06-26
**Branch:** `feature/round3-six-phase-build-hardening`
**Scope:** Implement 13 LLM organs from P3 requirements.

## Implementation Planning Table

| # | Organ | Impl Type | New Prompt | New Schema | Existing Wrapper Reused | Target Files |
|---|-------|-----------|------------|------------|------------------------|--------------|
| 1 | DisciplineIntentParser | NEW_LLM_ORGAN | `prompts/discipline_intent_parsing.py` | DisciplineIntentResult (in prompt) | AgentRole contract | `agents/discipline_intent_parser.py`, `prompts/discipline_intent_parsing.py` |
| 2 | VenueFunnelPlanner | NEW_LLM_ORGAN | `prompts/venue_funnel_planning.py` | VenueFunnelPlan (in prompt) | AgentRole contract | `agents/venue_funnel_planner.py`, `prompts/venue_funnel_planning.py` |
| 3 | VenueFamilyContextBuilder | NEW_LLM_ORGAN | `prompts/venue_family_context.py` | VenueFamilyContext (in prompt) | AgentRole contract | `agents/venue_family_context_builder.py`, `prompts/venue_family_context.py` |
| 4 | VenueMatrixAssessor | NEW_LLM_ORGAN | `prompts/venue_matrix_assessment.py` | VenueMatrixRow (in prompt) | FitAssessor axis vocabulary | `agents/venue_matrix_assessor.py`, `prompts/venue_matrix_assessment.py` |
| 5 | DepthRecommendationAgent | NEW_LLM_ORGAN | `prompts/depth_recommendation.py` | DepthRecommendation (in prompt) | AgentRole contract | `agents/depth_recommendation.py`, `prompts/depth_recommendation.py` |
| 6 | FitAssessmentOrgan | WIRE_EXISTING_ORGAN | — (exists) | — (exists) | `agents/fit_assessor.py` + `prompts/fit_assessment.py` | `agents/fit_assessor.py` (modify `_fallback_deterministic`) |
| 7 | MismatchNarrativeOrgan | WIRE_EXISTING_ORGAN | — (exists) | — (exists) | `agents/mismatch_narrator.py` + `prompts/mismatch_narrative.py` | `agents/mismatch_narrator.py` (verify fallback is honest) |
| 8 | RewritePlanOrgan | NEW_LLM_ORGAN | `prompts/rewrite_planning.py` | RewritePlan (exists in schema.py) | AgentRole contract | `agents/rewrite_planner.py`, `prompts/rewrite_planning.py` |
| 9 | CitationEcologyOrgan | NEW_LLM_ORGAN | `prompts/citation_ecology_analysis.py` | CitationEcologyReport (exists in schema.py) | AgentRole contract | `agents/citation_ecology.py`, `prompts/citation_ecology_analysis.py` |
| 10 | MavrinskySemantic | EXTEND_EXISTING_ORGAN | `prompts/fit_assessment.py` (16-axis variant) | Extended FitAssessment (16 axes) | `agents/fit_assessor.py` | `agents/fit_assessor.py` (add `execute_vpkg` method), `prompts/fit_assessment.py` (add 16-axis variant) |
| 11 | VenueRegimeDetector | EXTEND_EXISTING_ORGAN | `prompts/venue_fact_extraction.py` (extend) | regime_type field (exists in VenueModel) | `agents/venue_profiler.py` | `prompts/venue_fact_extraction.py` (add regime_type), `agents/venue_profiler.py` |
| 12 | VenuePolicyExtractor | EXTEND_EXISTING_ORGAN | `prompts/venue_fact_extraction.py` (extend) | policy fields (exist in VenueModel) | `agents/venue_profiler.py` | `prompts/venue_fact_extraction.py` (add policy fields), `agents/venue_profiler.py` |
| 13 | ComplianceSemanticOrgan | NEW_LLM_ORGAN | `prompts/compliance_assessment.py` | ComplianceChecklist (enhanced) | structural pre-check from `services/compliance_checklist_minimal.py` | `agents/compliance_assessor.py`, `prompts/compliance_assessment.py` |

## New Files to Create

| File | Purpose |
|------|---------|
| `src/kairoskopion/prompts/discipline_intent_parsing.py` | Prompt family for organ #1 |
| `src/kairoskopion/prompts/venue_funnel_planning.py` | Prompt family for organ #2 |
| `src/kairoskopion/prompts/venue_family_context.py` | Prompt family for organ #3 |
| `src/kairoskopion/prompts/venue_matrix_assessment.py` | Prompt family for organ #4 |
| `src/kairoskopion/prompts/depth_recommendation.py` | Prompt family for organ #5 |
| `src/kairoskopion/prompts/rewrite_planning.py` | Prompt family for organ #8 |
| `src/kairoskopion/prompts/citation_ecology_analysis.py` | Prompt family for organ #9 |
| `src/kairoskopion/prompts/compliance_assessment.py` | Prompt family for organ #13 |
| `src/kairoskopion/agents/discipline_intent_parser.py` | Agent for organ #1 |
| `src/kairoskopion/agents/venue_funnel_planner.py` | Agent for organ #2 |
| `src/kairoskopion/agents/venue_family_context_builder.py` | Agent for organ #3 |
| `src/kairoskopion/agents/venue_matrix_assessor.py` | Agent for organ #4 |
| `src/kairoskopion/agents/depth_recommendation.py` | Agent for organ #5 |
| `src/kairoskopion/agents/rewrite_planner.py` | Agent for organ #8 |
| `src/kairoskopion/agents/citation_ecology.py` | Agent for organ #9 |
| `src/kairoskopion/agents/compliance_assessor.py` | Agent for organ #13 |

## Existing Files to Modify

| File | Change |
|------|--------|
| `src/kairoskopion/agents/fit_assessor.py` | #6: `_fallback_deterministic` → all-unknown; #10: add `execute_vpkg` for 16-axis |
| `src/kairoskopion/agents/mismatch_narrator.py` | #7: verify fallback is structural-only (already correct) |
| `src/kairoskopion/prompts/fit_assessment.py` | #10: add 16-axis variant for VPKG assessment |
| `src/kairoskopion/prompts/venue_fact_extraction.py` | #11-12: extend prompt to explicitly ask for regime + policy fields |

## Implementation Order

1. **Batch 1** (no dependencies): #11, #12 (extend VenueProfiler), #6 (fix fallback), #7 (verify fallback), #1 (DisciplineIntentParser), #3 (VenueFamilyContextBuilder), #4 (VenueMatrixAssessor), #5 (DepthRecommendation)
2. **Batch 2** (depends on #1): #2 (VenueFunnelPlanner)
3. **Batch 3** (depends on #6/#7): #8 (RewritePlanner), #9 (CitationEcology), #10 (Mavrinsky 16-axis)
4. **Batch 4** (depends on #6/#7/#9): #13 (ComplianceAssessor)

## Status

| Track | Status |
|-------|--------|
| Track 0: preflight | DONE |
| Track 1: planning table | DONE |
| Track 2: implement #1-5 new organs | IN PROGRESS |
| Track 3: implement #6-13 old organs | IN PROGRESS |
| Track 4: provider metadata | PENDING |
| Track 5: failure policy | PENDING |
| Track 6: tests | PENDING |
| Track 7: integration smoke | PENDING |
| Track 8: reports | PENDING |
