"""Persistence layer — save pipeline results to JSONL registries.

Default storage layout::

    .kairoskopion/
        registries/
            article_models.jsonl
            manuscripts.jsonl
            venue_models.jsonl
            publication_regimes.jsonl
            submission_scenarios.jsonl
            fit_assessments.jsonl
            mismatch_maps.jsonl
            rewrite_plans.jsonl
            risk_reports.jsonl
            compliance_checklists.jsonl
            pipeline_runs.jsonl
            operation_traces.jsonl
            quality_gates.jsonl
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import registry as reg

if TYPE_CHECKING:
    from .pipelines.manuscript_venue_fit import ManuscriptVenueFitPipeline, ManuscriptVenueFitResult

_DEFAULT_STORAGE_ROOT = Path(".kairoskopion")
_REGISTRIES_DIR = "registries"


def storage_root_from_env() -> Path:
    """Resolve storage root: env var → default ``.kairoskopion/``."""
    env = os.environ.get("KAIROSKOPION_STORAGE_ROOT")
    return Path(env) if env else _DEFAULT_STORAGE_ROOT


def ensure_storage_root(path: Path | str | None = None) -> Path:
    """Create storage root directory if it doesn't exist. Returns the path."""
    root = Path(path) if path else storage_root_from_env()
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_registry_root(storage_root: Path | str | None = None) -> Path:
    """Create registries/ under storage root. Returns the registries path."""
    root = ensure_storage_root(storage_root)
    reg_root = root / _REGISTRIES_DIR
    reg_root.mkdir(parents=True, exist_ok=True)
    return reg_root


def _save(name: str, data: dict[str, Any], reg_root: Path) -> Path:
    return reg.append(name, data, base_dir=reg_root)


def save_pipeline_result(
    result: "ManuscriptVenueFitResult",
    pipeline: "ManuscriptVenueFitPipeline",
    storage_root: Path | str | None = None,
) -> dict[str, Path]:
    """Persist all entities from a pipeline result into JSONL registries.

    Returns a dict mapping registry name → file path.
    """
    reg_root = ensure_registry_root(storage_root)
    written: dict[str, Path] = {}

    if result.article:
        written["article_models"] = _save(
            "article_models", result.article.to_dict(), reg_root)

    if result.manuscript:
        written["manuscripts"] = _save(
            "manuscripts", result.manuscript.to_dict(), reg_root)

    if result.venue:
        written["venue_models"] = _save(
            "venue_models", result.venue.to_dict(), reg_root)

    if result.regime:
        written["publication_regimes"] = _save(
            "publication_regimes", result.regime.to_dict(), reg_root)

    if result.scenario:
        written["submission_scenarios"] = _save(
            "submission_scenarios", result.scenario.to_dict(), reg_root)

    if result.fit:
        written["fit_assessments"] = _save(
            "fit_assessments", result.fit.to_dict(), reg_root)

    if result.mismatch_map:
        written["mismatch_maps"] = _save(
            "mismatch_maps", result.mismatch_map.to_dict(), reg_root)

    if result.rewrite_plan:
        written["rewrite_plans"] = _save(
            "rewrite_plans", result.rewrite_plan.to_dict(), reg_root)

    if result.risk_report:
        written["risk_reports"] = _save(
            "risk_reports", result.risk_report.to_dict(), reg_root)

    if result.compliance:
        written["compliance_checklists"] = _save(
            "compliance_checklists", result.compliance.to_dict(), reg_root)

    # Pipeline run
    written["pipeline_runs"] = _save(
        "pipeline_runs", pipeline.run.to_dict(), reg_root)

    # Operation trace
    written["operation_traces"] = _save(
        "operation_traces", pipeline.trace.to_dict(), reg_root)

    # Quality gates
    if result.fit_gate:
        written["quality_gates"] = _save(
            "quality_gates", result.fit_gate.to_dict(), reg_root)
    if result.evidence_gate:
        written["quality_gates"] = _save(
            "quality_gates", result.evidence_gate.to_dict(), reg_root)

    return written


def list_registries(storage_root: Path | str | None = None) -> list[str]:
    """List all .jsonl registry names under storage root."""
    reg_root = ensure_storage_root(storage_root) / _REGISTRIES_DIR
    if not reg_root.exists():
        return []
    return sorted(p.stem for p in reg_root.glob("*.jsonl"))


def read_registry(name: str, storage_root: Path | str | None = None) -> list[dict[str, Any]]:
    """Read all records from a named registry."""
    reg_root = ensure_storage_root(storage_root) / _REGISTRIES_DIR
    return reg.read_all(name, base_dir=reg_root)


def storage_exists(storage_root: Path | str | None = None) -> bool:
    """Check whether storage root exists."""
    root = Path(storage_root) if storage_root else storage_root_from_env()
    return root.exists()


def registries_exist(storage_root: Path | str | None = None) -> bool:
    """Check whether registries dir exists."""
    root = Path(storage_root) if storage_root else storage_root_from_env()
    return (root / _REGISTRIES_DIR).exists()


def vault_exists(storage_root: Path | str | None = None) -> bool:
    """Check whether vault dir exists."""
    root = Path(storage_root) if storage_root else storage_root_from_env()
    return (root / "vault").exists()
