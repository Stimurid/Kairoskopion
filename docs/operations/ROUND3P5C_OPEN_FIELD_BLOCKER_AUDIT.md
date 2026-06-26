# Round III-P5C — Open-Field Blocker Audit

All prompt families in `src/kairoskopion/prompts/` audited for open-field
doctrine violations. Each finding classified by blocker type.

## Blocker type legend

| Code | Blocker | Description |
|------|---------|-------------|
| FLA | FIELD_LIST_ATTRACTOR | Listing specific fields/disciplines as examples inside a prompt — LLMs treat lists as default taxonomy |
| PSL | PHILOSOPHY_STS_LOCK | Hardcoded philosophy/STS/humanities concepts as default or primary examples |
| HML | HUMANITIES_LOCK | Assuming humanities epistemic structure (schools, canons, thinkers, camps) as universal |
| MMS | MODEL_MEMORY_SOURCE_RISK | Asking LLM to produce facts (venue names, ISSN, quartiles, classification codes, author names) from training memory without source evidence |
| IQS | INDEXING_QUARTILE_SIMPLIFICATION | Flattening per-database/per-year/per-category quartiles into a single value |
| SBV | SECTION_BLIND_VENUE_MODEL | Treating venue as monolithic — no sections, special issues, tracks, proceedings tracks |
| FER | FIXED_ENUM_REGIME | Using a closed enum of method/genre/regime values that cannot represent all fields |

## Findings by prompt file

### 1. `discipline_intent_parsing.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| 1 | FLA | `_DOMAIN_AGNOSTIC_DOCTRINE` | Listed 12 specific fields: mathematics, biology, medicine, semiconductor physics, etc. | **FIXED (Track 2)** — replaced with `_OPEN_FIELD_DOCTRINE` |
| 2 | FLA | `_DOMAIN_AGNOSTIC_DOCTRINE` | Listed 15 epistemic regimes as bullet points | **FIXED (Track 2)** — removed regime list |
| 3 | FER | `epistemic_regime` output field | Listed 15 specific regimes as closed set | **FIXED (Track 2)** — now open, evidence-derived |

### 2. `semantic_profiling.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| 4 | HML | System prompt | "humanities/social science work" framing | **FIXED (Track 7)** |
| 5 | PSL+FLA | Schools section | Lists Simondon, Vygotsky, Heidegger, etc. as examples | **FIXED (Track 7)** |
| 6 | HML+FER | `argument_move_type` enum | genealogy, concept_reconstruction, school_critique, polemical_essay — humanities-only | **FIXED (Track 7)** |
| 7 | FLA | JSON example | Philosophy-specific values in output example | **FIXED (Track 7)** |

### 3. `disciplinary_mapping.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| 8 | PSL+FLA | "Disciplinary landscape" | Lists 13 philosophy/STS/humanities fields | **FIXED (Track 8)** |
| 9 | PSL+FLA | "School/tradition awareness" | Lists Simondon, Vygotsky, Heidegger, etc. | **FIXED (Track 8)** |
| 10 | MMS | `example_venue_names` | Schema field invites LLM to produce venue names from memory | **FIXED (Track 8)** |
| 11 | FLA | `venue_type_hints` | "philosophy journal", "STS proceedings" | **FIXED (Track 8)** |

### 4. `field_positioning.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| 12 | PSL+FLA | `_AXES_REFERENCE` | Specific philosophy/STS examples per axis | **FIXED (Track 9)** |
| 13 | HML | `school_affiliation_vector` | Assumes intellectual camps — humanities-specific | **FIXED (Track 9)** |
| 14 | HML | `citation_network_signature` | must_cite, conspicuous_absence — camp dynamics | **FIXED (Track 9)** |
| 15 | IQS | `prestige_tier` | Simple enum, not per-database/year/category | **FIXED (Track 9)** |

### 5. `discipline_source_acquisition.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| 16 | MMS | System prompt | LLM asked to "identify authoritative classification entries" from memory | **FIXED (Track 4)** |
| 17 | MMS | `source_id`, `source_url` outputs | Could be fabricated by LLM | **FIXED (Track 4)** |

### 6. `discipline_seeding.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| 18 | FLA+MMS | "uncontroversially identified" | Lists Heidegger, Vygotsky as examples | **FIXED (Track 5)** |
| 19 | MMS | `key_authors` field | Allows memory-based author names | **FIXED (Track 5)** |

