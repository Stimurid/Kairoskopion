# Round III-P4: Remaining Zombie Grep Review

**Date:** 2026-06-26
**Pattern:** `DEFERRED|BLOCKED_NEEDS_LLM|blocked_needs_llm|deterministic fallback|semantic fallback|keyword|heuristic|infer_|stub|TODO|FIXME|needs_llm`

## Classification

### `needs_llm` — runtime failure status (ACCEPTABLE)

These are honest failure markers when LLM is unavailable. They do NOT produce semantic content.

| File | Context | Verdict |
|------|---------|---------|
| `agents/discipline_intent_parser.py:115` | `intent_parse_status: needs_llm` on fallback | OK — runtime failure |
| `agents/venue_funnel_planner.py:117` | `venue_families_status: FUNNEL_BLOCKED_NEEDS_LLM` | OK — runtime failure |
| `agents/venue_family_context_builder.py:114` | `families_status: BLOCKED_NEEDS_LLM` | OK — runtime failure |
| `agents/mismatch_narrator.py:252` | `narrative_status: needs_llm` | OK — runtime failure |
| `agents/rewrite_planner.py:155` | `summary: needs_llm_rewrite_planner` | OK — runtime failure |
| `agents/citation_ecology.py:147` | `summary: needs_llm` | OK — runtime failure |
| `api/cases.py:1089-1128` | Discipline intent/funnel/family fallback markers | OK — runtime failure |
| `api/cases.py:1886-1971` | Mismatch narrative `needs_llm` status handling | OK — runtime failure |
| `api/cases.py:2034-2084` | Risk officer / rewrite planner `needs_llm` fallback | OK — runtime failure |
| `services/llm_semantic_organs.py` | Full module for wiring LLM organs with `needs_llm` fallback | OK — runtime failure |
| `services/risk_report_needs_llm.py` | Builds empty risk report with `needs_llm` markers | OK — placeholder builder |
| `services/rewrite_plan_needs_llm.py` | Builds empty rewrite plan with `needs_llm` markers | OK — placeholder builder |
| `services/citation_plan_minimal.py:130,182,258` | Empty semantic fields with `origin=needs_llm` | OK — runtime failure |
| `services/human_dossier.py:396,1330,1406` | Russian-language handling of `needs_llm` status | OK — UI display |
| `services/llm_attempt_diagnostics.py:61` | `SEMANTIC_NEEDS_LLM` constant | OK — status constant |

### `deterministic fallback` — docstring/comment references (ACCEPTABLE)

| File | Context | Verdict |
|------|---------|---------|
| `agents/article_modeler.py:4` | Docstring: "with deterministic fallback" | OK — describes architecture |
| `agents/contract.py:5,60` | Contract docstring: "deterministic fallback" | OK — describes interface |
| `agents/fit_assessor.py:4,321` | Docstring + trace note "no deterministic semantic fallback" | OK — P4 change |
| `agents/mismatch_narrator.py:9` | Docstring: "Honest deterministic fallback" | OK — describes architecture |
| `agents/venue_profiler.py:4` | Docstring | OK |
| `pipelines/manuscript_venue_fit.py:4` | Docstring | OK |
| `services/llm_semantic_organs.py:4` | Docstring: explains removal of deterministic fallback | OK |
| `api/app.py:24` | Comment about agents dropping to fallback | OK |

### `heuristic` — technical extraction status (ACCEPTABLE)

| File | Context | Verdict |
|------|---------|---------|
| `agents/article_modeler.py:231-232` | `evidence_status="heuristic"` for regex extraction | OK — honest label for pre-LLM extraction |
| `agents/venue_profiler.py:123-124` | `evidence_status="heuristic"` for regex extraction | OK |
| `agents/semantic_profiler.py:190` | `evidence_status="heuristic"` | OK |
| `agents/disciplinary_mapper.py:237` | `evidence_status="heuristic"` | OK |
| `schema.py:482,541` | Disclaimer: "parsed heuristically from text" | OK — honest disclaimer |
| `services/article_enrichment.py` | Argument-move keyword detection | OK — pre-LLM technical feature |
| `services/article_modeling.py` | regex-based extraction | OK — deterministic extraction |
| `services/corpus_analyzer.py` | keyword-pattern corpus analysis | OK — deterministic pre-filter |
| `adapters/venue/editorial_board.py:283` | "heuristic patterns" for editor name parsing | OK — regex extraction |
| `enums.py:324` | Comment: "heuristic, not verified" | OK — enum documentation |

