# Round III-P2: Semantic Zombie Audit

**Date:** 2026-06-26

## Audit scope
All code added/modified in the 6-phase build (Round III-O, commits a638f11..8260f09), plus pre-existing services called by new code.

## Audit table

| File | Function | Behavior | Det. Technical? | Det. Semantic? | LLM-backed? | Classification | Action |
|------|----------|----------|:-:|:-:|:-:|----------------|--------|
| cases.py | `_infer_venue_families()` | keyword→discipline zone map | NO | YES | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | **REMOVED** |
| cases.py | `set_discipline_intent()` | stored raw text + called zombie | PARTIAL | YES (via _infer) | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | **FIXED** — stores text, marks needs_llm |
| cases.py | `_build_venue_family_from_venue()` | called zombie on venue name | NO | YES | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | **FIXED** — stores identity, marks BLOCKED |
| cases.py | `get_venue_matrix()` | exposed `confidence` field | PARTIAL | YES (confidence) | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | **FIXED** — removed confidence, added NOT_ASSESSED |
| cases.py | `investigate_venue_by_url()` | no SSRF protection | N/A | N/A | N/A | SECURITY_GAP | **FIXED** — full SSRF gate |
| cases.py | `set_adapter_mode()` | no env gate for LIVE_API | N/A | N/A | N/A | SECURITY_GAP | **FIXED** — env-gated |
| cases.py | `enrich_venue()` | compiles VenueProfilePackage | YES | NO | NO | OK_TECHNICAL_DETERMINISM | No action |
| cases.py | `get_venue_profile_package()` | returns compiled package | YES | NO | NO | OK_TECHNICAL_DETERMINISM | No action |
| cases.py | `get_compliance()` | calls minimal checklist | YES | PARTIAL | NO | OK_TECHNICAL_DETERMINISM | Labeled "mechanical" |
| cases.py | `build_submission_pack_api()` | compiles pack from parts | YES | NO | NO | OK_TECHNICAL_DETERMINISM | No action |
| cases.py | `set_depth_mode()` | mode selection | YES | NO | NO | OK_TECHNICAL_DETERMINISM | No action |
| cases.py | `set_budget_constraints()` | budget storage | YES | NO | NO | OK_TECHNICAL_DETERMINISM | No action |
| cases.py | `get_cost_estimate()` | arithmetic per mode | YES | NO | NO | OK_TECHNICAL_DETERMINISM | No action |
| venue_memory.py | `VenueMemoryRecord` | no review gate | PARTIAL | NO | NO | AUTO_CANONICALIZATION_RISK | **FIXED** — review_status, provenance |
| venue_memory.py | `upsert_from_venue()` | auto-upsert facts | YES | NO | NO | AUTO_CANONICALIZATION_RISK | **FIXED** — starts provisional |
| fit_assessment.py | `assess_fit()` | 12-axis keyword rules | NO | YES | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | DEFERRED — pre-existing agent fallback |
| mismatch_mapping.py | `build_mismatch_map()` | hardcoded severity/actions | NO | YES | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | DEFERRED — pre-existing agent fallback |
| rewrite_planning.py | `build_rewrite_plan()` | axis→change_type map | NO | YES | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | DEFERRED — pre-existing agent fallback |
| citation_ecology.py | `build_citation_ecology_report()` | threshold-based risk | NO | YES | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | DEFERRED — pre-existing agent fallback |
| mavrinsky_venue_selection.py | `assess_fit_for_vpkg()` | token hit counts | NO | YES | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | DEFERRED — pre-existing agent fallback |
| venue_profiling.py | `_detect_regime()` | substring→regime | NO | YES (borderline) | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | DEFERRED — pre-existing |
| venue_profiling.py | `_extract_*()` | regex→policy claims | NO | YES | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | DEFERRED — pre-existing |
| compliance_checklist_minimal.py | `build_minimal_compliance_checklist()` | field presence→status | PARTIAL | PARTIAL | NO | ZOMBIE_DETERMINISTIC_SEMANTIC | DEFERRED — labeled "mechanical" |
| discipline_matcher.py | `execute_deterministic()` | registry keyword pre-filter | YES | NO | NO | OK_TECHNICAL_DETERMINISM | No action (transparent, confidence=low) |
| input_classifier.py | `execute_deterministic()` | asks user, no guessing | YES | NO | NO | OK_TECHNICAL_DETERMINISM | No action |
| semantic_profiler.py | `execute_deterministic()` | copies fields, marks unknown | YES | BORDERLINE | NO | OK_TECHNICAL_DETERMINISM | No action (marked fallback) |
| fit_assessor.py | `_fallback_deterministic()` | wraps hardcoded fit | NO | YES | NO | SEMANTIC_FALLBACK_MUST_BLOCK | DEFERRED |

## Summary

- **REMOVED:** 1 (keyword→family map)
- **FIXED:** 5 (intent storage, family context, matrix, SSRF, adapter gate, VenueMemory review)
- **DEFERRED:** 8 (pre-existing agent fallbacks — require LLM organ contracts)
- **OK_TECHNICAL:** 12 (file IO, routing, arithmetic, compilation)
