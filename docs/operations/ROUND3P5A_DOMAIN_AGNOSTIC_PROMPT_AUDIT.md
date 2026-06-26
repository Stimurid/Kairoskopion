# Round III-P5A: Domain-Agnostic Prompt Maturity Audit

**Date:** 2026-06-26
**Reviewer:** Claude (automated) + owner direction
**Scope:** All 13 LLM organs from P4

## Audit Table

| # | Organ | Current Issue | Domain Lock-in? | Model-Memory Risk? | Thin-Contract Risk? | Required Repair | Verdict |
|---|-------|--------------|:--------------:|:-----------------:|:------------------:|----------------|---------|
| 1 | DisciplineIntentParser | Free-text parser only; system prompt uses "philosophy of technology, STS, continental register" as example; no article-awareness; no protected-core input | YES — philosophy/STS examples as structural logic | NO | YES — only parses operator text, ignores article evidence | Rename to Interpreter; expand inputs (ArticleModel, SemanticProfile, DisciplineMatches, protected core, scenario); add domain-agnostic epistemic regime; remove philosophy examples as default mental model | `NEEDS_DOMAIN_GENERALIZATION` |
| 2 | VenueFunnelPlanner | Asks for `representative_venues` from LLM memory; "STS core journals" as example family name; no corpus/evidence input | YES — STS example families | **YES — BLOCKER**: representative_venues from training memory presented as suggestions | NO | Remove model-memory venue facts; add corpus/evidence/VenueMemory inputs; separate known_corpus_candidates from external_discovery_tasks; no venue names without source_ref | `BLOCKER_MODEL_MEMORY_RECOMMENDER` |
| 3 | VenueFamilyContextBuilder | Suggests sibling venues from LLM memory; labels venue roles (flagship/mid-tier/emerging) without evidence; no corpus input | NO (prompt is generic) | **YES — BLOCKER**: sibling_venues from training memory; venue_role_in_family without evidence | NO | Remove model-memory siblings; add corpus/evidence inputs; use role_unknown when evidence absent; separate verified from unverified neighbors | `BLOCKER_MODEL_MEMORY_RECOMMENDER` |
| 4 | VenueMatrixAssessor | Only 3 axes (topic_fit, discipline_fit, core_risk); no epistemic regime; no evidence markers; no method/genre/language/audience axes | NO | NO | **YES**: 3 axes is too thin for preliminary pool matrix | Expand to 16 axes (per spec Track 6); add evidence/unknown markers per label; add preliminary_pool_fit framing; add domain-agnostic epistemic regime awareness | `THIN_JSON_CONTRACT` + `NEEDS_SCHEMA_EXPANSION` |
| 5 | DepthRecommendationAgent | Generic quick/standard/deep/exhaustive menu; no canonical mode names; no cost/adapter awareness; no field/epistemic regime awareness | NO | NO | YES — generic 4-level menu, not canonical depth strategy | Replace with canonical 5 modes (quick_scan/light_profile/deep_profile/submission_ready/post_review); add mechanical cost inputs; add adapter/organ activation plan; add stop conditions | `NEEDS_DOMAIN_GENERALIZATION` |
| 6 | FitAssessmentOrgan | Acceptable 16-axis baseline; no explicit evidence_source per axis; no domain-agnostic epistemic regime doctrine | NO (already generic) | NO | NO | Light patch: add domain-agnostic doctrine; add evidence_source distinction (source_fact/user_constraint/llm_inference/unknown) note; no field-specific assumptions | `NO_CHANGE_REQUIRED` → light patch |
| 7 | MismatchNarrativeOrgan | Acceptable baseline; uses "postphenomenological tradition (Verbeek, Ihde)" as citation example — humanities-biased; no user-decision requirement for core-touching actions | YES — humanities citation example | NO | NO | Light patch: add domain-agnostic doctrine; replace humanities-specific citation example with multi-domain examples; add user-decision requirement for core-touching actions | `NEEDS_DOMAIN_GENERALIZATION` (light) |
| 8 | RewritePlanOrgan | Adequate contract; no PatchQueue/WhiteCrow semantics; no protected-core approval workflow; no ReframePlan/ArticleVariant; no genre-conversion user-approval | NO | NO | YES — no operational lifecycle integration | Add protected-core user-approval; add ReframePlan candidates; add PatchQueue readiness; add no-op recommendations; add user-approval for genre/field/method changes | `NEEDS_DOMAIN_GENERALIZATION` |
| 9 | CitationEcologyOrgan | "canon_gap" and "key thinkers/traditions" are humanities-biased categories; bridge_references.key_thinkers assumes thinker-centric fields; no math/experimental/engineering citation logic | **YES**: canon_gap, key_thinkers, tradition-centric | NO | NO | Expand role map for all fields (proof/theorem, benchmark, standards, data/method citations); replace key_thinkers with field-neutral reference_anchors; add epistemic-regime-aware gap categories | `NEEDS_DOMAIN_GENERALIZATION` |
| 10 | MavrinskySemantic (VPKG) | Reuses FitAssessment VPKG mode via execute_vpkg(); no distinct prompt or semantic responsibility; name implies separate organ but is a mode of FitAssessorAgent | NO | NO | NO | Rename/report as FitAssessmentVPKGMode; it is not a separate organ — it is a mode of organ #6 | `SUBORGAN_RENAME_OR_MERGE` |
| 11 | VenueRegimeDetector | Acceptable source-only extraction suborgan embedded in venue_fact_extraction.py; no model-memory facts | NO | NO | NO | No change required; keep source-only discipline | `NO_CHANGE_REQUIRED` |
| 12 | VenuePolicyExtractor | Acceptable source-only extraction suborgan embedded in venue_fact_extraction.py; no model-memory facts | NO | NO | NO | No change required; keep source-only discipline | `NO_CHANGE_REQUIRED` |
| 13 | ComplianceSemanticOrgan | Acceptable baseline; no SubmissionPack lifecycle; no source freshness; no privacy/export warnings | NO | NO | YES — missing operational lifecycle | Add SubmissionPack readiness; add source freshness/staleness; add missing policy areas; add privacy/personal-data warnings; add export safety | `NEEDS_DOMAIN_GENERALIZATION` |

## Summary

| Verdict | Count | Organs |
|---------|-------|--------|
| `BLOCKER_MODEL_MEMORY_RECOMMENDER` | 2 | #2, #3 |
| `NEEDS_DOMAIN_GENERALIZATION` | 5 | #1, #5, #7, #8, #9 |
| `THIN_JSON_CONTRACT` + `NEEDS_SCHEMA_EXPANSION` | 1 | #4 |
| `NEEDS_DOMAIN_GENERALIZATION` (light patch) | 2 | #6, #13 |
| `SUBORGAN_RENAME_OR_MERGE` | 1 | #10 |
| `NO_CHANGE_REQUIRED` | 2 | #11, #12 |

**Blockers: 2** (#2 VenueFunnelPlanner, #3 VenueFamilyContextBuilder)
**Repairs required: 9** (#1, #2, #3, #4, #5, #6, #7, #8, #9, #13 + rename #10)
**Unchanged: 2** (#11, #12)
