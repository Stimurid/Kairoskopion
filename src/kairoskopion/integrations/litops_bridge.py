"""Litops Compatibility Bridge (Sprint 7).

Exports Kairoskopion pipeline artifacts as Litops-compatible JSONL records.
Litops schema: Source, Segment, Artifact, Use, EntityCandidate.

This bridge translates Kairoskopion entities into Litops registry format
without requiring Litops as a dependency. Output is JSONL files that can
be copied into a Litops project's 05_REGISTRY_EXPORT/ directory.

No LLM calls. No network. Pure deterministic mapping.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..schema import (
    ArticleModel,
    BibliographyProfile,
    ComplianceChecklist,
    FitAssessment,
    PublicationTrajectoryReport,
    RiskReport,
    SubmissionPack,
    SubmissionScenario,
    VenueModel,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _litops_source_id(kairon_id: str) -> str:
    """Map a Kairoskopion ID to a Litops source ID."""
    # Strip prefix and use as suffix for litops id
    short = kairon_id.split("_", 1)[-1] if "_" in kairon_id else kairon_id
    return f"src-{short[:6]}"


def _litops_artifact_id(kairon_id: str, prefix: str = "art") -> str:
    short = kairon_id.split("_", 1)[-1] if "_" in kairon_id else kairon_id
    return f"{prefix}-{short[:6]}"


# ---------------------------------------------------------------------------
# Entity converters
# ---------------------------------------------------------------------------


def article_to_litops_source(article: ArticleModel) -> dict[str, Any]:
    """Convert ArticleModel to a Litops Source record."""
    return {
        "source_id": _litops_source_id(article.article_model_id),
        "kairoskopion_id": article.article_model_id,
        "title": article.title_current or "(untitled manuscript)",
        "body_type": "markdown",
        "origin": "user_created",
        "content_genre": article.genre_current or "research_article",
        "language": article.language or "en",
        "facets": {
            "method_status": article.method_status,
            "novelty_mode": article.novelty_mode,
            "article_stage": article.article_stage,
            "word_count": getattr(article, "word_count", None),
        },
        "registered_at": getattr(article, "created_at", _now_iso()),
        "bridge_version": "kairoskopion-litops-v1",
    }


def venue_to_litops_source(venue: VenueModel) -> dict[str, Any]:
    """Convert VenueModel to a Litops Source record."""
    return {
        "source_id": _litops_source_id(venue.venue_model_id),
        "kairoskopion_id": venue.venue_model_id,
        "title": venue.canonical_name or "(unnamed venue)",
        "body_type": "json",
        "origin": "user_created",
        "content_genre": "venue_profile",
        "facets": {
            "venue_type": venue.venue_type,
            "publisher": venue.publisher_or_owner,
            "scope": (venue.scope_summary or "")[:200],
            "language_policy": venue.language_policy,
            "open_access": getattr(venue, "open_access_status", None),
        },
        "registered_at": getattr(venue, "created_at", _now_iso()),
        "bridge_version": "kairoskopion-litops-v1",
    }


def fit_to_litops_artifact(fit: FitAssessment) -> dict[str, Any]:
    """Convert FitAssessment to a Litops Artifact record."""
    axes_summary = "; ".join(
        f"{a.get('axis', '?')}={a.get('value', '?')}" for a in fit.axes
    )
    return {
        "artifact_id": _litops_artifact_id(fit.fit_assessment_id),
        "kairoskopion_id": fit.fit_assessment_id,
        "artifact_type": "fit_assessment",
        "title": f"Fit Assessment: {fit.overall_label}",
        "body_type": "json",
        "content_summary": f"Overall: {fit.overall_label}. Axes: {axes_summary}",
        "source_entity_ids": [
            _litops_source_id(fit.article_model_id) if fit.article_model_id else None,
            _litops_source_id(fit.venue_model_id) if fit.venue_model_id else None,
        ],
        "facets": {
            "overall_label": fit.overall_label,
            "axis_count": len(fit.axes),
            "confidence": fit.confidence,
        },
        "created_at": getattr(fit, "created_at", _now_iso()),
        "bridge_version": "kairoskopion-litops-v1",
    }


def risk_to_litops_artifact(risk: RiskReport) -> dict[str, Any]:
    """Convert RiskReport to a Litops Artifact record."""
    return {
        "artifact_id": _litops_artifact_id(risk.risk_report_id),
        "kairoskopion_id": risk.risk_report_id,
        "artifact_type": "risk_report",
        "title": f"Risk Report: {risk.overall_risk_label}",
        "body_type": "json",
        "content_summary": (
            f"Overall risk: {risk.overall_risk_label}. "
            f"{len(risk.risk_items)} items, "
            f"{len(risk.blocking_risks)} blocking."
        ),
        "source_entity_ids": [
            _litops_source_id(risk.article_model_id) if risk.article_model_id else None,
            _litops_source_id(risk.venue_model_id) if risk.venue_model_id else None,
        ],
        "facets": {
            "overall_risk_label": risk.overall_risk_label,
            "risk_item_count": len(risk.risk_items),
            "blocking_count": len(risk.blocking_risks),
        },
        "created_at": getattr(risk, "created_at", _now_iso()),
        "bridge_version": "kairoskopion-litops-v1",
    }


def trajectory_to_litops_artifact(
    report: PublicationTrajectoryReport,
) -> dict[str, Any]:
    """Convert PublicationTrajectoryReport to a Litops Artifact record."""
    return {
        "artifact_id": _litops_artifact_id(report.report_id),
        "kairoskopion_id": report.report_id,
        "artifact_type": "trajectory_report",
        "title": "Publication Trajectory Report",
        "body_type": "json",
        "content_summary": report.overall_recommendation or "",
        "source_entity_ids": [
            _litops_source_id(report.article_model_id) if report.article_model_id else None,
            _litops_source_id(report.venue_model_id) if report.venue_model_id else None,
        ],
        "facets": {
            "strengths_count": len(report.strengths),
            "weaknesses_count": len(report.weaknesses),
            "critical_actions_count": len(report.critical_actions),
            "confidence": report.confidence,
        },
        "created_at": _now_iso(),
        "bridge_version": "kairoskopion-litops-v1",
    }


def pack_to_litops_artifact(pack: SubmissionPack) -> dict[str, Any]:
    """Convert SubmissionPack to a Litops Artifact record."""
    return {
        "artifact_id": _litops_artifact_id(pack.submission_pack_id),
        "kairoskopion_id": pack.submission_pack_id,
        "artifact_type": "submission_pack",
        "title": f"Submission Pack ({pack.ready_status})",
        "body_type": "json",
        "content_summary": (
            f"Status: {pack.ready_status}. "
            f"{len(pack.files)} files, "
            f"{len(pack.blocking_issues)} blocking, "
            f"{len(pack.missing_items)} missing."
        ),
        "source_entity_ids": [
            _litops_source_id(pack.article_model_id) if pack.article_model_id else None,
            _litops_source_id(pack.venue_model_id) if pack.venue_model_id else None,
        ],
        "facets": {
            "ready_status": pack.ready_status,
            "file_count": len(pack.files),
            "blocking_count": len(pack.blocking_issues),
        },
        "created_at": pack.created_at,
        "bridge_version": "kairoskopion-litops-v1",
    }


def bibliography_to_litops_artifact(bib: BibliographyProfile) -> dict[str, Any]:
    """Convert BibliographyProfile to a Litops Artifact record."""
    bib_id = getattr(bib, "bibliography_profile_id", "bib_unknown")
    return {
        "artifact_id": _litops_artifact_id(bib_id),
        "kairoskopion_id": bib_id,
        "artifact_type": "bibliography_profile",
        "title": f"Bibliography ({bib.total_references} refs)",
        "body_type": "json",
        "content_summary": (
            f"{bib.total_references} references, "
            f"style: {bib.reference_style or 'unknown'}, "
            f"recency: {bib.recency_profile or 'unknown'}."
        ),
        "facets": {
            "total_references": bib.total_references,
            "reference_style": bib.reference_style,
            "recency_profile": bib.recency_profile,
            "doi_count": bib.doi_count,
        },
        "created_at": _now_iso(),
        "bridge_version": "kairoskopion-litops-v1",
    }


# ---------------------------------------------------------------------------
# Export pack
# ---------------------------------------------------------------------------


def build_litops_export_pack(
    *,
    article: ArticleModel | None = None,
    venue: VenueModel | None = None,
    fit: FitAssessment | None = None,
    risk: RiskReport | None = None,
    trajectory: PublicationTrajectoryReport | None = None,
    pack: SubmissionPack | None = None,
    bibliography: BibliographyProfile | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Build a complete Litops export pack from Kairoskopion artifacts.

    Returns a dict with keys 'sources' and 'artifacts', each containing
    a list of Litops-compatible records ready for JSONL serialization.
    """
    sources: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []

    if article:
        sources.append(article_to_litops_source(article))
    if venue:
        sources.append(venue_to_litops_source(venue))

    if fit:
        artifacts.append(fit_to_litops_artifact(fit))
    if risk:
        artifacts.append(risk_to_litops_artifact(risk))
    if trajectory:
        artifacts.append(trajectory_to_litops_artifact(trajectory))
    if pack:
        artifacts.append(pack_to_litops_artifact(pack))
    if bibliography:
        artifacts.append(bibliography_to_litops_artifact(bibliography))

    return {"sources": sources, "artifacts": artifacts}


def write_litops_export(
    export_pack: dict[str, list[dict[str, Any]]],
    output_dir: Path,
) -> dict[str, Path]:
    """Write Litops export pack as JSONL files.

    Creates:
      - sources.jsonl  (Litops Source records)
      - artifacts.jsonl (Litops Artifact records)

    Returns dict of written file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    for registry_name in ("sources", "artifacts"):
        records = export_pack.get(registry_name, [])
        if not records:
            continue
        path = output_dir / f"{registry_name}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        written[registry_name] = path

    return written
