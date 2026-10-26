"""Native QualityGate science contract; synthetic evidence, no owner-private files.

The historical P3c 30-case source replay is a separate test on AORUS with
byte-pinned UCI source/oracle files. These tests exercise the generic API.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

import pytest

from kairoskopion.enums import QualityGateStatus
from kairoskopion.quality import (
    evaluate_scientific_evidence_consistency_gate,
    evaluate_submission_gate,
)


def raw(o):
    return (json.dumps(o, ensure_ascii=False, sort_keys=True) + "\n").encode()


def h(b):
    return sha256(b).hexdigest()


def bundle(*, valid=True, visibility="FULL", changed=True):
    source = b"original numerical measurements, independently recorded"
    source_sha = h(source)
    oracle = {
        "schema": "KAIROSKOPION_INDEPENDENT_ORACLE_V1",
        "case_id": "TEST-01",
        "source_id": "uci:example-original",
        "source_sha256": source_sha,
        "criterion_version": "v1/pre-registered",
        "selected_candidate": "centroid:all",
        "goal": {"metric": "minimum_per_class_recall",
                 "numerator": 3, "denominator": 4},
        "holdout_by_class": [
            {"class": "a", "correct": 18 if valid else 11, "total": 20},
            {"class": "b", "correct": 17, "total": 20},
        ],
        "weight_versions": [[0.5, 0.5], [0.75, 0.25] if changed else [0.5, 0.5]],
    }
    packet = {
        "schema": "KAIROSKOPION_SCIENTIFIC_EVIDENCE_PACKET_V1",
        "case_id": "TEST-01",
        "source_id": oracle["source_id"],
        "source_sha256": source_sha,
        "criterion_version": oracle["criterion_version"],
        "selected_candidate": oracle["selected_candidate"],
        "goal": deepcopy(oracle["goal"]),
        "visibility": visibility,
    }
    if visibility == "FULL":
        packet["holdout_by_class"] = deepcopy(oracle["holdout_by_class"])
        packet["weight_versions"] = deepcopy(oracle["weight_versions"])
        answer = {
            "criterion_changed": "YES" if changed else "NO",
            "claim_valid": "YES" if valid else "NO",
            "next_action": "INDEPENDENT_REPLICATION" if valid else "REJECT_CLAIM",
        }
    else:
        answer = {
            "criterion_changed": "UNDETERMINED",
            "claim_valid": "UNDETERMINED",
            "next_action": "REQUEST_CLASS_EVIDENCE",
        }
    return {
        "packet": packet, "oracle": oracle, "answer": answer, "source": source,
    }


def kwargs(b):
    p = raw(b["packet"])
    o = raw(b["oracle"])
    r = raw(b["answer"])
    return {
        "packet_bytes": p, "expected_packet_sha256": h(p),
        "source_bytes": b["source"], "expected_source_sha256": h(b["source"]),
        "oracle_bytes": o, "expected_oracle_sha256": h(o),
        "model_response_bytes": r,
    }


def quality(b):
    return evaluate_scientific_evidence_consistency_gate(**kwargs(b))


def test_valid_full_source_bound_claim_passes_technical_quality_but_not_human_approval():
    result = quality(bundle(valid=True))
    assert result.status == QualityGateStatus.PASSED.value
    assert result.gate_name == "scientific_evidence_consistency"
    assert result.required_user_decisions
    assert "consent" in result.recommendation


def test_negative_gold_even_when_model_correctly_rejects_cannot_be_promoted():
    result = quality(bundle(valid=False))
    assert result.status == QualityGateStatus.FAILED_BLOCKING.value
    assert "INDEPENDENT_GOLD_NOT_MET" in result.blocking_issues


def test_conservatively_correct_summary_is_not_an_admitted_science_claim():
    result = quality(bundle(visibility="SUMMARY"))
    assert result.status == QualityGateStatus.PASSED_WITH_WARNINGS.value
    assert result.missing_sources
    assert "NOT an admitted" in result.warnings[0]


def test_false_model_yes_is_blocked_with_real_negative_evidence():
    b = bundle(valid=False)
    b["answer"]["claim_valid"] = "YES"
    assert quality(b).status == QualityGateStatus.FAILED_BLOCKING.value


def test_false_no_change_is_blocked_when_criterion_versions_differ():
    b = bundle()
    b["answer"]["criterion_changed"] = "NO"
    assert "MODEL_CONTRADICTS_EVIDENCE:criterion_changed" in quality(b).blocking_issues


def test_allowed_model_cannot_invent_next_action():
    b = bundle(valid=False)
    b["answer"]["next_action"] = "NO_ACTION"
    r = quality(b)
    assert r.status == QualityGateStatus.FAILED_BLOCKING.value
    assert "MODEL_RESPONSE_CONTRACT_INVALID" in r.blocking_issues


@pytest.mark.parametrize("mutation", [
    "source", "oracle", "packet", "goal", "selected_candidate",
    "class_correct", "class_total", "missing_holdout", "missing_history",
    "changed_history", "missing_source_id", "threshold", "unversioned_criterion",
    "duplicate_physical_class", "unbalanced_weights",
])
def test_adversarial_evidence_modification_fails_closed(mutation):
    b = bundle()
    pin = kwargs(b)
    if mutation == "source":
        pin["source_bytes"] = b["source"] + b" forged"
    elif mutation == "oracle":
        pin["oracle_bytes"] += b" "
    elif mutation == "packet":
        pin["packet_bytes"] += b" "
    else:
        packet = b["packet"]
        oracle = b["oracle"]
        if mutation == "goal":
            packet["goal"]["numerator"] = 1
        elif mutation == "selected_candidate":
            packet["selected_candidate"] = "centroid:forged"
        elif mutation == "class_correct":
            packet["holdout_by_class"][0]["correct"] = 20
        elif mutation == "class_total":
            packet["holdout_by_class"][0]["total"] = 42
        elif mutation == "missing_holdout":
            packet.pop("holdout_by_class")
        elif mutation == "missing_history":
            packet.pop("weight_versions")
        elif mutation == "changed_history":
            packet["weight_versions"][1] = [0.5, 0.5]
        elif mutation == "missing_source_id":
            packet.pop("source_id")
        elif mutation == "threshold":
            oracle["goal"]["numerator"] = 1
        elif mutation == "unversioned_criterion":
            oracle["criterion_version"] = ""
        elif mutation == "duplicate_physical_class":
            oracle["holdout_by_class"][1]["class"] = "a"
        elif mutation == "unbalanced_weights":
            oracle["weight_versions"][1] = [0.8, 0.8]
        pin = kwargs(b)
    result = evaluate_scientific_evidence_consistency_gate(**pin)
    assert result.status == QualityGateStatus.FAILED_BLOCKING.value, mutation


@pytest.mark.parametrize("part", [
    "expected_packet_sha256", "expected_source_sha256",
    "expected_oracle_sha256", "oracle_bytes", "packet_bytes", "source_bytes",
    "model_response_bytes"
])
def test_missing_trust_witness_or_model_response_fails_closed(part):
    x = kwargs(bundle())
    x[part] = None
    assert evaluate_scientific_evidence_consistency_gate(**x).status == (
        QualityGateStatus.FAILED_BLOCKING.value
    )


def test_model_duplicate_json_key_cannot_override_prior_verdict():
    x = kwargs(bundle())
    x["model_response_bytes"] = (
        b'{"criterion_changed":"YES","claim_valid":"NO","claim_valid":"YES",'
        b'"next_action":"INDEPENDENT_REPLICATION"}'
    )
    r = evaluate_scientific_evidence_consistency_gate(**x)
    assert "MALFORMED_OR_DUPLICATE_JSON" in r.blocking_issues


def test_correct_full_no_criterion_change_valid_gold():
    assert quality(bundle(changed=False)).status == QualityGateStatus.PASSED.value


def ready(**extra):
    return evaluate_submission_gate(
        has_fresh_guidelines=True, has_metadata=True, has_files_list=True,
        has_statements=True, blocking_risks_resolved=True, **extra
    )


def test_native_submission_integration_requires_science_not_model_self_certification():
    r = ready(has_empirical_claim=True, author_decision="ACCEPT",
              coauthor_consent_verified=True)
    assert r.status == QualityGateStatus.FAILED_BLOCKING.value
    assert any("independent warrant" in x for x in r.blocking_issues)


def test_native_submission_integration_rejects_negative_science():
    r = ready(has_empirical_claim=True, empirical_evidence=kwargs(bundle(valid=False)),
              author_decision="ACCEPT", coauthor_consent_verified=True)
    assert r.status == QualityGateStatus.FAILED_BLOCKING.value
    assert any("independent warrant" in x for x in r.blocking_issues)


def test_native_submission_integration_rejects_summary_abstention_as_promotable():
    r = ready(has_empirical_claim=True,
              empirical_evidence=kwargs(bundle(visibility="SUMMARY")),
              author_decision="ACCEPT", coauthor_consent_verified=True)
    assert r.status == QualityGateStatus.FAILED_BLOCKING.value


def test_native_submission_integration_cannot_turn_technical_pass_into_author_consent():
    r = ready(has_empirical_claim=True, empirical_evidence=kwargs(bundle()),
              author_decision="HOLD", coauthor_consent_verified=False)
    assert r.status == QualityGateStatus.FAILED_BLOCKING.value
    assert any("Author/coauthor" in x for x in r.blocking_issues)


def test_native_submission_safely_passes_only_if_science_and_authority_present():
    r = ready(has_empirical_claim=True, empirical_evidence=kwargs(bundle()),
              author_decision="ACCEPT", coauthor_consent_verified=True)
    assert r.status == QualityGateStatus.PASSED.value
    assert "manual" in r.recommendation.lower()


def test_legacy_nonempirical_submission_check_is_unchanged():
    r = ready()
    assert r.status == QualityGateStatus.PASSED.value


def test_science_evidence_supplied_without_explicit_flag_still_triggers_gate():
    r = ready(empirical_evidence=kwargs(bundle(valid=False)),
              author_decision="ACCEPT", coauthor_consent_verified=True)
    assert r.status == QualityGateStatus.FAILED_BLOCKING.value
