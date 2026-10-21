"""Offline R1 followup -> Z0 -> evidence-return transport.

Only a separately authorized source reader can create an OBSERVED return.
This module never opens a URL or manuscript and never approves publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from .citation_intake_z0 import _write_immutable
from .citation_r1 import _json, _orders, _validate_inputs, _validate_return


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _lines(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("Followup rows must be objects")
    return rows


def _inputs(audit_path: Path, queue_path: Path, followup_path: Path,
            protocols_path: Path, expected_sha: str | None = None) -> tuple[list[dict], dict, dict]:
    audit, orders = _json(audit_path), _orders(queue_path)
    _validate_inputs(audit, orders)
    source_sha = audit["source"]["sha256"]
    if expected_sha and source_sha.lower() != expected_sha.lower():
        raise ValueError("Original manuscript SHA mismatch")
    by_order = {o["work_order_id"]: o for o in orders}
    rows = _lines(followup_path)
    protocols = _json(protocols_path)
    cases = protocols.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Manual protocol has no cases[]")
    by_case = {c["case_id"]: c for c in cases}
    if len(by_case) != len(cases):
        raise ValueError("Duplicate manual case")
    seen = set()
    for row in rows:
        for key in ("task_id", "case_id", "step_index", "source_manuscript_sha256",
                    "work_order_ids", "required_operation", "review_status",
                    "source_evidence_uris", "owner_authority", "no_automatic_document_write",
                    "not_a_completed_hunt"):
            if key not in row:
                raise ValueError("Followup missing " + key)
        task_id = row["task_id"]
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", task_id) or task_id in seen:
            raise ValueError("Duplicate or invalid task_id")
        seen.add(task_id)
        if row["case_id"] not in by_case:
            raise ValueError("Followup has no manual case")
        if row["source_manuscript_sha256"] != source_sha:
            raise ValueError("Followup manuscript version drift")
        ids = row["work_order_ids"]
        if not isinstance(ids, list) or len(ids) != len(set(ids)) or any(i not in by_order for i in ids):
            raise ValueError("Unknown or duplicate Z0 work_order_id")
        if any(by_order[i]["source_sha256"] != source_sha for i in ids):
            raise ValueError("Z0 source version drift")
        if not ids and row["case_id"] != "R1-05":
            raise ValueError("Unanchored task outside R1-05")
        if row["no_automatic_document_write"] is not True or row["not_a_completed_hunt"] is not True:
            raise ValueError("Followup cannot authorize a document write or claim a hunt")
        if not isinstance(row["source_evidence_uris"], list):
            raise ValueError("source_evidence_uris must be a list")
    return rows, by_order, by_case


def prepare(audit: Path, queue: Path, followups: Path, protocols: Path, out: Path,
            expected_sha: str | None = None) -> dict:
    rows, orders, cases = _inputs(audit, queue, followups, protocols, expected_sha)
    version = _sha(queue.read_bytes()) + ":" + _sha(followups.read_bytes()) + ":" + _sha(protocols.read_bytes())
    out.mkdir(parents=True, exist_ok=True)
    for row in rows:
        ids = row["work_order_ids"]
        request = {
            "schema": "trm-cite-r1-task-request-v1", "task_id": row["task_id"],
            "case_id": row["case_id"], "step_index": row["step_index"],
            "source_sha256": row["source_manuscript_sha256"],
            "work_order_ids": ids, "kind": "Z0_LINKED" if ids else "AUTHOR_SOURCE_NEED",
            "correlation_id": _sha((version + ":" + row["task_id"]).encode()),
            "required_operation": row["required_operation"],
            "source_hints": sorted({hint for i in ids for hint in orders[i]["source_hints"]}),
            "acquisition_authorized_by_request": False,
        }
        _write_immutable(out / (row["task_id"] + ".request.json"),
                         (json.dumps(request, ensure_ascii=False, sort_keys=True) + "\n").encode())
    manifest = {"schema": "trm-cite-r1-batch-manifest-v1", "tasks": len(rows),
                "cases": len(cases), "distinct_z0_orders": len({i for row in rows for i in row["work_order_ids"]}),
                "author_source_needs": sum(not row["work_order_ids"] for row in rows),
                "queue_sha256": _sha(queue.read_bytes()), "followups_sha256": _sha(followups.read_bytes()),
                "protocols_sha256": _sha(protocols.read_bytes()), "source_sha256": rows[0]["source_manuscript_sha256"] if rows else None}
    _write_immutable(out / "manifest.json", (json.dumps(manifest, sort_keys=True) + "\n").encode())
    return manifest


def blocked(request_dir: Path, out: Path, reason: str = "SOURCE_READER_NOT_AVAILABLE") -> dict:
    manifest = _json(request_dir / "manifest.json")
    requests = sorted(request_dir.glob("*.request.json"))
    if len(requests) != manifest["tasks"]:
        raise ValueError("Incomplete request batch")
    out.mkdir(parents=True, exist_ok=True)
    for path in requests:
        req = _json(path)
        ret = {k: req[k] for k in ("task_id", "case_id", "source_sha256", "work_order_ids", "correlation_id")}
        ret.update({"schema": "trm-cite-r1-task-return-v1", "outcome": "BLOCKED",
                    "reason": reason, "provider": "NONE", "read_depth": "NONE",
                    "access": "NOT_ATTEMPTED", "acquisition_authorized": False,
                    "source_evidence": [], "negative_evidence": [reason], "errors": [reason]})
        _write_immutable(out / (req["task_id"] + ".return.json"),
                         (json.dumps(ret, ensure_ascii=False, sort_keys=True) + "\n").encode())
    return {"returns": len(requests), "outcome": "BLOCKED", "reason": reason}


def consume(audit: Path, queue: Path, followups: Path, protocols: Path,
            request_dir: Path, return_dir: Path, out: Path,
            expected_sha: str | None = None) -> dict:
    rows, orders, cases = _inputs(audit, queue, followups, protocols, expected_sha)
    expected = prepare(audit, queue, followups, protocols, request_dir, expected_sha)
    if _json(request_dir / "manifest.json") != expected:
        raise ValueError("Batch manifest mismatch")
    out.mkdir(parents=True, exist_ok=True)
    for row in rows:
        task = row["task_id"]
        req = _json(request_dir / (task + ".request.json"))
        ret_path = return_dir / (task + ".return.json")
        ret = _json(ret_path)
        if ret.get("schema") != "trm-cite-r1-task-return-v1":
            raise ValueError("Unknown task return schema")
        for key in ("task_id", "case_id", "source_sha256", "work_order_ids", "correlation_id"):
            if ret.get(key) != req[key]:
                raise ValueError("Task return correlation mismatch: " + key)
        if ret.get("outcome") == "OBSERVED":
            if ret.get("acquisition_authorized") is not True or ret.get("provider") in (None, "NONE"):
                raise ValueError("Observed task return lacks authorized provider")
            evidence = ret.get("source_evidence")
            if not isinstance(evidence, list) or not evidence:
                raise ValueError("Observed return lacks source evidence")
            for item in evidence:
                if not isinstance(item, dict):
                    raise ValueError("Evidence item is not an object")
                order_id = item.get("work_order_id")
                if order_id is None and len(req["work_order_ids"]) == 1:
                    order_id = req["work_order_ids"][0]
                if order_id is None and len(req["work_order_ids"]) > 1:
                    raise ValueError("Ambiguous Z0 link in compound evidence")
                if order_id is not None and order_id not in req["work_order_ids"]:
                    raise ValueError("Evidence has wrong Z0 link")
                if item.get("source_sha256", req["source_sha256"]) != req["source_sha256"]:
                    raise ValueError("Evidence source version drift")
                order = orders.get(order_id) if order_id is not None else None
                if item.get("intake_id") is not None and (order is None or item["intake_id"] != order["intake_id"]):
                    raise ValueError("Evidence has wrong original intake")
                if item.get("z0_case_id") is not None and (order is None or item["z0_case_id"] != order["case_id"]):
                    raise ValueError("Evidence has wrong original Z0 case")
                expected_source = {
                    "work_order_id": order_id,
                    "case_id": order["case_id"] if order is not None else None,
                    "intake_id": order["intake_id"] if order is not None else None,
                    "source_sha256": req["source_sha256"],
                    "correlation_id": req["correlation_id"],
                }
                common = {k: ret.get(k) for k in (
                    "provider", "acquisition_authorized", "read_depth",
                    "source_kind", "retrieved_at", "access", "license", "citation_mode"
                )}
                common["citation_mode"] = common.get("citation_mode") or "UNKNOWN"
                probe = {**common, **item, "schema": "trm-cite-r1-return-v1",
                         "outcome": "OBSERVED", **expected_source}
                # Never self-check a generated probe: validate against the real Z0 record.
                _validate_return(expected_source, probe)
        elif (ret.get("outcome") not in ("BLOCKED", "ERROR", "NEGATIVE") or
              not ret.get("reason") or ret.get("read_depth") != "NONE" or
              ret.get("source_evidence")):
            raise ValueError("Invalid negative return")
        manual = cases[req["case_id"]]
        checks = manual.get("checks", {})
        check_keys = sorted(checks) if isinstance(checks, dict) else [str(i) for i in range(len(checks))] if isinstance(checks, list) else []
        state = {"schema": "trm-cite-r1-task-state-v1", "task_id": task,
                 "case_id": req["case_id"], "step_index": req["step_index"],
                 "kind": req["kind"], "work_order_ids": req["work_order_ids"],
                 "source_sha256": req["source_sha256"], "correlation_id": req["correlation_id"],
                 "return_sha256": _sha(ret_path.read_bytes()), "outcome": ret["outcome"],
                 "reason": ret.get("reason"), "read_depth": ret.get("read_depth"),
                 "source_evidence": ret.get("source_evidence", []),
                 "negative_evidence": ret.get("negative_evidence", []),
                 "manual_case_inputs_present": "inputs" in manual,
                 "manual_case_checks_present": "checks" in manual,
                 "manual_source_evidence_present": ("source_evidence" in manual or
                    isinstance(checks, dict) and "source_evidence" in checks),
                 "manual_check_keys": check_keys,
                 "manual_comparison": "UNVERIFIED" if ret["outcome"] == "OBSERVED" else "NO_SOURCE_EVIDENCE",
                 "verification": {k: "NOT_CHECKED" for k in ("V1", "V2", "V3", "V4", "V5")},
                 "citation_gate": "NOT_PUBLICATION_READY", "author_gate": "PENDING",
                 "proposed_patch": None}
        _write_immutable(out / (task + ".state.json"),
                         (json.dumps(state, ensure_ascii=False, sort_keys=True) + "\n").encode())
    result = {"schema": "trm-cite-r1-batch-result-v1", "tasks": len(rows),
              "cases": len(cases), "blocked": sum(_json(out / (r["task_id"] + ".state.json"))["outcome"] == "BLOCKED" for r in rows),
              "observed": sum(_json(out / (r["task_id"] + ".state.json"))["outcome"] == "OBSERVED" for r in rows),
              "publication_ready": 0, "source_sha256": expected["source_sha256"],
              "scientific_status": "NO_EVIDENCE_ALL_BLOCKED" if all(
                  _json(out / (r["task_id"] + ".state.json"))["outcome"] == "BLOCKED" for r in rows
              ) else "AWAITING_INDEPENDENT_SCIENTIFIC_REVIEW",
              "manual_comparison": "STRUCTURAL_ONLY_AUTHOR_REVIEW_REQUIRED"}
    _write_immutable(out / "result.json", (json.dumps(result, sort_keys=True) + "\n").encode())
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare", "blocked", "consume"))
    p.add_argument("--audit", type=Path)
    p.add_argument("--queue", type=Path)
    p.add_argument("--followups", type=Path)
    p.add_argument("--protocols", type=Path)
    p.add_argument("--requests", type=Path, required=True)
    p.add_argument("--returns", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--expected-manuscript-sha256")
    args = p.parse_args(argv)
    if args.mode == "blocked":
        if not args.returns:
            p.error("--returns required")
        result = blocked(args.requests, args.returns)
    else:
        if not all((args.audit, args.queue, args.followups, args.protocols)):
            p.error("--audit, --queue, --followups, --protocols required")
        if args.mode == "prepare":
            result = prepare(args.audit, args.queue, args.followups, args.protocols,
                             args.requests, args.expected_manuscript_sha256)
        else:
            if not args.returns or not args.out:
                p.error("--returns and --out required")
            result = consume(args.audit, args.queue, args.followups, args.protocols,
                             args.requests, args.returns, args.out, args.expected_manuscript_sha256)
    print(json.dumps(result, sort_keys=True))
    # Technical transport can succeed even when zero source witnesses were read.
    # A CLI orchestrator must not interpret complete source loss as scientific success.
    if args.mode == "consume" and result.get("scientific_status") == "NO_EVIDENCE_ALL_BLOCKED":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
