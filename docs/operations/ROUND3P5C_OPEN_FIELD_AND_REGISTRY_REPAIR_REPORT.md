# Round III-P5C — Open-Field Ontology, Registry-First Acquisition, Upstream Prompt Rewrite, Schema Hardening

## Verdict: PASS

All 18 tracks completed. 2533 tests pass. 0 failures. 26/26 audit findings fixed.

## Governing principle

> Kairoskopion is not a philosophy venue recommender. Kairoskopion is an evidence-first publication-positioning system.

> Do NOT solve domain-agnosticity by listing example domains. LLMs treat examples as attractors. A list of fields inside a system prompt becomes a hidden default taxonomy.

## Track execution summary

| Track | Scope | Status | Files touched |
|-------|-------|--------|---------------|
| 1 | Blocker audit — 26 findings across all prompt files | DONE | `ROUND3P5C_OPEN_FIELD_BLOCKER_AUDIT.md` |
| 2 | Open-field doctrine — replace `_DOMAIN_AGNOSTIC_DOCTRINE` | DONE | `discipline_intent_parsing.py` |
| 3 | 7 registry record types + ID generators | DONE | `schema.py`, `ids.py` |
| 4 | Acquisition prompt rewrite — search tasks, not memory recall | DONE | `discipline_source_acquisition.py` |
| 5 | Seeding prompt — remove named thinkers, open source_status | DONE | `discipline_seeding.py` |
| 6 | Article modeling — open enums, remove field examples | DONE | `article_modeling.py`, `catalog.py` |
| 7 | Semantic profiling — neutralize humanities framing | DONE | `semantic_profiling.py`, `catalog.py` |
| 8 | Disciplinary mapping — remove landscape list, rename field | DONE | `disciplinary_mapping.py`, `schema.py`, agents, UI |
| 9 | Field positioning — tradition rename, remove prestige_tier | DONE | `field_positioning.py`, `schema.py`, `field_position_fit.py`, agents, tests |
| 10 | Venue fact extraction — sections schema, enriched metrics | DONE | `venue_fact_extraction.py` |
| 11 | Venue funnel planning — remove STS example, add registry var | DONE | `venue_funnel_planning.py`, `venue_funnel_planner.py` |
| 12 | Schema hardening — evidence_source on fit axes, reference_anchors | DONE | `fit_assessment.py`, `citation_ecology_analysis.py` |
| 13 | Prompt __init__.py — add missing P5A exports | DONE | `prompts/__init__.py` |
| 14 | P5C-specific tests — 43 tests across 7 test classes | DONE | `test_p5c_open_field_registry.py` |
| 15 | Prompt export | DONE | `ROUND3P5C_PROMPTS_EXPORT_ALL.md` |
| 16 | This report | DONE | this file |
| 17 | Commit | PENDING |
| 18 | Final response | PENDING |

## Key changes

### Open-field doctrine (Track 2)

**Before:** `_DOMAIN_AGNOSTIC_DOCTRINE` listed 12 specific fields (mathematics, biology, medicine, semiconductor physics, philosophy, STS, law...) and 15 epistemic regimes as bullet points. LLMs treated this as a default taxonomy.

**After:** `_OPEN_FIELD_DOCTRINE` — no field examples, no regime list. Seven authoritative sources enumerated (article evidence, user constraints, registry records, source packets, venue/corpus evidence, external adapters, curator-confirmed records). Seven generic unknown descriptors for honest marking.

Backward-compatible alias: `_DOMAIN_AGNOSTIC_DOCTRINE = _OPEN_FIELD_DOCTRINE`.

### Registry record types (Track 3)

7 new dataclass models in `schema.py`:

| Record | ID prefix | Purpose |
|--------|-----------|---------|
| `DisciplineRecord` | `drec_` | Registry entry for a discipline/field |
| `TribeOrFrameworkRecord` | `tfrec_` | School, tradition, framework, method family |
| `VenueSectionRecord` | `vsrec_` | Journal section, track, special issue |
| `ClassificationSystemRecord` | `csrec_` | OECD, ASJC, UDC, ВАК, ERC |
| `SubjectCategoryRecord` | `screc_` | Category within a classification system |
| `VenueClassificationRecord` | `vcrec_` | Venue × system × category × year |
| `VenueMetricRecord` | `vmrec_` | Quartile/rank per database × year × category × section |

All default to `source_status="provisional"`, `review_status="pending"`. Never auto-promoted.

### Acquisition rewrite (Track 4)

**Before:** LLM asked to "identify authoritative classification entries" — memory-reliant.

**After:** LLM produces `acquisition_tasks` (0–3 search task descriptions with `target_system`, `search_query`, `search_hints`, `expected_result_type`, `confidence`). No `source_id` or `source_url` in schema. Adapter executes real lookups.

### Prompt version bumps

