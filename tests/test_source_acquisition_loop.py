"""Tests for P7.4 Source Acquisition Execution Loop."""

import json
from pathlib import Path

import pytest

from kairoskopion.services.source_acquisition_loop import (
    ACQUISITION_STATUSES,
    EVIDENCE_KINDS,
    TSV_COLUMNS,
    AcquisitionLoopResult,
    classify_task_mode,
    validate_evidence,
    determine_record_status,
    parse_acquisition_tsv,
    validate_acquisition_tsv,
    run_acquisition_loop,
    create_acquisition_tasks_from_gaps,
    apply_tsv_decisions,
)
from kairoskopion.registry.services import RegistryHub


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def hub(tmp_path):
    return RegistryHub(data_dir=tmp_path / "registry")


@pytest.fixture
def evidence_pack_dir(tmp_path):
    d = tmp_path / "evidence_packs"
    d.mkdir()
    pack = d / "test_evidence_pack.md"
    pack.write_text("# Test Evidence Pack\n## Journal Identity\nName: Test Journal\nISSN: 1234-5678\n" * 5, encoding="utf-8")
    return d


@pytest.fixture
def sample_harvest_tasks():
    return [
        {
            "task_id": "htask_001",
            "task_type": "ingest_local_evidence_pack",
            "status": "ready",
            "local_source_ref": "",
            "adapter_hint": "",
            "query": "Ingest 5 venue evidence packs",
            "priority": "high",
        },
        {
            "task_id": "htask_002",
            "task_type": "fetch_venue_by_issn",
            "status": "ready",
            "adapter_hint": "openalex",
            "query": "fetch_venue_by_issn via OpenAlex",
            "priority": "normal",
        },
        {
            "task_id": "htask_003",
            "task_type": "fetch_metrics_by_venue",
            "status": "blocked",
            "adapter_hint": "scopus",
            "blocked_reason": "Requires auth/payment",
            "query": "fetch_metrics_by_venue via Scopus",
            "priority": "normal",
        },
        {
            "task_id": "htask_004",
            "task_type": "manual_web_lookup",
            "status": "planned",
            "adapter_hint": "manual_url",
            "query": "Manual lookup for VAK list",
            "priority": "normal",
        },
        {
            "task_id": "htask_005",
            "task_type": "fetch_venue_by_issn",
            "status": "completed",
            "adapter_hint": "crossref",
            "query": "Already completed",
            "priority": "normal",
        },
    ]


@pytest.fixture
def valid_tsv():
    return (
        "task_id\tauthority_id\ttarget_kind\ttarget_name\tclaim_type\t"
        "required_evidence\tsupplied_evidence_path_or_url\tevidence_kind\t"
        "access_status\treviewer_note\tdecision\n"
        "htask_001\tauth_vak\tvenue\tTest Journal\tvak_status\t"
        "VAK list\t\tmanual_note_with_citation\taccessible\t"
        "Confirmed via VAK website\taccept\n"
        "htask_002\tauth_scopus\tvenue_metric\tSJR\tmetric_value\t"
        "Scopus page\t\tinsufficient\tinaccessible\t"
        "No access\treject\n"
        "htask_003\tauth_doaj\tvenue\tTest\toa_status\t"
        "DOAJ entry\t\turl_reference_only\taccessible\t"
        "Skipping\tskip\n"
    )


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------

class TestClassifyTaskMode:
    def test_local_evidence_ready(self, evidence_pack_dir):
        task = {
            "task_type": "ingest_local_evidence_pack",
            "status": "ready",
            "local_source_ref": str(evidence_pack_dir),
        }
        assert classify_task_mode(task, evidence_pack_dir=evidence_pack_dir) == "local_evidence_ready"

    def test_blocked_no_paid_api(self):
        task = {"task_type": "fetch_metrics_by_venue", "status": "blocked", "adapter_hint": "scopus"}
        assert classify_task_mode(task) == "blocked_no_paid_api"

    def test_paid_adapter_blocked(self):
        task = {"task_type": "fetch_venue_by_issn", "status": "ready", "adapter_hint": "wos"}
        assert classify_task_mode(task, no_paid_api=True) == "blocked_no_paid_api"

    def test_free_adapter_ready(self):
        task = {"task_type": "fetch_venue_by_issn", "status": "ready", "adapter_hint": "openalex"}
        assert classify_task_mode(task) == "ready_for_import"

    def test_manual_lookup(self):
        task = {"task_type": "manual_web_lookup", "status": "planned", "adapter_hint": "manual_url"}
        assert classify_task_mode(task) == "manual_lookup_required"

    def test_completed_is_verified(self):
        task = {"task_type": "fetch_venue_by_issn", "status": "completed"}
        assert classify_task_mode(task) == "verified"

    def test_missing_source(self):
        task = {
            "task_type": "ingest_local_evidence_pack",
            "status": "ready",
            "local_source_ref": "/nonexistent/path",
        }
        assert classify_task_mode(task, evidence_pack_dir=Path("/nonexistent")) == "blocked_missing_source"


