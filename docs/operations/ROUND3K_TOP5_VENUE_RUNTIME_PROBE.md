# Round III-K Track 4: Venue Evidence Pack Runtime Resolver

## Objective

Build a runtime resolver that scans local evidence pack files and pipes their content into the existing `investigate_venue()` pipeline, enabling evidence-pack-driven venue investigation without manual text copy-paste.

## Implementation

### New Service: `venue_evidence_pack_resolver.py`

**File:** `src/kairoskopion/services/venue_evidence_pack_resolver.py`

Scans two directories for evidence pack markdown files:
1. `data/venue_evidence_packs/` — primary evidence packs
2. `private_inputs/logos_trial/` — Logos trial data (legacy)

**Key functions:**
- `scan_evidence_packs(project_root)` — scan all known dirs, extract ISSN + canonical name from markdown, return `list[ResolvedPack]`
- `resolve_by_issn(issn, project_root)` — find pack by ISSN
- `resolve_by_name(name, project_root)` — find pack by canonical name (case-insensitive)
- `resolve(*, issn, name, project_root)` — combined resolver: ISSN takes priority, falls back to name

**Data extraction:**
- ISSN via regex: `**ISSN:** XXXX-XXXX`
- Name via regex: `# Venue Evidence Pack: Name / English Name` (takes text before `/`)

**Design decisions:**
- No new database, no schema changes — simplest possible approach
- Reuses existing text-based profiling pipeline via `investigate_venue()`
- File filtering: must have `.md` extension AND `evidence_pack` in filename

### Case Orchestrator Integration

**File:** `src/kairoskopion/api/cases.py`

New method `investigate_venue_by_reference(*, issn=None, name=None)`:
- Resolves evidence pack via resolver
- Returns `{"status": "evidence_pack_not_found"}` if not found
- Otherwise calls `self.investigate_venue(pack.text)` with the full markdown text
- Logs decision with `source_file`, `issn`, `canonical_name`

### API Endpoint

**File:** `src/kairoskopion/api/app.py`

New endpoint: `POST /cases/{case_id}/investigate-venue-by-reference`
- Request body: `{"issn": "1811-833X"}` or `{"name": "Логос"}` or both
- Validates at least one of issn/name provided
- Returns venue investigation result or evidence_pack_not_found

## Test Coverage

**File:** `tests/test_round3k_venue_evidence_pack_resolver.py` — 20 tests

| Test Group | Count | Coverage |
|------------|-------|----------|
| ISSN extraction | 3 | regex match, X suffix, no match |
| Name extraction | 3 | with slash, without slash, no header |
| Scan + resolve (temp dir) | 8 | scan, resolve by ISSN/name, combined, priority, fallback |
| Real pack integration | 4 | Logos, ВФ, ФЖ, ЦУ resolvable by ISSN |
| Case orchestrator | 2 | not-found case, Logos by-reference |

All 20 tests pass.

## Usage

From the UI cockpit or API client:
```
POST /cases/{case_id}/investigate-venue-by-reference
{"issn": "0869-5377"}
```

This resolves the Логос evidence pack from disk and pipes it through the full venue profiling pipeline.

---

*Report generated: 2026-06-24. Track 4 COMPLETE.*