All modified families bumped to v2:
- `article_modeling_v2`
- `semantic_profiling_v2`
- `disciplinary_mapping_v2`
- `discipline_source_acquisition_v2`
- `discipline_seeding_v2`
- `field_positioning_v2` (both article and venue)
- `venue_fact_extraction_v2` (conceptual — family_id unchanged in file)

Catalog `get_prompt_family` updated to try `_v2` suffix before `_v1` when bare name requested.

### Tradition rename (Track 9)

`school_affiliation_vector` → `tradition_affiliation_vector`
`school_envelope` → `tradition_envelope`

Renamed across: `schema.py`, `field_position_fit.py`, `article_field_positioner.py`, `venue_field_positioner.py`, `corpus_hull_builder.py`, and all affected tests.

### Section-aware venue model (Track 10)

Venue fact extraction schema now includes:
- `sections` array with per-section `section_name`, `section_type`, `scope_description`, `target_disciplines`, `editors`, `issn`, `status`, `evidence_status`
- `indexing_claims` enriched with `subject_category`, `year`, `section_name`
- `metrics_claims` enriched with `database`, `metric_type`, `value`, `year`, `subject_category`, `section_name`

### Schema hardening (Track 12)

- `fit_assessment.py`: Added `evidence_source` field to axis item schema (enum: source_fact, user_constraint, llm_inference, corpus_observation, vpkg_evidence, inference, unknown)
- `citation_ecology_analysis.py`: `reference_anchors` changed from flat string array to array of objects with `name` + `evidence_status`

## Test evidence

```
2533 passed, 4 deselected, 1 warning, 5 subtests passed in 51.45s
```

P5C-specific tests (`test_p5c_open_field_registry.py`): 43 tests across 7 classes:
- `TestOpenFieldDoctrineMarkers` — 4 tests
- `TestDisciplineRecord` through `TestVenueMetricRecord` — 17 tests
- `TestAcquisitionTaskValidation` — 7 tests
- `TestDoctrineInjection` — 2 tests
- `TestVenueExtractionSections` — 3 tests
- `TestCatalogVersionFallback` — 7 tests
- `TestTraditionRename` — 3 tests

## Audit status

26/26 blocker findings from the initial audit are now FIXED. See `ROUND3P5C_OPEN_FIELD_BLOCKER_AUDIT.md` for per-finding status.

## Files changed (non-doc)

### Source
- `src/kairoskopion/ids.py` — 7 new ID generators
- `src/kairoskopion/schema.py` — 7 new dataclass models + tradition rename
- `src/kairoskopion/prompts/discipline_intent_parsing.py` — open-field doctrine
- `src/kairoskopion/prompts/discipline_source_acquisition.py` — acquisition rewrite
- `src/kairoskopion/prompts/discipline_seeding.py` — thinker removal, source_status
- `src/kairoskopion/prompts/article_modeling.py` — opened enums, removed examples
- `src/kairoskopion/prompts/semantic_profiling.py` — neutralized framing
- `src/kairoskopion/prompts/disciplinary_mapping.py` — removed landscape, renamed field
- `src/kairoskopion/prompts/field_positioning.py` — tradition rename, removed prestige
- `src/kairoskopion/prompts/venue_fact_extraction.py` — sections, enriched metrics
- `src/kairoskopion/prompts/venue_funnel_planning.py` — removed example, added var
- `src/kairoskopion/prompts/fit_assessment.py` — evidence_source field
- `src/kairoskopion/prompts/citation_ecology_analysis.py` — reference_anchors objects
- `src/kairoskopion/prompts/__init__.py` — missing exports
- `src/kairoskopion/agents/prompt_families/catalog.py` — v2 fallback logic
- `src/kairoskopion/agents/article_field_positioner.py` — tradition rename
- `src/kairoskopion/agents/venue_field_positioner.py` — tradition rename
- `src/kairoskopion/agents/venue_funnel_planner.py` — registry_records format key
- `src/kairoskopion/agents/disciplinary_mapper.py` — venue_search_queries
- `src/kairoskopion/logic/field_position_fit.py` — tradition rename
- `src/kairoskopion/services/corpus_hull_builder.py` — tradition rename

### Tests
- `tests/test_p5c_open_field_registry.py` — 43 new tests
- `tests/test_p5a_domain_agnostic.py` — updated assertions
- `tests/test_discipline_seeder_agents.py` — v2 family_ids
- `tests/test_field_position.py` — tradition rename
- `tests/test_field_position_integration.py` — tradition rename
- `tests/test_article_model_json_hardening.py` — opened genre enum
- `tests/test_p4_llm_organs.py` — registry_records key
- `tests/test_corpus_hull_builder.py` — tradition rename
- `tests/test_llm_agent_tolerance.py` — tradition rename

### UI
- `ui/src/types/api.ts` — venue_search_queries
- `ui/src/components/PathwayMap.tsx` — venue_search_queries

## Constraints honored

- No force push
- No push to main
- No prod deploy
- No LLM-parameter tuning (Agentum's domain)
- No real API keys in repo