# ---------------------------------------------------------------------------
# Evidence validation tests
# ---------------------------------------------------------------------------

class TestValidateEvidence:
    def test_local_pack_valid(self, tmp_path):
        f = tmp_path / "pack.md"
        f.write_text("Evidence content here" * 10, encoding="utf-8")
        valid, reason = validate_evidence("local_evidence_pack", str(f))
        assert valid is True

    def test_local_pack_missing(self):
        valid, reason = validate_evidence("local_evidence_pack", "/no/such/file.md")
        assert valid is False
        assert "not found" in reason

    def test_local_pack_inline_content(self):
        valid, _ = validate_evidence("local_evidence_pack", evidence_content="A" * 100)
        assert valid is True

    def test_url_reference_valid(self):
        valid, _ = validate_evidence("url_reference_only", "https://example.com/journal")
        assert valid is True

    def test_url_reference_no_url(self):
        valid, _ = validate_evidence("url_reference_only")
        assert valid is False

    def test_insufficient_always_invalid(self):
        valid, _ = validate_evidence("insufficient")
        assert valid is False

    def test_unknown_kind(self):
        valid, _ = validate_evidence("fake_kind")
        assert valid is False

    def test_manual_note_too_short(self):
        valid, _ = validate_evidence("manual_note_with_citation", evidence_content="short")
        assert valid is False

    def test_manual_note_valid(self):
        valid, _ = validate_evidence("manual_note_with_citation", evidence_content="This is a manual note with proper citation ref")
        assert valid is True


# ---------------------------------------------------------------------------
# Record status determination
# ---------------------------------------------------------------------------

class TestDetermineRecordStatus:
    def test_llm_seed_stays_without_evidence(self):
        status = determine_record_status("provisional_llm_seed", "insufficient", False)
        assert status == "provisional_llm_seed"

    def test_llm_seed_not_verified_by_url(self):
        status = determine_record_status("provisional_llm_seed", "url_reference_only", True)
        assert status == "provisional_llm_seed"

    def test_llm_seed_manual_note_requires_review(self):
        status = determine_record_status("provisional_llm_seed", "manual_note_with_citation", True)
        assert status == "manual_review_required"

    def test_local_evidence_upgrades(self):
        status = determine_record_status("provisional", "local_evidence_pack", True)
        assert status == "local_evidence_supported"

    def test_adapter_result_verifies(self):
        status = determine_record_status("provisional", "adapter_result", True)
        assert status == "externally_verified"

    def test_invalid_evidence_preserves_status(self):
        status = determine_record_status("provisional", "local_evidence_pack", False)
        assert status == "provisional"

    def test_corpus_grounded_upgrades(self):
        status = determine_record_status("provisional", "corpus_grounded", True)
        assert status == "local_evidence_supported"


# ---------------------------------------------------------------------------
# TSV parsing
# ---------------------------------------------------------------------------

class TestTSVImport:
    def test_valid_tsv(self, valid_tsv):
        rows, errors = parse_acquisition_tsv(valid_tsv)
        assert len(rows) == 3
        assert len(errors) == 0

    def test_missing_columns(self):
        bad_tsv = "task_id\tdecision\nhtask_001\taccept\n"
        rows, errors = parse_acquisition_tsv(bad_tsv)
        assert len(errors) == 1
        assert "Missing columns" in errors[0]

    def test_missing_task_id(self):
        tsv = "\t".join(TSV_COLUMNS) + "\n" + "\t".join([""] * len(TSV_COLUMNS)) + "\n"
        rows, errors = parse_acquisition_tsv(tsv)
        assert len(errors) >= 1
        assert "task_id" in errors[0]

    def test_invalid_decision(self):
        header = "\t".join(TSV_COLUMNS) + "\n"
        values = ["htask_001", "auth", "venue", "Test", "claim", "req", "", "manual_note_with_citation", "ok", "note", "maybe"]
        row = "\t".join(values) + "\n"
        rows, errors = parse_acquisition_tsv(header + row)
        assert len(errors) == 1
        assert "invalid decision" in errors[0]

    def test_validate_valid(self, valid_tsv):
        valid, errors = validate_acquisition_tsv(valid_tsv)
        assert valid is True
        assert len(errors) == 0

    def test_validate_invalid(self):
        valid, errors = validate_acquisition_tsv("bad\theader\n")
        assert valid is False


