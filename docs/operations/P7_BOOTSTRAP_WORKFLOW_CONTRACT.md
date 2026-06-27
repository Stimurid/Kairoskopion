# P7 Bootstrap — SeedRegistryWorkflow Contract

**Date:** 2026-06-27

## Purpose

Given an article text and a domain scope target, orchestrate registry-first seeding using existing Kairoskopion primitives. No manual Claude-curated facts. Every factual record must be source-backed or marked unknown/provisional/acquisition_needed.

## Service Location

`src/kairoskopion/services/seed_workflow.py`

## Core Class

`SeedRegistryWorkflow`

## Inputs

```python
@dataclass
class SeedWorkflowConfig:
    article_text: str
    article_source_ref: str
    domain_target: str                    # e.g. "education_ai_russia"
    target_language: str = "ru"
    target_country: str = "RU"
    target_zones: list[str]               # seed zone names for acquisition
    target_archetypes: list[str]          # article type families to consider
    no_live_llm: bool = True
    no_paid_api: bool = True
    output_dir: Path                      # e.g. data/seed_registry/education_ai_russia/
```

## Outputs

```python
@dataclass
class SeedWorkflowResult:
    article_archetype: dict | None
    discipline_lookups: list[dict]
    acquisition_tasks: list[dict]
    source_packets: list[dict]
    provisional_records: dict[str, list[dict]]  # by record type
    venue_universe: list[dict]
    shortlist: list[dict]
    deep_venue_tasks: list[dict]
    gaps: list[str]
    warnings: list[str]
```

## Workflow Stages

1. **Article archetype** — run ArticleModeler deterministic, derive archetype from article evidence
2. **Discipline/zone lookup** — search DisciplineRegistry, create acquisition tasks on miss
3. **Framework lookup** — search EpistemicFrameworkRegistry for relevant epistemics
4. **Venue search** — search VenueRegistry for target domain, create acquisition tasks on miss
5. **Source packet ingestion** — if local files/URLs available, create source packets
6. **Provisional record creation** — from source packets → provisional registry records
7. **Venue universe assembly** — combine registry records + acquisition tasks into universe draft
8. **Metric/classification check** — check VenueMetricRegistry for evidence-backed metrics
9. **Shortlist generation** — rank venues by evidence strength, report shortages
10. **Deep VenueModel tasks** — for shortlisted venues, create tasks or models from source evidence
11. **Gap report** — list all unknowns, insufficient evidence, deferred semantic tasks

## Doctrine

- Registry-first: always search before creating
- Source-backed: every factual record has evidence_refs
- Unknown is valid: gaps reported, not filled
- No LLM invention: deterministic path marks `needs_llm` states
- Provisional only: no canonical records created by workflow
- Existing infrastructure: uses RegistryHub, AcquisitionTaskStore, SourcePacketStore
