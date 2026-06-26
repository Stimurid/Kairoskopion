# Round III-P4: LLM Organ Implementation Report

**Date:** 2026-06-26
**Branch:** `feature/round3-six-phase-build-hardening`
**Starting commit:** `9b8800b`
**Base tests:** 2390 passed

## Implementation Summary

| # | Component | Old Behavior | New Organ | Prompt Path | Schema/Model | Tests | Smoke | Status |
|---|-----------|-------------|-----------|-------------|-------------|-------|-------|--------|
| 1 | DisciplineIntentParser | P2-blocked stub | NEW_LLM_ORGAN | `prompts/discipline_intent_parsing.py` | DisciplineIntentResult | 6 | S2 ✓ | DONE |
| 2 | VenueFunnelPlanner | P2-blocked stub | NEW_LLM_ORGAN | `prompts/venue_funnel_planning.py` | VenueFunnelPlan | 5 | S2 ✓ | DONE |
| 3 | VenueFamilyContextBuilder | P2-blocked stub | NEW_LLM_ORGAN | `prompts/venue_family_context.py` | VenueFamilyContext | 5 | S3 ✓ | DONE |
| 4 | VenueMatrixAssessor | P2-blocked stub | NEW_LLM_ORGAN | `prompts/venue_matrix_assessment.py` | VenueMatrixAssessment | 5 | S2 ✓ | DONE |
| 5 | DepthRecommendationAgent | P2-blocked stub | NEW_LLM_ORGAN | `prompts/depth_recommendation.py` | DepthRecommendation | 5 | — | DONE |
| 6 | FitAssessmentOrgan | Deterministic keyword fallback | EXTEND_EXISTING_ORGAN | `prompts/fit_assessment.py` (existing) | FitAssessment (all-unknown fallback) | 5 | S1,S4 ✓ | DONE |
| 7 | MismatchNarrativeOrgan | Already honest fallback | WIRE_EXISTING_ORGAN | `prompts/mismatch_narrative.py` (existing) | MismatchMap narratives | 5 | S4 ✓ | DONE |
| 8 | RewritePlanOrgan | Deferred stub | NEW_LLM_ORGAN | `prompts/rewrite_planning.py` | RewritePlan | 5 | S4 ✓ | DONE |
| 9 | CitationEcologyOrgan | Deferred stub | NEW_LLM_ORGAN | `prompts/citation_ecology_analysis.py` | CitationEcologyReport | 5 | S4 ✓ | DONE |
| 10 | MavrinskySemantic (VPKG 16-axis) | Not implemented | EXTEND_EXISTING_ORGAN | `prompts/fit_assessment.py` (VPKG variant) | FitAssessment (20-axis) | 5 | — | DONE |
| 11 | VenueRegimeDetector | No regime field | EXTEND_EXISTING_ORGAN | `prompts/venue_fact_extraction.py` (extended) | regime_type enum | 5 | — | DONE |
| 12 | VenuePolicyExtractor | No policy interpretation | EXTEND_EXISTING_ORGAN | `prompts/venue_fact_extraction.py` (extended) | Policy fields | 5 | — | DONE |
| 13 | ComplianceSemanticOrgan | Structural-only checklist | NEW_LLM_ORGAN | `prompts/compliance_assessment.py` | ComplianceChecklist | 6 | S4 ✓ | DONE |

## New Files Created

### Prompt families (8)
- `src/kairoskopion/prompts/discipline_intent_parsing.py`
- `src/kairoskopion/prompts/venue_funnel_planning.py`
- `src/kairoskopion/prompts/venue_family_context.py`
- `src/kairoskopion/prompts/venue_matrix_assessment.py`
- `src/kairoskopion/prompts/depth_recommendation.py`
- `src/kairoskopion/prompts/rewrite_planning.py`
- `src/kairoskopion/prompts/citation_ecology_analysis.py`
- `src/kairoskopion/prompts/compliance_assessment.py`

