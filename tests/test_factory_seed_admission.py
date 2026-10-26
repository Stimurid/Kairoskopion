"""P3i: actual Factory sources and P3 raw oracles cannot self-certify seed."""
from hashlib import sha256
import hmac
import json

import pytest

from kairoskopion.services.factory_seed_admission import (
    assess_factory_seed_admission, _canonical,
)
from tests.test_factory_scientific_source_pin import fixture as factory_fixture
from tests.test_p3h_original_science_binding import prepared as p3h_fixture
from tests.test_scientific_evidence_consistency_gate import bundle, raw, h


def signed(case, seed, revision, packet_sha, role, key):
    payload = {
        "schema": "AI4SCI_FACTORY_AUTHOR_CONSENT_V1",
        "case_id": case,
        "seed_id": seed,
        "revision": revision,
        "packet_sha256": packet_sha,
        "role": role,
        "decision": "ACCEPT",
    }
    signed_payload = {
        **payload,
        "signature": hmac.new(key, _canonical(payload), "sha256").hexdigest()
    }
    encoded = raw(signed_payload)
    return encoded, h(encoded)


def prepared(tmp_path):
    factory, _, _ = factory_fixture(tmp_path / "factory")
    p3h, _, _ = p3h_fixture(tmp_path / "p3h")
    b = bundle(valid=True)
    actual = (tmp_path / "p3h" / "evaldrift_P3" / "sonar_UCI_original.csv").read_bytes()
    b["oracle"]["source_sha256"] = h(actual)
    b["packet"]["source_sha256"] = h(actual)
    b["oracle"]["source_id"] = "uci:sonar"
    b["packet"]["source_id"] = "uci:sonar"
    p = raw(b["packet"])
    o = raw(b["oracle"])
    a = raw(b["answer"])
    authkey, coauthkey = b"x" * 32, b"y" * 32
    receipt_a, receipt_sha_a = signed(
        factory["case_id"], "C01-R2", "r2", h(p), "AUTHOR", authkey
    )
    receipt_c, receipt_sha_c = signed(
        factory["case_id"], "C01-R2", "r2", h(p), "COAUTHOR", coauthkey
    )
    args = {
        "case_id": factory["case_id"],
        "seed_id": "C01-R2", "revision": "r2",
        "claim_classification": "EMPIRICAL",
        "factory_root": factory["factory_storage_root"],
        "factory_source_id": factory["source_id"],
        "factory_source_bytes": factory["source_bytes"],
        "owner_expected_factory_receipt_sha256":
            factory["owner_expected_stage_receipt_sha256"],
        "experiment_root": p3h["experiment_root"],
        "owner_expected_lock_sha256": p3h["owner_expected_lock_sha256"],
        "owner_expected_replay_oracle_sha256":
            p3h["owner_expected_replay_oracle_sha256"],
        "owner_expected_numeric_oracle_sha256":
            p3h["owner_expected_numeric_oracle_sha256"],
        "experimental_dataset": "SONAR",
        "scientific_packet_bytes": p,
        "owner_expected_packet_sha256": h(p),
        "claim_oracle_bytes": o,
        "owner_expected_claim_oracle_sha256": h(o),
        "model_response_bytes": a,
        "author_receipt_bytes": receipt_a,
        "owner_author_receipt_sha256": receipt_sha_a,
        "owner_author_verification_key": authkey,
        "coauthor_receipt_bytes": receipt_c,
        "owner_coauthor_receipt_sha256": receipt_sha_c,
        "owner_coauthor_verification_key": coauthkey,
    }
    return args


def test_synthetic_all_valid_only_owner_review_not_article_admission(tmp_path):
    receipt = assess_factory_seed_admission(**prepared(tmp_path))
    assert receipt["status"] == "OWNER_REVIEW_ELIGIBLE"
    assert receipt["claim_level_science_status"] == "STRUCTURED_EVIDENCE_PASSED"
    assert receipt["original_p3h_oracle_bound"] is True
    assert receipt["author_consent_signed"] is True
    assert receipt["coauthor_consent_signed"] is True
    assert receipt["article_seed_created"] is False
    assert receipt["publication_authority"] == "NONE"
    assert receipt["external_send"] == "DISABLED"


