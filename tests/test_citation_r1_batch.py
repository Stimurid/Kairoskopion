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