### `keyword` — technical search/pre-filter (ACCEPTABLE)

| File | Context | Verdict |
|------|---------|---------|
| `services/discipline_registry/loader.py:96` | `candidates_keyword()` — substring pre-filter | OK — technical pre-filter, not semantic judgment |
| `services/fit_assessment.py:54-109` | `overlap_keywords` in legacy deterministic fit | **NOTE:** This is the OLD deterministic fit service. It is NO LONGER CALLED by FitAssessorAgent (P4 removed that call). Dead code path — still exists as a service but the agent bypasses it. |
| `services/article_enrichment.py:56,77,121-122` | `_extract_keywords()`, `_ARGUMENT_MOVE_PATTERNS` | OK — technical extraction features |
| `schema.py:232` | `keywords: list[str]` field on ArticleModel | OK — domain model field |
| `services/compliance.py:83-99` | keyword count compliance check | OK — structural compliance |
| `prompts/article_modeling.py:40,50` | "Extract from argument, not from abstract keywords" | OK — anti-keyword-dependency instruction |
| `prompts/disciplinary_mapping.py:22` | "not just a keyword" | OK — anti-keyword instruction |
| `agents/discipline_matcher.py:79,177-202` | `candidates_keyword` + fallback warning | OK — honest keyword-only label |

### `stub` — integration stubs and contract-only agents (ACCEPTABLE)

| File | Context | Verdict |
|------|---------|---------|
| `integrations/litops.py:1,3` | "interface/stub dataclasses" for Litops integration | OK — bounded context boundary |
| `integrations/whitecrow.py:1,3` | "interface/stub dataclasses" for WhiteCrow integration | OK — bounded context boundary |
| `agents/review/*.py` | "contract-only stub (future: LLM-required)" | OK — review layer not in P4 scope |
| `agents/base_shell.py:117` | `_contract_stub()` builder | OK — agent infrastructure |
| `agents/discipline_seeder.py:203,236` | Identity-only stub for unknown disciplines | OK — honest identity marker |
| `agents/discipline_source_acquisition.py:164-184` | `curator-stub` packet | OK — manual curation placeholder |
| `adapters/venue/base.py:13` | `OFFLINE_STUB` adapter mode | OK — offline/test mode |
| `api/cases.py:148-149` | `adapter_mode: "offline_stub"` default | OK — default offline mode |

### `DEFERRED` — enum value (ACCEPTABLE)

| File | Context | Verdict |
|------|---------|---------|
| `enums.py:299,531` | `DEFERRED = "deferred"` enum members | OK — lifecycle enum values used by non-P4 features |

### `TODO` / `FIXME` (NONE FOUND)

No TODO or FIXME hits in the grep results for P4-scoped files.

### `infer_` — function names (ACCEPTABLE)

| File | Context | Verdict |
|------|---------|---------|
| `services/article_enrichment.py:139` | `_infer_audience()` | OK — pre-LLM technical function, returns heuristic label |

## Summary

| Category | Count | Verdict |
|----------|-------|---------|
| `needs_llm` as runtime failure | 15+ | ACCEPTABLE |
| `deterministic fallback` in docstrings | 8 | ACCEPTABLE |
| `heuristic` as evidence_status | 10 | ACCEPTABLE |
| `keyword` as pre-filter | 8 | ACCEPTABLE |
| `stub` for integrations/contracts | 10+ | ACCEPTABLE |
| `DEFERRED` enum | 2 | ACCEPTABLE |
| Active semantic zombie | **0** | **CLEAN** |

### Dead code note
`services/fit_assessment.py` contains the OLD deterministic fit function with `overlap_keywords`. It is no longer called by `FitAssessorAgent` (P4 replaced the call path), but the service file still exists and could be called by other code paths (e.g. the pipeline's deterministic mode). This is acceptable — the pipeline's deterministic mode is explicitly documented as "no LLM" mode and the agent's `execute_deterministic()` now returns all-unknown instead of calling this function.

## RESULT: No active semantic zombies in P4 scope.
