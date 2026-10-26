"""P3h original source + independent numerical oracle is NOT ArticleSeed PASS."""
from hashlib import sha256
import json

import pytest

from kairoskopion.services.p3h_original_science_binding import (
    verify_original_p3h_source_oracle_binding,
)


def _raw(obj):
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _sha(raw):
    return sha256(raw).hexdigest()


def prepared(tmp_path):
    p3 = tmp_path / "evaldrift_P3"
    p3c = tmp_path / "evaldrift_P3c"
    p3.mkdir()
    p3c.mkdir()
    sources = {"SONAR": b"original sonar sample\n", "IONOSPHERE": b"original ionosphere sample\n"}
    for name, source in sources.items():
        (p3 / (name.lower() + "_UCI_original.csv")).write_bytes(source)
    source_pins = {name: _sha(raw) for name, raw in sources.items()}
    cases = ["SONAR-17", "SONAR-29", "IONOSPHERE-17", "IONOSPHERE-29", "IONOSPHERE-41"]
    design = {"cases": [{"case_id": c, "dataset": c.split("-")[0]} for c in cases]
              + [{"case_id": "SONAR-41", "dataset": "SONAR"},
                 {"case_id": "SONAR-73", "dataset": "SONAR"},
                 {"case_id": "IONOSPHERE-73", "dataset": "IONOSPHERE"}]}
    vault = {"schema": "P3_VAULT_FIXTURE", "cases": cases}
    design_sha, vault_sha = _sha(_raw(design)), _sha(_raw(vault))
    generator_sha = "9"*64
    audit = {
        "original_design_sha256": design_sha,
        "original_vault_sha256": vault_sha,
        "original_generator_raw_sha256": generator_sha,
    }
    audit_sha = _sha(_raw(audit))
    replay_rows, numeric_cases = [], {}
    for index, name in enumerate(cases):
        row = {"case_id": name}
        conditions = {}
        for arm_number, arm in enumerate(("S", "M", "H")):
            valid = index == 3 and arm in ("S", "M")
            choice = "all" if valid else "alternating"
            row[arm] = {"model": choice, "valid": valid}
            conditions[arm] = {"selected": choice, "gold_claim_valid": valid}
        replay_rows.append(row)
        numeric_cases[name] = conditions
    replay = {
        "schema": "AI4SCI_P3C_NUMPY_INDEPENDENT_ORACLE_V1",
        "original_sources": source_pins, "design_sha256": design_sha,
        "vault_sha256": vault_sha, "audit_packet_sha256": audit_sha,
        "original_P3_raw_generator_sha256": generator_sha,
        "comparisons": replay_rows, "cases_eligible": 5,
        "independent_dev_holdout_recomputations": 96,
        "negative_case_conditions": 13,
    }
    numeric = {
        "original_design_sha256": design_sha,
        "original_holdout_sha256": vault_sha,
        "p3c_auditor_input_sha256": audit_sha,
        "raw_sources_sha256": source_pins,
        "case_conditions": numeric_cases,
        "blocked_episodes": 18,
        "original_cases": 8,
    }
    lock = {
        "schema": "AI4SCI_P3_LOCK_V1", "author": "HOLD", "send": "DISABLED",
        "design_sha256": design_sha, "vault_sha256": vault_sha,
        "source_sha256": source_pins,
    }
    obj = {
        p3 / "lock.json": lock, p3 / "design.json": design,
        p3 / "holdout_vault.json": vault,
        p3c / "p3c_audit_inputs_LOCKED.json": audit,
        p3c / "p3c_independent_oracle.json": replay,
        p3c / "p3c_independent_numeric_oracle.json": numeric,
    }
    for path, value in obj.items():
        path.write_bytes(_raw(value))
    args = {
        "experiment_root": tmp_path,
        "owner_expected_lock_sha256": _sha(_raw(lock)),
        "owner_expected_replay_oracle_sha256": _sha(_raw(replay)),
        "owner_expected_numeric_oracle_sha256": _sha(_raw(numeric)),
    }
    return args, p3, p3c