# ---------------------------------------------------------------------------
# Acquisition loop execution
# ---------------------------------------------------------------------------

class TestAcquisitionLoop:
    def test_gap_to_acquisition_task(self, hub):
        gaps = ["Missing education venue universe", "No Scopus metrics"]
        tasks = create_acquisition_tasks_from_gaps(gaps, hub)
        assert len(tasks) == 2
        assert all(t.status == "open" for t in tasks)
        assert all(t.task_type == "gap_resolution" for t in tasks)

    def test_no_paid_api_stays_blocked(self, hub, sample_harvest_tasks):
        result = run_acquisition_loop(sample_harvest_tasks, hub, no_paid_api=True)
        blocked_tasks = [d for d in result.task_details if d["new_status"] == "blocked_no_paid_api"]
        assert len(blocked_tasks) >= 1

    def test_completed_task_counted(self, hub, sample_harvest_tasks):
        result = run_acquisition_loop(sample_harvest_tasks, hub, no_paid_api=True)
        verified = [d for d in result.task_details if d["new_status"] == "verified"]
        assert len(verified) == 1

    def test_local_evidence_closes_task(self, hub, evidence_pack_dir):
        tasks = [{
            "task_id": "htask_local",
            "task_type": "ingest_local_evidence_pack",
            "status": "ready",
            "local_source_ref": str(evidence_pack_dir),
            "query": "Ingest packs",
            "priority": "high",
        }]
        result = run_acquisition_loop(tasks, hub, evidence_pack_dir=evidence_pack_dir)
        assert result.closed_local == 1
        assert result.source_packets_created == 1

    def test_source_packet_provenance_preserved(self, hub, evidence_pack_dir):
        tasks = [{
            "task_id": "htask_prov",
            "task_type": "ingest_local_evidence_pack",
            "status": "ready",
            "local_source_ref": str(evidence_pack_dir),
            "query": "Provenance test",
            "priority": "high",
        }]
        run_acquisition_loop(tasks, hub, evidence_pack_dir=evidence_pack_dir)
        packets = hub.packets.list_all()
        assert len(packets) >= 1
        pkt = packets[0]
        assert pkt.source_type == "local_file"
        assert pkt.source_id == str(evidence_pack_dir)
        assert pkt.evidence_status == "corpus_grounded"

    def test_manual_task_created(self, hub, sample_harvest_tasks):
        result = run_acquisition_loop(sample_harvest_tasks, hub, no_paid_api=True)
        manual = [d for d in result.task_details if d["new_status"] == "manual_lookup_required"]
        assert len(manual) >= 1

    def test_dogfood_counts_stable(self, hub, sample_harvest_tasks):
        result = run_acquisition_loop(sample_harvest_tasks, hub, no_paid_api=True)
        assert result.total_tasks == 5
        total_accounted = (
            result.closed_local + result.closed_adapter +
            result.blocked + result.manual_required + result.rejected
        )
        assert total_accounted == 5

    def test_result_serializable(self, hub, sample_harvest_tasks):
        result = run_acquisition_loop(sample_harvest_tasks, hub, no_paid_api=True)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert json.dumps(d, ensure_ascii=False)


# ---------------------------------------------------------------------------
# TSV apply decisions
# ---------------------------------------------------------------------------

class TestApplyTSVDecisions:
    def test_apply_accept_with_manual_note(self, hub):
        tsv = (
            "task_id\tauthority_id\ttarget_kind\ttarget_name\tclaim_type\t"
            "required_evidence\tsupplied_evidence_path_or_url\tevidence_kind\t"
            "access_status\treviewer_note\tdecision\n"
            "htask_001\tauth_vak\tvenue\tTest\tvak\treq\t\t"
            "manual_note_with_citation\tok\tVAK confirmed via official list screenshot\taccept\n"
        )
        accepted, rejected, skipped, errors = apply_tsv_decisions(tsv, hub)
        assert accepted == 1
        assert rejected == 0
        assert len(errors) == 0

    def test_apply_reject(self, hub):
        tsv = (
            "task_id\tauthority_id\ttarget_kind\ttarget_name\tclaim_type\t"
            "required_evidence\tsupplied_evidence_path_or_url\tevidence_kind\t"
            "access_status\treviewer_note\tdecision\n"
            "htask_002\tauth_scopus\tmetric\tSJR\tmetric\treq\t\t"
            "insufficient\tinaccessible\tNo access\treject\n"
        )
        accepted, rejected, skipped, errors = apply_tsv_decisions(tsv, hub)
        assert rejected == 1

    def test_bad_tsv_returns_errors(self, hub):
        accepted, rejected, skipped, errors = apply_tsv_decisions("bad\n", hub)
        assert len(errors) > 0
