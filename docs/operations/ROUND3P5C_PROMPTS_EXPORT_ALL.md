# Round III-P5C Prompt Families Export

Generated: 2026-06-26

## Summary table

| # | File | family_id | version | Open-field doctrine | Key P5C changes |
|---|------|-----------|---------|---------------------|-----------------|
| 1 | `discipline_intent_parsing.py` | `discipline_intent_parsing_v2` | 2.0.0 | Injected (`_OPEN_FIELD_DOCTRINE`) | Opened enums: epistemic_regime free string, `additionalProperties: True` on root and sub-objects |
| 2 | `discipline_source_acquisition.py` | `discipline_source_acquisition_v2` | 2.0.0 | Injected (via import) | New family (P5C). Anti-memory rules: source_id/source_url always null, no recalled codes |
| 3 | `discipline_seeding.py` | `discipline_seeding_v2` | 2.0.0 | Injected (via import) | New family (P5C). `source_status` forced to `"provisional"`, key_authors only from packets |
| 4 | `article_modeling.py` | `article_modeling_v2` | 2.0.0 | Injected (via import) | Opened enums: `method_status` free string, `genre_current` free string, `argument_structure` free string. Relaxed required: `title`, `confidence`, `questions_for_user` moved to optional |
| 5 | `semantic_profiling.py` | `semantic_profiling_v2` | 2.0.0 | Injected (via import) | Opened enum: `argument_move_type` free string with description. `required: []` (all optional). `additionalProperties: True` |
| 6 | `disciplinary_mapping.py` | `disciplinary_mapping_v2` | 2.0.0 | Injected (via import) | Added `venue_search_queries` field (no memory venue names). `additionalProperties: False` on pathway items |
| 7a | `field_positioning.py` | `article_field_position_v2` | 2.0 | Injected (via import) | New family (P5C). 7-group axis model. `tradition_affiliation_vector` may be empty |
| 7b | `field_positioning.py` | `venue_field_position_v2` | 2.0 | Injected (via import) | New family (P5C). Envelope model (center + [min,max] per axis). Institutional signals: no single prestige tier |
| 8 | `venue_fact_extraction.py` | `venue_fact_extraction_v2` | 2.0.0 | Injected (via import) | Sections/tracks/special issues as first-class records. Indexing/metrics per-database/year/category. Evidence status taxonomy |
| 9 | `venue_funnel_planning.py` | `venue_funnel_planning_v2` | 2.0.0 | Injected (via `_DOMAIN_AGNOSTIC_DOCTRINE` alias) | No model-memory venue facts rule. `known_corpus_candidates` require `source_ref` + `evidence_status` |
| 10 | `fit_assessment.py` | `fit_assessment_v1` | 1.0.0 | Injected (via `_DOMAIN_AGNOSTIC_DOCTRINE` alias) | `evidence_source` enum expanded: `corpus_observation`, `vpkg_evidence`, `inference`. `required: []` (all optional). `additionalProperties: True`. VPKG 20-axis variant added |
| 11 | `citation_ecology_analysis.py` | `citation_ecology_analysis_v2` | 2.0.0 | Injected (via `_DOMAIN_AGNOSTIC_DOCTRINE` alias) | Domain-agnostic citation role taxonomy (12 roles). `bridge_references` with `evidence_status` per anchor. Gap categories domain-agnostic |

---

## Per-family details

### 1. discipline_intent_parsing_v2

**File:** `src/kairoskopion/prompts/discipline_intent_parsing.py`

**System prompt (first 3 lines):**
```
You are Discipline Intent Interpreter — a specialized role in
Kairoskopion's venue-positioning pipeline.

Your input:
```

**Open-field doctrine:** Yes, `_OPEN_FIELD_DOCTRINE` defined in this file and shared across all families.

**Version:** 2.0.0

**P5C changes:** `epistemic_regime` is free string (not enum). `additionalProperties: True` on root and on `article_supported_field_readings` items and `possible_field_translations` items. Schema allows open-ended field names.

---

### 2. discipline_source_acquisition_v2

**File:** `src/kairoskopion/prompts/discipline_source_acquisition.py`

**System prompt (first 3 lines):**
```
You are Discipline Source Acquisition Planner — Phase B agent for
Kairoskopion's disciplinary landscape registry.

Your job: given a discipline name, a region hint, and existing registry
```

**Open-field doctrine:** Yes, imported from `discipline_intent_parsing`.

**Version:** 2.0.0

**P5C changes:** New family created in P5C. Anti-memory rules enforced: `source_id` and `source_url` must always be null. No recalled classification codes, passport numbers, ASJC codes. Max 3 tasks per call. `additionalProperties: False` on task items.

