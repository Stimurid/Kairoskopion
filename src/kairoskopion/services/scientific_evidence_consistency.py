"""Source-bound, deterministic empirical-claim review for native QualityGates.

This is a small reusable *checker*, not an autonomous judge, article maker, or
runtime. The independent oracle must be computed outside the model and pinned
by the calling Factory source registry. A caller-supplied self-hash is NOT a
trust anchor. Correct negative judgments and honest abstentions cannot promote
a scientific claim to an ArticleSeed or authorize submission.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import re
from typing import Any

SCHEMA = "KAIROSKOPION_SCIENTIFIC_EVIDENCE_PACKET_V1"
ORACLE_SCHEMA = "KAIROSKOPION_INDEPENDENT_ORACLE_V1"
MAX_BYTES = 16_000_000
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ACTIONS = frozenset({
    "REJECT_CLAIM", "INDEPENDENT_REPLICATION", "REQUEST_CLASS_EVIDENCE"
})
_LABELS = frozenset({"YES", "NO", "UNDETERMINED"})


def _sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _pairs_no_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON field")
        obj[key] = value
    return obj


def _obj(raw: bytes) -> dict[str, Any]:
    item = json.loads(
        raw.decode("utf-8"), object_pairs_hook=_pairs_no_duplicate,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON"))
    )
    if not isinstance(item, dict):
        raise ValueError("top-level JSON object required")
    return item


def _counts(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or len(rows) < 2 or len(rows) > 64:
        raise ValueError("at least two explicitly measured classes required")
    good = []
    for item in rows:
        if not isinstance(item, dict) or set(item) != {"class", "correct", "total"}:
            raise ValueError("class evidence requires exact label/correct/total")
        label, correct, total = item["class"], item["correct"], item["total"]
        if (not isinstance(label, str) or not label or len(label) > 128
                or type(correct) is not int or type(total) is not int
                or total <= 0 or total > 1_000_000_000 or not 0 <= correct <= total):
            raise ValueError("class evidence has invalid integer measurements")
        good.append({"class": label, "correct": correct, "total": total})
    if len({r["class"] for r in good}) != len(good):
        raise ValueError("duplicate physical class")
    return good


def _weights(rows: Any, class_count: int) -> list[list[float]]:
    if not isinstance(rows, list) or not 2 <= len(rows) <= 128:
        raise ValueError("initial and final evaluator versions required")
    clean = []
    for vector in rows:
        if not isinstance(vector, list) or len(vector) != class_count:
            raise ValueError("evaluator vector length differs from physical classes")
        if any(type(x) not in (float, int) or not math.isfinite(x)
               or x < 0 or x > 1 for x in vector):
            raise ValueError("non-numeric or invalid evaluator weights")
        if abs(sum(vector) - 1.0) > 1e-6:
            raise ValueError("evaluator weights are not normalized")
        clean.append([float(x) for x in vector])
    return clean


def _pin(raw: Any, expected: Any, name: str, issues: list[str]) -> bool:
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES
            or not isinstance(expected, str) or _SHA256.fullmatch(expected) is None):
        issues.append(name + "_TRUSTED_PIN_MISSING")
        return False
    if _sha(raw) != expected:
        issues.append(name + "_HASH_MISMATCH")
        return False
    return True


def audit_empirical_claim(
    *,
    packet_bytes: bytes | None,
    expected_packet_sha256: str | None,
    source_bytes: bytes | None,
    expected_source_sha256: str | None,
    oracle_bytes: bytes | None,
    expected_oracle_sha256: str | None,
    model_response_bytes: bytes | None,
) -> dict[str, Any]:
    """Fail-closed replay of a versioned, externally pinned scientific claim.

    Expected hashes are *trusted arguments from a source registry*, never read
    from the untrusted packet/model response. This can check a pinned oracle's
    arithmetic, but cannot prove that its independent preparation was genuine.
    """
    problems: list[str] = []
    material = (
        _pin(packet_bytes, expected_packet_sha256, "PACKET", problems),
        _pin(source_bytes, expected_source_sha256, "SOURCE", problems),
        _pin(oracle_bytes, expected_oracle_sha256, "ORACLE", problems),
    )
    if not all(material):
        return {"status": "BLOCKED", "issues": sorted(set(problems)), "computed": None}
    if not isinstance(model_response_bytes, bytes) or not 0 < len(model_response_bytes) <= MAX_BYTES:
        return {"status": "BLOCKED", "issues": ["MODEL_RESPONSE_MISSING"], "computed": None}
    try:
        packet, oracle, response = (
            _obj(packet_bytes), _obj(oracle_bytes), _obj(model_response_bytes)
        )
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return {"status": "BLOCKED", "issues": ["MALFORMED_OR_DUPLICATE_JSON"], "computed": None}

    def check(ok: bool, code: str) -> None:
        if not ok:
            problems.append(code)

    check(packet.get("schema") == SCHEMA, "PACKET_SCHEMA_INVALID")
    check(oracle.get("schema") == ORACLE_SCHEMA, "INDEPENDENT_ORACLE_SCHEMA_INVALID")
    case_id = oracle.get("case_id")
    source_id = oracle.get("source_id")
    criterion_version = oracle.get("criterion_version")
    check(all(isinstance(z, str) and 0 < len(z) <= 256
              for z in (case_id, source_id, criterion_version)),
          "UNVERSIONED_ORACLE_IDENTITY")
    for field in ("case_id", "source_id", "criterion_version", "selected_candidate"):
        check(packet.get(field) == oracle.get(field), "MISMATCH_" + field.upper())
    check(oracle.get("source_sha256") == expected_source_sha256
          and packet.get("source_sha256") == expected_source_sha256,
          "SOURCE_IDENTITY_NOT_BOUND_TO_PIN")
    goal = oracle.get("goal")
    check(packet.get("goal") == goal, "SCIENTIFIC_GOAL_CHANGED")
    if not isinstance(goal, dict) or set(goal) != {"metric", "numerator", "denominator"}:
        problems.append("INDEPENDENT_GOAL_INVALID")
        numerator, denominator = 0, 1
    else:
        numerator, denominator = goal["numerator"], goal["denominator"]
        if (goal["metric"] != "minimum_per_class_recall"
                or type(numerator) is not int or type(denominator) is not int
                or denominator <= 0 or not 0 < numerator <= denominator):
            problems.append("INDEPENDENT_GOAL_INVALID")
            numerator, denominator = 0, 1
    try:
        counts = _counts(oracle.get("holdout_by_class"))
        vectors = _weights(oracle.get("weight_versions"), len(counts))
    except (ValueError, TypeError):
        problems.append("INDEPENDENT_ORACLE_MEASUREMENTS_INVALID")
        counts, vectors = [], []
    if not isinstance(oracle.get("selected_candidate"), str) or not oracle["selected_candidate"]:
        problems.append("ORACLE_SELECTION_MISSING")

    visibility = packet.get("visibility")
    if visibility == "FULL":
        if packet.get("holdout_by_class") != counts:
            problems.append("CLASS_COUNTS_DO_NOT_MATCH_ORACLE")
        if packet.get("weight_versions") != oracle.get("weight_versions"):
            problems.append("CRITERION_HISTORY_DOES_NOT_MATCH_ORACLE")
    elif visibility == "SUMMARY":
        if "holdout_by_class" in packet or "weight_versions" in packet:
            problems.append("SUMMARY_LEAKS_INDEPENDENT_EVIDENCE")
    else:
        problems.append("EVIDENCE_WINDOW_INVALID")

    # Model-provided meta-confidence is not a permission or a source witness.
    if (response.get("criterion_changed") not in _LABELS
            or response.get("claim_valid") not in _LABELS
            or response.get("next_action") not in _ACTIONS):
        problems.append("MODEL_RESPONSE_CONTRACT_INVALID")

    computed = None
    if visibility == "SUMMARY":
        computed = {
            "criterion_changed": "UNDETERMINED",
            "claim_valid": "UNDETERMINED",
            "next_action": "REQUEST_CLASS_EVIDENCE",
        }
    elif counts and vectors and numerator:
        changed = any(abs(a-b) > 0.03 for a,b in zip(vectors[0], vectors[-1]))
        valid = all(denominator * r["correct"] >= numerator * r["total"] for r in counts)
        computed = {
            "criterion_changed": "YES" if changed else "NO",
            "claim_valid": "YES" if valid else "NO",
            "next_action": "INDEPENDENT_REPLICATION" if valid else "REJECT_CLAIM",
        }
    if computed is None:
        problems.append("INDEPENDENT_EVIDENCE_NOT_COMPUTABLE")
    else:
        for key, value in computed.items():
            if response.get(key) != value:
                problems.append("MODEL_CONTRADICTS_EVIDENCE:" + key)
    if problems:
        return {"status": "BLOCKED", "issues": sorted(set(problems)), "computed": computed}

    if visibility == "SUMMARY":
        return {"status": "INSUFFICIENT_EVIDENCE", "issues": [], "computed": computed}
    if computed["claim_valid"] == "NO":
        return {"status": "CLAIM_INVALID", "issues": ["INDEPENDENT_GOLD_NOT_MET"],
                "computed": computed}
    return {"status": "STRUCTURED_EVIDENCE_PASSED", "issues": [], "computed": computed}
