"""G6B independent review: provider metadata never proves a primary quotation."""
import copy
import hashlib
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


def _with_witness(tmp_path, *, text=None, prefix=""):
    manuscript, audit, queue, order, evidence = _bound(tmp_path)
    body = evidence["passages"][0]["exact_text"]
    witness = tmp_path / "owned_source.txt"
    witness.write_text(prefix + (body if text is None else text), encoding="utf-8")
    digest = hashlib.sha256(witness.read_bytes()).hexdigest()
    evidence["source"]["source_sha256"] = digest
    evidence["source"]["witness_id"] = "text:" + digest
    evidence["passages"][0]["witness_id"] = "text:" + digest
    evidence["passages"][0]["locator"] = "text-char-offset:" + str(len(prefix))
    return manuscript, audit, queue, order, evidence, witness


def _consume(tmp_path, changes):
    _, audit, queue, _, evidence = _bound(tmp_path)
    evidence.update(changes)
    return bridge.consume_evidence_return(audit, queue, evidence,
                                          tmp_path / "ledger"), evidence


def test_no_witness_provider_cannot_self_certify_a_fake_anchored_passage(tmp_path):
    result, evidence = _consume(tmp_path, {})
    assert result.receipt["bridge_status"] == "WITNESS_UNVERIFIED"
    assert result.state["outcome"] == "UNVERIFIED"
    assert result.state["source_evidence"] == []
    assert result.state["reported_passages"][0]["passage_id"] == evidence["passages"][0]["passage_id"]
    assert result.state["witness_attestation"]["bytes_verified"] is False
    assert result.receipt["provider_execution"] == "OPEN_NOT_DEMONSTRATED"
    assert set(result.state["verification"].values()) == {"NOT_CHECKED"}


def test_real_owner_text_attests_one_unique_passage_without_scholarly_certification(tmp_path):
    _, audit, queue, _, evidence, witness = _with_witness(tmp_path)
    result = bridge.consume_evidence_return(audit, queue, evidence,
                                            tmp_path / "ledger", witness_path=witness)
    assert result.receipt["bridge_status"] == "ANCHORED"
    assert result.state["outcome"] == "OBSERVED"
    assert result.state["source_evidence"][0]["work_id"] == evidence["source"]["work_id"]
    assert result.state["witness_attestation"]["bytes_verified"] is True
    assert result.state["witness_attestation"]["uniqueness_verified"] is True
    assert set(result.state["verification"].values()) == {"NOT_CHECKED"}
    assert result.state["scientific_certification"] is False


def test_no_passage_is_negative_evidence_not_citation_error(tmp_path):
    result, _ = _consume(tmp_path, {"outcome": "NO_PASSAGE", "passages": []})
    assert result.state["outcome"] == "NEGATIVE"
    assert "NO_PASSAGE" in result.state["negative_evidence"]
    assert result.state["source_to_claim_relation"] == "NOT_CHECKED"


def test_more_than_one_reported_passage_is_ambiguous_not_first_match(tmp_path):
    _, audit, queue, _, evidence, witness = _with_witness(tmp_path)
    second = copy.deepcopy(evidence["passages"][0])
    second["passage_id"] = "passage:second"
    evidence["passages"].append(second)
    result = bridge.consume_evidence_return(audit, queue, evidence, tmp_path / "ledger",
                                            witness_path=witness)
    assert result.receipt["bridge_status"] == "ANCHOR_AMBIGUOUS"
    assert result.state["source_evidence"] == []
    assert result.state["source_to_claim_relation"] == "NOT_CHECKED"


def test_actual_witness_has_two_occurrences_prevents_first_match(tmp_path):
    _, audit, queue, _, evidence, witness = _with_witness(tmp_path)
    quote = evidence["passages"][0]["exact_text"]
    witness.write_text(quote + "\n" + quote, encoding="utf-8")
    digest = hashlib.sha256(witness.read_bytes()).hexdigest()
    evidence["source"]["source_sha256"] = digest
    evidence["source"]["witness_id"] = "text:" + digest
    evidence["passages"][0]["witness_id"] = "text:" + digest
    result = bridge.consume_evidence_return(audit, queue, evidence,
                                            tmp_path / "ledger", witness_path=witness)
    assert result.receipt["bridge_status"] == "ANCHOR_AMBIGUOUS"
    assert result.state["witness_attestation"]["actual_passage_occurrences"] == 2


def test_provider_failure_is_preserved_without_defect_inference(tmp_path):
    result, _ = _consume(tmp_path, {
        "outcome": "PROVIDER_FAILURE", "passages": [],
        "errors": ["PROVIDER_TIMEOUT"], "negative_evidence": []})
    assert result.state["outcome"] == "ERROR"
    assert result.state["errors"] == ["PROVIDER_TIMEOUT"]
    assert result.state["source_to_claim_relation"] == "NOT_CHECKED"


def test_identical_return_replays_idempotently(tmp_path):
    _, audit, queue, _, evidence, witness = _with_witness(tmp_path)
    ledger = tmp_path / "ledger"
    first = bridge.consume_evidence_return(audit, queue, evidence, ledger,
                                            witness_path=witness)
    second = bridge.consume_evidence_return(audit, queue, evidence, ledger,
                                             witness_path=witness)
    assert first.receipt["evidence_id"] == second.receipt["evidence_id"]
    assert second.replayed is True
    assert second.receipt["replay_status"] == "IDEMPOTENT_REPLAY"
    assert len(list(ledger.glob("*.state.json"))) == 1