---

### 3. discipline_seeding_v2

**File:** `src/kairoskopion/prompts/discipline_seeding.py`

**System prompt (first 3 lines):**
```
You are Discipline Seeder — Phase B agent for Kairoskopion's
disciplinary landscape registry.

Your job: given source packets describing a discipline, produce a
```

**Open-field doctrine:** Yes, imported from `discipline_intent_parsing`.

**Version:** 2.0.0

**P5C changes:** New family created in P5C. `source_status` forced to `"provisional"` (was `"llm_draft"`). `key_authors` only from packet excerpts, never from LLM memory. `key_authors[].role` enum: `founder`, `classic`, `contemporary`, `boundary_setter`, `critic`. Working-tool fields (`legitimate_objects`, `canonical_questions`, `forms_of_evidence`) validated non-empty. `evidence_refs` must mirror input packets. `additionalProperties: True` on root.

---

### 4. article_modeling_v2

**File:** `src/kairoskopion/prompts/article_modeling.py`

**System prompt (first 3 lines):**
```
You are Article Modeler — a specialized analytical role within Kairoskopion,
an evidence-first publication-positioning system.

Your task: given a manuscript (or abstract), reconstruct its publication-facing
```

**Open-field doctrine:** Yes, imported from `discipline_intent_parsing`.

**Version:** 2.0.0

**P5C changes:** Opened enums: `method_status` is free string (was enum), `genre_current` is free string (was enum), `argument_structure` is free string (was enum). Relaxed required list: `title`, `confidence`, `questions_for_user` moved to optional (unblocks cheaper LLM routes like claude-haiku-4-5, gpt-4o-mini). `additionalProperties: False` on root.

---

### 5. semantic_profiling_v2

**File:** `src/kairoskopion/prompts/semantic_profiling.py`

**System prompt (first 3 lines):**
```
You are Article Semantic Profiler — a specialized analytical role within
Kairoskopion, an evidence-first publication-positioning system.

Your task: given an ArticleModel and (optionally) the raw manuscript text,
```

**Open-field doctrine:** Yes, imported from `discipline_intent_parsing`.

**Version:** 2.0.0

**P5C changes:** `argument_move_type` changed from enum to free string with description field. Common patterns listed as examples, not constraints. `required: []` (all fields optional). `additionalProperties: True`. Explicit JSON-only output format instructions added. `known_disciplines_context` block added to user template for registry-aware matching.

---

### 6. disciplinary_mapping_v2

**File:** `src/kairoskopion/prompts/disciplinary_mapping.py`

**System prompt (first 3 lines):**
```
You are Disciplinary Pathway Mapper — a specialized analytical role within
Kairoskopion, an evidence-first publication-positioning system.

Your task: given an ArticleModel (and optionally an ArticleSemanticProfile),
```

**Open-field doctrine:** Yes, imported from `discipline_intent_parsing`.

**Version:** 2.0.0

**P5C changes:** Added `venue_search_queries` field (search terms for registry/API lookup, not specific venue names from memory). `venue_type_hints` described as "generic venue type labels derived from article evidence". `additionalProperties: False` on pathway items. Forbidden behavior: "Do NOT produce venue names from LLM memory".

---

### 7a. article_field_position_v2

**File:** `src/kairoskopion/prompts/field_positioning.py`

**System prompt (first 3 lines):**
```
You are Field Position Analyst — a specialized role within Kairoskopion,
an evidence-first publication-positioning system.

[Open-field doctrine injected]
```

**Open-field doctrine:** Yes, imported from `discipline_intent_parsing`.

**Version:** 2.0

**P5C changes:** New family (P5C). 7-group axis model (disciplinary positioning, tradition/framework, argument profile, methodological register, audience/register, geopolitics/institutional, temporal). `tradition_affiliation_vector` may be empty if field has no tradition structure. `notable_omissions` in citation_network_signature noted as "may or may not be significant depending on field norms". Institutional signals: "Do not assign a single prestige tier."

---

### 7b. venue_field_position_v2

**File:** `src/kairoskopion/prompts/field_positioning.py`

**System prompt (first 3 lines):**
```
You are Venue Field Position Analyst — a specialized role within Kairoskopion,
an evidence-first publication-positioning system.

[Open-field doctrine injected]
```

**Open-field doctrine:** Yes, imported from `discipline_intent_parsing`.

**Version:** 2.0

**P5C changes:** New family (P5C). Venue modeled as EXTENDED REGION (envelopes), not a point. Center vector + [min,max] envelope per dimension. `tradition_affiliation_vector` and `tradition_envelope` may be empty. Venue-specific method_stance: `requires_explicit_method`, `accepted_method_families`, `rejected_method_families`. Venue geographic_affinity: `editorial_board_regions`, `author_regions_published`, `anglophone_hegemony_index`. Institutional signals: no single prestige tier.

