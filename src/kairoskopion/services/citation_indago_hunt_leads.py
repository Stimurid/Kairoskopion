"""Map *real* Indago hunt output to a Z0-bound source-lead queue.

A provider-grounded item in Indago's new_verified[] is NOT a read fulltext,
independent passage witness, or V1--V5 certification.  This transport is a
lead importer upstream of R1; only source-byte attestation may promote a quote.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .citation_r1 import _orders, _validate_inputs

HUNT_STATUSES = {"PASS", "PARTIAL"}
KINDS = (
    ("new_verified", "PROVIDER_GROUNDED_ITEM"),
    ("new_unverified", "UNVERIFIED_ITEM"),
    ("hypotheses", "HYPOTHESIS_ONLY"),
    ("known_rediscovered", "ALREADY_KNOWN"),
)


class HuntLeadImportRefusal(ValueError):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class HuntLeadImport:
    receipt: dict[str, Any]
    leads: list[dict[str, Any]]
    replayed: bool


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise HuntLeadImportRefusal("Cannot read JSON input", "INPUT_UNREADABLE") from exc
    if not isinstance(raw, dict):
        raise HuntLeadImportRefusal("Expected object at root", "INVALID_INPUT_SCHEMA")
    return raw


def import_hunt_leads(
    *, audit_path: Path, queue_path: Path, meta_path: Path, candidates_path: Path,
    work_order_id: str, expected_task_id: str, output_dir: Path,
) -> HuntLeadImport:
    audit, meta, candidates = (_read(p) for p in
                               (audit_path, meta_path, candidates_path))
    try:
        orders = _orders(queue_path)
        _validate_inputs(audit, orders)
    except (KeyError, ValueError) as exc:
        raise HuntLeadImportRefusal("Z0 work orders invalid", "INVALID_Z0_BINDING") from exc
    order = next((x for x in orders if x.get("work_order_id") == work_order_id), None)
    if order is None:
        raise HuntLeadImportRefusal("Requested work order not in immutable Z0",
                                    "WORK_ORDER_NOT_FOUND")
    if not expected_task_id.strip() or meta.get("task_id") != expected_task_id:
        raise HuntLeadImportRefusal("Hunt task is not the intended request",
                                    "TASK_SCOPE_MISMATCH")
    hid = meta.get("hunt_id")
    if (not isinstance(hid, str) or not hid.startswith("h-")
            or candidates.get("hunt_id") != hid):
        raise HuntLeadImportRefusal("Hunt identities differ",
                                    "HUNT_IDENTITY_MISMATCH")
    if meta.get("status") not in HUNT_STATUSES or not meta.get("finished_at"):
        raise HuntLeadImportRefusal("Hunt not finished with usable evidence",
                                    "HUNT_NOT_COMPLETE")
    for key, _ in KINDS:
        if not isinstance(candidates.get(key, []), list):
            raise HuntLeadImportRefusal("Bad candidates bucket: " + key,
                                        "INVALID_CANDIDATES")
    for key in ("not_found", "unexecuted_provider_requests"):
        if not isinstance(candidates.get(key, []), list):
            raise HuntLeadImportRefusal("Bad negative/unexecuted queue",
                                        "INVALID_CANDIDATES")
    meta_sha = _sha(meta_path.read_bytes())
    candidates_sha = _sha(candidates_path.read_bytes())
    import_id = "import:" + _sha(_canonical({
        "hunt_id": hid, "task_id": expected_task_id, "meta_sha": meta_sha,
        "candidates_sha": candidates_sha,
        "case_id": order["case_id"], "work_order_id": order["work_order_id"],
        "manuscript_sha256": order["source_sha256"],
    }))
    out: list[dict[str, Any]] = []
    seen_normalized: dict[str, str] = {}
    counts: dict[str, int] = {}
    for bucket, classification in KINDS:
        entries = candidates.get(bucket, [])
        counts[bucket] = len(entries)
        for ordinal, item in enumerate(entries):
            if not isinstance(item, dict):
                raise HuntLeadImportRefusal("Candidate item must be an object",
                                            "INVALID_CANDIDATES")
            title = item.get("title")
            url = item.get("url")
            identifiers = item.get("identifiers") or []
            if not isinstance(title, str) or not title.strip():
                raise HuntLeadImportRefusal("Candidate title absent",
                                            "INVALID_CANDIDATES")
            if url is not None and not isinstance(url, str):
                raise HuntLeadImportRefusal("Candidate URL not text",
                                            "INVALID_CANDIDATES")
            if not isinstance(identifiers, list) or not all(
                isinstance(x, str) for x in identifiers
            ):
                raise HuntLeadImportRefusal("Bad identifiers", "INVALID_CANDIDATES")
            key = next((x.lower() for x in identifiers if x.lower().startswith("doi:")),
                       (url or title).strip().lower())
            # Duplicate records are retained with an explicit pointer.
            lead_id = "lead:" + _sha(_canonical({
                "import_id": import_id, "bucket": bucket,
                "ordinal": ordinal, "key": key,
            }))
            duplicate_of = seen_normalized.get(key)
            if not duplicate_of:
                seen_normalized[key] = lead_id
            out.append({
                "schema": "trm-cite-indago-hunt-lead-v1",
                "lead_id": lead_id, "import_id": import_id,
                "z0_case_id": order["case_id"],
                "work_order_id": order["work_order_id"],
                "intake_id": order["intake_id"],
                "manuscript_sha256": order["source_sha256"],
                "hunt_id": hid, "task_id": expected_task_id,
                "provider_bucket": bucket, "provider_classification": classification,
                "candidate_title": title, "candidate_url": url,
                "candidate_identifiers": identifiers,
                "why_relevant_reported": item.get("why_relevant"),
                "provider_evidence_ids": item.get("evidence_ids") or [],
                "provider_provenance": item.get("provenance"),
                "provider_hypothesis": item.get("is_hypothesis", bucket == "hypotheses"),
                "duplicate_of": duplicate_of,
                "read_depth": "PROVIDER_ITEM_NOT_FULLTEXT",
                "work_identity_verified": False,
                "edition_identity_verified": False,
                "source_bytes_attested": False,
                "source_evidence": [],
                "passage_verified": False,
                "V1_V5": ["NOT_CHECKED"] * 5,
                "scientific_certification": False,
                "publication_ready": False,
                "next_action": ("VERIFY_BIBLIOGRAPHIC_IDENTITY" if
                                bucket == "hypotheses" else
                                "CHECK_OWNER_LIBRARY_THEN_EXACT_WORK_FULLTEXT"),
            })
    receipt = {
        "schema": "trm-cite-indago-hunt-import-receipt-v1",
        "import_id": import_id, "hunt_id": hid, "task_id": expected_task_id,
        "hunt_status": meta["status"], "case_id": order["case_id"],
        "work_order_id": work_order_id,
        "source_hunt_meta_sha256": meta_sha,
        "source_hunt_candidates_sha256": candidates_sha,
        "lead_count": len(out), "bucket_counts": counts,
        "not_found": candidates.get("not_found", []),
        "unexecuted_provider_requests": candidates.get(
            "unexecuted_provider_requests", []),
        "all_source_leads_are_metadata_only": True,
        "original_manuscript_mutated": False,
        "new_verified_means_provider_item_not_scientific_citation": True,
        "R1_bytes_attested": False,
        "fulltext_handoff_required": True,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    rp = output_dir / "hunt_import_receipt.json"
    qp = output_dir / "hunt_leads.jsonl"
    if rp.exists():
        prev = _read(rp)
        if prev.get("import_id") != import_id:
            raise HuntLeadImportRefusal("Existing queue belongs to another hunt",
                                        "IMPORT_CONFLICT")
        if not qp.exists() or _sha(qp.read_bytes()) != prev.get("lead_queue_sha256"):
            raise HuntLeadImportRefusal("Existing queue bytes drift",
                                        "IMPORT_LEDGER_DRIFT")
        return HuntLeadImport(dict(prev, replay_status="IDEMPOTENT_REPLAY"),
                              out, True)
    if qp.exists():
        raise HuntLeadImportRefusal("Partial existing queue needs review",
                                    "PARTIAL_IMPORT_REVIEW_REQUIRED")
    body = b"".join(_canonical(lead) + b"\n" for lead in out)
    receipt["lead_queue_sha256"] = _sha(body)
    with qp.open("xb") as f:
        f.write(body)
    with rp.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(receipt, f, sort_keys=True, ensure_ascii=False, indent=2)
        f.write("\n")
    return HuntLeadImport(receipt, out, False)


def main() -> int:
    ap = argparse.ArgumentParser(description="Indago hunt evidence -> Z0 lead queue")
    for key in ("audit", "queue", "meta", "candidates", "output"):
        ap.add_argument("--" + key, type=Path, required=True)
    for key in ("work-order-id", "task-id"):
        ap.add_argument("--" + key, required=True)
    arg = ap.parse_args()
    try:
        result = import_hunt_leads(
            audit_path=arg.audit, queue_path=arg.queue, meta_path=arg.meta,
            candidates_path=arg.candidates, work_order_id=arg.work_order_id,
            expected_task_id=arg.task_id, output_dir=arg.output)
    except HuntLeadImportRefusal as exc:
        print(json.dumps({"status": "REFUSED", "code": exc.code, "reason": str(exc)}))
        return 2
    print(json.dumps(result.receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
