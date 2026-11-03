"""Verify existing native indago-port hunt bytes before scientific handoff.

A port hunt is NOT a vetted scientific finding: even successful native provider
metadata remains a scoped research return requiring Artikl D15/D24/D25.
This adapter imports receipts ONLY; it neither spawns research nor changes Indago.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .publication_runner import EvidenceBlocked, atomic_write, sha256

SCHEMA = "trimurti-indago-native-evidence-intake-v1"
REQUIRED_AUTHORITY = (
    "tasks_and_trails", "living_current", "source_ledger",
    "candidate_queue", "hunt_ledger",
)
MAX_RECEIPT_BYTES = 16_000_000


def read_json(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > MAX_RECEIPT_BYTES:
        raise EvidenceBlocked("native_receipt_missing_or_oversized:" + path.name)
    try:
        j = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError) as e:
        raise EvidenceBlocked("native_receipt_invalid_json:" + path.name) from e
    if not isinstance(j, dict):
        raise EvidenceBlocked("native_receipt_not_object:" + path.name)
    return j


def _valid_pin(value: str) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[a-f0-9]{64}", value))


def import_hunt(*, hunts_root: Path, hunt_dir: Path, output_root: Path,
                expected_task: str, trusted_original_sha: str,
                trusted_manuscript_sha: str, trusted_review_sha: str) -> dict:
    """Strong mechanical readback, no semantic novelty or publication authority."""
    for name, pin in (("original", trusted_original_sha),
                      ("manuscript", trusted_manuscript_sha),
                      ("review", trusted_review_sha)):
        if not _valid_pin(pin):
            raise EvidenceBlocked("invalid_external_science_sha_" + name)
    root = hunts_root.resolve(strict=True)
    work = hunt_dir.resolve(strict=True)
    if work.parent != root or not work.name.startswith("h-"):
        raise EvidenceBlocked("native_hunt_dir_outside_trusted_root")
    if not expected_task.startswith("TRIMURTI_"):
        raise EvidenceBlocked("non_trimurti_task")
    m = read_json(work / "meta.json")
    if m.get("task_id") != expected_task or m.get("hunt_id") != work.name:
        raise EvidenceBlocked("native_hunt_identity_mismatch")
    if m.get("agent_id") != "indago":
        raise EvidenceBlocked("native_agent_identity_mismatch")
    status = m.get("status")
    if status not in {"PASS", "PARTIAL", "BLOCKED"}:
        raise EvidenceBlocked("native_hunt_not_finalized")
    a = read_json(work / "authority_fingerprints.json")
    if a.get("hunt_id") != work.name:
        raise EvidenceBlocked("authority_hunt_mismatch")
    auth = a.get("authorities") or {}
    auth_ok = all(
        isinstance(auth.get(k), dict) and auth[k].get("source") == "LIVE"
        and auth[k].get("currentness") == "LIVE_VERIFIED"
        and _valid_pin(auth[k].get("sha256"))
        for k in REQUIRED_AUTHORITY
    )
    if not auth_ok:
        raise EvidenceBlocked("native_authorities_not_live_verified")
    if not (work / "result.md").is_file():
        raise EvidenceBlocked("native_result_file_missing")
    final_text = (work / "result.md").read_text(encoding="utf-8")
    if f"Indago hunt {work.name}" not in final_text or (
        f"status: **{status}**" not in final_text):
        raise EvidenceBlocked("native_result_status_or_id_mismatch")
    trace_path = work / "trace.jsonl"
    if not trace_path.is_file() or trace_path.stat().st_size > MAX_RECEIPT_BYTES:
        raise EvidenceBlocked("native_trace_missing_or_oversized")
    try:
        trace = [json.loads(x) for x in trace_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    except ValueError as e:
        raise EvidenceBlocked("invalid_native_trace_jsonl") from e
    if not trace or trace[-1].get("event") != "HUNT_END" or (
        trace[-1].get("hunt_id") != work.name) or (
        trace[-1].get("status") != status):
        raise EvidenceBlocked("native_trace_not_finalized_or_status_mismatch")
    counts = m.get("counts") or {}
    n = counts.get("waves_run")
    if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 128:
        raise EvidenceBlocked("invalid_native_wave_count")
    session_ids = m.get("session_ids") or []
    if len(session_ids) != n or len(set(session_ids)) != n:
        raise EvidenceBlocked("native_sessions_not_unique_or_missing")
    if any(not x.startswith("indago-" + work.name + "-w") for x in session_ids):
        raise EvidenceBlocked("native_session_identity_mismatch")
    files = ["meta.json", "result.md", "trace.jsonl", "authority_fingerprints.json",
             "candidates.json"]
    evidence_calls = 0
    parsed_waves = 0
    for k in range(1, n + 1):
        wave_file = f"wave-{k}.json"
        evidence_file = f"wave-{k}.evidence.json"
        files += [wave_file, evidence_file, f"wave-{k}.raw.json"]
        w = read_json(work / wave_file)
        if w.get("row", {}).get("wave") != k:
            raise EvidenceBlocked("native_wave_number_mismatch")
        parsed_waves += int(w["row"].get("parse_ok") is True)
        b = work / evidence_file
        if not b.is_file() or b.stat().st_size > MAX_RECEIPT_BYTES:
            raise EvidenceBlocked("native_evidence_missing_or_oversized")
        try:
            blocks = json.loads(b.read_text(encoding="utf-8"))
        except ValueError as e:
            raise EvidenceBlocked("invalid_native_provider_evidence") from e
        if not isinstance(blocks, list):
            raise EvidenceBlocked("native_provider_evidence_not_list")
        evidence_calls += len(blocks)
    if counts.get("waves_ok") != parsed_waves or counts.get("provider_calls") != evidence_calls:
        raise EvidenceBlocked("native_count_not_byte_consistent")
    candidate = read_json(work / "candidates.json")
    if candidate.get("hunt_id") != work.name:
        raise EvidenceBlocked("native_candidate_hunt_mismatch")
    for count, key in (("new_verified", "new_verified"), ("new_unverified", "new_unverified"),
                       ("hypotheses", "hypotheses"), ("known_rediscovered", "known_rediscovered")):
        if not isinstance(candidate.get(key), list) or len(candidate[key]) != counts.get(count):
            raise EvidenceBlocked("native_candidate_count_mismatch:" + key)
    hashes = {}
    for name in files:
        p = work / name
        if not p.is_file() or p.stat().st_size > MAX_RECEIPT_BYTES:
            raise EvidenceBlocked("native_file_missing_or_oversized:" + name)
        hashes[name] = {"sha256": sha256(p.read_bytes()), "bytes": p.stat().st_size}
    research_status = ("SCOPED_NATIVE_EVIDENCE_REQUIRES_SCIENTIFIC_REVIEW"
                       if status in {"PASS", "PARTIAL"} and parsed_waves and evidence_calls
                       else "NATIVE_HUNT_NO_ADMISSIBLE_SCIENCE_RETURN")
    receipt = {
        "schema": SCHEMA, "task_id": expected_task, "native_hunt_id": work.name,
        "native_status": status, "research_status": research_status,
        "original_sha256": trusted_original_sha,
        "manuscript_sha256": trusted_manuscript_sha,
        "previous_review_sha256": trusted_review_sha,
        "agent": "indago", "authority": {k:auth[k]["sha256"] for k in REQUIRED_AUTHORITY},
        "counts": counts, "degradations": m.get("degradations") or [],
        "reason_codes": m.get("reason_codes") or [],
        "private_artifact_dir": str(work),
        "file_digests": hashes,
        "evidence_depth": "NATIVE_PROVIDER_RETURNS_NOT_INDEPENDENT_FULL_PRIMARY_READ",
        "novelty_accepted": False, "article_seed_accepted": False,
        "author_gate": "HOLD", "manuscript_go": False, "send": False,
        "new_w12_routes": 0, "world_mutation": False,
        "next": "ARTIKL_D15_D24_SCIENTIFIC_CROSSCHECK_OR_NATIVE_RETRY",
    }
    output_root.mkdir(parents=True,exist_ok=True)
    out=output_root/("indago-intake-" + work.name + ".json")
    content=(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
    if out.exists() and out.read_bytes()!=content:
        raise EvidenceBlocked("native_evidence_intake_changed_after_write")
    if not out.exists():
        atomic_write(out,content)
    return receipt


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--hunts-root",required=True,type=Path)
    ap.add_argument("--hunt-dir",required=True,type=Path)
    ap.add_argument("--output-root",required=True,type=Path)
    ap.add_argument("--expected-task",required=True)
    ap.add_argument("--trusted-original-sha",required=True)
    ap.add_argument("--trusted-manuscript-sha",required=True)
    ap.add_argument("--trusted-review-sha",required=True)
    args=ap.parse_args()
    try:
        r=import_hunt(hunts_root=args.hunts_root,hunt_dir=args.hunt_dir,
          output_root=args.output_root,expected_task=args.expected_task,
          trusted_original_sha=args.trusted_original_sha,
          trusted_manuscript_sha=args.trusted_manuscript_sha,
          trusted_review_sha=args.trusted_review_sha)
    except (EvidenceBlocked,OSError) as e:
        print(json.dumps({"status":"BLOCKED_EVIDENCE_INTAKE","reason":str(e)}))
        return 2
    print(json.dumps(r,ensure_ascii=False))
    return 0 if r["research_status"]=="SCOPED_NATIVE_EVIDENCE_REQUIRES_SCIENTIFIC_REVIEW" else 10


if __name__=="__main__":
    raise SystemExit(main())