---

### 8. venue_fact_extraction_v2

**File:** `src/kairoskopion/prompts/venue_fact_extraction.py`

**System prompt (first 3 lines):**
```
You are Venue Profiler — a specialized analytical role within Kairoskopion,
an evidence-first publication-positioning system.

Your task: given venue source text (guidelines, official pages, policy documents),
```

**Open-field doctrine:** Yes, imported from `discipline_intent_parsing`.

**Version:** 2.0.0

**P5C changes:** Sections/tracks/special issues as first-class records in `sections` array (each with `section_name`, `section_type`, `scope_description`, `target_disciplines`, `editors`, `issn`, `status`, `evidence_status`). Indexing claims per-database/year/category with `section_name` field. Metrics claims per-database/year/category with `section_name` field. Evidence status taxonomy: `fact_from_source`, `vendor_claim`, `inference`, `unknown`. Regime classification added. `additionalProperties: False` on root.

---

### 9. venue_funnel_planning_v2

**File:** `src/kairoskopion/prompts/venue_funnel_planning.py`

**System prompt (first 3 lines):**
```
You are Venue Funnel Planner — a specialized role in Kairoskopion's
venue-positioning pipeline.

Your input:
```

**Open-field doctrine:** Yes, via `_DOMAIN_AGNOSTIC_DOCTRINE` alias.

**Version:** 2.0.0

**P5C changes:** No model-memory venue facts rule enforced. `known_corpus_candidates` require `source_ref` and `evidence_status` (`corpus_known`, `evidence_pack`, `user_provided`). `candidate_families` use `family_descriptor` (descriptive label, not venue name). `external_discovery_tasks` with `target_sources` and `query_hints`. Validator checks `source_ref` presence to detect model-memory facts. `additionalProperties: True` on root.

---

### 10. fit_assessment_v1

**File:** `src/kairoskopion/prompts/fit_assessment.py`

**System prompt (first 3 lines):**
```
You are Fit Assessor — a specialized analytical role within Kairoskopion,
an evidence-first publication-positioning system.

Your task: compare an ArticleModel against a VenueModel in the context of
```

**Open-field doctrine:** Yes, via `_DOMAIN_AGNOSTIC_DOCTRINE` alias.

**Version:** 1.0.0 (no v2 bump)

**P5C changes:** `evidence_source` enum expanded to 7 values: `source_fact`, `user_constraint`, `llm_inference`, `corpus_observation`, `vpkg_evidence`, `inference`, `unknown`. `required: []` (all fields optional). `additionalProperties: True`. 16 axes expanded to 20 in VPKG variant (added: `argument_form_fit`, `rewrite_effort`, `citation_effort`, `evidence_confidence`). VPKG variant family added: `fit_assessment_vpkg_v1`. Explicit JSON-only output format instructions added.

---

### 11. citation_ecology_analysis_v2

**File:** `src/kairoskopion/prompts/citation_ecology_analysis.py`

**System prompt (first 3 lines):**
```
You are Citation Ecology Analyst — a specialized role in
Kairoskopion's fit-assessment pipeline.

Your input:
```

**Open-field doctrine:** Yes, via `_DOMAIN_AGNOSTIC_DOCTRINE` alias.

**Version:** 2.0.0

**P5C changes:** Domain-agnostic citation role taxonomy (12 roles including `proof_theorem_foundation`, `benchmark_comparison`, `standards_regulation_policy`). Domain-agnostic gap categories (7 categories). `bridge_references` with structured `reference_anchors` requiring `evidence_status` (`from_bibliography`, `from_venue_corpus`, `from_registry`, `unknown`). Anti-fabrication rules: no specific citation references, no DOIs, suggest areas/roles/recency windows only. Validator checks for fabricated year patterns in suggested actions and anchors.

---

## Open-field doctrine (shared block)

All 11 families inject the same `_OPEN_FIELD_DOCTRINE` block (defined in `discipline_intent_parsing.py`, imported by others via `_DOMAIN_AGNOSTIC_DOCTRINE` alias).

First 3 lines:
```
## Open-field doctrine

Kairoskopion operates over an open publication field.

Do not assume any default discipline, field family, method regime,
```

Key content: 7 evidence sources enumerated (article evidence, user constraints, accepted registry records, source packets, venue/corpus evidence, explicit external adapter/search results, curator/user-confirmed records). 7 generic unknown markers defined (`field_unknown`, `method_regime_unknown`, etc.). Two terminal rules: "Never convert unknown into absence. Never convert model memory into fact."