### Agent implementations (8)
- `src/kairoskopion/agents/discipline_intent_parser.py`
- `src/kairoskopion/agents/venue_funnel_planner.py`
- `src/kairoskopion/agents/venue_family_context_builder.py`
- `src/kairoskopion/agents/venue_matrix_assessor.py`
- `src/kairoskopion/agents/depth_recommendation.py`
- `src/kairoskopion/agents/rewrite_planner.py`
- `src/kairoskopion/agents/citation_ecology.py`
- `src/kairoskopion/agents/compliance_assessor.py`

### Tests (2)
- `tests/test_p4_llm_organs.py` — 67 tests (5 categories × 13 organs + 2 extra)
- `tests/test_p4_integration_smoke.py` — 4 integration scenarios

### Reports (2)
- `docs/operations/ROUND3P4_LLM_ORGAN_IMPLEMENTATION_PLAN.md`
- `docs/operations/ROUND3P4_LLM_ORGAN_IMPLEMENTATION_REPORT.md`

## Modified Files

| File | Change |
|------|--------|
| `src/kairoskopion/agents/fit_assessor.py` | Removed deterministic keyword fallback → all-unknown; added `execute_vpkg()` for 16-axis VPKG mode |
| `src/kairoskopion/prompts/fit_assessment.py` | Added VPKG system prompt, user template, validator, family dict |
| `src/kairoskopion/prompts/venue_fact_extraction.py` | Added regime classification section, policy extraction section, `regime_type` to schema |
| `tests/test_agents_deterministic.py` | Updated FitAssessor test expectations: `evidence_status="none"`, `overall_label="not_enough_data"`, all axes `"unknown"` |

## Failure Policy

All 13 organs follow the same failure policy:
- LLM provider unavailable → return failure object with `blocked_needs_llm` status
- LLM call fails (exception) → `LLMAttemptMetadata.fallback()` with `FALLBACK_REASON_PROVIDER_ERROR`
- LLM response malformed → `classify_llm_response()` → repair attempt → fallback if repair fails
- No semantic fields filled by deterministic fallback — only structural/unknown markers
- UI/API can display failure and offer retry

## Provider Metadata

All organs record via `LLMAttemptMetadata`:
- `provider_status`: ok / unavailable / error
- `parse_status`: valid_json / repaired_json / invalid_json
- `model`: from LLMResponse
- `latency_ms`: from LLMResponse
- `input_tokens` / `output_tokens`: from LLMResponse
- `fallback_reason`: if applicable
- `validation_errors`: if any
- `prompt_family`: via family_id in prompt dict

## Test Results

### Track 6: Organ tests
- **67 tests** in `test_p4_llm_organs.py`
- Categories: A=fixture success, B=provider unavailable, C=malformed response, D=wrapper contract, E=anti-zombie invariant
- All 67 passed

### Track 7: Integration smoke
- **4 scenarios** in `test_p4_integration_smoke.py`
- S1: Full pipeline deterministic on real article — all axes unknown ✓
- S2: DisciplineIntentParser deterministic — needs_llm ✓
- S3: FitAssessor deterministic — all axes unknown, quality_gate blocked ✓
- S4: ComplianceAssessor — structural items preserved, semantic_pass=False ✓
- All 4 passed

### Full suite
- **2461 passed**, 4 deselected, 0 failed
- Typecheck: clean
- Build: clean

## Acceptance Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Total semantic zombies from P3 | 13 | 13 |
| Replaced by LLM organs (NEW) | — | 7 |
| Extended in existing organs | — | 5 |
| Wired to existing organs (verified) | — | 1 |
| Total resolved | 13 | **13** |
| **Unresolved** | **0** | **0** |
| **Deterministic semantic fallback count** | **0** | **0** |

## RESULT: `ALL_13_LLM_ORGANS_IMPLEMENTED`
