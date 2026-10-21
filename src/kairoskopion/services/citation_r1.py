"""R1 file transport: a bounded evidence return and deterministic case consumer.

This module never fetches sources. A separately authorized reader may return a
small, source-anchored receipt. The consumer records proposals, not certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .citation_intake_z0 import _write_immutable

DEPTHS = {"SEARCH_RESULT", "PUBLISHER_ABSTRACT", "SECTION_TEXT",
          "ANCHORED_PASSAGE", "FULL_BOOK", "NONE"}
OUTCOMES = {"OBSERVED", "BLOCKED", "ERROR", "NEGATIVE"}
MODES = {"PARAPHRASE", "QUOTE", "UNKNOWN"}


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Expected JSON object")
    return value


def _orders(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    orders = [json.loads(line) for line in lines if line.strip()]
    ids = [o["work_order_id"] for o in orders]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate work_order_id")
    return orders


def _validate_inputs(audit: dict, orders: list[dict]) -> None:
    cases = {c["case_id"]: c for c in audit["repair_cases"]}
    intakes = {i["intake_id"]: i for i in audit["intakes"]}
    sha = audit["source"]["sha256"]
    for o in orders:
        c = cases.get(o["case_id"])
        i = intakes.get(o["intake_id"])
        if not c or not i or c["intake_id"] != i["intake_id"]:
            raise ValueError("Work order is not in original audit")
        if (o["source_sha256"] != sha or i["source_sha256"] != sha or
                o["original_fragment"] != i["original_fragment"] or
                o["manuscript_anchor"] != i["anchor"] or
                o["group_id"] != i["group_id"] or
                o["verification"] != c["verification"]):
            raise ValueError("Stale or altered work order")
        if o["external_search_authorized_by_this_file"] is not False:
            raise ValueError("Queue cannot grant source access")


def request_for(order: dict, queue_sha256: str) -> dict:
    """Minimal envelope; never carries manuscript context or snapshot path."""
    correlation = _digest((queue_sha256 + ":" + order["work_order_id"]).encode())
    return {
        "schema": "trm-cite-r1-request-v1", "work_order_id": order["work_order_id"],
        "case_id": order["case_id"], "intake_id": order["intake_id"],
        "source_sha256": order["source_sha256"],
        "correlation_id": correlation, "source_hints": order["source_hints"],
        "acquisition_authorized_by_request": False,
    }


def prepare(audit_path: Path, queue_path: Path, out: Path) -> dict:
    audit, orders = _json(audit_path), _orders(queue_path)
    _validate_inputs(audit, orders)
    queue_sha = _digest(queue_path.read_bytes())
    out.mkdir(parents=True, exist_ok=True)
    count = 0
    for order in orders:
        request = request_for(order, queue_sha)
        payload = (json.dumps(request, sort_keys=True, ensure_ascii=False) + "\n").encode()
        _write_immutable(out / (order["work_order_id"] + ".request.json"), payload)
        count += 1
    return {"orders": count, "queue_sha256": queue_sha, "request_dir": str(out)}


def blocked_return(request: dict, reason: str) -> dict:
    """Honest local canary when no authorized provider interface is available."""
    return {
        "schema": "trm-cite-r1-return-v1", "work_order_id": request["work_order_id"],
        "case_id": request["case_id"], "intake_id": request["intake_id"],
        "source_sha256": request["source_sha256"],
        "correlation_id": request["correlation_id"], "provider": "NONE",
        "outcome": "BLOCKED", "reason": reason, "source_kind": "NONE",
        "read_depth": "NONE", "retrieved_at": None, "access": "NOT_ATTEMPTED",
        "license": "UNKNOWN", "work_id": None, "edition_id": None,
        "witness_id": None, "passage_id": None, "byte_sha256": None,
        "locator": None, "negative_evidence": [], "errors": [reason],
        "source_author_claim": None, "article_author_claim": None,
        "citation_mode": "UNKNOWN",
        "acquisition_authorized": False,
    }


def _validate_return(request: dict, ret: dict) -> None:
    for key in ("work_order_id", "case_id", "intake_id", "source_sha256",
                "correlation_id"):
        if ret.get(key) != request[key]:
            raise ValueError("Return correlation mismatch: " + key)
    if ret.get("schema") != "trm-cite-r1-return-v1":
        raise ValueError("Unknown return schema")
    if ret.get("outcome") not in OUTCOMES or ret.get("read_depth") not in DEPTHS:
        raise ValueError("Invalid outcome or read depth")
    if ret.get("citation_mode", "UNKNOWN") not in MODES:
        raise ValueError("Invalid citation mode")
    if ret["outcome"] == "OBSERVED":
        if not ret.get("acquisition_authorized") or not ret.get("provider") or ret["provider"] == "NONE":
            raise ValueError("Observed source lacks authorized provider")
        for key in ("source_kind", "retrieved_at", "access", "license", "work_id",
                    "edition_id", "witness_id", "locator"):
            if not ret.get(key):
                raise ValueError("Observed source lacks " + key)
        dt = datetime.fromisoformat(ret["retrieved_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if (not dt.tzinfo or dt.astimezone(timezone.utc) > now or
                dt.astimezone(timezone.utc) < now - timedelta(days=30)):
            raise ValueError("Invalid retrieval time")
        if ret["read_depth"] == "NONE":
            raise ValueError("Observed source has no read depth")
        if ret["read_depth"] in {"ANCHORED_PASSAGE", "FULL_BOOK"}:
            digest = ret.get("byte_sha256")
            if (not ret.get("passage_id") or not isinstance(digest, str) or
                    len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower())):
                raise ValueError("Passage lacks identity or byte digest")
    elif ret.get("read_depth") != "NONE" and ret["outcome"] in {"BLOCKED", "ERROR"}:
        raise ValueError("Blocked return cannot claim read depth")
    if ret["outcome"] != "OBSERVED" and not (ret.get("reason") or ret.get("errors")):
        raise ValueError("Non-observation lacks reason")


def consume(audit_path: Path, queue_path: Path, request_path: Path,
            return_path: Path, out: Path) -> dict:
    audit, orders = _json(audit_path), _orders(queue_path)
    _validate_inputs(audit, orders)
    queue_sha = _digest(queue_path.read_bytes())
    req = _json(request_path)
    order = next((o for o in orders if o["work_order_id"] == req.get("work_order_id")), None)
    if not order or req != request_for(order, queue_sha):
        raise ValueError("Request is stale or spoofed")
    ret = _json(return_path)
    _validate_return(req, ret)
    case = next(c for c in audit["repair_cases"] if c["case_id"] == order["case_id"])
    # The machine records what it read. Scientific support and author approval
    # require independent review even when a precise passage is returned.
    verification = dict(case["verification"])
    if ret.get("citation_mode") == "PARAPHRASE":
        verification["V2"] = "N/A_PARAPHRASE"
    if ret["outcome"] == "OBSERVED":
        verification["V1"] = "EVIDENCE_PROPOSED" if ret["read_depth"] in {
            "ANCHORED_PASSAGE", "FULL_BOOK"} else "IDENTITY_ONLY_PROPOSED"
    state = {
        "schema": "trm-cite-r1-case-state-v1", "case_id": case["case_id"],
        "work_order_id": order["work_order_id"], "correlation_id": req["correlation_id"],
        "original_source_sha256": order["source_sha256"],
        "return_sha256": _digest(return_path.read_bytes()),
        "outcome": ret["outcome"], "verification": verification,
        "source_identity": {k: ret.get(k) for k in
                            ("source_kind", "read_depth", "work_id", "edition_id",
                             "witness_id", "passage_id", "byte_sha256", "locator")},
        "retrieved_at": ret.get("retrieved_at"), "provider": ret.get("provider"),
        "access": ret.get("access"), "license": ret.get("license"),
        "source_author_claim": ret.get("source_author_claim"),
        "article_author_claim": ret.get("article_author_claim"),
        "negative_evidence": ret.get("negative_evidence", []),
        "errors": ret.get("errors", []),
        "citation_gate": "NOT_PUBLICATION_READY", "author_gate": case["author_gate"],
        "proposed_patch": None,
    }
    out.mkdir(parents=True, exist_ok=True)
    stem = order["work_order_id"]
    _write_immutable(out / (stem + ".return.json"), return_path.read_bytes())
    _write_immutable(out / (stem + ".state.json"),
                     (json.dumps(state, sort_keys=True, ensure_ascii=False) + "\n").encode())
    return state


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Local R1 source-evidence return consumer")
    p.add_argument("mode", choices=["prepare", "blocked-canary", "consume"])
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--queue", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--request", type=Path)
    p.add_argument("--return-file", type=Path)
    args = p.parse_args(argv)
    if args.mode == "prepare":
        result = prepare(args.audit, args.queue, args.out)
    elif args.mode == "blocked-canary":
        if not args.request:
            p.error("--request required")
        request = _json(args.request)
        result = blocked_return(request, "AUTHORIZED_PROVIDER_INTERFACE_NOT_EXPOSED")
        args.out.mkdir(parents=True, exist_ok=True)
        _write_immutable(args.out / (request["work_order_id"] + ".blocked.json"),
                         (json.dumps(result, sort_keys=True) + "\n").encode())
    else:
        if not args.request or not args.return_file:
            p.error("--request and --return-file required")
        result = consume(args.audit, args.queue, args.request, args.return_file, args.out)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
