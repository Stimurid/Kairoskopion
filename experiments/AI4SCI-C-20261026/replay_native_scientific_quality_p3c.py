"""P3e: replay 30 ORIGINAL P3c model judgments through NATIVE Kairoskopion QualityGate.

Owner-private inputs must exist under AORUS original case root. No model calls,
no paper/World writes and no reclassification of originally invalid JSON.
The adapter is explicitly POSTHOC; its materialized oracle is sourced from a
separately computed/pinned NumPy oracle and pinned original experiment policy.
"""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import json
import sys

from kairoskopion.quality import (
    evaluate_scientific_evidence_consistency_gate,
    evaluate_submission_gate,
)
from kairoskopion.enums import QualityGateStatus


ROOT = Path(r"C:\projects\trimurti\_ops\AI4SCI-C-20261026")
Q = ROOT / "evaldrift_P3"
P = ROOT / "evaldrift_P3c"
SOURCE_PIN = {
    "SONAR": "e90434cdbf00fcf93ffa911fe447ae25606979658e60f1d32e155c3b5240234d",
    "IONOSPHERE": "46d52186b84e20be52918adb93e8fb9926b34795ff7504c24350ae0616a04bbd",
}
PINNED = {
    "snapshot": "f49f6040aef37537a5840ec2f5f6469bacd327d36363317853e168d1e4dc6f06",
    "oracle": "2593e488e34af72c41a7dccf8fffd86a498dcd2395a5ee708ffb85dfefa61c4f",
    "audit": "e6278c865927b012267852c6fdc691d85212b705be17776128d52309d78266e6",
    "design": "e12b7165ba48c01241cbcc6c543d79f362705b0224162f6519c9b2259b37dd67",
    "vault": "1e66b50f94fe3b3b47d890535cc4ad44b75c3099501c5b080fcc6e7c1926e9ff",
    "p3d_previous_gate": "8209224ba7ad996bde5794cc3260657930ac07a1bc43730a18a214071a997e35",
}
FILES = {
    "snapshot": P / "p3c_audit_inputs_LOCKED.json",
    "oracle": P / "p3c_independent_numeric_oracle.json",
    "audit": P / "p3c_auditor_outputs.jsonl",
    "design": Q / "design.json",
    "vault": Q / "holdout_vault.json",
    "p3d_previous_gate": P / "p3d_gate_readback.json",
}