def test_unverified_replay_cannot_silently_upgrade_to_verified(tmp_path):
    _, audit, queue, _, evidence, witness = _with_witness(tmp_path)
    ledger = tmp_path / "ledger"
    bridge.consume_evidence_return(audit, queue, evidence, ledger)
    with pytest.raises(bridge.IndagoBridgeRefusal) as caught:
        bridge.consume_evidence_return(audit, queue, evidence, ledger,
                                        witness_path=witness)
    assert caught.value.code == "REPLAY_ATTESTATION_CHANGED"


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


def test_fake_digest_and_cross_source_passages_fail_closed(tmp_path):
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


def test_consistent_fake_text_and_digest_fails_against_real_file(tmp_path):
    _, audit, queue, _, evidence, witness = _with_witness(tmp_path)
    fake = "A fabricated passage with internally matching digest."
    evidence["passages"][0]["exact_text"] = fake
    evidence["passages"][0]["text_sha256"] = hashlib.sha256(fake.encode("utf-8")).hexdigest()
    with pytest.raises(bridge.IndagoBridgeRefusal) as caught:
        bridge.consume_evidence_return(audit, queue, evidence, tmp_path / "ledger",
                                        witness_path=witness)
    assert caught.value.code == "PASSAGE_NOT_IN_WITNESS"


def test_wrong_witness_bytes_fail_closed_even_if_quote_present(tmp_path):
    _, audit, queue, _, evidence, witness = _with_witness(tmp_path)
    evidence["source"]["source_sha256"] = "a" * 64
    with pytest.raises(bridge.IndagoBridgeRefusal) as caught:
        bridge.consume_evidence_return(audit, queue, evidence, tmp_path / "ledger",
                                        witness_path=witness)
    assert caught.value.code == "WITNESS_HASH_MISMATCH"


def test_text_quote_locator_must_match_actual_offset(tmp_path):
    _, audit, queue, _, evidence, witness = _with_witness(tmp_path, prefix="intro\n")
    evidence["passages"][0]["locator"] = "text-char-offset:1"
    with pytest.raises(bridge.IndagoBridgeRefusal) as caught:
        bridge.consume_evidence_return(audit, queue, evidence, tmp_path / "ledger",
                                        witness_path=witness)
    assert caught.value.code == "LOCATOR_DISAGREEMENT"


def test_unverified_printed_page_not_assumed_to_be_pdf_page_index(tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    _, audit, queue, _, evidence = _bound(tmp_path)
    witness = tmp_path / "owned_source.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    quote = "Primary source quotation, only one passage."
    page.insert_text((40, 40), quote)
    doc.save(str(witness))
    doc.close()
    digest = hashlib.sha256(witness.read_bytes()).hexdigest()
    evidence["source"]["source_sha256"] = digest
    evidence["source"]["witness_id"] = "pdf:" + digest
    evidence["passages"][0].update(witness_id="pdf:" + digest, locator="printed-page:94",
                                  exact_text=quote,
                                  text_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest())
    pending = bridge.consume_evidence_return(audit, queue, evidence, tmp_path / "pending",
                                             witness_path=witness)
    assert pending.receipt["bridge_status"] == "WITNESS_UNVERIFIED"
    assert pending.state["witness_attestation"]["bytes_verified"] is True
    assert pending.state["source_evidence"] == []
    evidence["return_id"] += "-verified"
    evidence["passages"][0]["locator"] = "pdf-page-index:0"
    anchored = bridge.consume_evidence_return(audit, queue, evidence, tmp_path / "anchored",
                                              witness_path=witness)
    assert anchored.receipt["bridge_status"] == "ANCHORED"
    assert anchored.state["witness_attestation"]["locator_verified"] is True


def test_end_to_end_z0_r1_r3_r2_r4_receipt_with_real_witness(tmp_path):
    manuscript, audit, queue, _, evidence, witness = _with_witness(tmp_path)
    return_path = tmp_path / "return.json"
    return_path.write_text(json.dumps(evidence), encoding="utf-8")
    receipt = bridge.consume_and_plan(audit, queue, return_path, tmp_path / "ledger",
                                      tmp_path / "plan", manuscript, witness_path=witness)
    assert receipt["bridge_receipt"]["bridge_status"] == "ANCHORED"
    plan = receipt["r2_r4_plan"]
    assert plan["r3_reentry"] is None
    assert "IDENTITY_AND_PASSAGE_PROPOSED" in {
        c["evidence_label"] for c in plan["r4_candidates"]}
    assert set(plan["verification"].values()) == {"NOT_CHECKED"}
    assert plan["citation_gate"] == "NOT_PUBLICATION_READY"


def test_end_to_end_without_real_witness_retains_research_debt(tmp_path):
    manuscript, audit, queue, _, evidence, _ = _with_witness(tmp_path)
    return_path = tmp_path / "return.json"
    return_path.write_text(json.dumps(evidence), encoding="utf-8")
    receipt = bridge.consume_and_plan(audit, queue, return_path, tmp_path / "ledger",
                                      tmp_path / "plan", manuscript)
    assert receipt["bridge_receipt"]["bridge_status"] == "WITNESS_UNVERIFIED"
    assert receipt["r2_r4_plan"]["r3_reentry"] is not None
    assert receipt["r2_r4_plan"]["citation_gate"] == "NOT_PUBLICATION_READY"
