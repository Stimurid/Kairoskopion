import json

import pytest

from kairoskopion.services.citation_intake_z0 import persist_audit
from kairoskopion.services.citation_r1_batch import blocked, consume, prepare


def _fixture(tmp_path):
    draft = tmp_path / "synthetic.md"
    draft.write_text("A claim (Luckin 2016). Another (Descartes 1701).", encoding="utf-8")
    _, audit = persist_audit(draft, tmp_path / "z0")
    queue = audit.with_name("citation_work_orders.jsonl")
    orders = [json.loads(line) for line in queue.read_text(encoding="utf-8").splitlines()]
    source_sha = json.loads(audit.read_text(encoding="utf-8"))["source"]["sha256"]
    cases = [{"case_id": f"R1-0{i}", "inputs": [], "checks": {"source_evidence": []}}
             for i in range(1, 6)]
    protocols = tmp_path / "protocols.json"
    protocols.write_text(json.dumps({"cases": cases}), encoding="utf-8")
    rows = []
    for n in range(13):
        case_id = f"R1-0{min(n // 3 + 1, 5)}" if n < 10 else "R1-05"
        ids = [] if n >= 10 else [orders[n % 2]["work_order_id"]]
        if n == 2:
            ids = [o["work_order_id"] for o in orders]
        rows.append({"task_id": f"r1-task-{n:02}", "case_id": case_id,
                     "step_index": n, "source_manuscript_sha256": source_sha,
                     "work_order_ids": ids, "required_operation": "CHECK_SOURCE",
                     "review_status": "PENDING", "source_evidence_uris": [],
                     "owner_authority": "OWNER", "no_automatic_document_write": True,
                     "not_a_completed_hunt": True})
    followups = tmp_path / "followups.jsonl"
    followups.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return audit, queue, followups, protocols, rows


def test_thirteen_tasks_two_process_negative_return_and_replay(tmp_path):
    audit, queue, followups, protocols, rows = _fixture(tmp_path)
    requests, returns, states = (tmp_path / name for name in ("requests", "returns", "states"))
    manifest = prepare(audit, queue, followups, protocols, requests)
    assert manifest["tasks"] == 13
    assert manifest["author_source_needs"] == 3
    assert manifest["distinct_z0_orders"] == 2
    assert blocked(requests, returns)["returns"] == 13
    result = consume(audit, queue, followups, protocols, requests, returns, states)
    assert result["blocked"] == 13
    assert result["publication_ready"] == 0
    assert consume(audit, queue, followups, protocols, requests, returns, states) == result
    unanchored = json.loads((states / "r1-task-10.state.json").read_text())
    assert unanchored["kind"] == "AUTHOR_SOURCE_NEED"
    assert unanchored["work_order_ids"] == []
    assert unanchored["verification"] == {v: "NOT_CHECKED" for v in ("V1", "V2", "V3", "V4", "V5")}


def test_wrong_correlation_version_drift_and_permission_denial(tmp_path):
    audit, queue, followups, protocols, rows = _fixture(tmp_path)
    requests, returns = tmp_path / "requests", tmp_path / "returns"
    prepare(audit, queue, followups, protocols, requests)
    blocked(requests, returns)
    path = returns / "r1-task-00.return.json"
    ret = json.loads(path.read_text())
    ret["correlation_id"] = "wrong"
    path.write_text(json.dumps(ret))
    with pytest.raises(ValueError, match="correlation mismatch"):
        consume(audit, queue, followups, protocols, requests, returns, tmp_path / "states")
    ret["correlation_id"] = json.loads((requests / "r1-task-00.request.json").read_text())["correlation_id"]
    ret.update(outcome="OBSERVED", reason=None, read_depth="ANCHORED_PASSAGE",
               source_evidence=[{"provider": "reader", "acquisition_authorized": False}])
    path.write_text(json.dumps(ret))
    with pytest.raises(ValueError, match="authorized provider"):
        consume(audit, queue, followups, protocols, requests, returns, tmp_path / "states")
    rows[0]["source_manuscript_sha256"] = "0" * 64
    followups.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="version drift"):
        prepare(audit, queue, followups, protocols, tmp_path / "drift")


def test_owner_utf8_bom_without_mutating_original(tmp_path):
    audit, queue, followups, protocols, _ = _fixture(tmp_path)
    original_followups = followups.read_bytes()
    original_protocols = protocols.read_bytes()
    followups.write_bytes(bytes([0xEF, 0xBB, 0xBF]) + original_followups)
    protocols.write_bytes(bytes([0xEF, 0xBB, 0xBF]) + original_protocols)
    from kairoskopion.services.citation_r1_batch import prepare
    m = prepare(audit, queue, followups, protocols, tmp_path / "bom_requests")
    assert m["tasks"] == 13
    assert followups.read_bytes().startswith(bytes([0xEF, 0xBB, 0xBF]))
    assert protocols.read_bytes().startswith(bytes([0xEF, 0xBB, 0xBF]))


