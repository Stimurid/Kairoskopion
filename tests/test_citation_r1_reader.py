"""Evidence-origin regression tests. All source text in this module is fictional.

The fixtures have no real author, publisher, DOI, or primary-text locator.
A synthetic positive provider return MUST NOT pass production R1 consume.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path

import pytest

from kairoskopion.services.citation_intake_z0 import persist_audit
from kairoskopion.services.citation_r1_batch import prepare, consume
from kairoskopion.services.cite_r1_permits import (
    Permit, save_permit, load_permits, validate_permit_against_hosts,
    DEFAULT_ALLOWED_HOSTS,
)
from kairoskopion.services.cite_r1_reader import (
    SourceReaderProvider, WitnessBytes, acquire_fixture_witness,
    verify_witness_against_permit, run_batch, _read_batch_inputs,
    REASON_FIXTURE_HASH_MISMATCH, REASON_BAD_READ_DEPTH,
    REASON_STALE_RETRIEVED_AT, REASON_LOCATOR_MISMATCH,
    REASON_DUPLICATE_ANCHOR, REASON_PASSAGE_NOT_FOUND,
    REASON_SPOOFED_CORRELATION, REASON_REPLAY_DETECTED,
)

TEXT = (
    "SYNTHETIC TEST ONLY -- no real publication or historical work.\n"
    "WORK: TEST-WORK\n"
    "EDITION: TEST-EDITION\n"
    "WITNESS: TEST-WITNESS\n"
    "LOCATOR: fictional-section-1\n"
    "The violet calculator counts imaginary stones in the story.\n"
)
PASSAGE = "The violet calculator counts imaginary stones in the story."
NOW = lambda: datetime.now(timezone.utc).isoformat()


def _source(tmp_path):
    fixtures = tmp_path / "test-sources"
    fixtures.mkdir(exist_ok=True)
    file = fixtures / "invented.txt"
    file.write_text(TEXT, encoding="utf-8")
    return fixtures, file


def _permit(wo, file, **overrides):
    fields = dict(
        work_order_id=wo, allowed_task_ids=("r1-task-01", "test"),
        provider="SYNTHETIC_TEST_READER",
        authorized_by="TEST_RUNNER_ONLY", mode="FIXTURE",
        fixture_path="invented.txt", work_id="TEST-WORK",
        edition_id="TEST-EDITION", witness_id="TEST-WITNESS",
        expected_locator="LOCATOR: fictional-section-1",
        expected_passage=PASSAGE,
        license="TEST_DATA_NO_EXTERNAL_REUSE", source_kind="SYNTHETIC_TEXT",
        access="TEST_ARTIFACT_ONLY", witness_class="SYNTHETIC_TEST",
        witness_sha256=sha256(file.read_bytes()).hexdigest(),
        observed_at=NOW(), read_depth="ANCHORED_PASSAGE",
    )
    fields.update(overrides)
    return Permit(**fields)


def _batch(tmp_path):
    draft = tmp_path / "synthetic.md"
    draft.write_text("A claim (Luckin 2016). Another (Descartes 1701).", encoding="utf-8")
    audit, dest = persist_audit(draft, tmp_path / "z0")
    queue = dest.with_name("citation_work_orders.jsonl")
    orders = [json.loads(line) for line in queue.read_text().splitlines()]
    assert len(orders) >= 2
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
    followups.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    requests = tmp_path / "requests"
    manifest = prepare(dest, queue, followups, protocols, requests)
    return draft, dest, queue, followups, protocols, requests, orders, source_sha, manifest


def _req(requests, task="r1-task-01"):
    return json.loads((requests / f"{task}.request.json").read_text())


def _order_map(orders):
    return {o["work_order_id"]: o for o in orders}


def _synthetic_provider(permit, fixtures):
    return SourceReaderProvider(
        permits={permit.work_order_id: permit}, fixtures_dir=fixtures,
        test_mode=True,
    )


def test_fixture_is_marked_fictional_and_has_no_real_source():
    assert "SYNTHETIC TEST ONLY" in TEXT
    assert "LOCATOR: fictional-section-1" in TEXT
    assert "quantumvis differentibus" not in TEXT


def test_permit_round_trip_and_identity_digest(tmp_path):
    fixture, file = _source(tmp_path)
    permit = _permit("wo-1", file)
    store = tmp_path / "permits"
    saved = save_permit(store, permit)
    assert saved.exists()
    assert load_permits(store)["wo-1"] == permit
    assert permit.witness_sha256 == sha256(file.read_bytes()).hexdigest()


def test_bad_or_missing_witness_sha_rejected(tmp_path):
    _, file = _source(tmp_path)
    with pytest.raises(ValueError, match="witness_sha256"):
        _permit("wo-1", file, witness_sha256="")
    with pytest.raises(ValueError, match="witness_sha256"):
        _permit("wo-1", file, witness_sha256="abcd")


def test_fixture_origin_timestamp_is_not_stamped_as_new(tmp_path):
    fixture, file = _source(tmp_path)
    time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    permit = _permit("wo-1", file, observed_at=time)
    witness = acquire_fixture_witness(permit, fixtures_dir=fixture)
    assert witness.fetched_at == time
    assert witness.sha256 == permit.witness_sha256


def test_synthetic_fixture_never_observed_in_production(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, requests, orders, sha, manifest = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    provider = SourceReaderProvider(permits={permit.work_order_id: permit}, fixtures_dir=fixture)
    ret = provider.read_request(_req(requests), _order_map(orders))
    assert ret["outcome"] == "BLOCKED"
    assert ret["reason"] == "SYNTHETIC_TEST_NOT_ADMISSIBLE"
    assert ret["source_evidence"] == []


def test_positive_test_only_transport_with_pinned_synthetic_bytes(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, requests, orders, sha, manifest = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    ret = _synthetic_provider(permit, fixture).read_request(_req(requests), _order_map(orders))
    assert ret["outcome"] == "OBSERVED"
    assert ret["test_only"] is True
    assert ret["witness_class"] == "SYNTHETIC_TEST"
    assert ret["byte_sha256"] == permit.witness_sha256
    assert ret["citation_gate"] == "NOT_PUBLICATION_READY"


def test_consumer_refuses_any_synthetic_observed_evidence(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, followups, protocols, req, orders, sha, manifest = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    returns = tmp_path / "returns"
    summary = run_batch(audit, queue, req, returns,
                        permits={permit.work_order_id: permit},
                        fixtures_dir=fixture, test_mode=True)
    assert summary["observed"] >= 1
    with pytest.raises(ValueError, match="Synthetic evidence"):
        consume(audit, queue, followups, protocols, req, returns, tmp_path / "states")


def test_missing_file_produces_typed_block(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file, fixture_path="not_there.txt")
    ret = _synthetic_provider(permit, fixture).read_request(_req(req), _order_map(orders))
    assert ret["outcome"] == "BLOCKED"
    assert ret["reason"] == "FIXTURE_FILE_MISSING"


def test_pinned_hash_mismatch_blocks_instead_of_upgrading(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file, witness_sha256="0"*64)
    ret = _synthetic_provider(permit, fixture).read_request(_req(req), _order_map(orders))
    assert ret["outcome"] == "BLOCKED"
    assert ret["reason"] == REASON_FIXTURE_HASH_MISMATCH


def test_wrong_synthetic_edition_or_witness_is_detected(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    for edit in ({"edition_id": "FALSE-EDITION"}, {"witness_id": "WRONG-WITNESS"}):
        permit = _permit(orders[1]["work_order_id"], file, **edit)
        ret = _synthetic_provider(permit, fixture).read_request(_req(req), _order_map(orders))
        assert ret["outcome"] == "BLOCKED"
        assert ret["reason"] == "SYNTHETIC_IDENTITY_MISMATCH"


def test_wrong_locator_is_checked_against_body_not_echoed(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file,
                     expected_locator="LOCATOR: non-existent-section")
    ret = _synthetic_provider(permit, fixture).read_request(_req(req), _order_map(orders))
    assert ret["outcome"] == "BLOCKED"
    assert ret["reason"] == REASON_LOCATOR_MISMATCH


def test_missing_passage_is_real_negative(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file, expected_passage="not present in the test")
    ret = _synthetic_provider(permit, fixture).read_request(_req(req), _order_map(orders))
    assert ret["outcome"] == "BLOCKED"
    assert ret["reason"] == REASON_PASSAGE_NOT_FOUND


def test_duplicate_passage_cannot_pick_first(tmp_path):
    fixture, file = _source(tmp_path)
    file.write_text(TEXT + PASSAGE + "\n", encoding="utf-8")
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    ret = _synthetic_provider(permit, fixture).read_request(_req(req), _order_map(orders))
    assert ret["outcome"] == "BLOCKED"
    assert ret["reason"] == REASON_DUPLICATE_ANCHOR


def test_stale_and_future_fixture_times_block_without_fresh_timestamp(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    for days in (-40, 1):
        old = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        permit = _permit(orders[1]["work_order_id"], file, observed_at=old)
        ret = _synthetic_provider(permit, fixture).read_request(_req(req), _order_map(orders))
        assert ret["outcome"] == "BLOCKED"
        assert ret["reason"] == REASON_STALE_RETRIEVED_AT


def test_metadata_depth_does_not_masquerade_as_read_passage(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file, read_depth="SEARCH_RESULT")
    ret = _synthetic_provider(permit, fixture).read_request(_req(req), _order_map(orders))
    assert ret["outcome"] == "BLOCKED"
    assert ret["reason"] == REASON_BAD_READ_DEPTH


def test_absent_permit_compound_and_author_need_stay_blocked(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    dest = tmp_path / "returns"
    summary = run_batch(audit, queue, req, dest, permits={})
    assert summary["tasks"] == 13 and summary["observed"] == 0
    assert json.loads((dest / "r1-task-02.return.json").read_text())["outcome"] == "BLOCKED"
    author = [json.loads(x.read_text()) for x in dest.glob("*.return.json")
              if json.loads(x.read_text()).get("kind") == "AUTHOR_SOURCE_NEED"]
    assert len(author) == 3
    assert all(x["work_order_ids"] == [] and x["outcome"] == "BLOCKED" for x in author)


def test_wrong_work_order_blocked_with_real_id_lookup(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    bad = _req(req)
    bad["work_order_ids"] = ["wo-does-not-exist"]
    ret = _synthetic_provider(permit, fixture).read_request(bad, _order_map(orders))
    assert ret["outcome"] == "BLOCKED"
    assert ret["reason"] == "WORK_ORDER_NOT_IN_Z0_QUEUE"


def test_original_correlation_forgery_rejected_by_manifest(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    file = req / "r1-task-01.request.json"
    data = json.loads(file.read_text())
    data["correlation_id"] = "forged-" + data["correlation_id"]
    file.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=REASON_SPOOFED_CORRELATION):
        _read_batch_inputs(audit, queue, req)


def test_host_check_runs_before_live_fetch(tmp_path):
    fixture, file = _source(tmp_path)
    permit = _permit("wo-test", file, mode="LIVE", fixture_path=None,
                     live_url="https://not-allowlisted.example.org/test",
                     witness_class="LIVE_AUTHORIZED_SOURCE_READ")
    ok, msg = validate_permit_against_hosts(permit, DEFAULT_ALLOWED_HOSTS)
    assert ok is False and "not-allowlisted.example.org" in msg
    def must_not_fetch(*args, **kwargs):
        raise AssertionError("Unauthorized host was fetched")
    p = SourceReaderProvider(permits={"wo-test": permit}, live_fetcher=must_not_fetch)
    request = {"schema": "trm-cite-r1-task-request-v1",
               "task_id": "test", "case_id": "R1-01", "step_index": 0,
               "source_sha256": "a"*64, "correlation_id": "b"*64,
               "work_order_ids": ["wo-test"], "kind": "Z0_LINKED"}
    order = {"wo-test": {"work_order_id": "wo-test",
                        "case_id": "test-z0", "intake_id": "test-ci"}}
    ret = p.read_request(request, order)
    assert ret["outcome"] == "BLOCKED"
    assert "not-allowlisted.example.org" in ret["reason"]


def test_mock_live_reader_is_test_only_and_does_not_certify(tmp_path):
    fixture, file = _source(tmp_path)
    permit = _permit("wo-test", file, mode="LIVE", fixture_path=None,
                     live_url="https://www.unicaen.fr/not-a-real-witness",
                     witness_class="LIVE_AUTHORIZED_SOURCE_READ")
    def fake_live(p, *, allowed_hosts):
        raw = file.read_bytes()
        return WitnessBytes(
            text=raw.decode("utf-8"), sha256=sha256(raw).hexdigest(),
            byte_length=len(raw), source_uri=p.live_url,
            license_tag="TEST_ONLY", retrieval_mode="LIVE",
            fetched_at=NOW(), citation_mode=p.citation_mode
        )
    provider = SourceReaderProvider(permits={"wo-test": permit}, live_fetcher=fake_live)
    request = {"schema": "trm-cite-r1-task-request-v1",
               "task_id": "test", "case_id": "R1-01", "step_index": 0,
               "source_sha256": "a"*64, "correlation_id": "b"*64,
               "work_order_ids": ["wo-test"], "kind": "Z0_LINKED"}
    order = {"wo-test": {"work_order_id": "wo-test",
                        "case_id": "test-z0", "intake_id": "test-ci"}}
    ret = provider.read_request(request, order)
    assert ret["outcome"] == "OBSERVED"
    assert ret["test_only"] is True
    assert ret["witness_class"] == "LIVE_AUTHORIZED_SOURCE_READ"
    assert ret["citation_gate"] == "NOT_PUBLICATION_READY"


def test_mock_live_digest_drift_rejected(tmp_path):
    fixture, file = _source(tmp_path)
    permit = _permit("wo-test", file, mode="LIVE", fixture_path=None,
                     live_url="https://www.unicaen.fr/synthetic-fixture",
                     witness_class="LIVE_AUTHORIZED_SOURCE_READ",
                     witness_sha256="f"*64)
    def fake_live(p, *, allowed_hosts):
        return WitnessBytes(TEXT, sha256(TEXT.encode()).hexdigest(),
                            len(TEXT.encode()), p.live_url, "TEST", "LIVE", NOW(), "QUOTE")
    request = {"schema": "trm-cite-r1-task-request-v1",
               "task_id": "test", "case_id": "R1-01", "step_index": 0,
               "source_sha256": "a"*64, "correlation_id": "b"*64,
               "work_order_ids": ["wo-test"], "kind": "Z0_LINKED"}
    order = {"wo-test": {"work_order_id": "wo-test",
                        "case_id": "test-z0", "intake_id": "test-ci"}}
    ret = SourceReaderProvider(permits={"wo-test": permit}, live_fetcher=fake_live).read_request(request, order)
    assert ret["outcome"] == "BLOCKED"
    assert ret["reason"] == REASON_FIXTURE_HASH_MISMATCH


def test_same_provider_replay_blocks_repeated_correlation(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    permit = _permit(orders[1]["work_order_id"], file)
    provider = _synthetic_provider(permit, fixture)
    request = _req(req)
    first = provider.read_request(request, _order_map(orders))
    second = provider.read_request(request, _order_map(orders))
    assert first["outcome"] == "OBSERVED"
    assert second["outcome"] == "BLOCKED" and second["reason"] == REASON_REPLAY_DETECTED


def test_completed_batch_replays_exact_bytes_without_refetch(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    dest = tmp_path / "returns"
    first = run_batch(audit, queue, req, dest, permits={})
    tracked = sorted(dest.glob("*.json"))
    hashes = {x.name: sha256(x.read_bytes()).hexdigest() for x in tracked}
    again = run_batch(audit, queue, req, dest, permits={})
    assert again == first
    assert {x.name: sha256(x.read_bytes()).hexdigest() for x in tracked} == hashes


def test_existing_return_mutation_rejected_on_cold_replay(tmp_path):
    fixture, file = _source(tmp_path)
    _, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    dest = tmp_path / "returns"
    run_batch(audit, queue, req, dest, permits={})
    first = dest / "r1-task-00.return.json"
    fake = json.loads(first.read_text())
    fake["reason"] = "FORGED_AFTER_RUN"
    first.write_text(json.dumps(fake))
    with pytest.raises(ValueError, match="modified after completion"):
        run_batch(audit, queue, req, dest, permits={})


def test_full_batch_never_touches_original(tmp_path):
    fixture, file = _source(tmp_path)
    draft, audit, queue, f, p, req, orders, sha, _ = _batch(tmp_path)
    before = draft.read_bytes()
    run_batch(audit, queue, req, tmp_path / "returns", permits={})
    assert draft.read_bytes() == before
    assert sha256(before).hexdigest() == sha


def test_shared_z0_order_does_not_authorize_other_tasks(tmp_path):
    fixtures, file = _source(tmp_path)
    _, audit, queue, f, p, requests, orders, sha, _ = _batch(tmp_path)
    id1 = orders[1]["work_order_id"]
    permit = _permit(id1, file, allowed_task_ids=("r1-task-01",))
    result = run_batch(audit, queue, requests, tmp_path / "returns",
                       permits={id1: permit}, fixtures_dir=fixtures,
                       test_mode=True)
    assert result["observed"] == 1
    assert result["blocked"] == 12
    observed = json.loads((tmp_path/"returns"/"r1-task-01.return.json").read_text())
    refused = json.loads((tmp_path/"returns"/"r1-task-03.return.json").read_text())
    assert observed["outcome"] == "OBSERVED"
    assert refused["outcome"] == "BLOCKED"
    assert refused["reason"] == "TASK_NOT_IN_SOURCE_PERMIT"
    assert result["stats"]["requests_blocked"] == 12


def test_no_evidence_provider_cli_exit_is_three(tmp_path):
    from kairoskopion.services.cite_r1_reader import main
    _, audit, queue, f, p, requests, orders, sha, _ = _batch(tmp_path)
    permits = tmp_path / "empty-permits"
    permits.mkdir()
    code = main(["--audit",str(audit),"--queue",str(queue),
                 "--requests",str(requests),"--out",str(tmp_path/"returns"),
                 "--permits",str(permits)])
    assert code == 3


def test_fixture_path_cannot_escape_authorized_source_root(tmp_path):
    _, file = _source(tmp_path)
    for path in ("../not-authorized.txt", "C:/private/source.txt", "subfolder/test.txt"):
        with pytest.raises(ValueError, match="safe filename"):
            _permit("wo-test", file, fixture_path=path)


def test_live_source_http_scheme_is_denied(tmp_path):
    _, file = _source(tmp_path)
    p = _permit("wo-test", file, mode="LIVE", fixture_path=None,
                live_url="http://www.unicaen.fr/example",
                witness_class="LIVE_AUTHORIZED_SOURCE_READ")
    allowed, msg = validate_permit_against_hosts(p, DEFAULT_ALLOWED_HOSTS)
    assert allowed is False
    assert msg == "Only HTTPS public-source reads are permitted"
