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


# ---------------------------------------------------------------------------
# TRM-074: source-corpus handoff to the INSTALLED LitOps -> WhiteCrow surface.
# This is a provenance-only route, separate from manuscript/venue exports.
# ---------------------------------------------------------------------------


def build_talk_corpus_litops_staging_pack(
    storage_root: Path | str, case_id: str = "T3-TALK-20261019",
) -> dict[str, Any]:
    """Map an admitted talk corpus into real LitOps Source + context_pack types.

    Source IDs identify *captures*, not document titles: changed content gets
    another ID; canonical Drive document identity remains in provenance fields.
    Neither a context_pack nor WhiteCrow import is an authoritative ArticleSeed.
    """
    from hashlib import sha256
    from ..registry import read_all

    root = Path(storage_root)
    case_path = root / "talk_corpora" / case_id / "case_ledger.json"
    research_path = root / "talk_corpora" / case_id / "research_stage_handoff.json"
    if not case_path.is_file() or not research_path.is_file():
        raise ValueError("corpus and Kairon research handoff required")
    raw = case_path.read_bytes()
    digest = sha256(raw).hexdigest()
    ledger = json.loads(raw.decode("utf-8"))
    research = json.loads(research_path.read_text(encoding="utf-8"))
    if ledger.get("case_id") != case_id or research.get("case_id") != case_id:
        raise ValueError("corpus/research case identity mismatch")
    if research.get("source_ledger_sha256") != digest:
        raise ValueError("research handoff not bound to current corpus ledger")
    if ledger.get("publication_send") != "DISALLOWED":
        raise ValueError("external sends prohibited for source context")
    if any(x.get("article_seed_created") or x.get("author_approved")
           for x in ledger.get("held_article_seed_envelopes", [])):
        raise ValueError("unreviewed ArticleSeed promoted upstream")

    snapshots = ledger.get("source_snapshots") or []
    if not snapshots:
        raise ValueError("corpus source snapshots absent")
    persisted = read_all("source_snapshots", base_dir=root / "registries")
    known = {
        (x.get("source_id"), x.get("content_hash"))
        for x in persisted if x.get("extraction_status") == "extracted"
    }
    canonical_ids: set[str] = set()
    ids_by_family: dict[str, list[str]] = {}
    lit_sources: list[dict[str, Any]] = []
    for entry in sorted(snapshots, key=lambda x: x["key"]):
        source_id = entry["source_id"]
        sha = entry["content_sha256"]
        if not source_id.startswith("drive:") or len(sha) != 64:
            raise ValueError("unpinned source identity or content digest")
        if (source_id, sha[:16]) not in known:
            raise ValueError(f"source not admitted by existing intake registry: {entry['key']}")
        if source_id in canonical_ids:
            raise ValueError("same Drive document duplicated in corpus snapshot")
        canonical_ids.add(source_id)
        if entry["extraction_status"] != "extracted":
            raise ValueError("source extracted status unverified")
        capture_id = "src-trm074-" + sha256(
            (source_id + "|" + sha).encode("utf-8")
        ).hexdigest()[:22]
        family = entry["family"]
        ids_by_family.setdefault(family, []).append(capture_id)
        textual_genre = (
            "chat_log" if entry["kind"] == "CHAT_LOG"
            else "transcript" if "TRANSCRIPT" in entry["kind"]
            else "deep_research_report" if entry["kind"] == "RESEARCH_SYNTHESIS"
            else "lecture" if entry["kind"] == "SPEECH_SCRIPT"
            else "project_log"
        )
        lit_sources.append({
            "source_id": capture_id,
            "original_filename": entry["key"] + ".txt",
            "canonical_filename": "",
            "remote_path": "",
            "source_channel": "kairoskopion_owner_private_capture",
            "source_media_type": "text/plain",
            "status": "raw_registered",
            "language": "ru",
            "threads": [case_id, family],
            "topics": [],
            "tags": ["trm074", "source-provenance-only"],
            "body_type": "txt",
            "origin": "mixed" if family == "CROSS" else "user_prior_work",
            "capture_mode": "manual_upload",
            "content_genre": textual_genre,
            "work_roles": ["source_material", "needs_review"],
            "processing_state": "text_extracted",
            "source_document_id": source_id,
            "source_document_url": entry["source_url"],
            "source_capture_sha256": sha,
            "source_version_label": entry["version"],
            "source_author_state": entry["author_state"],
            "source_read_coverage": entry["read_coverage"],
            "source_kind": entry["kind"],
            "source_title_collision_safe": True,
            "semantic_acceptance": "NOT_ASSESSED",
            "external_send": "DISABLED",
        })
    families = sorted(f for f in ids_by_family if f != "CROSS")
    if not families:
        raise ValueError("no independently attributed talk families")
    context_ids = sorted(ids_by_family.get("CROSS", []))
    lit_artifacts: list[dict[str, Any]] = []
    for family in families:
        aid = "art-trm074-context-" + sha256(
            (case_id + "|" + digest + "|" + family).encode("utf-8")
        ).hexdigest()[:22]
        own_ids = sorted(ids_by_family[family])
        lit_artifacts.append({
            "artifact_id": aid,
            "title": f"{case_id} / {family} / pinned source context — SCIENCE HOLD",
            "artifact_type": "context_pack",
            "stage": "candidate",
            "status": "HOLD_SOURCE_PROVENANCE_ONLY",
            "source_ids": sorted(set(own_ids + context_ids)),
            "family_source_ids": own_ids,
            "cross_context_source_ids": context_ids,
            "segment_ids": [],
            "threads": [case_id, family],
            "topics": [],
            "reportable": False,
            "field_ready": False,
            "whitecrow_candidate": False,
            "publication_trajectories": [],
            "manuscript_status": "NOT_CREATED",
            "organ_run_id": "",
            "notes": "Source-only context; not an ArticleSeed, field acceptance, or manuscript.",
            "case_id": case_id,
            "family": family,
            "source_ledger_sha256": digest,
            "world_ref": ledger.get("world_ref"),
            "semantic_mutation": "NONE",
            "author_approved": False,
            "external_send": "DISABLED",
        })
    return {
        "schema": "TRM074_TO_INSTALLED_LITOPS_CONTEXT_PACK_V1",
        "case_id": case_id,
        "source_ledger_sha256": digest,
        "source_records": lit_sources,
        "artifact_records": lit_artifacts,
        "status": "SOURCE_ONLY_NO_WHITE_CROW_SCIENCE_ACCEPTANCE",
        "external_send": "DISABLED",
    }