def test_observed_evidence_real_correlation_and_limited_science(tmp_path):
    from datetime import datetime, timezone
    from kairoskopion.services.citation_r1_batch import consume, blocked, prepare
    audit, queue, followups, protocols, _ = _fixture(tmp_path)
    requests, returns, states = [tmp_path / v for v in ("rq", "ret", "states")]
    prepare(audit, queue, followups, protocols, requests)
    blocked(requests, returns)
    req = json.loads((requests / "r1-task-00.request.json").read_text())
    assert len(req["work_order_ids"]) == 1
    order = next(json.loads(l) for l in queue.read_text().splitlines() if
                 json.loads(l)["work_order_id"] == req["work_order_ids"][0])
    rp = returns / "r1-task-00.return.json"
    ret = json.loads(rp.read_text())
    ret.update({
        "outcome": "OBSERVED", "reason": None,
        "provider": "SYNTHETIC_AUTHORIZED_FIXTURE", "acquisition_authorized": True,
        "read_depth": "ANCHORED_PASSAGE",
        "source_kind": "SYNTHETIC_PUBLIC_PRIMARY",
        "access": "READABLE_FULL", "license": "CC0_TEST_FIXTURE",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "witness_class": "MANUAL_WEB_OBSERVED",
        "source_evidence": [{
            "work_order_id": req["work_order_ids"][0],
            "intake_id": order["intake_id"], "z0_case_id": order["case_id"],
            "source_kind": "SYNTHETIC_PUBLIC_PRIMARY",
            "read_depth": "ANCHORED_PASSAGE",
            "access": "READABLE_FULL", "license": "CC0_TEST_FIXTURE",
            "provider": "SYNTHETIC_AUTHORIZED_FIXTURE",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "acquisition_authorized": True,
            "witness_class": "MANUAL_WEB_OBSERVED",
            "work_id": "work-fixture", "edition_id": "edition-fixture",
            "witness_id": "witness-fixture", "locator": "p.1 exact",
            "passage_id": "passage-fixture", "byte_sha256": "a" * 64
        }]
    })
    rp.write_text(json.dumps(ret))
    result = consume(audit, queue, followups, protocols, requests, returns, states)
    assert result["observed"] == 1
    assert result["blocked"] == 12
    assert result["publication_ready"] == 0
    state = json.loads((states / "r1-task-00.state.json").read_text())
    assert state["citation_gate"] == "NOT_PUBLICATION_READY"
    assert all(x == "NOT_CHECKED" for x in state["verification"].values())


def test_observed_wrong_intake_and_compound_without_order_rejected(tmp_path):
    from datetime import datetime, timezone
    from kairoskopion.services.citation_r1_batch import consume, blocked, prepare
    audit, queue, followups, protocols, _ = _fixture(tmp_path)
    requests, returns = tmp_path / "rq", tmp_path / "ret"
    prepare(audit, queue, followups, protocols, requests)
    blocked(requests, returns)
    req = json.loads((requests / "r1-task-00.request.json").read_text())
    rp = returns / "r1-task-00.return.json"
    ret = json.loads(rp.read_text())
    ret.update({
        "outcome": "OBSERVED", "reason": None, "provider": "SYNTHETIC",
        "acquisition_authorized": True, "read_depth": "ANCHORED_PASSAGE",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_kind": "SYNTHETIC_PRIMARY", "access": "READABLE_FULL", "license": "CC0",
        "witness_class": "MANUAL_WEB_OBSERVED",
        "source_evidence": [{
            "work_order_id": req["work_order_ids"][0], "intake_id": "forged",
            "work_id": "a", "edition_id": "b", "witness_id": "c",
            "locator": "p1", "passage_id": "p", "byte_sha256": "a"*64,
            "witness_class": "MANUAL_WEB_OBSERVED",
        }]
    })
    rp.write_text(json.dumps(ret))
    with pytest.raises(ValueError, match="wrong original intake"):
        consume(audit, queue, followups, protocols, requests, returns, tmp_path / "s1")
    # The third synthetic task has two distinct source identities; no first-hit success.
    ret0 = json.loads((returns / "r1-task-02.return.json").read_text())
    req2 = json.loads((requests / "r1-task-02.request.json").read_text())
    assert len(req2["work_order_ids"]) == 2
    ret0.update({
        "outcome": "OBSERVED", "reason": None, "provider": "SYNTHETIC",
        "acquisition_authorized": True, "read_depth": "METADATA_ONLY",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_kind": "SYNTHETIC_METADATA", "access": "READABLE_FULL", "license": "CC0",
        "source_evidence": [{"work_id": "a", "edition_id": "b", "witness_id": "c", "locator": "p1"}]
    })
    (returns / "r1-task-02.return.json").write_text(json.dumps(ret0))
    with pytest.raises(ValueError, match="wrong original intake|Ambiguous Z0 link"):
        consume(audit, queue, followups, protocols, requests, returns, tmp_path / "s2")
