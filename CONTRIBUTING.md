# Contributing to Kairoskopion

## Development setup

```bash
git clone https://github.com/Stimurid/Kairoskopion.git
cd Kairoskopion
python -m venv .venv
.venv/Scripts/activate    # Windows
source .venv/bin/activate # Linux/Mac
pip install -e ".[dev]"
pytest
```

## Branch workflow

1. Create a feature branch from `main`: `git checkout -b feature/your-feature`
2. Implement on the feature branch
3. Ensure all tests pass: `pytest`
4. Push and create a pull request
5. Do not push directly to `main`

## Code style

- Python 3.11+, type hints on public functions
- All hooks-style: stateless service functions, not classes with state
- No external runtime dependencies (dev dependencies: pytest, pytest-cov)
- Every new feature needs at least one test
- Negative-case tests required for domain invariants

## Testing

```bash
# All tests
pytest

# With coverage
pytest --cov=kairoskopion

# Single file
pytest tests/test_cli.py -v
```

All tests must pass before any commit. Tests use `tmp_path` — never write to real filesystem.

## Architecture rules

- Read `CLAUDE.md` and `docs/SPEC_COVERAGE_MATRIX.md` before starting work
- Pick sprints from `docs/BACKLOG.md`
- Evidence-first: every claim must trace to a source or be marked UNKNOWN
- No single fit score — always multi-axis
- No fake references
- No LLM calls without explicit decision
- JSONL registries are append-only
- Vault cards are projections, not canonical data

## Git policy

- No force push
- No push to `main` without review
- No delete remote branches
- No commit `.venv`, `dist`, `.env` with secrets