@pytest.mark.parametrize("field,value,issue", [
    ("claim_classification", None, "CLAIM_CLASSIFICATION_NOT_TRUSTED_OR_NOT_EMPIRICAL"),
    ("claim_classification", "NONEMPIRICAL", "CLAIM_CLASSIFICATION_NOT_TRUSTED_OR_NOT_EMPIRICAL"),
    ("owner_expected_factory_receipt_sha256", "0"*64, "FACTORY_SOURCE_PIN_REJECTED"),
    ("factory_source_id", "drive:untrusted", "FACTORY_SOURCE_PIN_REJECTED"),
    ("owner_expected_numeric_oracle_sha256", "0"*64, "ORIGINAL_NUMERIC_ORACLE_BINDING_REJECTED"),
    ("owner_expected_claim_oracle_sha256", "0"*64, "CLAIM_LEVEL_SCIENTIFIC_WARRANT_NOT_PASSED"),
    ("experimental_dataset", "OTHER", "CLAIM_LEVEL_SCIENTIFIC_WARRANT_NOT_PASSED"),
    ("author_receipt_bytes", None, "AUTHOR_SIGNATURE_OR_DECISION_NOT_VERIFIED"),
    ("coauthor_receipt_bytes", None, "COAUTHOR_SIGNATURE_OR_DECISION_NOT_VERIFIED"),
    ("owner_author_verification_key", b"z"*32, "AUTHOR_SIGNATURE_OR_DECISION_NOT_VERIFIED"),
    ("owner_coauthor_verification_key", b"z"*32, "COAUTHOR_SIGNATURE_OR_DECISION_NOT_VERIFIED"),
    ("seed_id", "DIFFERENT", "AUTHOR_SIGNATURE_OR_DECISION_NOT_VERIFIED"),
    ("revision", "r3", "COAUTHOR_SIGNATURE_OR_DECISION_NOT_VERIFIED"),
])
def test_missing_or_forged_independent_authority_fails_closed(tmp_path, field, value, issue):
    args = prepared(tmp_path)
    args[field] = value
    decision = assess_factory_seed_admission(**args)
    assert decision["status"] == "BLOCKED"
    assert issue in decision["blockers"]
    assert decision["article_seed_created"] is False


def test_source_bytes_mutation_invalidates_factory_authority(tmp_path):
    args = prepared(tmp_path)
    args["factory_source_bytes"] += b"adversarial mutation"
    decision = assess_factory_seed_admission(**args)
    assert "FACTORY_SOURCE_PIN_REJECTED" in decision["blockers"]


def test_raw_model_cannot_override_independent_gold(tmp_path):
    args = prepared(tmp_path)
    answer = json.loads(args["model_response_bytes"])
    answer["claim_valid"] = "NO"
    args["model_response_bytes"] = raw(answer)
    decision = assess_factory_seed_admission(**args)
    assert "CLAIM_LEVEL_SCIENTIFIC_WARRANT_NOT_PASSED" in decision["blockers"]


def test_author_signed_only_hold_is_not_consent(tmp_path):
    args = prepared(tmp_path)
    signature = json.loads(args["author_receipt_bytes"])
    signature["decision"] = "HOLD"
    payload = {k: v for k, v in signature.items() if k != "signature"}
    signature["signature"] = hmac.new(
        args["owner_author_verification_key"], _canonical(payload), "sha256"
    ).hexdigest()
    args["author_receipt_bytes"] = raw(signature)
    args["owner_author_receipt_sha256"] = h(args["author_receipt_bytes"])
    decision = assess_factory_seed_admission(**args)
    assert decision["status"] == "BLOCKED"
    assert "AUTHOR_SIGNATURE_OR_DECISION_NOT_VERIFIED" in decision["blockers"]