def admit_talk_context_into_installed_litops(
    storage_root: Path | str, litops_root: Path | str,
    case_id: str = "T3-TALK-20261019",
) -> dict[str, Any]:
    """Invoke actual LitOps registries and read-only WhiteCrow importer.

    Must be called in an isolated, owner-authorized LITOPS_ROOT with installed
    LitOps and WhiteCrow Python packages. No raw source copy is performed.
    """
    import os
    from hashlib import sha256
    from litops.config import get_root
    from litops import registry as litops_registry
    from whitecrow.litops_import import build_import_pack
    from whitecrow.first_workset import build_workset

    target = Path(litops_root).resolve()
    if not os.environ.get("LITOPS_SKIP_DOTENV"):
        raise ValueError("LITOPS_SKIP_DOTENV required for isolated source stage")
    if target != get_root().resolve():
        raise ValueError("actual LitOps registry root does not match requested isolated target")
    # On a clean LitOps root, legacy registry._jsonl_path chooses 10_REGISTRY
    # until 05_REGISTRY_EXPORT exists, whereas WhiteCrow reads only the latter.
    # Ensure the canonical v0.3 registry and non-destructively recover an
    # isolated preflight attempt that used the legacy fallback.
    canonical = target / "05_REGISTRY_EXPORT"
    if not canonical.exists():
        from shutil import copy2
        canonical.mkdir(parents=True, exist_ok=True)
        legacy = target / "10_REGISTRY"
        for filename in ("sources.jsonl", "artifacts.jsonl"):
            if (legacy / filename).is_file():
                copy2(legacy / filename, canonical / filename)
    packet = build_talk_corpus_litops_staging_pack(storage_root, case_id)
    old_sources = {r["source_id"]: r for r in litops_registry.read_sources()}
    old_artifacts = {r["artifact_id"]: r for r in litops_registry.read_artifacts()
                     if r.get("artifact_id")}
    new_sources = new_artifacts = 0
    def _persist(rows: list[dict[str, Any]], old: dict[str, dict[str, Any]],
                 id_key: str, append) -> int:
        inserted = 0
        for record in rows:
            rid = record[id_key]
            found = old.get(rid)
            if found is not None:
                if not all(found.get(key) == val for key, val in record.items()):
                    raise ValueError(f"immutable LitOps {id_key} collision: {rid}")
                continue
            append(record)
            old[rid] = record
            inserted += 1
        return inserted

    new_sources = _persist(
        packet["source_records"], old_sources, "source_id",
        litops_registry.append_source,
    )
    new_artifacts = _persist(
        packet["artifact_records"], old_artifacts, "artifact_id",
        litops_registry.append_artifact,
    )
    import_index = build_import_pack(target)
    refs = {r.litops_artifact_id: r for r in import_index.artifacts}
    expected_ids = {r["artifact_id"] for r in packet["artifact_records"]}
    blocked = {
        r.litops_artifact_id: r.blocked_reason for r in import_index.blocked
        if r.litops_artifact_id in expected_ids
    }
    if blocked or not expected_ids.issubset(refs):
        raise ValueError("WhiteCrow rejected or missed staged context packs: " + str(blocked))
    if any(refs[ident].seed_kind != "context_pack_seed" for ident in expected_ids):
        raise ValueError("WhiteCrow type projection altered context-only intent")
    if any(
        refs[ident].provenance.organ_run_id
        or refs[ident].manuscript_status != "NOT_CREATED"
        for ident in expected_ids
    ):
        raise ValueError("WhiteCrow imported an unwarranted organ run/manuscript")
    workset = build_workset(import_index, max_context_packs=len(expected_ids))
    workset_ids = {r["litops_artifact_id"] for r in workset.context_packs}
    if workset_ids != expected_ids or workset.is_manuscript:
        raise ValueError("WhiteCrow first workset did not preserve source-only contexts")
    if workset.primary_anchor_artifact_id or workset.w23_seed.get("available"):
        raise ValueError("isolated talk workset cannot claim W23 certification")
    receipt = {
        "schema": "TRM074_LITOPS_WHITE_CROW_READBACK_V1",
        "case_id": case_id,
        "source_ledger_sha256": packet["source_ledger_sha256"],
        "litops_sources_total": len(packet["source_records"]),

        "litops_contexts_total": len(packet["artifact_records"]),

        "whitecrow_imported_context_ids": sorted(expected_ids),
        "whitecrow_blocked_contexts": blocked,
        "whitecrow_import_warnings": import_index.import_warnings,
        "whitecrow_first_workset_context_ids": sorted(workset_ids),
        "whitecrow_first_workset_manuscript": workset.is_manuscript,
        "whitecrow_w23_certification_available": bool(workset.w23_seed.get("available")),
        "whitecrow_status": "CONTEXT_ONLY_SCIENCE_AND_AUTHOR_GATE_HOLD",
        "litops_real_registry": str(target / "05_REGISTRY_EXPORT"),
        "article_seed_created": False,
        "world_mutated": False,
        "external_send": "DISABLED",
    }
    output = Path(storage_root) / "talk_corpora" / case_id / "litops_whitecrow_stage.json"
    encoded = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".tmp").write_bytes(encoded)
    output.with_suffix(".tmp").replace(output)
    return {
        "receipt_path": str(output),
        "sha256": sha256(encoded).hexdigest(),
        "source_records": len(packet["source_records"]),
        "context_packs": len(packet["artifact_records"]),
        "new_sources": new_sources,
        "new_context_packs": new_artifacts,
        "whitecrow_imported": len(expected_ids),
        "article_seed_created": 0,
        "external_send": "DISABLED",
    }
