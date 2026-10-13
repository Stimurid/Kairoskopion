"""Offline, no-submit import adapter over the PR19 reference state machine.

An operator-supplied approval file is a trust input, not a generated QA result.
No network, subprocess, manuscript transformation, or submission actuator exists
here. One coordinator-serialized worker per output directory, as in PR19.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Callable

from .submission_package_factory import (
    ARTIFACT_KINDS, DEFAULT_QA, SubmissionPackageFactoryStore, _digest, _target,
)
from .target_world_catalog import TargetWorldCatalog, _digest as snapshot_digest


class EvidenceBlocked(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save_json(path: Path, value: dict) -> None:
    atomic_write(path, json.dumps(value, sort_keys=True, ensure_ascii=False,
                                separators=(",", ":")).encode("utf-8"))


def local_path(root: Path, value: str) -> Path:
    """Resolve only explicitly supplied relative files within the input root."""
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise EvidenceBlocked("BLOCKED_NEEDS_ADAPTER: relative local path required")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise EvidenceBlocked("input_path_outside_workspace")
    return path


def read_bound(root: Path, row: dict) -> bytes:
    digest = row.get("sha256")
    if (not isinstance(digest, str) or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)):
        raise EvidenceBlocked("sha256_required_for_local_import")
    data = local_path(root, row.get("path")).read_bytes()
    if sha256(data) != digest:
        raise EvidenceBlocked("input_hash_mismatch:" + row["path"])
    return data


def _current_target(catalog: TargetWorldCatalog, expected: dict) -> dict:
    package = catalog.get_package(expected["package_id"])
    entries = [e for e in catalog.list_entries()
               if e.get("package_id") == expected["package_id"]]
    if package is None or len(entries) != 1:
        raise EvidenceBlocked("BLOCKED_NEEDS_ADAPTER: frozen_target_catalog_missing")
    if (snapshot_digest(package["snapshot"]) != expected["content_digest"]
            or package["content_digest"] != expected["content_digest"]
            or entries[0]["content_digest"] != expected["content_digest"]):
        raise EvidenceBlocked("stale_target_world_digest")
    current = {**package, "catalog_status": entries[0]["status"]}
    if _target(current) != _target(expected):
        raise EvidenceBlocked("stale_target_world_status_or_identity")
    return current


def run_import(*, manifest_path: Path, approval_path: Path, input_root: Path,
               output_root: Path, catalog_root: Path, resume: bool = False,
               allow_fixtures: bool = False,
               checkpoint: Callable[[str], None] = lambda phase: None) -> dict:
    """Import approved bytes, verify all evidence on EVERY run, then build kwargs.

    Paths and catalog must be operator-provided local workspace locations. The
    caller serializes workers; resume is authorized only after the old worker
    stopped. checkpoint is a test fault-injection seam, never loaded from JSON.
    """
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        result = {"schema_version": "publication-import-result-v1",
                  "execution_id": None, "article_id": None, "run_id": None,
                  "status": "BLOCKED_NEEDS_ADAPTER" if isinstance(exc, OSError) else "BLOCKED",
                  "blockers": [str(exc)], "finalization_request": None,
                  "fixture_gate_request": None, "external_submit_events": [],
                  "live_acceptance": "NOT_CLAIMED"}
        save_json(output_root / "current.json", result)
        return result
    execution_id = _digest(manifest)
    folder = output_root / execution_id
    result_path = folder / "result.json"
    result = {"schema_version": "publication-import-result-v1",
              "execution_id": execution_id, "article_id": None,
              "status": "CHECKING", "blockers": [], "run_id": None,
              "finalization_request": None, "fixture_gate_request": None,
              "external_submit_events": [], "live_acceptance": "NOT_CLAIMED"}
    # Invalidate the prior deliverable before any revalidation (including resume).
    save_json(output_root / "current.json", result)
    save_json(result_path, result)
    # Share PR19 identity across input-manifest revisions. Moving a receipt or
    # editing an import manifest must not bypass terminal per-run immutability.
    store = SubmissionPackageFactoryStore(output_root)
    try:
        if manifest["schema_version"] != "publication-import-v1":
            raise EvidenceBlocked("unsupported_manifest_schema")
        fixture = manifest["evidence_mode"] == "FIXTURE"
        if manifest["evidence_mode"] not in {"FIXTURE", "REAL"}:
            raise EvidenceBlocked("unknown_evidence_mode")
        if fixture and not allow_fixtures:
            raise EvidenceBlocked("fixture_requires_explicit_opt_in")
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        pins = approval.get("approved_qa_sha256")
        if (not isinstance(pins, list)
                or any(not isinstance(p, str) or len(p) != 64
                       or any(c not in "0123456789abcdef" for c in p) for p in pins)):
            raise EvidenceBlocked("approval_receipt_pins_must_be_sha256_list")
        if (approval["manifest_digest"] != execution_id
                or approval["evidence_mode"] != manifest["evidence_mode"]
                or approval["decision"] != "APPROVED_FOR_LOCAL_DRY_RUN"
                or not approval["authority_ref"].strip()):
            raise EvidenceBlocked("approval_not_bound_to_manifest")
        expiry = datetime.fromisoformat(approval["valid_until"].replace("Z", "+00:00"))
        if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
            raise EvidenceBlocked("approval_expired_or_unzoned")
        spec = deepcopy(manifest["spec"])
        result["article_id"] = spec["article_id"]
        # This executable spine cannot weaken the package/QA policy via input.
        spec["required_artifact_kinds"] = sorted(ARTIFACT_KINDS)
        spec["required_qa_types"] = sorted(DEFAULT_QA)
        sibling = spec["authoritative_sibling"]
        source = manifest["sibling_file"]
        if source["sha256"] != sibling.get("sha256"):
            raise EvidenceBlocked("sibling_hash_binding_missing")
        read_bound(input_root, source)
        verified_files = [source]
        catalog = TargetWorldCatalog(catalog_root)
        _current_target(catalog, spec["target_world_package"])
        run = store.start(**spec)
        run_id = run["run_id"]
        result["run_id"] = run_id
        if any(a["status"] == "IN_PROGRESS" for a in run["artifacts"].values()) or run["qa_in_progress"]:
            if not resume:
                raise EvidenceBlocked("interrupted_worker_requires_explicit_resume")
        if resume:
            before = _digest(run)
            run = store.recover(run_id)
            recovery_path = folder / ("recovery-" + before + ".json")
            save_json(recovery_path, {"run_id": run_id, "before_digest": before,
                                     "after_digest": _digest(run),
                                     "terminal_receipts_preserved": True})
        checkpoint("PLANNED")
        if set(manifest["artifacts"]) != ARTIFACT_KINDS:
            raise EvidenceBlocked("BLOCKED_NEEDS_ADAPTER: all_four_artifacts_required")
        for kind in sorted(ARTIFACT_KINDS):
            row = manifest["artifacts"][kind]
            store.begin_artifact(run_id, kind)
            checkpoint("MATERIALIZING:" + kind)
            version = row["version"]
            if row["file"]["sha256"] != version.get("sha256"):
                raise EvidenceBlocked("artifact_hash_binding_missing:" + kind)
            if row["source_sibling"] != sibling:
                raise EvidenceBlocked("artifact_sibling_lineage_mismatch:" + kind)
            data = read_bound(input_root, row["file"])
            verified_files.append(row["file"])
            # Copies are opaque; no text/metadata rewrite or export is implied.
            imported = folder / "imports" / row["file"]["sha256"]
            if imported.exists() and sha256(imported.read_bytes()) != sha256(data):
                raise EvidenceBlocked("imported_artifact_corrupt:" + kind)
            if not imported.exists():
                atomic_write(imported, data)
            store.record_artifact(run_id, kind=kind, artifact=version,
                                  source_sibling=row["source_sibling"])
            checkpoint("ARTIFACT_COMPLETE:" + kind)
        checkpoint("QA_PENDING")
        for kind in sorted(ARTIFACT_KINDS):
            row = manifest["artifacts"][kind]
            for qtype in DEFAULT_QA:
                store.begin_qa(run_id, kind=kind, qa_type=qtype)
                checkpoint("QA_RUNNING:" + kind + ":" + qtype)
                pointer = row.get("qa", {}).get(qtype)
                if pointer is None:
                    raise EvidenceBlocked("BLOCKED_NEEDS_ADAPTER: receipt_missing:" + kind + ":" + qtype)
                data = read_bound(input_root, pointer)
                verified_files.append(pointer)
                if pointer["sha256"] not in approval["approved_qa_sha256"]:
                    raise EvidenceBlocked("qa_receipt_not_independently_approved")
                receipt = json.loads(data)
                expected = {"article_id": spec["article_id"], "kind": kind,
                            "qa_type": qtype, "artifact": row["version"],
                            "source_sibling": sibling,
                            "target_world_package_id": spec["target_world_package"]["package_id"],
                            "target_world_digest": spec["target_world_package"]["content_digest"],
                            "policy_snapshot_refs": spec["policy_snapshot_refs"],
                            "evidence_mode": manifest["evidence_mode"]}
                if any(receipt.get(key) != value for key, value in expected.items()):
                    raise EvidenceBlocked("qa_receipt_lineage_mismatch:" + kind + ":" + qtype)
                if (not isinstance(receipt.get("producer_ref"), str)
                        or not receipt["producer_ref"].strip()
                        or not isinstance(receipt.get("evidence_files"), list)
                        or not receipt["evidence_files"]):
                    raise EvidenceBlocked("BLOCKED_NEEDS_ADAPTER: qa_evidence_missing")
                evidence = receipt["evidence_files"]
                if qtype == "VISUAL_RENDER":
                    count = receipt.get("page_count")
                    if (type(count) is not int or count < 1
                            or [e.get("page") for e in evidence] != list(range(1, count + 1))):
                        raise EvidenceBlocked("full_page_render_evidence_incomplete")
                for item in evidence:
                    evidence_bytes = read_bound(input_root, item)
                    verified_files.append(item)
                    evidence_path = folder / "imports" / item["sha256"]
                    atomic_write(evidence_path, evidence_bytes)
                saved_receipt = output_root / "evidence" / "receipts" / (pointer["sha256"] + ".json")
                atomic_write(saved_receipt, data)
                store.record_qa(run_id, kind=kind, qa_type=qtype, artifact=row["version"],
                                status=receipt["status"], evidence_ref=saved_receipt.resolve().as_uri())
                checkpoint("QA_COMPLETE:" + kind + ":" + qtype)
        # Recheck mutable catalog immediately before handoff, including retries.
        _current_target(catalog, spec["target_world_package"])
        run = store.get(run_id)
        if run["blockers"]:
            result.update(status="BLOCKED", blockers=run["blockers"])
        else:
            checkpoint("FINALIZATION_READY")
            _current_target(catalog, spec["target_world_package"])
            if (json.loads(approval_path.read_text(encoding="utf-8")) != approval
                    or _digest(json.loads(manifest_path.read_text(encoding="utf-8"))) != execution_id
                    or expiry <= datetime.now(timezone.utc)):
                raise EvidenceBlocked("approval_or_manifest_changed_during_run")
            for pointer in verified_files:
                read_bound(input_root, pointer)
            request = store.build_finalization_request(run_id)
            # PR19 returns function kwargs; the HTTP API expects package_id.
            request["target_world_package_id"] = request.pop("target_world_package")["package_id"]
            result.update(status="FIXTURE_DRY_RUN_COMPLETE" if fixture else "DRY_RUN_COMPLETE")
            result["fixture_gate_request" if fixture else "finalization_request"] = request
            checkpoint("HANDED_OFF")
        result["factory_phase"] = store.get(run_id)["phase"]
    except (EvidenceBlocked, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        reason = str(exc)
        result.update(status="BLOCKED_NEEDS_ADAPTER" if isinstance(exc, (OSError, KeyError))
                      or "BLOCKED_NEEDS_ADAPTER" in reason else "BLOCKED",
                      blockers=[reason], finalization_request=None, fixture_gate_request=None)
        if result["run_id"]:
            try:
                result["factory_phase"] = store.get(result["run_id"])["phase"]
            except (OSError, ValueError, KeyError):
                result["factory_phase"] = "UNKNOWN"
    save_json(result_path, result)
    save_json(output_root / "current.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("manifest", "approval", "input-root", "output-root", "catalog-root"):
        parser.add_argument("--" + flag, required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-fixtures", action="store_true")
    args = parser.parse_args(argv)
    result = run_import(manifest_path=args.manifest, approval_path=args.approval,
                        input_root=args.input_root, output_root=args.output_root,
                        catalog_root=args.catalog_root, resume=args.resume,
                        allow_fixtures=args.allow_fixtures)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] in {"DRY_RUN_COMPLETE", "FIXTURE_DRY_RUN_COMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