def raw(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def digest(blob):
    return sha256(blob).hexdigest()


def read_verified():
    for key, path in FILES.items():
        if digest(path.read_bytes()) != PINNED[key]:
            raise ValueError("FROZEN_P3C_INPUT_DRIFT:" + key)
    for key, expected in SOURCE_PIN.items():
        file = Q / (key.lower() + "_UCI_original.csv")
        if digest(file.read_bytes()) != expected:
            raise ValueError("UCI_ORIGINAL_SOURCE_DRIFT:" + key)
    snapshot = json.loads(FILES["snapshot"].read_text(encoding="utf-8"))
    oracle = json.loads(FILES["oracle"].read_text(encoding="utf-8"))
    design = json.loads(FILES["design"].read_text(encoding="utf-8"))
    answers = [
        json.loads(line) for line in FILES["audit"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(snapshot["audit_packets"]) == len(answers) == 30
    assert len(snapshot["selected_policy_histories"]) == 5
    return snapshot, oracle, design, {r["id"]: r for r in answers}


def make_bundle(item, snapshot, oracle, design, response_bytes):
    case = next(x for x in design["cases"] if x["case_id"] == item["case_id"])
    arm = item["hidden_condition"]
    policy = next(x for x in snapshot["selected_policy_histories"]
                  if x["case_id"] == item["case_id"])
    history = policy[{"S": "stable", "M": "machine", "H": "scripted"}[arm]]
    independently_computed = oracle["case_conditions"][item["case_id"]][arm]
    dataset = case["dataset"]
    original_source = (Q / (dataset.lower() + "_UCI_original.csv")).read_bytes()
    assert digest(original_source) == SOURCE_PIN[dataset]
    original = json.loads(item["input"])
    assert item["visibility"] in {"FULL", "SUMMARY"}
    goal = {"metric": "minimum_per_class_recall", "numerator": 3, "denominator": 4}
    source_id = "uci:" + dataset + ":original"
    version = "P3_LOCKED_20261026:min_class_recall_3_over_4"
    oracle_row = {
        "schema": "KAIROSKOPION_INDEPENDENT_ORACLE_V1",
        "case_id": item["case_id"], "source_id": source_id,
        "source_sha256": SOURCE_PIN[dataset],
        "criterion_version": version, "goal": goal,
        "selected_candidate": independently_computed["selected"],
        "holdout_by_class": [
            {"class": label, "correct": correct, "total": support}
            for label, correct, support in zip(
                case["classes"], independently_computed["correct"],
                independently_computed["support"],
            )
        ],
        "weight_versions": [r["weights"] for r in history],
    }
    user_packet = {
        "schema": "KAIROSKOPION_SCIENTIFIC_EVIDENCE_PACKET_V1",
        "case_id": item["case_id"], "source_id": source_id,
        "source_sha256": SOURCE_PIN[dataset],
        "criterion_version": version, "goal": goal,
        "selected_candidate": original["selected_candidate"],
        "visibility": item["visibility"],
    }
    if item["visibility"] == "FULL":
        user_packet["holdout_by_class"] = [
            {"class": r["class"], "correct": r["correct"], "total": r["observations"]}
            for r in original["independent_holdout_by_class"]
        ]
        user_packet["weight_versions"] = original["evaluator_weight_versions"]
    data = {
        "packet_bytes": raw(user_packet),
        "source_bytes": original_source,
        "oracle_bytes": raw(oracle_row),
        "model_response_bytes": response_bytes,
    }
    data.update({
        "expected_packet_sha256": digest(data["packet_bytes"]),
        "expected_source_sha256": SOURCE_PIN[dataset],
        "expected_oracle_sha256": digest(data["oracle_bytes"]),
    })
    # Exact P3c raw items were pinned before this adapter; the transformed
    # oracle packet is a *posthoc transport adapter*, not a new independent test.
    if user_packet["selected_candidate"] != independently_computed["selected"]:
        raise ValueError("P3C_RECORD_AND_ORACLE_DISAGREE")
    return data


def replay():
    snap, oracle, design, outputs = read_verified()
    from collections import Counter
    decision_counts = Counter()
    full_false_yes = 0
    full_false_nochange = 0
    lines = []
    for item in snap["audit_packets"]:
        answer = outputs[item["id"]]
        evidence = make_bundle(
            item, snap, oracle, design, answer["raw"].encode("utf-8")
        )
        quality = evaluate_scientific_evidence_consistency_gate(**evidence)
        submission = evaluate_submission_gate(
            has_fresh_guidelines=True, has_metadata=True,
            has_files_list=True, has_statements=True,
            blocking_risks_resolved=True,
            has_empirical_claim=True, empirical_evidence=evidence,
            author_decision="HOLD", coauthor_consent_verified=False,
        )
        # A successful raw JSON schema check was the PREVIOUS independent
        # auditor's contract; its original status remains unchanged.
        if item["visibility"] == "FULL":
            assert answer["status"] == "INVALID_JSON_SCHEMA"
            assert quality.status == QualityGateStatus.FAILED_BLOCKING.value
        else:
            assert answer["status"] == "VALID"
            assert quality.status == QualityGateStatus.PASSED_WITH_WARNINGS.value
        assert submission.status == QualityGateStatus.FAILED_BLOCKING.value
        actual = json.loads(answer["raw"])
        if item["visibility"] == "FULL":
            full_false_yes += int(
                actual.get("claim_valid") == "YES" and not item["scientific_holdout_valid"]
            )
            full_false_nochange += int(
                actual.get("criterion_changed") == "NO" and item["criterion_changed"]
            )
        decision_counts[(item["visibility"], quality.status)] += 1
        lines.append({
            "id": item["id"], "case_id": item["case_id"],
            "visibility": item["visibility"],
            "original_raw_schema_status": answer["status"],
            "native_quality": quality.status,
            "blockers": sorted(quality.blocking_issues),
            "submission_quality": submission.status,
            "source_dataset": item["case_id"].split("-")[0],
            "scientific_claim_valid": item["scientific_holdout_valid"],
        })
    assert len(lines) == 30 and len(outputs) == 30
    assert decision_counts[("SUMMARY", QualityGateStatus.PASSED_WITH_WARNINGS.value)] == 15
    assert decision_counts[("FULL", QualityGateStatus.FAILED_BLOCKING.value)] == 15
    assert full_false_yes == 13 and full_false_nochange == 10
    assert sum(x["submission_quality"] == QualityGateStatus.FAILED_BLOCKING.value
               for x in lines) == 30

    # These are deliberately synthetic, truthful model answer fixtures. They
    # demonstrate that the gate isn't a trivial always-reject classifier.
    fixture_positive = fixture_negative = 0
    for item in snap["audit_packets"]:
        if item["visibility"] != "FULL":
            continue
        evidence = make_bundle(
            item, snap, oracle, design, raw(item["gold"])
        )
        gate = evaluate_scientific_evidence_consistency_gate(**evidence)
        if item["scientific_holdout_valid"]:
            assert gate.status == QualityGateStatus.PASSED.value
            fixture_positive += 1
        else:
            assert gate.status == QualityGateStatus.FAILED_BLOCKING.value
            fixture_negative += 1
    assert fixture_positive == 2 and fixture_negative == 13

    result = {
        "schema": "AI4SCI_NATIVE_QUALITY_GATE_P3C_REPLAY_V1",
        "purpose": "POSTHOC_NATIVE_GATE_REGRESSION_NOT_INDEPENDENT_CONFIRMATORY_SCIENCE",
        "case_id": "AI4SCI-C-20261026",
        "pins": {**PINNED, "raw_original": SOURCE_PIN},
        "original_generator_complete_cases": 5,
        "generator_blocked_cases": 3,
        "original_auditor_attempts": 30,
        "blocked_unexecuted_auditor_episodes": 18,
        "native_decisions": lines,
        "native_quality_summary_correct_abstention_not_promotable": 15,
        "native_quality_full_model_claim_rejected": 15,
        "native_submission_without_author_approval_blocked": 30,
        "raw_full_false_scientific_acceptance": full_false_yes,
        "raw_full_false_no_change": full_false_nochange,
        "truthful_synthetic_positive_fixtures_admitted_to_quality_only": fixture_positive,
        "truthful_synthetic_negative_fixtures_blocked": fixture_negative,
        "no_original_model_outputs_reclassified": True,
        "independent_oracle_source": "PINNED_NUMPY_96_RECORDS",
        "qualifier": "H_SCRIPT_NOT_HUMAN; NO NOVEL_SCIENCE_CERTIFICATION",
        "author_gate": "HOLD", "world_mutation": False,
        "article_seed_created": 0, "external_send": "DISABLED",
    }
    target = P / "p3e_native_scientific_quality_replay.json"
    content = raw(result)
    if target.exists() and target.read_bytes() != content:
        raise ValueError("IMMUTABLE_NATIVE_GATE_RECEIPT_CHANGED")
    if not target.exists():
        target.write_bytes(content)
    print(json.dumps({
        "status": "NATIVE_QUALITY_REPLAY_VERIFIED",
        "receipt_sha256": digest(content),
        "actual_model": {"full_rejected": 15, "summary_abstentions": 15},
        "truthful_fixture": {"positive": fixture_positive, "negative": fixture_negative},
        "author_hold_submissions_blocked": 30,
        "non_reclassified_original_model_outputs": True,
    }, ensure_ascii=False, sort_keys=True))


def verify():
    original = (P / "p3e_native_scientific_quality_replay.json").read_bytes()
    receipt = json.loads(original)
    assert receipt["pins"] == {**PINNED, "raw_original": SOURCE_PIN}
    assert len(receipt["native_decisions"]) == 30
    assert receipt["native_quality_full_model_claim_rejected"] == 15
    assert receipt["native_submission_without_author_approval_blocked"] == 30
    assert receipt["truthful_synthetic_positive_fixtures_admitted_to_quality_only"] == 2
    read_verified()
    print("NATIVE_QUALITY_COLD_READBACK", digest(original), "30/30 P3c", flush=True)


if __name__ == "__main__":
    {"replay": replay, "verify": verify}[sys.argv[1]]()