### 7. `article_modeling.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| 20 | FER | `method_status` enum | Only 6 values: conceptual_method, empirical_method, case_based, mixed, review_method, unknown | **FIXED (Track 6)** |
| 21 | FER+HML | `genre_current` enum | humanities-biased: theoretical_essay, conceptual_article, book_review | **FIXED (Track 6)** |
| 22 | FLA | `disciplinary_register_current` | Description lists "philosophy, STS, sociology, education, ethics, etc." | **FIXED (Track 6)** |
| 23 | HML | `citation_ecology_description` | Example: "heavy on philosophy?" | **FIXED (Track 6)** |

### 8. `venue_fact_extraction.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| 24 | SBV | Entire prompt | Treats venue as monolithic — no sections, special issues, tracks | **FIXED (Track 10)** |
| 25 | IQS | `indexing_claims`, `metrics_claims` | Flat lists, not per-database/year/category records | **FIXED (Track 10)** |

### 9. `venue_funnel_planning.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| — | — | — | No field-list attractors found. Model-memory guard present (P5A). | OK |

### 10. `venue_family_context.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| — | — | — | No field-list attractors found. Model-memory guard present (P5A). | OK |

### 11. `venue_matrix_assessment.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| — | — | — | No field-list attractors found. Evidence markers present (P5A). | OK |

### 12. `depth_recommendation.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| — | — | — | No field-list attractors found. 5 canonical modes (P5A). | OK |

### 13. `fit_assessment.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| — | — | — | No field-list attractors found. Doctrine injected (P5A). | OK |

### 14. `mismatch_narrative.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| — | — | — | No field-list attractors found. Doctrine injected (P5A). | OK |

### 15. `citation_ecology_analysis.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| — | — | — | No field-list attractors found. Domain-agnostic roles (P5A). | OK |

### 16. `rewrite_planning.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| — | — | — | No field-list attractors found. User approval invariant (P5A). | OK |

### 17. `compliance_assessment.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| — | — | — | No field-list attractors found. Lifecycle fields (P5A). | OK |

### 18. `input_classification.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| 26 | FLA | minor | "Russian philosophical notes" mention | **FIXED (Track 6)** |

### 19. `discipline_matching.py`
| # | Blocker | Location | Finding | Status |
|---|---------|----------|---------|--------|
| — | — | — | Uses registry input, no hardcoded fields. | OK |

## 14 mandatory findings verification

Per P5C specification, these 14 must be found and documented:

| # | Required finding | Audit # | Status |
|---|-----------------|---------|--------|
| 1 | _DOMAIN_AGNOSTIC_DOCTRINE lists fields | #1 | FIXED |
| 2 | _DOMAIN_AGNOSTIC_DOCTRINE lists regimes | #2 | FIXED |
| 3 | semantic_profiling.py humanities lock | #4, #5, #6, #7 | **FIXED** |
| 4 | disciplinary_mapping.py field landscape | #8, #9 | **FIXED** |
| 5 | disciplinary_mapping.py example_venue_names | #10 | **FIXED** |
| 6 | field_positioning.py axes examples | #12 | **FIXED** |
| 7 | field_positioning.py school_affiliation | #13 | **FIXED** |
| 8 | discipline_source_acquisition.py memory reliance | #16, #17 | **FIXED** |
| 9 | discipline_seeding.py named thinkers | #18, #19 | **FIXED** |
| 10 | article_modeling.py fixed enums | #20, #21 | **FIXED** |
| 11 | article_modeling.py humanities examples | #22, #23 | **FIXED** |
| 12 | venue_fact_extraction.py section-blind model | #24 | **FIXED** |
| 13 | venue_fact_extraction.py indexing simplification | #25 | **FIXED** |
| 14 | input_classification.py philosophy mention | #26 | **FIXED** |

**All 14 mandatory findings verified.** All 26 findings FIXED across Tracks 2–10.

## Summary

- **Total findings:** 26
- **Fixed:** 26/26 (Tracks 2–10)
- **Pending:** 0
- **Clean files:** 10 (P5A organs already compliant)
- **Blocker type distribution:** FLA ×10, PSL ×4, HML ×6, MMS ×5, IQS ×2, SBV ×1, FER ×3
- **Tests:** 2533 passed, 0 failures (including 43 P5C-specific tests)