def test_frozen_original_sources_and_two_oracles_bind_without_claim_promotion(tmp_path):
    args, _, _ = prepared(tmp_path)
    result = verify_original_p3h_source_oracle_binding(**args)
    assert result["status"] == "ORIGINAL_SOURCE_AND_ORACLE_BINDING_VERIFIED"
    assert result["cases_checked"] == 5
    assert result["independent_arm_agreements"] == 15
    assert result["invalid_case_conditions"] == 13
    assert result["author_gate"] == "HOLD"
    assert result["article_seed_created"] is False
    assert result["fresh_independent_recomputation_executed"] is False
    assert result["oracle_independence_authenticated_by_host"] is False
    assert verify_original_p3h_source_oracle_binding(**args) == result


@pytest.mark.parametrize("field", [
    "owner_expected_lock_sha256", "owner_expected_replay_oracle_sha256",
    "owner_expected_numeric_oracle_sha256",
])
def test_owner_pin_different_or_missing_blocks(tmp_path, field):
    args, _, _ = prepared(tmp_path)
    with pytest.raises(ValueError, match="owner SHA256|external owner"):
        verify_original_p3h_source_oracle_binding(**(args | {field: "0" * 64}))
    with pytest.raises(ValueError, match="owner SHA256"):
        verify_original_p3h_source_oracle_binding(**(args | {field: None}))


@pytest.mark.parametrize("filename", [
    "sonar_UCI_original.csv", "ionosphere_UCI_original.csv",
    "design.json", "holdout_vault.json",
])
def test_raw_measurement_and_locked_experiment_mutation_blocks(tmp_path, filename):
    args, p3, _ = prepared(tmp_path)
    path = p3 / filename
    path.write_bytes(path.read_bytes() + b"corruption")
    with pytest.raises(ValueError):
        verify_original_p3h_source_oracle_binding(**args)


def test_numerical_oracle_cannot_invent_new_provenance(tmp_path):
    args, _, p3c = prepared(tmp_path)
    path = p3c / "p3c_independent_numeric_oracle.json"
    fake = json.loads(path.read_bytes())
    fake["raw_sources_sha256"]["SONAR"] = "0" * 64
    path.write_bytes(_raw(fake))
    # Even a caller recomputing the new oracle SHA cannot evade original source register.
    args["owner_expected_numeric_oracle_sha256"] = _sha(path.read_bytes())
    with pytest.raises(ValueError, match="numerical oracle provenance"):
        verify_original_p3h_source_oracle_binding(**args)


def test_two_oracles_contradict_each_other_blocked(tmp_path):
    args, _, p3c = prepared(tmp_path)
    path = p3c / "p3c_independent_numeric_oracle.json"
    fake = json.loads(path.read_bytes())
    fake["case_conditions"]["SONAR-17"]["H"]["selected"] = "first_two"
    path.write_bytes(_raw(fake))
    args["owner_expected_numeric_oracle_sha256"] = _sha(path.read_bytes())
    with pytest.raises(ValueError, match="contradict one another"):
        verify_original_p3h_source_oracle_binding(**args)


def test_authority_mutation_fails_even_when_caller_forces_new_lock_digest(tmp_path):
    args, p3, _ = prepared(tmp_path)
    path = p3 / "lock.json"
    forged = json.loads(path.read_bytes())
    forged["author"] = "ACCEPT"
    path.write_bytes(_raw(forged))
    args["owner_expected_lock_sha256"] = _sha(path.read_bytes())
    with pytest.raises(ValueError, match="preregistration authority"):
        verify_original_p3h_source_oracle_binding(**args)


def test_duplicate_json_fields_cannot_be_silently_accepted(tmp_path):
    args, p3, _ = prepared(tmp_path)
    path = p3 / "lock.json"
    path.write_bytes(path.read_bytes().rstrip()[:-1] + b',"author":"ACCEPT"}\n')
    args["owner_expected_lock_sha256"] = _sha(path.read_bytes())
    with pytest.raises(ValueError, match="duplicate P3h JSON field"):
        verify_original_p3h_source_oracle_binding(**args)
