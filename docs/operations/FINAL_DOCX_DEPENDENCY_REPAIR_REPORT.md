# DOCX Dependency Repair Report

**Date:** 2026-07-09
**Branch:** `feature/p10-operational-harvest-final`

---

## Root cause

`python-docx` was already declared in `pyproject.toml` under both `[project.optional-dependencies.extract]` and `[project.optional-dependencies.dev]`, but the active virtual environment had been installed without the `[dev]` extra. The package was missing at runtime, causing 5 DOCX-related tests to fail with `ModuleNotFoundError`.

## Manifest status

| Field | Before | After |
|---|---|---|
| `pyproject.toml` extract extra | `python-docx>=1.0` | unchanged |
| `pyproject.toml` dev extra | `python-docx>=1.0` | unchanged |
| Lock file | none (project uses setuptools, no lock) | unchanged |
| requirements.txt | none | unchanged |

No manifest changes were required. The dependency was already correctly declared.

## Resolution

**Case A applies:** `python-docx` was already declared. The fix was to install with the correct dependency group:

```
pip install -e ".[dev]"
```

This installed `python-docx==1.2.0` along with all other dev dependencies.

## Installation command

The canonical environment setup command for this project is:

```
pip install -e ".[dev,extract,api]"
```

This installs all optional dependency groups needed for full test coverage and API operation.

## Focused DOCX test result

```
pytest tests/test_document_intake.py tests/test_file_upload_formats.py tests/test_run_local.py -v
45 passed in 3.87s
```

All previously failing DOCX tests now pass.

## Full suite result

```
pytest tests -q
3248 passed, 8 deselected, 1 warning in 82.43s
```

Zero failures. The 8 deselected tests are network-marked (expected).

## Reproducibility

The documented install command `pip install -e ".[dev]"` is sufficient to reproduce this fix in any clean Python >=3.11 environment. No undocumented global installs are required.
