"""Tests for TRM-SOURCE-CORPUS-FIRST-005 (B-1 / M-1 / M-2 / corpus adapter).

All fixtures here are synthetic and clearly marked as such.  No real
publisher text is referenced; the optional real-owner PDF path lives
in an external private run and is referenced by SHA only.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from kairoskopion.services.citation_intake_z0 import persist_audit
from kairoskopion.services.citation_r1_batch import (
    KNOWN_WITNESS_CLASSES,
    consume,
    prepare,
    recompute_summary_from_returns,
    verify_provider_summary,
)
from kairoskopion.services.cite_r1_permits import Permit, save_permit
from kairoskopion.services.cite_r1_corpus_ingest import (
    ALLOWED_PROVENANCE,
    CorpusAnchor,
    CorpusIngestRecord,
    PARSE_CONF_HIGH,
    PROVENANCE_INDAGO,
    PROVENANCE_OWNER,
    PROVENANCE_UPLOAD,
    build_r1_return_from_anchor,
    parse_owner_corpus,
    verify_anchor_against_plaintext,
)


# ---------------------------------------------------------------------------
# Shared synthetic fixtures (no real content, no real citations)
# ---------------------------------------------------------------------------


SYNTHETIC_PLAINTEXT = (
    "SYNTHETIC FIXTURE -- not a real primary text.\n"
    "WORK: SYNTH-WORK-A\n"
    "EDITION: SYNTH-EDITION-1\n"
    "WITNESS: SYNTH-WITNESS-1\n"
    "LOCATOR: synth-page-3\n"
    "An imaginary passage about abstract calculators.\n"
)

SYNTHETIC_PASSAGE = "An imaginary passage about abstract calculators."
REAL_OWNER_LUKSHA_SHA = (
    "5a84d385e7122acb774ab3068fd3688b461d102ccadbef3449a5c0d55540c6fb"
)
REAL_OWNER_LUKSHA_DIR = (
    Path(r"C:\AI\llm\aiye-executor\runs\TRM_CITE_Z0_20261020")
    / "luksha_private_audit" / "original_snapshots"
)


def _write_synthetic_corpus(tmp_path: Path) -> Path:
    target = tmp_path / "synth_corpus.txt"
    target.write_bytes(SYNTHETIC_PLAINTEXT.encode("utf-8"))
    return target


def _anchor(passage: str = SYNTHETIC_PASSAGE) -> CorpusAnchor:
    return CorpusAnchor(
        work_id="SYNTH-WORK-A",
        edition_id="SYNTH-EDITION-1",
        witness_id="SYNTH-WITNESS-1",
        locator_label="synth-page-3",
        passage_text=passage,
        edition_page_or_offset="p.3",
        license="SYNTHETIC_TEST_NO_PROVENANCE",
        access="OWNER_HELD_SYNTHETIC",
    )


def _setup_z0(tmp_path: Path) -> tuple[Path, Path, Path]:
    draft = tmp_path / "draft.md"
    draft.write_text("A claim (Author 1900).", encoding="utf-8")
    _, audit = persist_audit(draft, tmp_path / "z0")
    queue = audit.with_name("citation_work_orders.jsonl")
    return draft, audit, queue


def _setup_r1_batch(tmp_path: Path) -> dict:
    _, audit, queue = _setup_z0(tmp_path)
    orders = [json.loads(line) for line in queue.read_text(
        encoding="utf-8-sig").splitlines() if line.strip()]
    source_sha = json.loads(audit.read_text(
        encoding="utf-8-sig"))["source"]["sha256"]
    protocols = tmp_path / "protocols.json"
    protocols.write_text(json.dumps({"cases": [
        {"case_id": f"R1-0{i}", "inputs": [], "checks": {}}
        for i in range(1, 6)
    ]}), encoding="utf-8")
    followups = tmp_path / "followups.jsonl"
    rows = []
    for n in range(2):
        rows.append({
            "task_id": f"r1-corpus-{n:02}", "case_id": "R1-01",
            "step_index": n, "source_manuscript_sha256": source_sha,
            "work_order_ids": [orders[0]["work_order_id"]],
            "required_operation": "CHECK_TEST_SOURCE",
            "review_status": "PENDING", "source_evidence_uris": [],
            "owner_authority": "OWNER_CORPUS",
            "no_automatic_document_write": True,
            "not_a_completed_hunt": True,
        })
    followups.write_text("".join(
        json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    requests = tmp_path / "requests"
    prepare(audit, queue, followups, protocols, requests)
    return {
        "audit": audit, "queue": queue, "followups": followups,
        "protocols": protocols, "requests": requests,
        "orders": orders, "source_sha": source_sha, "rows": rows,
    }


# ---------------------------------------------------------------------------
# Adapter unit tests
# ---------------------------------------------------------------------------


def test_allowed_provenance_set_matches_owner_policy():
    assert ALLOWED_PROVENANCE == frozenset({
        "OWNER_CORPUS", "EXISTING_INDAGO_PROVIDER",
        "DOCUMENT_UPLOAD", "OTHER_RECORDED",
    })
    assert "LICENSE_GATED" not in ALLOWED_PROVENANCE
    assert "PUBLISHER_HOST_REQUIRED" not in ALLOWED_PROVENANCE


def test_known_witness_classes_listed_externally():
    assert KNOWN_WITNESS_CLASSES == frozenset({
        "LIVE_AUTHORIZED_SOURCE_READ",
        "MANUAL_WEB_OBSERVED",
        "SYNTHETIC_TEST",
    })


def test_parse_owner_corpus_keeps_original_sha_and_recorded_debt(tmp_path):
    corpus = _write_synthetic_corpus(tmp_path)
    before = corpus.read_bytes()
    record = parse_owner_corpus(corpus, out_dir=tmp_path / "pt")
    assert record.source_sha256 == sha256(before).hexdigest()
    assert record.parse_confidence == PARSE_CONF_HIGH
    assert record.bytes_total == len(before)
    assert record.plain_text_path.exists()
    assert "SYNTHETIC FIXTURE" in record.plain_text_path.read_text(
        encoding="utf-8")
    assert corpus.read_bytes() == before, (
        "parser must never mutate the original file"
    )


def test_parse_owner_corpus_flags_unknown_extension_without_resorting_to_real(tmp_path):
    target = tmp_path / "weird.xyz"
    target.write_text("SYNTHETIC FIXTURE X.", encoding="utf-8")
    record = parse_owner_corpus(target)
    assert "UNRECOGNIZED_SUFFIX" in record.parse_debt
    # Honest downgrade: any debt tag prevents HIGH confidence.
    assert record.parse_confidence == "MEDIUM"


def test_parse_owner_corpus_empty_file_is_honest_unreadable(tmp_path):
    target = tmp_path / "empty.txt"
    target.write_text("", encoding="utf-8")
    record = parse_owner_corpus(target)
    assert record.parse_confidence == "UNREADABLE"
    assert "PARSED_TEXT_IS_EMPTY" in record.parse_debt


def test_anchor_verification_requires_unique_occurrence(tmp_path):
    corpus = _write_synthetic_corpus(tmp_path)
    record = parse_owner_corpus(corpus, out_dir=tmp_path / "pt")
    good = verify_anchor_against_plaintext(_anchor(), record.plain_text_path)
    assert good["passage_present"] is True
    assert good["duplicate_passage"] is False
    assert good["locator_present"] is True
    assert good["verified_passage_id"].startswith("passage:")
    assert good["verified_passage_id"] != "passage:anchor_missing"
    dup_corpus = tmp_path / "dup.txt"
    dup_corpus.write_text(SYNTHETIC_PLAINTEXT + SYNTHETIC_PASSAGE,
                          encoding="utf-8")
    dup_record = parse_owner_corpus(dup_corpus, out_dir=tmp_path / "pt2")
    dup = verify_anchor_against_plaintext(_anchor(), dup_record.plain_text_path)
    assert dup["duplicate_passage"] is True


def test_build_r1_return_from_anchor_rejects_drift_between_manuscript_and_source(tmp_path):
    setup = _setup_r1_batch(tmp_path)
    corpus = _write_synthetic_corpus(tmp_path)
    record = parse_owner_corpus(corpus, out_dir=tmp_path / "pt")
    anchor = _anchor()
    verification = verify_anchor_against_plaintext(anchor, record.plain_text_path)
    request = json.loads(
        (setup["requests"] / "r1-corpus-00.request.json").read_text(
            encoding="utf-8-sig"))
    work_order = setup["orders"][0]
    ret = build_r1_return_from_anchor(
        request=request, work_order=work_order,
        source_uri=str(corpus),
        source_sha256=setup["source_sha"], ingest=record,
        anchor=anchor, provenance=PROVENANCE_OWNER,
        verification=verification,
        authorized_by="OWNER_AUTHORITY_2026-10-21",
        permit_id=None,
    )
    assert ret["outcome"] == "OBSERVED"
    assert ret["witness_class"] == "MANUAL_WEB_OBSERVED"
    assert ret["source_provenance"] == PROVENANCE_OWNER
    assert ret["citation_gate"] == "NOT_PUBLICATION_READY"
    assert ret["author_gate"] == "PENDING"
    assert ret["ingest_sha256"] == sha256(corpus.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="manuscript sha256 drift"):
        build_r1_return_from_anchor(
            request=request, work_order=work_order,
            source_uri=str(corpus),
            source_sha256="0" * 64, ingest=record,
            anchor=anchor, provenance=PROVENANCE_UPLOAD,
            verification=verification,
            authorized_by="OWNER_AUTHORITY_2026-10-21",
            permit_id=None,
        )


def test_build_r1_return_from_anchor_refuses_provenance_outside_policy(tmp_path):
    setup = _setup_r1_batch(tmp_path)
    corpus = _write_synthetic_corpus(tmp_path)
    record = parse_owner_corpus(corpus, out_dir=tmp_path / "pt2")
    anchor = _anchor()
    verification = verify_anchor_against_plaintext(anchor, record.plain_text_path)
    request = json.loads(
        (setup["requests"] / "r1-corpus-00.request.json").read_text(
            encoding="utf-8-sig"))
    work_order = setup["orders"][0]
    with pytest.raises(ValueError, match="provenance not in allowed"):
        build_r1_return_from_anchor(
            request=request, work_order=work_order,
            source_uri=str(corpus),
            source_sha256=setup["source_sha"], ingest=record,
            anchor=anchor, provenance="LICENSE_GATED",
            verification=verification,
            authorized_by="OWNER_AUTHORITY_2026-10-21",
            permit_id=None,
        )


def test_corpus_path_is_admitted_by_batch_consumer_with_truth_payload(tmp_path):
    setup = _setup_r1_batch(tmp_path)
    corpus = _write_synthetic_corpus(tmp_path)
    record = parse_owner_corpus(corpus, out_dir=tmp_path / "pt")
    anchor = _anchor()
    verification = verify_anchor_against_plaintext(anchor, record.plain_text_path)
    request = json.loads(
        (setup["requests"] / "r1-corpus-00.request.json").read_text(
            encoding="utf-8-sig"))
    work_order = setup["orders"][0]
    ret = build_r1_return_from_anchor(
        request=request, work_order=work_order,
        source_uri=str(corpus),
        source_sha256=setup["source_sha"], ingest=record,
        anchor=anchor, provenance=PROVENANCE_OWNER,
        verification=verification,
        authorized_by="OWNER_AUTHORITY_2026-10-21",
        permit_id=None,
    )
    returns_dir = tmp_path / "returns"
    returns_dir.mkdir()
    (returns_dir / "r1-corpus-00.return.json").write_text(
        json.dumps(ret, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    # Build a blocked return for the second request so verify_provider_summary
    # does not trip on missing returns.
    other_req = json.loads(
        (setup["requests"] / "r1-corpus-01.request.json").read_text(
            encoding="utf-8-sig"))
    blocked = {
        "schema": "trm-cite-r1-task-return-v1",
        "task_id": other_req["task_id"],
        "case_id": other_req["case_id"], "step_index": other_req["step_index"],
        "source_sha256": other_req["source_sha256"],
        "work_order_ids": list(other_req["work_order_ids"]),
        "correlation_id": other_req["correlation_id"],
        "kind": other_req.get("kind", "Z0_LINKED"),
        "acquisition_authorized_by_request":
            bool(other_req.get("acquisition_authorized_by_request", False)),
        "acquisition_authorized": False,
        "witness_class": "NO_WITNESS",
        "outcome": "BLOCKED",
        "reason": "NO_PERMIT_FOR_TASK",
        "provider": "NONE",
        "read_depth": "NONE",
        "source_kind": "NONE",
        "retrieved_at": None,
        "access": "NOT_ATTEMPTED",
        "license": "UNKNOWN",
        "work_id": None, "edition_id": None, "witness_id": None,
        "passage_id": None, "byte_sha256": None, "locator": None,
        "negative_evidence": ["NO_PERMIT_FOR_TASK"],
        "errors": ["NO_PERMIT_FOR_TASK"],
        "source_evidence": [],
        "citation_gate": "NOT_PUBLICATION_READY",
        "author_gate": "PENDING",
    }
    (returns_dir / "r1-corpus-01.return.json").write_text(
        json.dumps(blocked, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    states = tmp_path / "states"
    result = consume(
        setup["audit"], setup["queue"], setup["followups"],
        setup["protocols"], setup["requests"], returns_dir, states)
    assert result["observed"] == 1
    assert result["blocked"] == 1
    payload = result["provider_summary_truth"]
    assert payload["recomputed_observed"] == 1
    assert payload["match_observed"] is True
    assert payload["witness_class_distribution"].get(
        "MANUAL_WEB_OBSERVED") == 1


def test_real_owner_corpus_is_referenced_by_sha_only_without_copying(tmp_path):
    """Mark a non-publishing canary: the real owner's private file is
    referenced via its pinned SHA but never copied into the test tree.

    The adapter must accept it as an owner corpus ingest purely as a
    filename + anchor; the test never copies the bytes into the
    repository and only runs when the path actually exists on the
    runner.
    """
    real_path = REAL_OWNER_LUKSHA_DIR / (
        REAL_OWNER_LUKSHA_SHA + ".md")
    if not real_path.is_file():
        pytest.skip("Real owner manuscript not present on this runner")
    raw = real_path.read_bytes()
    assert sha256(raw).hexdigest() == REAL_OWNER_LUKSHA_SHA
    out_pt = tmp_path / "real_pt"
    record = parse_owner_corpus(real_path, out_dir=out_pt)
    assert record.source_sha256 == REAL_OWNER_LUKSHA_SHA
    assert real_path.read_bytes() == raw, "adapter must not mutate source"
    assert record.plain_text_path.exists()
    assert record.plain_text_path == out_pt / (
        REAL_OWNER_LUKSHA_SHA + ".plaintext")
    text = record.plain_text_path.read_text(encoding="utf-8", errors="replace")
    candidate = " ".join(text.split())[:120]
    assert candidate, "real corpus yielded no text to anchor against"


# ---------------------------------------------------------------------------
# M-1: consumer refuses unknown / missing witness_class
# ---------------------------------------------------------------------------


def _synthetic_test_permit(work_order_id: str, file_path: Path) -> Permit:
    return Permit(
        work_order_id=work_order_id,
        allowed_task_ids=("r1-task-01", "r1-task-00", "r1-task-00.r"),
        provider="SYNTHETIC_TEST_READER",
        authorized_by="TEST_RUNNER",
        mode="FIXTURE",
        fixture_path=file_path.name,
        work_id="SYNTH-WORK-A",
        edition_id="SYNTH-EDITION-1",
        witness_id="SYNTH-WITNESS-1",
        expected_locator="LOCATOR: synth-page-3",
        expected_passage=SYNTHETIC_PASSAGE,
        license="SYNTHETIC_TEST_NO_PROVENANCE",
        source_kind="SYNTHETIC_TEXT",
        access="TEST_ARTIFACT_ONLY",
        witness_class="SYNTHETIC_TEST",
        witness_sha256=sha256(file_path.read_bytes()).hexdigest(),
        observed_at=datetime.now(timezone.utc).isoformat(),
        read_depth="ANCHORED_PASSAGE",
    )


def test_citation_r1_consume_rejects_unknown_witness_class(tmp_path):
    _, audit, queue = _setup_z0(tmp_path)
    requests_dir = tmp_path / "rq"
    from kairoskopion.services.citation_r1 import prepare as r1_prepare
    r1_prepare(audit, queue, requests_dir)
    request_path = next(requests_dir.glob("*.request.json"))
    req = json.loads(request_path.read_text(encoding="utf-8-sig"))
    ret = {
        **req, "schema": "trm-cite-r1-return-v1", "outcome": "OBSERVED",
        "provider": "OWNER_CORPUS_INGEST",
        "acquisition_authorized": True,
        "source_kind": "OWNER_HELD", "read_depth": "ANCHORED_PASSAGE",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "access": "OWNER_HELD_BYTES",
        "license": "OWNER_HELD_NO_PROVENANCE_DECLARED",
        "work_id": "w", "edition_id": "e", "witness_id": "x",
        "passage_id": "passage:abc",
        "byte_sha256": "a" * 64,
        "locator": "p. 1",
        "witness_class": "WHATEVER_FAKE",
    }
    ret_path = tmp_path / "ret.json"
    ret_path.write_text(json.dumps(ret, ensure_ascii=False, sort_keys=True))
    from kairoskopion.services.citation_r1 import consume as single_consume
    with pytest.raises(ValueError, match="unknown witness_class"):
        single_consume(audit, queue, request_path, ret_path, tmp_path / "st")


def test_citation_r1_consume_rejects_missing_witness_class(tmp_path):
    _, audit, queue = _setup_z0(tmp_path)
    requests_dir = tmp_path / "rq"
    from kairoskopion.services.citation_r1 import prepare as r1_prepare
    r1_prepare(audit, queue, requests_dir)
    request_path = next(requests_dir.glob("*.request.json"))
    req = json.loads(request_path.read_text(encoding="utf-8-sig"))
    ret = {
        **req, "schema": "trm-cite-r1-return-v1", "outcome": "OBSERVED",
        "provider": "OWNER_CORPUS_INGEST",
        "acquisition_authorized": True,
        "source_kind": "OWNER_HELD", "read_depth": "ANCHORED_PASSAGE",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "access": "OWNER_HELD_BYTES",
        "license": "OWNER_HELD_NO_PROVENANCE_DECLARED",
        "work_id": "w", "edition_id": "e", "witness_id": "x",
        "passage_id": "passage:abc",
        "byte_sha256": "a" * 64,
        "locator": "p. 1",
    }
    ret_path = tmp_path / "ret.json"
    ret_path.write_text(json.dumps(ret, ensure_ascii=False, sort_keys=True))
    from kairoskopion.services.citation_r1 import consume as single_consume
    with pytest.raises(ValueError, match="lacks witness_class"):
        single_consume(audit, queue, request_path, ret_path, tmp_path / "st")


def test_batch_consumer_rejects_unknown_evidence_witness_class(tmp_path):
    setup = _setup_r1_batch(tmp_path)
    returns_dir = tmp_path / "returns"
    returns_dir.mkdir()
    request = json.loads(
        (setup["requests"] / "r1-corpus-00.request.json").read_text(
            encoding="utf-8-sig"))
    work_order = setup["orders"][0]
    fake = {
        "schema": "trm-cite-r1-task-return-v1",
        "task_id": request["task_id"],
        "case_id": request["case_id"],
        "step_index": request["step_index"],
        "source_sha256": request["source_sha256"],
        "work_order_ids": list(request["work_order_ids"]),
        "correlation_id": request["correlation_id"],
        "kind": "Z0_LINKED",
        "acquisition_authorized_by_request": False,
        "acquisition_authorized": True,
        "outcome": "OBSERVED",
        "reason": None,
        "provider": "FORGED", "read_depth": "ANCHORED_PASSAGE",
        "source_kind": "OWNER_HELD",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "access": "PUBLIC",
        "license": "OWNER_HELD_NO_PROVENANCE_DECLARED",
        "work_id": "w", "edition_id": "e", "witness_id": "x",
        "passage_id": "passage:x", "byte_sha256": "a" * 64,
        "locator": "p. 1",
        "witness_class": "JUNK_FAKE",
        "citation_mode": "QUOTE",
        "source_evidence": [{
            "work_order_id": work_order["work_order_id"],
            "intake_id": work_order["intake_id"],
            "z0_case_id": work_order["case_id"],
            "source_kind": "OWNER_HELD",
            "read_depth": "ANCHORED_PASSAGE",
            "access": "PUBLIC",
            "license": "OWNER_HELD_NO_PROVENANCE_DECLARED",
            "provider": "FORGED",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "acquisition_authorized": True,
            "work_id": "w", "edition_id": "e", "witness_id": "x",
            "locator": "p. 1", "passage_id": "passage:x",
            "byte_sha256": "a" * 64,
            "witness_class": "JUNK_FAKE",
        }],
        "negative_evidence": [], "errors": [],
        "citation_gate": "NOT_PUBLICATION_READY",
        "author_gate": "PENDING",
    }
    (returns_dir / "r1-corpus-00.return.json").write_text(
        json.dumps(fake, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    other_req = json.loads(
        (setup["requests"] / "r1-corpus-01.request.json").read_text(
            encoding="utf-8-sig"))
    blocked = {
        "schema": "trm-cite-r1-task-return-v1",
        "task_id": other_req["task_id"], "case_id": other_req["case_id"],
        "step_index": other_req["step_index"],
        "source_sha256": other_req["source_sha256"],
        "work_order_ids": list(other_req["work_order_ids"]),
        "correlation_id": other_req["correlation_id"],
        "kind": other_req.get("kind", "Z0_LINKED"),
        "acquisition_authorized_by_request": False,
        "acquisition_authorized": False, "witness_class": "NO_WITNESS",
        "outcome": "BLOCKED", "reason": "NO_PERMIT",
        "provider": "NONE", "read_depth": "NONE",
        "source_kind": "NONE", "retrieved_at": None,
        "access": "NOT_ATTEMPTED", "license": "UNKNOWN",
        "work_id": None, "edition_id": None, "witness_id": None,
        "passage_id": None, "byte_sha256": None, "locator": None,
        "negative_evidence": ["NO_PERMIT"], "errors": ["NO_PERMIT"],
        "source_evidence": [],
        "citation_gate": "NOT_PUBLICATION_READY",
        "author_gate": "PENDING",
    }
    (returns_dir / "r1-corpus-01.return.json").write_text(
        json.dumps(blocked, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    with pytest.raises(ValueError, match="unknown witness_class"):
        consume(
            setup["audit"], setup["queue"], setup["followups"],
            setup["protocols"], setup["requests"], returns_dir,
            tmp_path / "states")


# ---------------------------------------------------------------------------
# M-2: tampered provider summary is detected
# ---------------------------------------------------------------------------


def _make_recording_batch(tmp_path: Path) -> dict:
    """Helper: produce the same shape as the existing test fixture."""
    from dataclasses import replace
    fixture, file = _source_files(tmp_path)
    _, audit, queue, f, p, req, orders, sha, manifest = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    save_permit(tmp_path / "permits", permit)
    return {"audit": audit, "queue": queue, "req": req, "orders": orders,
            "permit": permit, "fixture_dir": fixture,
            "permit_dir": tmp_path / "permits"}


def _source_files(tmp_path):
    fixtures = tmp_path / "test-sources"
    fixtures.mkdir(exist_ok=True)
    file = fixtures / "invented.txt"
    file.write_text(SYNTHETIC_PLAINTEXT, encoding="utf-8")
    return fixtures, file


def _permit(wo, file, **overrides):
    fields = dict(
        work_order_id=wo, allowed_task_ids=("r1-task-01", "test"),
        provider="SYNTHETIC_TEST_READER",
        authorized_by="TEST_RUNNER_ONLY", mode="FIXTURE",
        fixture_path=file.name, work_id="SYNTH-WORK-A",
        edition_id="SYNTH-EDITION-1", witness_id="SYNTH-WITNESS-1",
        expected_locator="LOCATOR: synth-page-3",
        expected_passage=SYNTHETIC_PASSAGE,
        license="SYNTHETIC_TEST_NO_PROVENANCE",
        source_kind="SYNTHETIC_TEXT",
        access="TEST_ARTIFACT_ONLY", witness_class="SYNTHETIC_TEST",
        witness_sha256=sha256(file.read_bytes()).hexdigest(),
        observed_at=datetime.now(timezone.utc).isoformat(),
        read_depth="ANCHORED_PASSAGE",
    )
    fields.update(overrides)
    return Permit(**fields)


def _batch(tmp_path):
    draft = tmp_path / "synthetic.md"
    draft.write_text("A claim (Luckin 2016). Another (Descartes 1701).",
                     encoding="utf-8")
    audit, dest = persist_audit(draft, tmp_path / "z0")
    queue = dest.with_name("citation_work_orders.jsonl")
    orders = [json.loads(line) for line in queue.read_text().splitlines()]
    source_sha = json.loads(dest.read_text())["source"]["sha256"]
    protocols = tmp_path / "protocols.json"
    protocols.write_text(json.dumps({"cases": [
        {"case_id": f"R1-0{i}", "inputs": [], "checks": {}}
        for i in range(1, 6)
    ]}), encoding="utf-8")
    rows = []
    for n in range(13):
        ids = ([] if n >= 10 else [orders[n % 2]["work_order_id"]])
        if n == 2:
            ids = [orders[0]["work_order_id"], orders[1]["work_order_id"]]
        case = "R1-05" if n >= 10 else f"R1-0{min(n // 3 + 1, 4)}"
        rows.append({
            "task_id": f"r1-task-{n:02}", "case_id": case, "step_index": n,
            "source_manuscript_sha256": source_sha,
            "work_order_ids": ids, "required_operation": "CHECK_TEST_SOURCE",
            "review_status": "PENDING", "source_evidence_uris": [],
            "owner_authority": "TEST_ONLY",
            "no_automatic_document_write": True,
            "not_a_completed_hunt": True,
        })
    followups = tmp_path / "followups.jsonl"
    followups.write_text("".join(
        json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    requests = tmp_path / "requests"
    manifest = prepare(dest, queue, followups, protocols, requests)
    return draft, dest, queue, followups, protocols, requests, orders, source_sha, manifest


def test_tampered_provider_summary_counts_are_detected(tmp_path):
    fixture, file = _source_files(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    returns_dir = tmp_path / "returns"
    from kairoskopion.services.cite_r1_reader import run_batch
    summary = run_batch(audit, queue, req, returns_dir,
                        permits={permit.work_order_id: permit},
                        fixtures_dir=fixture, test_mode=True)
    stored = returns_dir / "provider_summary.json"
    truth = recompute_summary_from_returns(returns_dir)
    assert truth["tasks"] == summary["tasks"]
    bad = json.loads(stored.read_text(encoding="utf-8-sig"))
    bad["observed"] = summary["tasks"]
    stored.write_text(json.dumps(bad, ensure_ascii=False, sort_keys=True))
    with pytest.raises(ValueError, match="tampered"):
        verify_provider_summary(returns_dir)


def test_tampered_provider_summary_return_digest_is_detected(tmp_path):
    fixture, file = _source_files(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    returns_dir = tmp_path / "returns"
    from kairoskopion.services.cite_r1_reader import run_batch
    run_batch(audit, queue, req, returns_dir,
              permits={permit.work_order_id: permit},
              fixtures_dir=fixture, test_mode=True)
    truth = recompute_summary_from_returns(returns_dir)
    sample_task = next(iter(truth["return_digests"]))
    stored = returns_dir / "provider_summary.json"
    bad = json.loads(stored.read_text(encoding="utf-8-sig"))
    bad["return_digests"][sample_task] = "f" * 64
    stored.write_text(json.dumps(bad, ensure_ascii=False, sort_keys=True))
    with pytest.raises(ValueError, match="drifted from immutable bytes"):
        verify_provider_summary(returns_dir)


def test_recompute_summary_agrees_with_stored_when_untouched(tmp_path):
    fixture, file = _source_files(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    returns_dir = tmp_path / "returns"
    from kairoskopion.services.cite_r1_reader import run_batch
    run_batch(audit, queue, req, returns_dir,
              permits={permit.work_order_id: permit},
              fixtures_dir=fixture, test_mode=True)
    truth = verify_provider_summary(returns_dir)
    assert truth["observed"] >= 1
    assert sum(truth["witness_class_distribution"].values()) == truth["observed"]


# ---------------------------------------------------------------------------
# B-1: cold start refuses preplaced returns whose run id mismatches
# ---------------------------------------------------------------------------


def test_preplaced_return_with_different_run_id_is_refused(tmp_path):
    fixture, file = _source_files(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    returns_dir = tmp_path / "returns"
    returns_dir.mkdir()
    request = json.loads(
        (req / "r1-task-01.request.json").read_text(encoding="utf-8-sig"))
    preplaced = {
        "schema": "trm-cite-r1-task-return-v1",
        "task_id": request["task_id"], "case_id": request["case_id"],
        "step_index": request["step_index"],
        "source_sha256": request["source_sha256"],
        "work_order_ids": list(request["work_order_ids"]),
        "correlation_id": request["correlation_id"],
        "kind": "Z0_LINKED",
        "acquisition_authorized_by_request": False,
        "acquisition_authorized": True,
        "witness_class": "MANUAL_WEB_OBSERVED",
        "outcome": "OBSERVED",
        "reason": None,
        "provider": "FORGED_BEFORE_RUN",
        "read_depth": "ANCHORED_PASSAGE",
        "source_kind": "OWNER_HELD",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "access": "OWNER_HELD_BYTES",
        "license": "OWNER_HELD_NO_PROVENANCE_DECLARED",
        "work_id": "w", "edition_id": "e", "witness_id": "x",
        "passage_id": "passage:x", "byte_sha256": "a" * 64,
        "locator": "p. 1", "citation_mode": "QUOTE",
        "transport_run_id": "run_definitely_not_matching_any_real_run",
        "source_evidence": [],
        "negative_evidence": [], "errors": [],
        "citation_gate": "NOT_PUBLICATION_READY",
        "author_gate": "PENDING",
    }
    (returns_dir / "r1-task-01.return.json").write_text(
        json.dumps(preplaced, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    from kairoskopion.services.cite_r1_reader import run_batch
    with pytest.raises(ValueError, match="B-1"):
        run_batch(audit, queue, req, returns_dir,
                  permits={permit.work_order_id: permit},
                  fixtures_dir=fixture, test_mode=True,
                  accept_preplaced=False)


def test_preplaced_return_for_unknown_task_is_refused(tmp_path):
    fixture, file = _source_files(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    returns_dir = tmp_path / "returns"
    returns_dir.mkdir()
    preplaced = {
        "schema": "trm-cite-r1-task-return-v1",
        "task_id": "r1-task-99-pretender",
        "case_id": "R1-01", "step_index": 0,
        "source_sha256": sha,
        "work_order_ids": [orders[1]["work_order_id"]],
        "correlation_id": "x" * 64,
        "kind": "Z0_LINKED",
        "acquisition_authorized_by_request": False,
        "acquisition_authorized": True, "witness_class": "MANUAL_WEB_OBSERVED",
        "outcome": "OBSERVED", "reason": None,
        "provider": "FORGED", "read_depth": "ANCHORED_PASSAGE",
        "source_kind": "OWNER_HELD",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "access": "OWNER_HELD_BYTES",
        "license": "OWNER_HELD_NO_PROVENANCE_DECLARED",
        "work_id": "w", "edition_id": "e", "witness_id": "x",
        "passage_id": "p", "byte_sha256": "a" * 64, "locator": "p.1",
        "citation_mode": "QUOTE",
        "transport_run_id": "run_x",
        "source_evidence": [], "negative_evidence": [], "errors": [],
        "citation_gate": "NOT_PUBLICATION_READY",
        "author_gate": "PENDING",
    }
    (returns_dir / "r1-task-99-pretender.return.json").write_text(
        json.dumps(preplaced, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    from kairoskopion.services.cite_r1_reader import run_batch
    with pytest.raises(ValueError, match="B-1"):
        run_batch(audit, queue, req, returns_dir,
                  permits={}, fixtures_dir=fixture, test_mode=True,
                  accept_preplaced=False)


def test_accept_preplaced_opt_in_adopts_legitimate_priors(tmp_path):
    fixture, file = _source_files(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    returns_dir = tmp_path / "returns"
    from kairoskopion.services.cite_r1_reader import run_batch
    summary_a = run_batch(audit, queue, req, returns_dir,
                          permits={permit.work_order_id: permit},
                          fixtures_dir=fixture, test_mode=True)
    summary_b = run_batch(audit, queue, req, returns_dir,
                          permits={permit.work_order_id: permit},
                          fixtures_dir=fixture, test_mode=True,
                          accept_preplaced=True)
    assert summary_a["observed"] == summary_b["observed"]


# Source-grounded PDF extraction and locator controls (2026-10-21).

def test_pdf_real_page_text_extraction_from_synthetic_pdf(tmp_path):
    """Binary PDF internals must never masquerade as readable source text."""
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    page = doc.new_page()
    passage = "SYNTHETIC TEST ONLY: The laboratory protocol is explicitly fictional."
    page.insert_text((72, 90), passage, fontsize=11)
    path = tmp_path / "synthetic_source.pdf"
    path.write_bytes(doc.tobytes())
    doc.close()

    record = parse_owner_corpus(path, out_dir=tmp_path / "pt")
    assert record.parser_name == "pdf_page_text_extraction"
    assert record.parse_confidence == "HIGH"
    extracted = record.plain_text_path.read_text(encoding="utf-8")
    assert "[PDF_PAGE_INDEX_1]" in extracted
    assert passage in extracted
    assert record.text_length < record.bytes_total
    assert "stream" not in extracted[:20]


def test_malformed_pdf_never_gets_high_confidence_binary_text(tmp_path):
    source = tmp_path / "fake.pdf"
    source.write_bytes(b"%PDF-1.4\nstream\n" + bytes(range(256)) * 12
                       + b"\nendstream\n%%EOF")
    record = parse_owner_corpus(source, out_dir=tmp_path / "pt")
    assert record.parse_confidence == "UNREADABLE"
    assert record.text_length == 0
    assert any(x.startswith("PDF_") for x in record.parse_debt)


def test_corpus_missing_locator_or_ambiguous_passage_cannot_be_observed(tmp_path):
    from dataclasses import replace
    setup = _setup_r1_batch(tmp_path)
    corpus = _write_synthetic_corpus(tmp_path)
    record = parse_owner_corpus(corpus, out_dir=tmp_path / "pt")
    anchor = _anchor()
    request = json.loads(
        (setup["requests"] / "r1-corpus-00.request.json").read_text(
            encoding="utf-8-sig"))
    order = setup["orders"][0]
    invalid_locator = replace(anchor, locator_label="NO_SUCH_PDF_PAGE_INDEX")
    invalid_verification = verify_anchor_against_plaintext(
        invalid_locator, record.plain_text_path)
    assert invalid_verification["passage_occurrences"] == 1
    assert invalid_verification["verified_passage_id"] == "passage:anchor_missing"
    with pytest.raises(ValueError, match="declared locator missing"):
        build_r1_return_from_anchor(
            request=request, work_order=order,
            source_uri=str(corpus), source_sha256=setup["source_sha"],
            ingest=record, anchor=invalid_locator,
            provenance=PROVENANCE_OWNER, verification=invalid_verification,
            authorized_by="TEST_OWNER", permit_id=None)

    duplicate = tmp_path / "duplicated.txt"
    duplicate.write_text(SYNTHETIC_PLAINTEXT + SYNTHETIC_PASSAGE, encoding="utf-8")
    dup_record = parse_owner_corpus(duplicate, out_dir=tmp_path / "pt2")
    dup_verification = verify_anchor_against_plaintext(
        anchor, dup_record.plain_text_path)
    assert dup_verification["duplicate_passage"] is True
    assert dup_verification["verified_passage_id"] == "passage:anchor_missing"
    with pytest.raises(ValueError, match="non-unique"):
        build_r1_return_from_anchor(
            request=request, work_order=order,
            source_uri=str(duplicate), source_sha256=setup["source_sha"],
            ingest=dup_record, anchor=anchor,
            provenance=PROVENANCE_OWNER, verification=dup_verification,
            authorized_by="TEST_OWNER", permit_id=None)
