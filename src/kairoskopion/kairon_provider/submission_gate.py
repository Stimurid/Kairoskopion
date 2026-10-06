"""Fail-closed publication package finalization for the publication front.

This module does not generate manuscripts, mutate Artikl state, or submit to a
journal. It binds already-produced artifacts to one frozen TargetWorld package
and explicit QA/human/route gates. The same semantic inputs produce the same
manifest id; storage returns the first durable receipt on repeat assessment.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


READY_FOR_HUMAN_SUBMISSION = "READY_FOR_HUMAN_SUBMISSION"
BLOCKED = "BLOCKED"

_ALLOWED_ROUTE = {"LIVE", "BLOCKED", "UNKNOWN"}
_ALLOWED_AUTHOR_FIELDS = {"CONFIRMED", "OPEN", "NOT_REQUIRED"}
_UNACCEPTABLE_TARGET_STATUSES = {"PROVISIONAL", "HISTORICAL"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _uniq(values: list[str]) -> list[str]:
    return sorted({str(v) for v in values if str(v).strip()})


def _normalized_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for item in artifacts or []:
        normalized.append({
            "kind": str(item.get("kind") or "").strip(),
            "ref": str(item.get("ref") or "").strip(),
            "revision": (
                str(item.get("revision")).strip()
                if item.get("revision") not in (None, "")
                else None
            ),
            "sha256": (
                str(item.get("sha256")).strip()
                if item.get("sha256") not in (None, "")
                else None
            ),
        })
    return sorted(
        normalized,
        key=lambda x: (
            x["kind"],
            x["ref"],
            x["revision"] or "",
            x["sha256"] or "",
        ),
    )


def _normalized_qa(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for item in receipts or []:
        normalized.append({
            "qa_type": str(item.get("qa_type") or "").strip().upper(),
            "status": str(item.get("status") or "").strip().upper(),
            "artifact_ref": str(item.get("artifact_ref") or "").strip(),
            "evidence_ref": str(item.get("evidence_ref") or "").strip(),
        })
    return sorted(
        normalized,
        key=lambda x: (
            x["qa_type"],
            x["artifact_ref"],
            x["evidence_ref"],
            x["status"],
        ),
    )


def assess_submission_package(
    *,
    article_id: str,
    manuscript_revision: str,
    venue_id: str,
    submission_pack: dict[str, Any],
    target_world_package: dict[str, Any],
    artifacts: list[dict[str, Any]],
    qa_receipts: list[dict[str, Any]],
    route_status: str,
    author_fields_status: str,
    policy_snapshot_refs: list[str],
    required_artifact_kinds: list[str] | None = None,
    required_qa_types: list[str] | None = None,
    external_blockers: list[str] | None = None,
) -> dict[str, Any]:
    """Build one deterministic, fail-closed package manifest.

    READY_FOR_HUMAN_SUBMISSION is emitted only when the pre-artifact skeleton
    is clear, exact artifacts are version-bound, required QA receipts pass,
    current policy evidence exists, the submission route is live, and author
    fields are confirmed (or explicitly not required).
    """

    if not str(article_id).strip():
        raise ValueError("article_id is required")
    if not str(manuscript_revision).strip():
        raise ValueError("manuscript_revision is required")
    if not str(venue_id).strip():
        raise ValueError("venue_id is required")

    package_id = str(target_world_package.get("package_id") or "").strip()
    content_digest = str(target_world_package.get("content_digest") or "").strip()
    target_status = str(target_world_package.get("status") or "").strip()
    snapshot = target_world_package.get("snapshot")
    if not package_id or not content_digest or not isinstance(snapshot, dict):
        raise ValueError(
            "target_world_package must include package_id, content_digest, and snapshot"
        )

    route = str(route_status or "").strip().upper()
    author_state = str(author_fields_status or "").strip().upper()
    if route not in _ALLOWED_ROUTE:
        raise ValueError(f"unsupported route_status: {route_status}")
    if author_state not in _ALLOWED_AUTHOR_FIELDS:
        raise ValueError(
            f"unsupported author_fields_status: {author_fields_status}"
        )

    required_artifacts = _uniq(
        required_artifact_kinds or ["manuscript_docx"]
    )
    required_qa = _uniq(
        [x.upper() for x in (
            required_qa_types
            or ["SEMANTIC_QA", "PRIVACY_SCRUB", "VISUAL_RENDER"]
        )]
    )
    policy_refs = _uniq(policy_snapshot_refs or [])
    artifact_rows = _normalized_artifacts(artifacts)
    qa_rows = _normalized_qa(qa_receipts)

    blockers: list[str] = list(external_blockers or [])

    # Existing SubmissionPack is a pre-artifact skeleton. Any unresolved state
    # remains a blocker at the final package boundary.
    for item in submission_pack.get("blocking_issues") or []:
        blockers.append(f"skeleton:blocking:{item}")
    for item in submission_pack.get("missing_items") or []:
        blockers.append(f"skeleton:missing:{item}")
    for item in submission_pack.get("unknowns") or []:
        blockers.append(f"skeleton:unknown:{item}")

    if target_status in _UNACCEPTABLE_TARGET_STATUSES or not target_status:
        blockers.append(
            f"target_world_status_not_finalizable:{target_status or 'UNKNOWN'}"
        )

    by_kind: dict[str, list[dict[str, Any]]] = {}
    for artifact in artifact_rows:
        kind = artifact["kind"]
        if not kind:
            blockers.append("artifact_missing_kind")
            continue
        if not artifact["ref"]:
            blockers.append(f"artifact_missing_ref:{kind}")
        if not artifact["revision"] and not artifact["sha256"]:
            blockers.append(f"artifact_unversioned:{kind}")
        by_kind.setdefault(kind, []).append(artifact)

    for kind in required_artifacts:
        if not by_kind.get(kind):
            blockers.append(f"required_artifact_missing:{kind}")

    qa_by_type: dict[str, list[dict[str, Any]]] = {}
    for receipt in qa_rows:
        qtype = receipt["qa_type"]
        if not qtype:
            blockers.append("qa_missing_type")
            continue
        qa_by_type.setdefault(qtype, []).append(receipt)
        if receipt["status"] == "FAIL":
            blockers.append(f"qa_failed:{qtype}")
        if not receipt["evidence_ref"]:
            blockers.append(f"qa_missing_evidence:{qtype}")

    for qtype in required_qa:
        passes = [
            r for r in qa_by_type.get(qtype, [])
            if r["status"] == "PASS" and r["evidence_ref"]
        ]
        if not passes:
            blockers.append(f"required_qa_not_passed:{qtype}")

    if not policy_refs:
        blockers.append("policy_snapshot_missing")
    if route != "LIVE":
        blockers.append(f"submission_route_not_live:{route}")
    if author_state not in {"CONFIRMED", "NOT_REQUIRED"}:
        blockers.append(f"author_fields_not_confirmed:{author_state}")

    blockers = _uniq(blockers)

    target_summary = {
        "package_id": package_id,
        "content_digest": content_digest,
        "status": target_status,
        "target_id": snapshot.get("target_id"),
        "snapshot_id": snapshot.get("snapshot_id"),
    }
    skeleton_summary = {
        "ready_status": submission_pack.get("ready_status"),
        "status": submission_pack.get("status"),
        "blocking_issues": _uniq(submission_pack.get("blocking_issues") or []),
        "missing_items": _uniq(submission_pack.get("missing_items") or []),
        "unknowns": _uniq(submission_pack.get("unknowns") or []),
    }
    semantic_payload = {
        "schema_version": "publication-package-finalization-v1",
        "article_id": str(article_id),
        "manuscript_revision": str(manuscript_revision),
        "venue_id": str(venue_id),
        "target_world": target_summary,
        "submission_pack_skeleton": skeleton_summary,
        "artifacts": artifact_rows,
        "qa_receipts": qa_rows,
        "policy_snapshot_refs": policy_refs,
        "required_artifact_kinds": required_artifacts,
        "required_qa_types": required_qa,
        "route_status": route,
        "author_fields_status": author_state,
        "blockers": blockers,
        "human_gate": "FINAL_SUBMISSION_BY_TIMUR_ONLY",
    }
    digest = _digest(semantic_payload)
    manifest_id = f"submissionpkg:{article_id}:{digest[:16]}"

    return {
        **semantic_payload,
        "manifest_id": manifest_id,
        "content_digest": digest,
        "status": READY_FOR_HUMAN_SUBMISSION if not blockers else BLOCKED,
        "source_submission_pack_id": submission_pack.get("submission_pack_id"),
        "assessed_at": _now(),
    }


class SubmissionPackageStore:
    """Durable idempotent store for finalization manifests."""

    def __init__(self, root: str | Path):
        self.root = Path(root) / "kairon_provider" / "submission_packages"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, manifest_id: str) -> Path:
        return self.root / f"{hashlib.sha256(manifest_id.encode('utf-8')).hexdigest()}.json"

    def put(self, manifest: dict[str, Any]) -> dict[str, Any]:
        manifest_id = str(manifest.get("manifest_id") or "")
        if not manifest_id:
            raise ValueError("manifest_id is required")
        path = self._path(manifest_id)
        if path.is_file():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing.get("content_digest") != manifest.get("content_digest"):
                raise ValueError("manifest id collision with different content")
            return existing
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)
        return manifest

    def get(self, manifest_id: str) -> dict[str, Any] | None:
        path = self._path(manifest_id)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if data.get("manifest_id") == manifest_id else None
