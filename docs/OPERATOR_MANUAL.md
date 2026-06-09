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

All 215+ tests must pass before any commit.

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
  vault/
    articles/    — ArticleModel markdown cards
    venues/      — VenueModel markdown cards
    fits/        — FitAssessment report cards
    risks/       — RiskReport cards
    compliance/  — ComplianceChecklist cards
    mismatches/  — MismatchMap cards
    submissions/ — (empty until SubmissionPack implemented)
    traces/      — Pipeline run trace reports
```

## Reading vault cards

Vault cards are markdown files with YAML frontmatter.
Open them in any text editor, VS Code, or Obsidian.

Example:
```bash
cat .kairoskopion/vault/fits/fit_*.md
```

## Run with local files (once implemented)

```bash
kairoskopion run-local \
  --manuscript my_paper.md \
  --venue-guidelines journal_guidelines.md \
  --scenario scenario.json \
  --storage-root ./my_analysis
```

This command is being implemented in the next sprint.

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
