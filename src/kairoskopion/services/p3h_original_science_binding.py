"""P3h read-only binding of ORIGINAL Sonar/Ionosphere bytes to P3c gold.

The owner-approved lock and independent oracle hashes are EXTERNAL inputs.
Neither a model response nor any file under the candidate's control can be its
own trust anchor. This validates data lineage and the independent numerical
results already recomputed by the owner; it does not recompute model training,
prove independence of the oracle author, or authorize an empirical claim.

Separate from the pre-existing Factory science gate and ArticleSeed promotion.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

_HASH = re.compile(r"[a-f0-9]{64}\Z")
_FILES = {
    "lock": ("evaldrift_P3", "lock.json"),
    "design": ("evaldrift_P3", "design.json"),
    "holdout": ("evaldrift_P3", "holdout_vault.json"),
    "sonar": ("evaldrift_P3", "sonar_UCI_original.csv"),
    "ionosphere": ("evaldrift_P3", "ionosphere_UCI_original.csv"),
    "audit": ("evaldrift_P3c", "p3c_audit_inputs_LOCKED.json"),
    "replay_oracle": ("evaldrift_P3c", "p3c_independent_oracle.json"),
    "numeric_oracle": ("evaldrift_P3c", "p3c_independent_numeric_oracle.json"),
}
_MAX_BYTES = 2_000_000


def _pinned_hex(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise ValueError(f"{field}: owner SHA256 pin missing or invalid")
    return value


def _read_bytes(root: Path, parts: tuple[str, str]) -> bytes:
    path = root.joinpath(*parts)
    if path.is_symlink() or not path.is_file():
        raise ValueError("required P3h original artifact absent or symlinked")
    if not 0 < path.stat().st_size <= _MAX_BYTES:
        raise ValueError("original artifact outside P3h size policy")
    return path.read_bytes()


def _json(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate P3h JSON field")
            result[key] = value
        return result

    try:
        result = json.loads(
            raw.decode("utf-8"), object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite P3h JSON")),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid P3h JSON") from exc
    if not isinstance(result, dict):
        raise ValueError("P3h JSON object required")
    return result


def verify_original_p3h_source_oracle_binding(
    *,
    experiment_root: str | Path,
    owner_expected_lock_sha256: str,
    owner_expected_replay_oracle_sha256: str,
    owner_expected_numeric_oracle_sha256: str,
) -> dict[str, Any]:
    """Verify existing locked original bytes and two *previously written* oracles.

    Caller pins must come from an independently retained owner authority.
    A self-calculated pin from experiment_root is an INVALID invocation.
    The returned receipt deliberately cannot be construed as a claim PASS.
    """
    expected = {
        "lock": _pinned_hex(owner_expected_lock_sha256, "lock"),
        "replay_oracle": _pinned_hex(owner_expected_replay_oracle_sha256, "replay_oracle"),
        "numeric_oracle": _pinned_hex(owner_expected_numeric_oracle_sha256, "numeric_oracle"),
    }
    root = Path(experiment_root).resolve()
    raw = {key: _read_bytes(root, path) for key, path in _FILES.items()}
    hashes = {key: sha256(value).hexdigest() for key, value in raw.items()}
    for key, digest in expected.items():
        if hashes[key] != digest:
            raise ValueError(f"{key}: external owner SHA256 mismatch")
    lock = _json(raw["lock"])
    design = _json(raw["design"])
    vault = _json(raw["holdout"])
    audit = _json(raw["audit"])
    replay = _json(raw["replay_oracle"])
    numeric = _json(raw["numeric_oracle"])

    if (lock.get("schema") != "AI4SCI_P3_LOCK_V1"
            or lock.get("author") != "HOLD"
            or lock.get("send") != "DISABLED"):
        raise ValueError("original preregistration authority changed")
    for key, locked in (
        ("design", lock.get("design_sha256")),
        ("holdout", lock.get("vault_sha256")),
    ):
        if hashes[key] != locked:
            raise ValueError(f"{key}: original lock content mismatch")
    source_pins = lock.get("source_sha256")
    if not isinstance(source_pins, dict) or set(source_pins) != {"SONAR", "IONOSPHERE"}:
        raise ValueError("missing original dataset source register")
    for name, key in (("SONAR", "sonar"), ("IONOSPHERE", "ionosphere")):
        if hashes[key] != _pinned_hex(source_pins[name], name):
            raise ValueError(f"{name}: original dataset byte mismatch")
    if (replay.get("schema") != "AI4SCI_P3C_NUMPY_INDEPENDENT_ORACLE_V1"
            or replay.get("original_sources") != source_pins
            or replay.get("design_sha256") != hashes["design"]
            or replay.get("vault_sha256") != hashes["holdout"]
            or replay.get("audit_packet_sha256") != hashes["audit"]):
        raise ValueError("NumPy independent replay provenance mismatch")
    if (numeric.get("original_design_sha256") != hashes["design"]
            or numeric.get("original_holdout_sha256") != hashes["holdout"]
            or numeric.get("p3c_auditor_input_sha256") != hashes["audit"]
            or numeric.get("raw_sources_sha256") != source_pins):
        raise ValueError("independent numerical oracle provenance mismatch")

    results = replay.get("comparisons")
    conditions = numeric.get("case_conditions")
    if not isinstance(results, list) or not isinstance(conditions, dict):
        raise ValueError("independent case-condition evidence missing")
    if len(results) != 5 or len(conditions) != 5:
        raise ValueError("original five eligible P3c cases not present")
    case_ids = [r.get("case_id") for r in results if isinstance(r, dict)]
    if (not all(isinstance(x, str) and x for x in case_ids)
            or len(set(case_ids)) != 5 or set(case_ids) != set(conditions)):
        raise ValueError("independent oracle case identities disagree")
    valid_dataset_cases = {
        v.get("case_id") for v in design.get("cases", [])
        if isinstance(v, dict) and v.get("dataset") in source_pins
    }
    if not set(case_ids).issubset(valid_dataset_cases):
        raise ValueError("independent oracle case missing from preregistered design")
    checks = 0
    negative = 0
    for result in results:
        name = result["case_id"]
        for arm in ("S", "M", "H"):
            item = result.get(arm)
            numeric_item = conditions[name].get(arm)
            if not isinstance(item, dict) or not isinstance(numeric_item, dict):
                raise ValueError("independent arm measurements missing")
            if (item.get("model") != numeric_item.get("selected")
                    or type(item.get("valid")) is not bool
                    or item["valid"] != numeric_item.get("gold_claim_valid")):
                raise ValueError("independent numerical oracles contradict one another")
            checks += 1
            negative += not item["valid"]
    if (replay.get("cases_eligible") != len(results)
            or replay.get("independent_dev_holdout_recomputations") != 96
            or replay.get("negative_case_conditions") != negative
            or numeric.get("blocked_episodes") != 18
            or numeric.get("original_cases") != 8):
        raise ValueError("replay measurement totals contradict frozen P3c experiment")
    if (audit.get("original_design_sha256") != hashes["design"]
            or audit.get("original_vault_sha256") != hashes["holdout"]
            or audit.get("original_generator_raw_sha256") != replay.get("original_P3_raw_generator_sha256")):
        raise ValueError("P3c frozen evaluation packet differs from original experiment")
    return {
        "schema": "AI4SCI_P3H_ORIGINAL_SOURCE_NUMERIC_ORACLE_READBACK_V1",
        "status": "ORIGINAL_SOURCE_AND_ORACLE_BINDING_VERIFIED",
        "source_hashes": dict(source_pins),
        "lock_sha256": hashes["lock"],
        "design_sha256": hashes["design"],
        "holdout_sha256": hashes["holdout"],
        "audit_sha256": hashes["audit"],
        "independent_replay_sha256": hashes["replay_oracle"],
        "independent_numeric_oracle_sha256": hashes["numeric_oracle"],
        "cases_checked": len(results),
        "candidate_dev_holdout_recomputations_reported": 96,
        "independent_arm_agreements": checks,
        "invalid_case_conditions": negative,
        "original_byte_source_verified": True,
        "oracle_provenance_pinned": True,
        "oracle_independence_authenticated_by_host": False,
        "fresh_independent_recomputation_executed": False,
        "scientific_claim_admitted": False,
        "article_seed_created": False,
        "author_gate": "HOLD",
        "external_send": "DISABLED",
    }
