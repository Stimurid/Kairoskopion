# Round III-P5A — LLM Organ Prompt Families: Summary Index

All 13 prompt organs repaired under Round III-P5A semantic doctrine enforcement.
Every family is now **v2** and lives under `src/kairoskopion/prompts/`.

| # | Organ Name | File | Family Constant(s) | Ver | Key Changes |
|---|-----------|------|---------------------|-----|-------------|
| 1 | DisciplineIntentParsing | `discipline_intent_parsing.py` | `DISCIPLINE_INTENT_SYSTEM`, `DISCIPLINE_INTENT_USER_TEMPLATE` | v2 | Domain-agnostic doctrine source, epistemic regime, field translations |
| 2 | VenueFunnelPlanning | `venue_funnel_planning.py` | `VENUE_FUNNEL_SYSTEM`, `VENUE_FUNNEL_USER_TEMPLATE` | v2 | No model-memory, source_ref required, corpus candidates |
| 3 | VenueFamilyContext | `venue_family_context.py` | `VENUE_FAMILY_CONTEXT_SYSTEM`, `VENUE_FAMILY_CONTEXT_USER_TEMPLATE` | v2 | No model-memory sibling suggestions, evidence_basis required |
| 4 | VenueMatrixAssessment | `venue_matrix_assessment.py` | `VENUE_MATRIX_SYSTEM`, `VENUE_MATRIX_USER_TEMPLATE` | v2 | 16 axes with evidence markers, preliminary_assessment replaces semantic_assessment |
| 5 | DepthRecommendation | `depth_recommendation.py` | `DEPTH_RECOMMENDATION_SYSTEM`, `DEPTH_RECOMMENDATION_USER_TEMPLATE` | v2 | 5 canonical modes, cost/risk tradeoff |
| 6 | FitAssessment | `fit_assessment.py` | `FIT_ASSESSMENT_SYSTEM`, `FIT_ASSESSMENT_USER_TEMPLATE` | v2 | Light patch: doctrine injection, evidence_source per axis |
| 7 | MismatchNarrative | `mismatch_narrative.py` | `MISMATCH_NARRATIVE_SYSTEM`, `MISMATCH_NARRATIVE_USER_TEMPLATE` | v2 | Light patch: multi-domain examples, user-approval for core |
| 8 | RewritePlanning | `rewrite_planning.py` | `REWRITE_PLANNING_SYSTEM`, `REWRITE_PLANNING_USER_TEMPLATE` | v2 | reframe_candidates, patch_queue_readiness, user_approval invariant |
| 9 | CitationEcologyAnalysis | `citation_ecology_analysis.py` | `CITATION_ECOLOGY_SYSTEM`, `CITATION_ECOLOGY_USER_TEMPLATE` | v2 | 12 domain-agnostic roles, 7 gap categories, reference_anchors |
| 10 | VenueFactExtraction | `venue_fact_extraction.py` | `VENUE_FACT_EXTRACTION_SYSTEM`, `VENUE_FACT_EXTRACTION_USER_TEMPLATE` | v2 | NO_CHANGE_REQUIRED — already compliant |
| 11 | VenueFactExtraction (alias) | `venue_fact_extraction.py` | (same as #10) | v2 | NO_CHANGE_REQUIRED — same file, organ numbering artefact |
| 12 | (reserved) | — | — | — | Alias of #10/#11, no separate file |
| 13 | ComplianceAssessment | `compliance_assessment.py` | `COMPLIANCE_ASSESSMENT_SYSTEM`, `COMPLIANCE_ASSESSMENT_USER_TEMPLATE` | v2 | Submission pack lifecycle, freshness, privacy/export warnings |

**Total distinct prompt files touched:** 11 (10 modified + 1 confirmed no-change-required).

All families enforce: no model-memory reliance, evidence_source traceability,
domain-agnostic examples, and LLM-only semantic doctrine per Round III-P2.
