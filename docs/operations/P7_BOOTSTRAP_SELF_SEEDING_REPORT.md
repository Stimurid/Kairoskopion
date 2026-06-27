# P7 Bootstrap — Self-Seeding Workflow Report

**Date:** 2026-06-27
**Branch:** `feature/round3-p7-llm-integration`

## Dogfood Run

| parameter | value |
|-----------|-------|
| Input file | `08_cited_clean_current_base.md` (76 KB, ~10828 words) |
| Mode | `--no-live-llm` (deterministic only) |
| Zones | Higher Education, AI in Education, Educational Technology |
| Target domain | `education_ai_russia` |
| Output dir | `data/seed_registry/education_ai_russia/` |

## Results

| metric | value |
|--------|-------|
| Run ID | `run_20260627_112051997082_2dd99314` |
| Article archetype | YES (confidence=low, status=draft) |
| Discipline lookups | 3 (all miss — empty registry) |
| Acquisition tasks created | 6 (3 discipline + 3 venue discovery) |
| Source packets | 1 (article file ingested) |
| Venue universe | 0 (empty registry) |
| Shortlist | 0 |
| Deep venue tasks | 0 |
| Gaps | 5 |
| Warnings | 3 |

## Gaps Detected

1. Article archetype incomplete — needs LLM for: genre_detection, claim_extraction, method_detection
2. Venue registry empty for domain 'education_ai_russia' — 3 acquisition tasks created
3. No VenueMetricRecords — Q1/Q2 ranking not possible without source-backed metrics
4. Shortlist has 0 venues — shortage of 5 vs minimum 5
5. Article archetype needs LLM for full semantic extraction

## Warnings

1. Venue universe empty — only acquisition tasks exist
2. Running in no-live-LLM mode — semantic analysis deferred
3. 6 open acquisition tasks — resolve to populate registry

## Output Files

| file | content |
|------|---------|
| `article_archetypes/archetype_run_2026.json` | Article archetype (draft, confidence=low) |
| `acquisition_tasks/open_tasks.json` | 6 open acquisition tasks |
| `reports/gaps.md` | Gap report |
| `reports/workflow_run_report.json` | Full result JSON |

## Assessment

The workflow executed correctly in deterministic mode:
- **Registry-first doctrine**: all 3 discipline queries searched existing (empty) registry before creating acquisition tasks
- **No invented data**: all fields marked unknown/missing are honestly reported as gaps
- **Acquisition tasks**: correctly created for every miss (discipline + venue)
- **Privacy**: raw article text never written to tracked output
- **Provenance**: archetype traces to `deterministic_article_modeler`, confidence=low
- **Unknowns preserved**: abstract, genre, method, novelty, protected_core all marked unknown

The pipeline correctly identifies what it cannot do without LLM and creates tasks for what it cannot find in the registry. This is the intended behavior for no-LLM mode.
