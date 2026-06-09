# Operator Manual — Kairoskopion

## Prerequisites

- Python 3.11+
- Git

## Installation

```bash
cd C:\projects\Kairoskopion\Kairoskopion

# Create virtual environment (once)
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install in dev mode
pip install -e ".[dev]"
```

## Running tests

```bash
# All tests
pytest

# Verbose with coverage
pytest -v --cov=kairoskopion

# Single test file
pytest tests/test_cli.py -v
```

All 351+ tests must pass before any commit.

## CLI commands

### Check environment

```bash
kairoskopion status
```

Shows: version, working directory, storage root, whether registries/vault exist.

### Run fixture pipeline

```bash
# Default storage root (.kairoskopion/ in cwd)
kairoskopion run-fixture

# Custom storage root
kairoskopion --storage-root /tmp/kairon_test run-fixture
```

Runs the synthetic manuscript + venue pipeline end-to-end.
Creates 13 JSONL registries and 7 vault markdown cards.

### Run with local files

```bash
kairoskopion run-local \
  --manuscript my_paper.md \
  --venue-guidelines journal_guidelines.md \
  --scenario scenario.json \
  --storage-root ./my_analysis
```

Accepts `.md`, `.txt`, `.json`, `.html` files. Each input file is registered as a
SourceSnapshot with content hash and persisted to the `source_snapshots` registry.

The scenario file must be valid JSON with at least a `goal` field. Example:
```json
{
  "goal": "Publish in Q1 STS journal",
  "target_venue_type": "journal",
  "rewrite_depth": "medium"
}
```

Output: same as `run-fixture` — JSONL registries, vault cards, pipeline summary.

### Run mock adapters

```bash
# Default storage root
kairoskopion adapters-smoke

# Custom storage root
kairoskopion --storage-root /tmp/kairon_test adapters-smoke
```

Runs all three mock adapters (OpenAlex, Crossref, OpenCitations) with fixed
deterministic data. Creates SourceSnapshot and EvidenceItem records for each
adapter result. No network calls, no API keys needed.

All evidence is marked VENDOR_CLAIM with is_mock=True. References are never
verified by mock data.

### Generate vault indexes

```bash
kairoskopion vault-index
```

Generates per-section INDEX.md files, root INDEX.md, and manifest.json.
Cross-links in vault cards (fit→article+venue, mismatch→fit, etc.) are created
during pipeline runs; this command generates the indexes on top.

### Export storage bundle

```bash
kairoskopion export-bundle --output backup.zip
```

Creates a zip archive containing:
- `registries/*.jsonl` — all JSONL registries
- `vault/**/*.md` — all vault cards and indexes
- `vault/manifest.json` — vault manifest
- `metadata.json` — bundle metadata (version, creation time, registry counts)

Vault indexes and manifest are regenerated before archiving.

### Import storage bundle

```bash
# Append mode (default) — adds records to existing registries
kairoskopion import-bundle --bundle backup.zip

# Replace mode — overwrites target storage
kairoskopion import-bundle --bundle backup.zip --mode replace
```

Imports registries and vault cards from a previously exported bundle.
In append mode, JSONL records are appended to existing registries.
In replace mode, the target registries directory is cleared first.

### Validate storage bundle

```bash
kairoskopion validate-bundle --bundle backup.zip
```

Checks bundle structure: zip integrity, metadata.json presence, registry
file presence. Reports errors and warnings without modifying anything.

### Inspect stored results

```bash
kairoskopion inspect-storage
```

Shows: registry record counts, entity IDs, vault card files.

### Storage root override

Priority (highest first):
1. `--storage-root PATH` CLI flag
2. `KAIROSKOPION_STORAGE_ROOT` environment variable
3. Default: `.kairoskopion/` in current working directory

## Where artifacts appear

After `run-fixture`:

```
.kairoskopion/
  registries/
    article_models.jsonl      — ArticleModel records
    manuscripts.jsonl         — ManuscriptModel records
    venue_models.jsonl        — VenueModel records
    fit_assessments.jsonl     — FitAssessment records
    mismatch_maps.jsonl       — MismatchMap records
    rewrite_plans.jsonl       — RewritePlan records
    risk_reports.jsonl        — RiskReport records
    compliance_checklists.jsonl
    pipeline_runs.jsonl       — PipelineRun status
    operation_traces.jsonl    — OperationTrace records
    quality_gates.jsonl       — QualityGateResult records
    publication_regimes.jsonl
    submission_scenarios.jsonl
    bibliography_profiles.jsonl
    citation_ecology_reports.jsonl
    adapter_results.jsonl       — AdapterResult records (adapters-smoke)
    source_snapshots.jsonl      — SourceSnapshot records (run-local, adapters-smoke)
    evidence_items.jsonl        — EvidenceItem records (adapters-smoke)
  vault/
    INDEX.md             — root index with section counts and links
    manifest.json        — machine-readable vault manifest (counts, card paths)
    articles/    INDEX.md + ArticleModel markdown cards
    venues/      INDEX.md + VenueModel markdown cards
    fits/        INDEX.md + FitAssessment cards (cross-linked to article/venue)
    risks/       RiskReport cards (cross-linked to article/venue)
    compliance/  ComplianceChecklist cards (cross-linked)
    mismatches/  MismatchMap cards (cross-linked to fit)
    citations/   INDEX.md + CitationEcologyReport cards (cross-linked)
    adapters/    INDEX.md
    submissions/ (empty until SubmissionPack implemented)
    traces/      INDEX.md + Pipeline run trace reports
```

## Reading vault cards

Vault cards are markdown files with YAML frontmatter.
Open them in any text editor, VS Code, or Obsidian.

Cross-links use relative paths (e.g. `../articles/art_xxx.md`) compatible
with Obsidian link navigation.

Example:
```bash
cat .kairoskopion/vault/fits/fit_*.md
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'kairoskopion'`

Package not installed. Run:
```bash
pip install -e ".[dev]"
```

### `kairoskopion: command not found`

Virtual environment not activated. Run:
```bash
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

### Tests fail with import errors

Ensure you're running pytest from the project root with the venv activated:
```bash
cd C:\projects\Kairoskopion\Kairoskopion
.\.venv\Scripts\activate
pytest
```
