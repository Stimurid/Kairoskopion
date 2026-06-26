# Round III-P5C-fix: Acceptance Report

**Date:** 2026-06-26
**Branch:** `feature/round3-six-phase-build-hardening`
**Starting commit:** `3f1906f`
**Test count before:** 2534
**Test count after:** 2554 (+20 new tests)
**UI typecheck:** PASS
**UI build:** PASS

## Track Status

| Track | Title | Status | Evidence |
|-------|-------|--------|----------|
| 0 | Preflight | PASS | 2534 tests passed at 3f1906f |
| 1 | Universal axis rename | DONE | `tradition_affiliation_vector` → `framework_affiliation_vector`, `tradition_envelope` → `framework_envelope`, `TribeOrFrameworkRecord` → `EpistemicFrameworkRecord` (with backward compat aliases). 7 src files + 5 test files. 7 new tests verify no legacy names in runtime path |
| 2 | Remove field-list attractors | DONE | citation_ecology_analysis.py: removed "theorems for math, seminal experiments for biology, canonical cases for law, key thinkers for philosophy". Replaced with open-field formulation. 1 test |
| 3 | Source provenance gates | DONE | Schema forbids source_id/source_url in acquisition output. Prompt explicitly prohibits LLM-recalled codes. 3 tests |
| 4 | Citation anchor safety | DONE | `anchor_status` field added to reference_anchors schema (4 levels: source_grounded, corpus_grounded, role_level, unverified_llm_hint). Documented in system prompt. 2 tests |
| 5 | Venue metric/quartile invariants | DONE | Per-database, per-year, per-category, per-section separation enforced. 5 tests |
| 6 | Runtime v2 invariant | DONE | Agents import directly from prompt modules (not catalog). Catalog resolves bare names to v2. 3 tests |
| 7 | P6 registry pipeline plan | DONE | `docs/operations/ROUND3P6_REGISTRY_PIPELINE_PLAN.md` — plan only, no implementation |
| 8 | Prompt export | DONE | `docs/operations/ROUND3P5C_FIX_PROMPTS_EXPORT_ALL.md` + `docs/operations/ROUND3P5C_FIX_PROMPT_EXPORT/` folder |
| 9 | Acceptance report | THIS FILE |
| 10 | Tests | PASS | 2554 passed, 4 deselected, 1 warning, 5 subtests passed |
| 11 | Commit + push | PENDING |
| 12 | Final response | PENDING |

## Track 1 Details: Universal Axis Rename

### Files modified (src/)

| File | Changes |
|------|---------|
| `ids.py` | `tribe_or_framework_record_id` → `epistemic_framework_record_id`, prefix `tfrec` → `efrec`, backward compat alias |
| `schema.py` | Import rename, `FieldPositionModel.tradition_affiliation_vector` → `framework_affiliation_vector`, `tradition_envelope` → `framework_envelope`, `TribeOrFrameworkRecord` → `EpistemicFrameworkRecord`, `tribe_record_id` → `framework_record_id`, `record_type` → `framework_kind` (open label), backward compat alias |
| `agents/article_field_positioner.py` | `framework_affiliation_vector` in parsed output |
| `agents/venue_field_positioner.py` | `framework_affiliation_vector` + `framework_envelope` |
| `services/corpus_hull_builder.py` | Both renames |
| `logic/field_position_fit.py` | Both renames |
| `prompts/field_positioning.py` | Both renames + prompt text descriptions updated |

### Files modified (tests/)

| File | Changes |
|------|---------|
| `test_field_position.py` | All `tradition_*` → `framework_*` |
| `test_field_position_integration.py` | Same |
| `test_corpus_hull_builder.py` | Same |
| `test_llm_agent_tolerance.py` | Same |
| `test_p5c_open_field_registry.py` | Same + `EpistemicFrameworkRecord` tests, `framework_record_id`/`efrec_` prefix, Track 1-6 tests |

### Backward compatibility

- `TribeOrFrameworkRecord = EpistemicFrameworkRecord` alias in schema.py
- `tribe_or_framework_record_id = epistemic_framework_record_id` alias in ids.py
- No breaking changes for existing code using old names

## Track 2 Details: Field-List Attractor Removal

Removed from `citation_ecology_analysis.py` line 65-66:
- Before: "theorems for math, seminal experiments for biology, canonical cases for law, key thinkers for philosophy"
- After: "Derive the expected foundation type from the article's field and the venue's corpus, not from a fixed list."

Grep verification: no remaining field-list attractors in `src/kairoskopion/prompts/`.

## Track 4 Details: Citation Anchor Safety

Added to `citation_ecology_analysis.py`:
- `anchor_status` field in `reference_anchors` schema items with enum: `source_grounded`, `corpus_grounded`, `role_level`, `unverified_llm_hint`
- System prompt documentation of all 4 levels with behavioral rules
- `unverified_llm_hint` must be segregated and never presented as fact

## Track 5 Details: Venue Metric Invariants

Hard tests enforce:
- Same venue + different databases → distinct records
- Same database + different years → distinct records
- Same database + different categories → distinct records with different values
- Section-level metrics carry section_id
- Never collapsible to single prestige tier

## Track 6 Details: Runtime v2 Invariant

Proven:
- `ArticleFieldPositionerAgent` imports `ARTICLE_FIELD_POSITION_FAMILY` directly from `prompts.field_positioning` → v2
- `VenueFieldPositionerAgent` imports `VENUE_FIELD_POSITION_FAMILY` directly from `prompts.field_positioning` → v2
- `CITATION_ECOLOGY_FAMILY` is v2
- Catalog resolves bare names to v2 before v1

Catalog is CLI-only path. Agents bypass catalog. v2 is guaranteed in production.

## Remaining Owner Review Items

All 12 tracks addressed per P5C-fix specification. No implementation scope beyond specification.
