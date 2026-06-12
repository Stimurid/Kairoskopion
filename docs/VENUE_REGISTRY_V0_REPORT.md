# Venue Registry / Source Collector Architecture v0 — Report

**Date:** 2026-06-12
**Branch:** `feature/venue-registry-source-collector-v0`
**Baseline:** `v0.2.0-alpha-rc5` (641 tests, 14 CLI commands)

## Summary

Designed and implemented a general venue evidence registry: data model, provenance discipline, import path, seed corpus format, CLI integration, and report integration. The system follows the evidence-first principle: every claim traces to a source or is marked UNKNOWN.

## What was built

### Core entities (schema.py)

| Entity | ID prefix | Purpose |
|--------|-----------|---------|
| VenueRecord | `vrec_` | Canonical venue identity (name, ISSN, aliases, URLs) |
| VenueSource | `vsrc_` | Single retrieved page/document with provenance fields |
| VenueClaim | `vclm_` | One fact extracted from one source, with evidence status |
| VenueEvidencePack | `vpack_` | Assembled profile with provenance sections |

### Evidence taxonomy

7 statuses: `official_fact`, `external_claim`, `inference`, `unknown`, `conflicting`, `stale`, `deprecated`.

### Source types

10 types with freshness windows (60-365 days): `official_homepage`, `official_author_guidelines`, `official_editorial_policy`, `official_archive`, `official_contacts`, `registry_card`, `indexer_page`, `publisher_page`, `third_party_summary`, `manual_note`.

### Conflict resolution rules

1. Single claim for a path: accepted as-is.
2. Multiple claims, same value: best-status claim wins.
3. One official fact vs non-official claims: official fact wins.
4. Multiple official facts with different values: reported as conflict, not resolved.
5. Claims with `conflict_group` marker: always reported as conflict regardless of status.
6. No official facts, different values: reported as conflict.

### Seed corpus

5 synthetic venues in `examples/venue_seed_corpus/`:
- `vrec_synth_philo` — English philosophy journal (full evidence)
- `vrec_synth_russian` — Russian-only humanities journal
- `vrec_synth_empirical` — Empirical social science (data policy)
- `vrec_synth_incomplete` — Minimal evidence (many unknowns)
- `vrec_synth_formal` — IEEE-style with explicit APC conflict

Format: 3 JSONL files (venues.jsonl, sources.jsonl, claims.jsonl) with 5 venues, 12 sources, 34 claims.

### CLI commands (2 new, total 16)

| Command | Purpose |
|---------|---------|
| `import-venue-seed --corpus <dir>` | Import JSONL seed corpus into venue registries |
| `build-venue-evidence-pack --venue-id <id> [--output <file>]` | Build evidence pack Markdown from registry |

### Services module

`src/kairoskopion/services/venue_registry.py` — 562 lines:
- `import_venue_seed_corpus()` — read + validate JSONL
- `persist_import_result()` — write to JSONL registries
- `build_venue_evidence_pack()` — assemble evidence pack with conflict resolution
- `evidence_pack_to_markdown()` — render for `run-local --venue-guidelines`

### Tests

32 new tests in `tests/test_venue_registry.py`:
- Domain model serialization (4 tests)
- Import validation (6 tests)
- Persistence (1 test)
- Evidence pack building (8 tests)
- Conflict resolution (4 tests)
- Markdown rendering (6 tests)
- Staleness detection (3 tests)

### Architecture documentation

`docs/VENUE_REGISTRY_ARCHITECTURE.md` — 9-section spec covering purpose, core entities, evidence taxonomy, source types, provenance fields, venue profile fields, freshness policy, integration points, and non-goals.

## Synthetic trial

**Pipeline:** `import-venue-seed` -> `build-venue-evidence-pack` -> `run-local`

1. Imported seed corpus: 5 venues, 12 sources, 34 claims.
2. Built evidence pack for `vrec_synth_philo` (Philosophy & Social Theory Review): 9 official facts, 0 conflicts, 10 unknowns.
3. Fed evidence pack Markdown as `--venue-guidelines` to `run-local` with `manuscript_sample.md`.
4. Pipeline completed: fit=possible, 4 mismatches, 6 risks, 8 compliance items, all registries written.

The evidence pack Markdown is consumed correctly by the existing venue profiling service — no adapter needed.

## Bug found and fixed

**Conflict group detection** — claims with `conflict_group` marker were not detected when only one claim in the group was marked (the other had `conflict_group: null`). Fixed to treat any non-null `conflict_group` as triggering conflict detection for the entire claim path.

## Files changed

| File | Change |
|------|--------|
| `src/kairoskopion/enums.py` | +VenueClaimStatus, +VenueSourceType enums |
| `src/kairoskopion/ids.py` | +venue_record_id, +venue_source_id, +venue_claim_id, +venue_evidence_pack_id |
| `src/kairoskopion/schema.py` | +VenueRecord, +VenueSource, +VenueClaim, +VenueEvidencePack dataclasses |
| `src/kairoskopion/services/venue_registry.py` | NEW — full service module |
| `src/kairoskopion/cli.py` | +cmd_import_venue_seed, +cmd_build_venue_evidence_pack |
| `tests/test_venue_registry.py` | NEW — 32 tests |
| `examples/venue_seed_corpus/` | NEW — 3 JSONL files + README |
| `docs/VENUE_REGISTRY_ARCHITECTURE.md` | NEW — architecture spec |
| `docs/VENUE_REGISTRY_V0_REPORT.md` | NEW — this report |

## Test count

- Before: 641 tests
- After: 673 tests (32 new)
- All passing.

## Non-goals confirmed

- No mass crawler, no journal database, no LLM calls.
- No Logos-specific logic, no tuning to one manuscript.
- No Web UI, no Telegram, no reviewer simulation.
- Seed corpus is synthetic-only — no copyrighted content.
