"""Artikl citation workflow reusing existing Z0, Indago R3 and R2-R4.

This is a *consumer* of recorded evidence, not a live Indago provider.
No witness bytes means NO anchored passage. No machine scientific PASS.
R5/R6 remain separate explicit author-gated operations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .citation_intake_z0 import persist_audit
from .citation_indago_r3_bridge import IndagoBridgeRefusal, consume_and_plan


def run_citation_workflow(
    manuscript: Path,
    output_dir: Path,
    *,
    evidence_return: Path | None = None,
    witness_path: Path | None = None,
) -> dict:
    """One stable entry: Z0 intake, optionally R3 return and R2-R4 plan.

    Caller/Indago owns search execution. A provided return must carry its
    provenance; supplying a JSON file does NOT prove a live provider call.
    """
    manuscript = Path(manuscript)
    output_dir = Path(output_dir)
    original_sha = hashlib.sha256(manuscript.read_bytes()).hexdigest()
    audit, audit_path = persist_audit(manuscript, output_dir / "intake")
    queue_path = audit_path.with_name("citation_work_orders.jsonl")
    if audit.source["sha256"] != original_sha:
        raise RuntimeError("Input manuscript changed during Z0 capture")
    result = {
        "schema": "trm-cite-artikl-entry-v1",
        "manuscript_sha256": original_sha,
        "audit_file": str(audit_path),
        "work_orders_file": str(queue_path),
        "work_orders": sum(1 for _ in queue_path.open(encoding="utf-8-sig")),
        "citation_gate": "NOT_PUBLICATION_READY",
        "source_to_claim_relation": "NOT_CHECKED",
        "verification": {f"V{i}": "NOT_CHECKED" for i in range(1, 6)},
        "scientific_certification": False,
        "author_gate": "PENDING",
        "original_manuscript_mutated": False,
        "provider_execution": "NOT_DEMONSTRATED",
    }
    if evidence_return is None:
        result.update(status="AWAITING_INDAGO_EVIDENCE_RETURN")
        return result
    if not Path(evidence_return).is_file():
        raise ValueError("EvidenceReturn path is not a file")
    result_bundle = consume_and_plan(
        audit_path, queue_path, Path(evidence_return),
        output_dir / "r3_ledger", output_dir / "r2_r4_plan",
        manuscript, witness_path=Path(witness_path) if witness_path else None,
    )
    bridge = result_bundle["bridge_receipt"]
    result.update(
        status="EVIDENCE_CONSUMED_PLAN_CREATED",
        bridge_receipt=bridge,
        witness_status=bridge.get("witness_attestation", {}).get("status", "NOT_CHECKED"),
        r2_r4_plan=result_bundle["r2_r4_plan"],
    )
    # Never promote a discovered passage to V4/V5 or author consent.
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manuscript", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--evidence-return", type=Path)
    p.add_argument("--witness-path", type=Path)
    args = p.parse_args(argv)
    try:
        result = run_citation_workflow(args.manuscript, args.output_dir,
                                       evidence_return=args.evidence_return,
                                       witness_path=args.witness_path)
    except (IndagoBridgeRefusal, OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "REFUSED", "error": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    # An intake-only pass is successful transport, not scientific acceptance.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
