import copy
import json
from pathlib import Path

import pytest

from kairoskopion.services import citation_indago_r3_bridge as bridge
from kairoskopion.services.citation_intake_z0 import persist_audit

FIXTURE = Path(__file__).parent / "fixtures" / "indago_evidence_return_real_shape.json"


def _bound(tmp_path):
    manuscript = tmp_path / "article.md"
    manuscript.write_text("A bounded claim (Frolov 2026).\n", encoding="utf-8")
    _, audit_path = persist_audit(manuscript, tmp_path / "z0")
    queue = audit_path.parent / "citation_work_orders.jsonl"
    order = json.loads(queue.read_text(encoding="utf-8").splitlines()[0])
    evidence = json.loads(FIXTURE.read_text(encoding="utf-8"))
    evidence.update(case_id=order["case_id"], work_order_id=order["work_order_id"],
                    intake_id=order["intake_id"],
                    manuscript_sha256=order["source_sha256"])
    return manuscript, audit_path, queue, order, evidence


def _consume(tmp_path, evidence):
    _, audit, queue, _, base = _bound(tmp_path)
    base.update(evidence)
    return bridge.consume_evidence_return(audit, queue, base, tmp_path / "ledger"), base


def test_happy_path_real_shape_creates_typed_r1_state(tmp_path):
    result, evidence = _consume(tmp_path, {})
    assert result.receipt["bridge_status"] == "ANCHORED"
    assert result.receipt["provider_execution"] == "OPEN_NOT_DEMONSTRATED"
    assert result.state["outcome"] == "OBSERVED"
    assert result.state["source_evidence"][0]["work_id"] == evidence["source"]["work_id"]
    assert set(result.state["verification"].values()) == {"NOT_CHECKED"}
    assert result.state["scientific_certification"] is False


def test_no_passage_is_negative_evidence_not_citation_error(tmp_path):
    result, _ = _consume(tmp_path, {"outcome": "NO_PASSAGE", "passages": []})
    assert result.state["outcome"] == "NEGATIVE"
    assert "NO_PASSAGE" in result.state["negative_evidence"]
    assert result.state["source_to_claim_relation"] == "NOT_CHECKED"


def test_more_than_one_passage_is_ambiguous_not_first_match(tmp_path):
    _, _, _, _, evidence = _bound(tmp_path)
    second = copy.deepcopy(evidence["passages"][0])
    second["passage_id"] = "passage:second"
    second["locator"] = "printed-page:109"
    evidence["passages"].append(second)
    result = bridge.consume_evidence_return(*_bound(tmp_path)[1:3], evidence,
                                            tmp_path / "ledger")
    assert result.receipt["bridge_status"] == "ANCHOR_AMBIGUOUS"
    assert result.state["source_evidence"] == []
    assert result.state["source_to_claim_relation"] == "NOT_CHECKED"


def test_provider_failure_is_preserved_without_defect_inference(tmp_path):
    result, _ = _consume(tmp_path, {
        "outcome": "PROVIDER_FAILURE", "passages": [],
        "errors": ["PROVIDER_TIMEOUT"], "negative_evidence": []})
    assert result.state["outcome"] == "ERROR"
    assert result.state["errors"] == ["PROVIDER_TIMEOUT"]
    assert result.state["source_to_claim_relation"] == "NOT_CHECKED"


def test_identical_return_replays_idempotently(tmp_path):
    _, audit, queue, _, evidence = _bound(tmp_path)
    ledger = tmp_path / "ledger"
    first = bridge.consume_evidence_return(audit, queue, evidence, ledger)
    second = bridge.consume_evidence_return(audit, queue, evidence, ledger)
    assert first.receipt["evidence_id"] == second.receipt["evidence_id"]
    assert second.replayed is True
    assert second.receipt["replay_status"] == "IDEMPOTENT_REPLAY"
    assert len(list(ledger.glob("*.state.json"))) == 1


def test_wrong_case_and_orphan_fail_closed(tmp_path):
    _, audit, queue, _, evidence = _bound(tmp_path)
    evidence["case_id"] = "cr_wrong"
    with pytest.raises(bridge.IndagoBridgeRefusal) as caught:
        bridge.consume_evidence_return(audit, queue, evidence, tmp_path / "ledger")
    assert caught.value.code == "WRONG_CASE_OR_STALE"
    evidence["work_order_id"] = "wo_orphan"
    with pytest.raises(bridge.IndagoBridgeRefusal) as caught:
        bridge.consume_evidence_return(audit, queue, evidence, tmp_path / "ledger")
    assert caught.value.code == "ORPHAN_WORK_ORDER"


def test_fake_and_cross_source_passages_fail_closed(tmp_path):
    _, audit, queue, _, evidence = _bound(tmp_path)
    evidence["passages"][0]["exact_text"] += " tampered"
    with pytest.raises(bridge.IndagoBridgeRefusal) as caught:
        bridge.consume_evidence_return(audit, queue, evidence, tmp_path / "ledger")
    assert caught.value.code == "FAKE_PASSAGE"
    _, _, _, _, evidence = _bound(tmp_path)
    evidence["passages"][0]["witness_id"] = "pdf:other"
    with pytest.raises(bridge.IndagoBridgeRefusal) as caught:
        bridge.consume_evidence_return(audit, queue, evidence, tmp_path / "ledger2")
    assert caught.value.code == "CROSS_SOURCE_PASSAGE_ANCHOR"


def test_end_to_end_z0_r1_r3_r2_r4_receipt(tmp_path):
    manuscript, audit, queue, _, evidence = _bound(tmp_path)
    return_path = tmp_path / "return.json"
    return_path.write_text(json.dumps(evidence), encoding="utf-8")
    receipt = bridge.consume_and_plan(audit, queue, return_path,
                                      tmp_path / "ledger", tmp_path / "plan",
                                      manuscript)
    assert receipt["bridge_receipt"]["bridge_status"] == "ANCHORED"
    plan = receipt["r2_r4_plan"]
    assert plan["r3_reentry"] is None
    assert "IDENTITY_AND_PASSAGE_PROPOSED" in {
        c["evidence_label"] for c in plan["r4_candidates"]}
    assert set(plan["verification"].values()) == {"NOT_CHECKED"}
    assert plan["citation_gate"] == "NOT_PUBLICATION_READY"
