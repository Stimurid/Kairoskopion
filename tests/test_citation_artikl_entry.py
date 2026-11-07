"""Regression tests: one Artikl citation entry, no automatic scholarly PASS."""
import hashlib
import json
from pathlib import Path

from kairoskopion.cli import main as cli_main
from kairoskopion.services.citation_artikl_entry import run_citation_workflow


FIXTURE = Path(__file__).parent / "fixtures" / "indago_evidence_return_real_shape.json"


def _manuscript(tmp_path):
    manuscript = tmp_path / "article.md"
    manuscript.write_text("A bounded claim (Frolov 2026).\n", encoding="utf-8")
    return manuscript


def _evidence(result, tmp_path):
    order = json.loads(
        Path(result["work_orders_file"]).read_text(encoding="utf-8").splitlines()[0]
    )
    evidence = json.loads(FIXTURE.read_text(encoding="utf-8"))
    evidence.update(
        case_id=order["case_id"],
        work_order_id=order["work_order_id"],
        intake_id=order["intake_id"],
        manuscript_sha256=order["source_sha256"],
    )
    quote = evidence["passages"][0]["exact_text"]
    witness = tmp_path / "source.txt"
    witness.write_text(quote, encoding="utf-8")
    digest = hashlib.sha256(witness.read_bytes()).hexdigest()
    evidence["source"]["source_sha256"] = digest
    evidence["source"]["witness_id"] = "text:" + digest
    evidence["passages"][0]["witness_id"] = "text:" + digest
    evidence["passages"][0]["locator"] = "text-char-offset:0"
    ret = tmp_path / "indago_return.json"
    ret.write_text(json.dumps(evidence), encoding="utf-8")
    return ret, witness


def test_intake_only_has_separate_source_science_and_author_status(tmp_path):
    manuscript = _manuscript(tmp_path)
    original = manuscript.read_bytes()
    output = tmp_path / "out"
    receipt = run_citation_workflow(manuscript, output)
    assert receipt["status"] == "AWAITING_INDAGO_EVIDENCE_RETURN"
    assert receipt["work_orders"] >= 1
    assert receipt["citation_gate"] == "NOT_PUBLICATION_READY"
    assert receipt["scientific_certification"] is False
    assert receipt["source_to_claim_relation"] == "NOT_CHECKED"
    assert receipt["author_gate"] == "PENDING"
    assert set(receipt["verification"].values()) == {"NOT_CHECKED"}
    assert manuscript.read_bytes() == original
    assert run_citation_workflow(manuscript, output)["audit_file"] == receipt["audit_file"]


def test_verified_original_text_does_not_automatically_certify_claim(tmp_path):
    manuscript = _manuscript(tmp_path)
    output = tmp_path / "out"
    intake = run_citation_workflow(manuscript, output)
    ret, witness = _evidence(intake, tmp_path)
    result = run_citation_workflow(manuscript, output,
                                   evidence_return=ret, witness_path=witness)
    assert result["bridge_receipt"]["bridge_status"] == "ANCHORED"
    assert result["witness_status"] == "VERIFIED_UNIQUE"
    assert result["scientific_certification"] is False
    assert result["author_gate"] == "PENDING"
    assert set(result["verification"].values()) == {"NOT_CHECKED"}


def test_provider_quote_without_witness_does_not_become_passage_evidence(tmp_path):
    manuscript = _manuscript(tmp_path)
    output = tmp_path / "out"
    intake = run_citation_workflow(manuscript, output)
    ret, _ = _evidence(intake, tmp_path)
    result = run_citation_workflow(manuscript, output, evidence_return=ret)
    assert result["bridge_receipt"]["bridge_status"] == "WITNESS_UNVERIFIED"
    assert result["scientific_certification"] is False
    assert result["citation_gate"] == "NOT_PUBLICATION_READY"


def test_cli_workflow_dispatch_and_missing_return_fail_closed(tmp_path, capsys):
    manuscript = _manuscript(tmp_path)
    output = tmp_path / "out"
    assert cli_main(["cite-workflow", "--manuscript", str(manuscript),
                     "--output-dir", str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "AWAITING_INDAGO_EVIDENCE_RETURN"
    assert cli_main(["cite-workflow", "--manuscript", str(manuscript),
                     "--output-dir", str(output), "--evidence-return",
                     str(tmp_path / "missing.json")]) == 2
    assert manuscript.read_text(encoding="utf-8").startswith("A bounded claim")
