"""Typed Indago EvidenceReturn -> R1 case-state bridge.

This is a local consumer, not a provider client.  It accepts recorded returns
only after binding them to an immutable Z0 audit and work order.  Transport,
metadata, and DOI identity never certify scientific support (V1--V5).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .citation_indago_witness_check import WitnessRefusal, attest_passages
from .citation_r1 import _orders, _validate_inputs
from .citation_repair_r2_r6 import load_prior_states, plan_repair

EVIDENCE_RETURN_SCHEMA = "trm-indago-evidence-return-v1"
STATE_SCHEMA = "trm-cite-r1-case-state-v1"
RECEIPT_SCHEMA = "trm-cite-r3-indago-bridge-receipt-v1"
OUTCOMES = {"MATCHED", "NO_PASSAGE", "NEGATIVE_HUNT", "PROVIDER_FAILURE"}


class IndagoBridgeRefusal(ValueError):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IndagoBridgeRefusal(f"Unreadable JSON: {path}", "INVALID_JSON") from exc
    if not isinstance(value, dict):
        raise IndagoBridgeRefusal("EvidenceReturn must be an object", "INVALID_SCHEMA")
    return value


def _required_str(obj: dict[str, Any], key: str, owner: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise IndagoBridgeRefusal(f"{owner} lacks {key}", "INVALID_SCHEMA")
    return value


def _is_sha(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value.lower()))


def _load_bound(audit_path: Path, queue_path: Path,
                evidence: dict[str, Any]) -> tuple[dict, dict, dict]:
    audit = _read_object(audit_path)
    try:
        orders = _orders(queue_path)
        _validate_inputs(audit, orders)
    except (KeyError, ValueError) as exc:
        raise IndagoBridgeRefusal(str(exc), "INVALID_Z0_BINDING") from exc
    if evidence.get("schema") != EVIDENCE_RETURN_SCHEMA:
        raise IndagoBridgeRefusal("Unknown EvidenceReturn schema", "UNKNOWN_SCHEMA")
    for key in ("return_id", "case_id", "work_order_id", "intake_id",
                "manuscript_sha256", "provider", "recorded_at"):
        _required_str(evidence, key, "EvidenceReturn")
    order = next((o for o in orders
                  if o.get("work_order_id") == evidence["work_order_id"]), None)
    if order is None:
        raise IndagoBridgeRefusal("Orphan work order", "ORPHAN_WORK_ORDER")
    expected = {
        "case_id": order["case_id"], "intake_id": order["intake_id"],
        "manuscript_sha256": order["source_sha256"],
    }
    for key, value in expected.items():
        if evidence.get(key) != value:
            raise IndagoBridgeRefusal(f"Stale or wrong-case binding: {key}",
                                      "WRONG_CASE_OR_STALE")
    case = next((c for c in audit["repair_cases"]
                 if c["case_id"] == evidence["case_id"]), None)
    if case is None or case.get("intake_id") != evidence["intake_id"]:
        raise IndagoBridgeRefusal("Case/intake binding failed", "WRONG_CASE_OR_STALE")
    return audit, order, case


def _source(evidence: dict[str, Any]) -> dict[str, Any]:
    source = evidence.get("source")
    if not isinstance(source, dict):
        raise IndagoBridgeRefusal("EvidenceReturn lacks source", "INVALID_SCHEMA")
    for key in ("work_id", "edition_id", "witness_id", "source_sha256",
                "source_kind", "access_origin"):
        _required_str(source, key, "source")
    if not _is_sha(source["source_sha256"]):
        raise IndagoBridgeRefusal("Invalid source_sha256", "INVALID_SOURCE_IDENTITY")
    # Owner PDFs and archives are ordinary inputs; access_origin is descriptive.
    return source


def _passages(evidence: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    passages = evidence.get("passages")
    if not isinstance(passages, list):
        raise IndagoBridgeRefusal("passages must be a list", "INVALID_SCHEMA")
    valid: list[dict[str, Any]] = []
    for item in passages:
        if not isinstance(item, dict):
            raise IndagoBridgeRefusal("Passage must be an object", "INVALID_SCHEMA")
        for key in ("passage_id", "work_id", "edition_id", "witness_id",
                    "locator", "text_sha256"):
            _required_str(item, key, "passage")
        if any(item[key] != source[key]
               for key in ("work_id", "edition_id", "witness_id")):
            raise IndagoBridgeRefusal("Cross-source passage anchor",
                                      "CROSS_SOURCE_PASSAGE_ANCHOR")
        if not item["passage_id"].startswith("passage:") or not _is_sha(item["text_sha256"]):
            raise IndagoBridgeRefusal("Invalid passage identity", "FAKE_PASSAGE")
        if item.get("locator_present") is not True:
            raise IndagoBridgeRefusal("Passage locator is not attested", "FAKE_PASSAGE")
        occurrences = item.get("passage_occurrences")
        if not isinstance(occurrences, int) or isinstance(occurrences, bool) or occurrences < 1:
            raise IndagoBridgeRefusal("Invalid passage occurrence count", "FAKE_PASSAGE")
        exact = item.get("exact_text")
        if exact is not None and (
            not isinstance(exact, str)
            or hashlib.sha256(exact.encode()).hexdigest()
            != item["text_sha256"].lower()
        ):
            raise IndagoBridgeRefusal("Passage text digest mismatch", "FAKE_PASSAGE")
        valid.append(item)
    return valid


@dataclass(frozen=True)
class BridgeResult:
    receipt: dict[str, Any]
    state: dict[str, Any]
    replayed: bool


def consume_evidence_return(audit_path: Path, queue_path: Path,
                            evidence: dict[str, Any], ledger_dir: Path,
                            *, witness_path: Path | None = None) -> BridgeResult:
    """Bind a return to Z0, then independently attest *actual witness bytes*.

    Without operator-provided witness bytes a provider-returned quote is merely
    a CANDIDATE, never real R1 anchored evidence or a reason to skip Indago.
    """
    _, order, case = _load_bound(audit_path, queue_path, evidence)
    outcome = evidence.get("outcome")
    if outcome not in OUTCOMES:
        raise IndagoBridgeRefusal("Invalid outcome", "INVALID_SCHEMA")
    source = _source(evidence)
    passages = _passages(evidence, source)
    negatives = evidence.get("negative_evidence", [])
    errors = evidence.get("errors", [])
    if (not isinstance(negatives, list) or not all(isinstance(x, str) for x in negatives)
            or not isinstance(errors, list) or not all(isinstance(x, str) for x in errors)):
        raise IndagoBridgeRefusal("Invalid negative evidence/errors", "INVALID_SCHEMA")
    if outcome == "MATCHED" and not passages:
        raise IndagoBridgeRefusal("MATCHED return has no passage", "NO_PASSAGE")
    if outcome != "MATCHED" and passages:
        raise IndagoBridgeRefusal("Non-match return contains passages", "OUTCOME_CONTRADICTION")
    if outcome in {"NEGATIVE_HUNT", "PROVIDER_FAILURE"} and not (negatives or errors):
        raise IndagoBridgeRefusal("Negative/failure lacks evidence", "INVALID_SCHEMA")

    attestation: dict[str, Any] = {
        "status": "NOT_APPLICABLE", "bytes_verified": False,
        "locator_verified": False, "uniqueness_verified": False,
    }
    if outcome == "MATCHED":
        try:
            attestation = attest_passages(source, passages, witness_path)
        except WitnessRefusal as exc:
            raise IndagoBridgeRefusal(str(exc), exc.code) from exc
    unique = [p for p in passages if p["passage_occurrences"] == 1]
    if outcome == "MATCHED":
        if len(passages) != 1 or not unique or attestation["status"] == "ANCHOR_AMBIGUOUS":
            bridge_status, r1_outcome = "ANCHOR_AMBIGUOUS", "NEGATIVE"
        elif attestation["status"] == "VERIFIED_UNIQUE":
            bridge_status, r1_outcome = "ANCHORED", "OBSERVED"
        else:
            # The provider can claim a locator, hash and unique passage.
            # None is scientific evidence until our own local file confirms it.
            bridge_status, r1_outcome = "WITNESS_UNVERIFIED", "UNVERIFIED"
    elif outcome == "PROVIDER_FAILURE":
        bridge_status, r1_outcome = "PROVIDER_FAILURE_RECORDED", "ERROR"
    else:
        bridge_status, r1_outcome = "NEGATIVE_EVIDENCE_RECORDED", "NEGATIVE"

    identity = {
        "return_id": evidence["return_id"], "case_id": evidence["case_id"],
        "intake_id": evidence["intake_id"],
        "manuscript_sha256": evidence["manuscript_sha256"],
        "work_order_id": evidence["work_order_id"],
        "provider": evidence["provider"], "recorded_at": evidence["recorded_at"],
        "source": source,
        "outcome": outcome, "passages": passages,
        "negative_evidence": negatives, "errors": errors,
    }
    evidence_id = "evidence:" + _digest(identity)
    ledger_dir.mkdir(parents=True, exist_ok=True)
    index_path = ledger_dir / (hashlib.sha256(evidence["return_id"].encode()).hexdigest() + ".receipt.json")
    if index_path.exists():
        prior = _read_object(index_path)
        if prior.get("evidence_id") != evidence_id:
            raise IndagoBridgeRefusal("return_id reused with different evidence",
                                      "REPLAY_ID_CONFLICT")
        state = _read_object(ledger_dir / prior["state_file"])
        if (attestation.get("bytes_verified") and
                state.get("witness_attestation", {}).get("status")
                != attestation.get("status")):
            raise IndagoBridgeRefusal("Cannot silently promote an old unverified return",
                                      "REPLAY_ATTESTATION_CHANGED")
        replay = dict(prior, replay_status="IDEMPOTENT_REPLAY")
        return BridgeResult(replay, state, True)

    source_evidence: list[dict[str, Any]] = []
    if bridge_status == "ANCHORED":
        p = unique[0]
        source_evidence.append({
            "evidence_id": evidence_id, "work_order_id": order["work_order_id"],
            "intake_id": order["intake_id"], "z0_case_id": case["case_id"],
            "case_id": case["case_id"], "work_id": source["work_id"],
            "edition_id": source["edition_id"], "witness_id": source["witness_id"],
            "source_sha256": source["source_sha256"], "source_kind": source["source_kind"],
            "source_provenance": source["access_origin"], "read_depth": "ANCHORED_PASSAGE",
            "passage_id": p["passage_id"], "passage_occurrences": 1,
            "locator_present": True, "locator": p["locator"],
            "text_sha256": p["text_sha256"],
        })
    carried_negative = list(dict.fromkeys(
        negatives + errors + (["ANCHOR_AMBIGUOUS"] if bridge_status == "ANCHOR_AMBIGUOUS" else [])
        + (["NO_PASSAGE"] if outcome == "NO_PASSAGE" else [])))
    state = {
        "schema": STATE_SCHEMA, "case_id": case["case_id"],
        "work_order_id": order["work_order_id"], "work_order_ids": [order["work_order_id"]],
        "original_source_sha256": order["source_sha256"], "evidence_id": evidence_id,
        "outcome": r1_outcome, "bridge_status": bridge_status,
        "verification": {f"V{i}": "NOT_CHECKED" for i in range(1, 6)},
        "source_evidence": source_evidence, "negative_evidence": carried_negative,
        "reported_passages": [
            {"passage_id": p["passage_id"], "locator": p["locator"],
             "text_sha256": p["text_sha256"], "status": "PROVIDER_REPORTED"}
            for p in passages
        ] if bridge_status == "WITNESS_UNVERIFIED" else [],
        "witness_attestation": attestation,
        "errors": errors, "provider": evidence["provider"],
        "retrieved_at": evidence["recorded_at"], "citation_gate": "NOT_PUBLICATION_READY",
        "author_gate": "PENDING", "source_to_claim_relation": "NOT_CHECKED",
        "scientific_certification": False, "proposed_patch": None,
    }
    state_name = evidence_id.split(":", 1)[1] + ".state.json"
    receipt = {
        "schema": RECEIPT_SCHEMA, "evidence_id": evidence_id,
        "return_id": evidence["return_id"], "case_id": case["case_id"],
        "work_order_id": order["work_order_id"], "bridge_status": bridge_status,
        "replay_status": "RECORDED", "state_file": state_name,
        "provider_execution": "OPEN_NOT_DEMONSTRATED",
        "witness_attestation": attestation,
        "scientific_certification": False,
    }
    # Exclusive creation avoids silently overwriting any evidence ledger.
    for path, payload in ((ledger_dir / state_name, state), (index_path, receipt)):
        try:
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
        except FileExistsError as exc:
            raise IndagoBridgeRefusal("Evidence ledger collision", "LEDGER_COLLISION") from exc
    return BridgeResult(receipt, state, False)


def consume_file(audit_path: Path, queue_path: Path, return_path: Path,
                 ledger_dir: Path,
                 *, witness_path: Path | None = None) -> BridgeResult:
    return consume_evidence_return(audit_path, queue_path,
                                   _read_object(return_path), ledger_dir,
                                   witness_path=witness_path)


def consume_and_plan(audit_path: Path, queue_path: Path, return_path: Path,
                     ledger_dir: Path, plan_dir: Path,
                     manuscript_path: Path,
                     *, witness_path: Path | None = None) -> dict[str, Any]:
    result = consume_file(audit_path, queue_path, return_path, ledger_dir,
                          witness_path=witness_path)
    bundle = plan_repair(audit_path, plan_dir, result.state["case_id"], manuscript_path,
                         prior_states=load_prior_states(
                             [ledger_dir / result.receipt["state_file"]]),
                         queue_orders=_orders(queue_path))
    return {"bridge_receipt": result.receipt, "r2_r4_plan": bundle}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay-safe Indago EvidenceReturn consumer")
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--return-file", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--witness-path", type=Path, default=None,
                        help="Operator-held original PDF/TXT/MD; required for ANCHORED")
    args = parser.parse_args(argv)
    try:
        result = consume_file(args.audit, args.queue, args.return_file, args.ledger,
                              witness_path=args.witness_path)
    except IndagoBridgeRefusal as exc:
        print(json.dumps({"status": "REFUSED", "code": exc.code, "error": str(exc)}))
        return 2
    print(json.dumps(result.receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
