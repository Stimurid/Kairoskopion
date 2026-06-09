"""Vault / markdown artifact filesystem output.

Default vault layout::

    .kairoskopion/
        vault/
            articles/   — ArticleModel cards
            venues/     — VenueModel cards
            fits/       — FitAssessment cards
            risks/      — RiskReport cards
            submissions/ — SubmissionPack cards
            traces/     — pipeline artifacts / full reports
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .cards import (
    article_model_card,
    citation_ecology_card,
    compliance_checklist_card,
    fit_assessment_card,
    mismatch_map_card,
    risk_report_card,
    venue_model_card,
)
from .persistence import ensure_storage_root

if TYPE_CHECKING:
    from .pipelines.manuscript_venue_fit import ManuscriptVenueFitPipeline, ManuscriptVenueFitResult

_VAULT_DIR = "vault"
_SUBDIRS = ("articles", "venues", "fits", "risks", "compliance", "mismatches", "citations", "submissions", "traces")


def ensure_vault_root(storage_root: Path | str | None = None) -> Path:
    """Create vault/ and subdirectories under storage root."""
    root = ensure_storage_root(storage_root) / _VAULT_DIR
    root.mkdir(parents=True, exist_ok=True)
    for sub in _SUBDIRS:
        (root / sub).mkdir(exist_ok=True)
    return root


def _write_card(vault_root: Path, subdir: str, filename: str, content: str) -> Path:
    path = vault_root / subdir / filename
    path.write_text(content, encoding="utf-8")
    return path


def write_article_card(
    data: dict[str, Any],
    vault_root: Path,
) -> Path:
    """Write ArticleModel markdown card to vault/articles/."""
    entity_id = data.get("article_model_id", "unknown")
    md = article_model_card(data)
    return _write_card(vault_root, "articles", f"{entity_id}.md", md)


def write_venue_card(
    data: dict[str, Any],
    vault_root: Path,
) -> Path:
    """Write VenueModel markdown card to vault/venues/."""
    entity_id = data.get("venue_model_id", "unknown")
    md = venue_model_card(data)
    return _write_card(vault_root, "venues", f"{entity_id}.md", md)


def write_fit_report(
    data: dict[str, Any],
    vault_root: Path,
) -> Path:
    """Write FitAssessment markdown card to vault/fits/."""
    entity_id = data.get("fit_assessment_id", "unknown")
    md = fit_assessment_card(data)
    return _write_card(vault_root, "fits", f"{entity_id}.md", md)


def write_risk_card(
    data: dict[str, Any],
    vault_root: Path,
) -> Path:
    """Write RiskReport markdown card to vault/risks/."""
    entity_id = data.get("risk_report_id", "unknown")
    md = risk_report_card(data)
    return _write_card(vault_root, "risks", f"{entity_id}.md", md)


def write_compliance_card(
    data: dict[str, Any],
    vault_root: Path,
) -> Path:
    """Write ComplianceChecklist markdown card to vault/compliance/."""
    entity_id = data.get("compliance_checklist_id", "unknown")
    md = compliance_checklist_card(data)
    return _write_card(vault_root, "compliance", f"{entity_id}.md", md)


def write_mismatch_card(
    data: dict[str, Any],
    vault_root: Path,
) -> Path:
    """Write MismatchMap markdown card to vault/mismatches/."""
    entity_id = data.get("mismatch_map_id", "unknown")
    md = mismatch_map_card(data)
    return _write_card(vault_root, "mismatches", f"{entity_id}.md", md)


def write_citation_ecology_card(
    data: dict[str, Any],
    vault_root: Path,
) -> Path:
    """Write CitationEcologyReport markdown card to vault/citations/."""
    entity_id = data.get("citation_ecology_report_id", "unknown")
    md = citation_ecology_card(data)
    return _write_card(vault_root, "citations", f"{entity_id}.md", md)


def write_pipeline_artifact(
    artifact_markdown: str,
    pipeline_run_id: str,
    vault_root: Path,
) -> Path:
    """Write full pipeline artifact to vault/traces/."""
    return _write_card(vault_root, "traces", f"{pipeline_run_id}.md", artifact_markdown)


def write_pipeline_result_cards(
    result: "ManuscriptVenueFitResult",
    pipeline: "ManuscriptVenueFitPipeline",
    storage_root: Path | str | None = None,
) -> dict[str, Path]:
    """Write all vault cards from a pipeline result. Returns name→path map."""
    vault_root = ensure_vault_root(storage_root)
    written: dict[str, Path] = {}

    if result.article:
        written["article_card"] = write_article_card(
            result.article.to_dict(), vault_root)

    if result.venue:
        written["venue_card"] = write_venue_card(
            result.venue.to_dict(), vault_root)

    if result.fit:
        written["fit_card"] = write_fit_report(
            result.fit.to_dict(), vault_root)

    if result.risk_report:
        written["risk_card"] = write_risk_card(
            result.risk_report.to_dict(), vault_root)

    if result.compliance:
        written["compliance_card"] = write_compliance_card(
            result.compliance.to_dict(), vault_root)

    if result.mismatch_map:
        written["mismatch_card"] = write_mismatch_card(
            result.mismatch_map.to_dict(), vault_root)

    if result.citation_ecology:
        written["citation_ecology_card"] = write_citation_ecology_card(
            result.citation_ecology.to_dict(), vault_root)

    if result.artifact_markdown:
        written["pipeline_artifact"] = write_pipeline_artifact(
            result.artifact_markdown,
            pipeline.run.pipeline_run_id,
            vault_root,
        )

    return written
