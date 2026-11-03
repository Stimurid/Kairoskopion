"""Synthetic tests only: no real operational observations or author approval."""
import json
from pathlib import Path
import pytest

from kairoskopion.kairon_provider.c04_measurement_gate import (
    SCHEMA,CHARter_HASH,validate,readback,
)
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked

PIN="a"*64
WITNESS="b"*64
TIME="2026-11-03T09:00:00+00:00"

def case():
    return {"schema":SCHEMA,"operation_id":"SYNTHETIC_NOT_REAL_TEST_CASE",
       "specification_sha256":PIN,"t0_utc":TIME,
       "coder_id":"SYNTHETIC_BLINDED_CODER_A",
       "measurement_charter_sha256":CHARter_HASH,
       "dimensions":{k:{"state":2,"evidence_quality":"E2",
               "observed_utc":"2026-11-02T08:00:00Z","witness_sha256":WITNESS,
               "rationale":"Synthetic evidence from a fabricated test fixture only",
               "not_applicable_reason":None}
               for k in "KAQTW"}}

def check(j):
    return validate(j,raw_bytes=json.dumps(j).encode(),expected_charter_sha256=CHARter_HASH)

def test_valid_synthetic_does_not_claim_scholarly_truth():
    r=check(case())
    assert r["gate"]=="STRUCTURE_ONLY_VALID"
    assert r["dimensions"]["K"]["substantive_state"]==2
    assert r["dimensions"]["K"]["evidence_quality"]=="E2"
    assert r["scientific_status"]=="UNVALIDATED_PROPOSED_CODEBOOK"
    assert r["author_gate"]=="HOLD" and r["send"] is False
    assert r["construct_validity_established"] is False

def test_evidence_quality_not_state():
    j=case()
    j["dimensions"]["K"]["evidence_quality"]="E0"
    with pytest.raises(EvidenceBlocked,match="zero_evidence_cannot_assert_state"):
        check(j)

def test_missing_witness_with_high_evidence_rejected():
    j=case()
    j["dimensions"]["A"]["witness_sha256"]=None
    with pytest.raises(EvidenceBlocked,match="high_evidence_requires_dated_witness"):
        check(j)

def test_later_witness_is_temporal_leakage():
    j=case()
    j["dimensions"]["Q"]["observed_utc"]="2026-11-03T10:00:00Z"
    with pytest.raises(EvidenceBlocked,match="post_t0_witness_leakage"):
        check(j)

def test_outcome_field_forbidden_in_preaward_snapshot():
    j=case()
    j["outcome_Y"]=1
    with pytest.raises(EvidenceBlocked,match="schema_or_keys_invalid"):
        check(j)

def test_boolean_state_never_equal_to_numeric_one():
    j=case()
    j["dimensions"]["W"]["state"]=True
    with pytest.raises(EvidenceBlocked,match="substantive_state_invalid"):
        check(j)

def test_unknown_and_zero_must_not_be_conflated():
    j=case()
    j["dimensions"]["K"]={"state":"UNKNOWN","evidence_quality":"E0",
          "observed_utc":None,"witness_sha256":None,
          "rationale":"No information in the frozen synthetic snapshot","not_applicable_reason":None}
    r=check(j)
    assert r["dimensions"]["K"]["substantive_state"]=="UNKNOWN"
    assert r["dimensions"]["A"]["substantive_state"]==2
    assert r["dimensions"]["K"]["evidence_quality"]=="E0"

def test_na_requires_explicit_witness_and_justification():
    j=case()
    j["dimensions"]["T"]["state"]="NOT_APPLICABLE"
    j["dimensions"]["T"]["not_applicable_reason"]="One-site operation with documented no-transfer rule"
    assert check(j)["dimensions"]["T"]["substantive_state"]=="NOT_APPLICABLE"
    j["dimensions"]["T"]["not_applicable_reason"]=None
    with pytest.raises(EvidenceBlocked,match="na_requires_supported_exemption"):
        check(j)

def test_charter_sha_pin_not_model_supplied():
    j=case()
    j["measurement_charter_sha256"]="f"*64
    with pytest.raises(EvidenceBlocked,match="untrusted_or_stale_charter_sha"):
        check(j)

def test_extra_dimensions_rejected():
    j=case()
    j["dimensions"]["S"]={"state":1}
    with pytest.raises(EvidenceBlocked,match="all_five"):
        check(j)

def test_receipt_cold_replay_and_tamper(tmp_path):
    charter=tmp_path/"M114.md"
    charter.write_bytes(b"not the real charter")
    snap=tmp_path/"synthetic.json"
    snap.write_text(json.dumps(case()),encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="untrusted_or_stale_charter_sha"):
        readback(input_path=snap,charter_path=charter,output_path=tmp_path/"result.json")
