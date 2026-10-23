"""Reference-only package preparation; one serialized worker per data root.

Adapters own materialization and QA. Artikl owns sibling semantics. This module
never opens artifact refs, renders documents, or sends a submission. Resume is
explicit, after the coordinator has stopped the previous worker.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .submission_gate import assess_submission_package, READY_FOR_HUMAN_SUBMISSION


DEFAULT_QA = ("SEMANTIC_QA", "PRIVACY_SCRUB", "VISUAL_RENDER")
ARTIFACT_KINDS = {"manuscript_docx", "title_page", "cover_letter", "submission_checklist"}
PLANNED = "PLANNED"
MATERIALIZING = "MATERIALIZING"
QA_PENDING = "QA_PENDING"
FINALIZATION_READY = "FINALIZATION_READY"
BLOCKED = "BLOCKED"
HANDED_OFF = "HANDED_OFF"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("nonempty string required")
    return value


def _refs(values: list[str]) -> list[str]:
    if not isinstance(values, (list, tuple)):
        raise ValueError("list of references required")
    return sorted({_text(v) for v in values})


def _version(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - {"ref", "revision", "sha256"}:
        raise ValueError("only ref/revision/sha256 accepted; no content payload")
    result = {"ref": _text(value.get("ref")), "revision": None, "sha256": None}
    for key in ("revision", "sha256"):
        if value.get(key) is not None:
            result[key] = _text(value[key])
    if not (result["revision"] or result["sha256"]):
        raise ValueError("unversioned reference")
    sha = result["sha256"]
    if sha and (len(sha) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha)):
        raise ValueError("sha256 must contain 64 hexadecimal characters")
    return result


def _choice(value: str, allowed: set[str]) -> str:
    if value not in allowed:
        raise ValueError("unsupported status or kind")
    return value


def _skeleton(value: dict[str, Any]) -> dict[str, Any]:
    # SubmissionPack may contain a manuscript-derived cover letter. Never copy it.
    return {
        "submission_pack_id": _text(value.get("submission_pack_id")),
        "ready_status": _text(value.get("ready_status", "unknown")),
        "status": _text(value.get("status", "unknown")),
        **{key: _refs(value.get(key) or []) for key in
           ("blocking_issues", "missing_items", "unknowns")},
    }


def _target(value: dict[str, Any]) -> dict[str, Any]:
    snapshot = value.get("snapshot") or {}
    return {
        "package_id": _text(value.get("package_id")),
        "content_digest": _text(value.get("content_digest")),
        "status": _text(value.get("status", "UNKNOWN")),
        "catalog_status": _text(value.get("catalog_status") or value.get("status", "UNKNOWN")),
        "snapshot": {
            "target_id": _text(snapshot.get("target_id")),
            "snapshot_id": _text(snapshot.get("snapshot_id")),
        },
    }


def _request(run: dict[str, Any]) -> dict[str, Any]:
    spec = run["spec"]
    artifacts = [deepcopy(a) for a in run["artifacts"].values() if a["status"] == "COMPLETE"]
    qa = [deepcopy(q) for q in run["qa_receipts"].values()]
    # Gate's opaque revision string binds the ENTIRE authoritative pointer,
    # including ref and hash when both hash and revision were supplied.
    return {
        "article_id": spec["article_id"],
        "venue_id": spec["venue_id"],
        "manuscript_revision": _json(spec["authoritative_sibling"]),
        "submission_pack": deepcopy(spec["submission_pack"]),
        "target_world_package": deepcopy(spec["target_world_package"]),
        "artifacts": sorted(artifacts, key=lambda a: a["kind"]),
        "qa_receipts": sorted(qa, key=_json),
        "route_status": spec["route_status"],
        "author_fields_status": spec["author_fields_status"],
        "policy_snapshot_refs": list(spec["policy_snapshot_refs"]),
        "required_artifact_kinds": list(spec["required_artifact_kinds"]),
        "required_qa_types": list(spec["required_qa_types"]),
    }


def _refresh(run: dict[str, Any]) -> None:
    manifest = assess_submission_package(**_request(run))
    blockers = list(manifest["blockers"])
    for kind, artifact in run["artifacts"].items():
        for qtype in run["spec"]["required_qa_types"]:
            receipt = run["qa_receipts"].get(kind + ":" + qtype)
            if not receipt or receipt["status"] != "PASS":
                blockers.append(f"artifact_qa_not_passed:{kind}:{qtype}")
        if artifact["status"] == "FAILED":
            blockers.append(f"artifact_failed:{kind}")
    run["blockers"] = sorted(set(blockers))
    hard = [b for b in blockers if not b.startswith((
        "required_artifact_missing:", "required_qa_not_passed:", "artifact_qa_not_passed:",
    ))]
    if hard:
        run["phase"] = BLOCKED
    elif any(a["status"] == "IN_PROGRESS" for a in run["artifacts"].values()):
        run["phase"] = MATERIALIZING
    elif any(a["status"] != "COMPLETE" for a in run["artifacts"].values()):
        run["phase"] = PLANNED
    elif blockers:
        run["phase"] = QA_PENDING
    elif run.get("handoff_request") is not None:
        run["phase"] = HANDED_OFF
    else:
        run["phase"] = FINALIZATION_READY


class SubmissionPackageFactoryStore:
    """Atomic JSON state, following provider stores; no public arbitrary put.

    Calls must be serialized by the coordinator (as for BatchRunStore). Atomic
    replacement protects against interrupted writes, not concurrent workers.
    COMPLETE artifact versions and terminal QA receipts are immutable per run.
    Corrected materialization requires a new versioned sibling or policy input.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root) / "kairon_provider" / "submission_package_runs"

    def _path(self, run_id: str) -> Path:
        return self.root / (hashlib.sha256(_text(run_id).encode("utf-8")).hexdigest() + ".json")

    def _save(self, run: dict[str, Any]) -> dict[str, Any]:
        _refresh(run)
        self.root.mkdir(parents=True, exist_ok=True)
        # Unique sibling temp file, flushed before atomic replace; abandoned
        # .tmp files are never interpreted as committed state on recovery.
        fd, name = tempfile.mkstemp(dir=self.root, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(_json(run))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self._path(run["run_id"]))
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return deepcopy(run)

    def get(self, run_id: str) -> dict[str, Any]:
        run = json.loads(self._path(run_id).read_text(encoding="utf-8"))
        if run["run_id"] != run_id or run_id != "package-run:" + _digest(run["spec"]):
            raise ValueError("run identity mismatch")
        return run

    def start(
        self, *, article_id: str, venue_id: str,
        authoritative_sibling: dict[str, Any], target_world_package: dict[str, Any],
        submission_pack: dict[str, Any], policy_snapshot_refs: list[str],
        route_status: str, author_fields_status: str,
        required_artifact_kinds: list[str] | None = None,
        required_qa_types: list[str] | None = None,
    ) -> dict[str, Any]:
        kinds = _refs(required_artifact_kinds if required_artifact_kinds is not None else ["manuscript_docx"])
        qa = _refs(required_qa_types if required_qa_types is not None else list(DEFAULT_QA))
        if not kinds or not qa:
            raise ValueError("empty artifact/QA policy is unsupported by the finalization gate")
        for kind in kinds:
            _choice(kind, ARTIFACT_KINDS)
        for qtype in qa:
            _choice(qtype, set(DEFAULT_QA))
        spec = {
            "schema_version": "submission-package-factory-v1",
            "article_id": _text(article_id), "venue_id": _text(venue_id),
            "authoritative_sibling": _version(authoritative_sibling),
            "target_world_package": _target(target_world_package),
            "submission_pack": _skeleton(submission_pack),
            "policy_snapshot_refs": _refs(policy_snapshot_refs),
            "route_status": _choice(route_status, {"LIVE", "BLOCKED", "UNKNOWN"}),
            "author_fields_status": _choice(author_fields_status, {"CONFIRMED", "OPEN", "NOT_REQUIRED"}),
            "required_artifact_kinds": kinds, "required_qa_types": qa,
        }
        if spec["target_world_package"]["snapshot"]["target_id"] != venue_id:
            raise ValueError("target-world target_id must match venue_id")
        run_id = "package-run:" + _digest(spec)
        if self._path(run_id).exists():
            return self.get(run_id)
        return self._save({
            "run_id": run_id, "spec": spec, "phase": PLANNED, "blockers": [],
            "artifacts": {kind: {
                "kind": kind, "ref": None, "revision": None, "sha256": None,
                "source_sibling": deepcopy(spec["authoritative_sibling"]), "status": "PENDING",
            } for kind in kinds},
            "qa_receipts": {}, "qa_in_progress": [], "handoff_request": None,
        })

    def begin_artifact(self, run_id: str, kind: str) -> dict[str, Any]:
        run = self.get(run_id)
        artifact = run["artifacts"][kind]
        if artifact["status"] == "PENDING":
            artifact["status"] = "IN_PROGRESS"
            return self._save(run)
        return run

    def record_artifact(
        self, run_id: str, *, kind: str, artifact: dict[str, Any],
        source_sibling: dict[str, Any],
    ) -> dict[str, Any]:
        run = self.get(run_id)
        prior = run["artifacts"][kind]
        lineage = _version(source_sibling)
        if lineage != run["spec"]["authoritative_sibling"]:
            raise ValueError("artifact source sibling mismatch")
        row = {"kind": kind, **_version(artifact), "source_sibling": lineage, "status": "COMPLETE"}
        if prior["status"] == "COMPLETE":
            if prior != row:
                raise ValueError("completed artifact version is immutable")
            return run
        # Different kinds cannot share a ref: the legacy gate binds QA by ref.
        if any(a["kind"] != kind and a["ref"] == row["ref"] for a in run["artifacts"].values()):
            raise ValueError("artifact ref already assigned to another kind")
        run["artifacts"][kind] = row
        return self._save(run)

    def begin_qa(self, run_id: str, *, kind: str, qa_type: str) -> dict[str, Any]:
        run = self.get(run_id)
        self._qa_artifact(run, kind, qa_type)
        key = kind + ":" + qa_type
        if key not in run["qa_receipts"] and key not in run["qa_in_progress"]:
            run["qa_in_progress"] = sorted([*run["qa_in_progress"], key])
            return self._save(run)
        return run

    @staticmethod
    def _qa_artifact(run: dict[str, Any], kind: str, qa_type: str) -> dict[str, Any]:
        _choice(qa_type, set(run["spec"]["required_qa_types"]))
        artifact = run["artifacts"][kind]
        if artifact["status"] != "COMPLETE":
            raise ValueError("QA requires completed artifact")
        return artifact

    def record_qa(
        self, run_id: str, *, kind: str, qa_type: str,
        artifact: dict[str, Any], status: str, evidence_ref: str,
    ) -> dict[str, Any]:
        run = self.get(run_id)
        current = self._qa_artifact(run, kind, qa_type)
        version = _version(artifact)
        if version != {key: current[key] for key in ("ref", "revision", "sha256")}:
            raise ValueError("QA artifact version mismatch")
        row = {
            "qa_type": qa_type, "status": _choice(status, {"PASS", "FAIL"}),
            "artifact_ref": version["ref"], "artifact_revision": version["revision"],
            "artifact_sha256": version["sha256"], "evidence_ref": _text(evidence_ref),
        }
        key = kind + ":" + qa_type
        prior = run["qa_receipts"].get(key)
        if prior is not None:
            if prior != row:
                raise ValueError("terminal QA receipt is immutable")
            return run
        run["qa_receipts"][key] = row
        run["qa_in_progress"] = [q for q in run["qa_in_progress"] if q != key]
        return self._save(run)

    def recover(self, run_id: str) -> dict[str, Any]:
        """After worker shutdown, reset claims only; preserve terminal receipts."""
        run = self.get(run_id)
        for artifact in run["artifacts"].values():
            if artifact["status"] == "IN_PROGRESS":
                artifact["status"] = "PENDING"
        run["qa_in_progress"] = []
        return self._save(run)

    def build_finalization_request(self, run_id: str) -> dict[str, Any]:
        """Return assess_submission_package kwargs; create no submission event.

        HANDED_OFF means this local request is durably available. It is not
        confirmation of gate acceptance, external delivery, or publication.
        """
        run = self.get(run_id)
        _refresh(run)
        if run["blockers"]:
            raise ValueError("package not ready: " + "; ".join(run["blockers"]))
        request = _request(run)
        if assess_submission_package(**request)["status"] != READY_FOR_HUMAN_SUBMISSION:
            raise ValueError("existing finalization gate blocked request")
        if run["handoff_request"] is None:
            run["handoff_request"] = request
            self._save(run)
        elif run["handoff_request"] != request:
            raise ValueError("handoff request mismatch")
        return deepcopy(request)
