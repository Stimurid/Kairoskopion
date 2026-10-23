"""TRM-073 W3 multi-head discovery intake and W2 preservation regressions."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from kairoskopion.services.trm073_research_stage import (
    PACKET_SCHEMA_W3,
    readback_research_stage,
    register_packet_stager,
    stage_research_packet,
)

OWNER_W3 = Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\TRM073_W3_SCIENCE_INPUT_20261020.json")
OWNER_W3_SHA = "fc88b3f51ec6baea196e7317ccdbe74f4e7dc79d540e324a84e026e6684b3ba7"
OWNER_W2 = Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\TRM073_W2_SCIENCE_INPUT_20261020.json")
OWNER_W2_SHA = "eb5afb2838dec43a20b1d7a7edab2e632963a6099232f122e04d379f3a4f2547"
OWNER_W1_MANIFEST = Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\case-manifest-v3-w1.json")


def _owner_head_bindings_json(manifest_path: Path) -> str:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index = {(s["family"], s["key"]): s for s in manifest.get("sources") or []}
    bindings = []
    for head_id, family, key, version in (
        ("HEAD-01", "A", "A07", "v0.7"),
        ("HEAD-03", "C", "C04", "v0.4"),
    ):
        source = index[(family, key)]
        local_path = Path(str(source["local_path"]))
        digest = hashlib.sha256(local_path.read_bytes()).hexdigest().upper()
        bindings.append({
            "head_id": head_id,
            "source_family": family,
            "source_key": key,
            "expected_content_sha256": digest,
            "expected_version": version,
        })
    return json.dumps(bindings)


def _synthetic_w3_packet() -> dict:
    works = [
        {
            "id": "W3-A01",
            "title": "Comparator A",
            "actual_venue": "Journal A",
            "doi": "10.1000/w3a01",
            "source_url": "https://publisher.example/a01",
            "genre": "RESEARCH",
            "read_depth": "ABSTRACT_ONLY",
            "epistemic_role": "PUBLISHED_COMPARATOR",
            "venue_native_verification": "PUBLISHER_PAGE_VERIFIED",
            "full_text_certified": False,
        },
        {
            "id": "W3-C01",
            "title": "Comparator C",
            "actual_venue": "Journal C",
            "doi": "10.1000/w3c01",
            "source_url": "https://publisher.example/c01",
            "genre": "RESEARCH",
            "read_depth": "METADATA_ONLY",
            "epistemic_role": "PUBLISHED_COMPARATOR",
            "venue_native_verification": "PUBLISHER_PAGE_VERIFIED",
            "full_text_certified": False,
        },
    ]
    routes = [
        {
            "route_candidate_id": "A-TEST",
            "head_id": "HEAD-01",
            "journal_name": "Journal A",
            "opponent_id": "W3-A01",
            "scholarly_problem": "Problem A",
            "required_next_test": "Need full text",
            "route_status": "DISCOVERED_PREQUALIFICATION",
            "author_gate": "HOLD",
            "current_cfp": "NOT_ASSERTED",
            "w12_equivalent": False,
            "editor_model": "PENDING",
            "journal_policy": "PENDING",
        },
        {
            "route_candidate_id": "C-TEST",
            "head_id": "HEAD-03",
            "journal_name": "Journal C",
            "opponent_id": "W3-C01",
            "scholarly_problem": "Problem C",
            "required_next_test": "Need mechanism evidence",
            "route_status": "DISCOVERED_PREQUALIFICATION",
            "author_gate": "HOLD",
            "current_cfp": "NOT_ASSERTED",
            "w12_equivalent": False,
            "editor_model": "PENDING",
            "journal_policy": "PENDING",
        },
        {
            "route_candidate_id": "C-MISSING-OPP",
            "head_id": "HEAD-03",
            "journal_name": "Форсайт",
            "opponent_id": "W3-R03",
            "scholarly_problem": "Missing opponent",
            "required_next_test": "Do not fabricate",
            "route_status": "DISCOVERED_PREQUALIFICATION",
            "author_gate": "HOLD",
            "current_cfp": "NOT_ASSERTED",
            "w12_equivalent": False,
            "editor_model": "PENDING",
            "journal_policy": "PENDING",
        },
    ]
    return {
        "schema": PACKET_SCHEMA_W3,
        "case_id": "CASE-W3",
        "wave_id": "W3-SYNTH",
        "primary_claim_text_status": "ORIGINAL_WORLD_CLAIM_ANCHORS_PENDING",
        "scientific_owner_decision": "HOLD",
        "route_target_min_w12_equivalent": 80,
        "work_refs": works,
        "route_candidates": routes,
        "official_policies": [],
        "safety": {
            "send": False,
            "article_seed_created": False,
            "world_mutation": False,
        },
    }


def _write_packet(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "w3.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_w3_stages_evidence_route_challenges_and_two_head_reopens(tmp_path):
    storage = tmp_path / "stage"
    result = stage_research_packet(_write_packet(tmp_path, _synthetic_w3_packet()), storage)
    receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["counts"]["publisher_references"] == 2
    assert receipt["counts"]["scholarly_route_challenges"] == 3
    assert receipt["counts"]["field_reopen_proposals"] == 2
    assert receipt["counts"]["proposed_routes"] == 3
    assert receipt["counts"]["w12_equivalent_routes"] == 0
    assert "W3-R03" in receipt["unresolved_refs"]
    graph = OpportunityGraphStore(storage)
    evidence = graph.list_records("Evidence")
    assert all(not row.get("full_text_certified") for row in evidence)
    assert graph.list_records("ArticleSeed") == []
    assert graph.list_records("OpportunityRoute") == []
    assert graph.list_records("World") == []
    reopens = [x for x in graph.replay_events() if x["kind"] == "FIELD_REOPEN_PROPOSAL"]
    assert len(reopens) == 2
    assert {x["subject_id"] for x in reopens} == {"HEAD-01", "HEAD-03"}
    assert graph.list_records("Journal") == []
    candidates = graph.list_records("JournalDiscoveryCandidate")
    assert candidates
    assert all(not c.get("official_url") for c in candidates)
    readback = json.loads(
        (storage / "research_stage" / "CASE-W3" / "W3-SYNTH" / "readback.json").read_text(encoding="utf-8")
    )
    assert readback["per_route_edges_verified"] is True


def test_w3_rejects_full_text_certified_claims(tmp_path):
    payload = _synthetic_w3_packet()
    payload["work_refs"][0]["full_text_certified"] = True
    with pytest.raises(ValueError, match="full_text_certified cannot be asserted"):
        stage_research_packet(_write_packet(tmp_path, payload), tmp_path / "stage")


def test_w3_rejects_full_text_read_depth(tmp_path):
    payload = _synthetic_w3_packet()
    payload["work_refs"][0]["read_depth"] = "FULL_TEXT"
    with pytest.raises(ValueError, match="FULL_TEXT read_depth is not allowed"):
        stage_research_packet(_write_packet(tmp_path, payload), tmp_path / "stage")


def test_w3_manifest_rejects_expected_sha_mismatch(tmp_path):
    source_path = tmp_path / "a07.txt"
    source_path.write_text("wrong bytes\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "schema": "TRM074_COLD_CASE_V1",
        "case_id": "CASE-BIND",
        "publication_send": "DISALLOWED",
        "sources": [{
            "family": "A",
            "key": "A07",
            "source_id": "drive:test-a07",
            "kind": "SPEECH_SCRIPT",
            "version": "v0.7",
            "local_path": str(source_path),
        }],
    }), encoding="utf-8")
    payload = _synthetic_w3_packet()
    payload["w1_source_manifest_path"] = str(manifest_path)
    payload["original_head_sources"] = [{
        "head_id": "HEAD-01",
        "source_family": "A",
        "source_key": "A07",
        "expected_content_sha256": "DEADBEEF",
    }]
    with pytest.raises(ValueError, match="expected_content_sha256"):
        stage_research_packet(_write_packet(tmp_path, payload), tmp_path / "bind-stage")


def test_w3_rejects_invalid_head_id(tmp_path):
    payload = _synthetic_w3_packet()
    payload["route_candidates"][0]["head_id"] = "HEAD-02"
    with pytest.raises(ValueError, match="HEAD-01 or HEAD-03"):
        stage_research_packet(_write_packet(tmp_path, payload), tmp_path / "stage")


def test_w3_manifest_binds_versioned_original_sources(tmp_path):
    source_path = tmp_path / "a07.txt"
    source_path.write_text("synthetic original speech script body for binding test\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "schema": "TRM074_COLD_CASE_V1",
        "case_id": "CASE-BIND",
        "publication_send": "DISALLOWED",
        "sources": [{
            "family": "A",
            "key": "A07",
            "source_id": "drive:test-a07",
            "kind": "SPEECH_SCRIPT",
            "version": "v0.7",
            "author_state": "NOT_VERIFIED",
            "local_path": str(source_path),
        }],
    }), encoding="utf-8")
    payload = _synthetic_w3_packet()
    payload["w1_source_manifest_path"] = str(manifest_path)
    payload["original_head_sources"] = [{
        "head_id": "HEAD-01",
        "source_family": "A",
        "source_key": "A07",
    }]
    storage = tmp_path / "bind-stage"
    stage_research_packet(_write_packet(tmp_path, payload), storage)
    receipt = json.loads(
        (storage / "research_stage" / "CASE-W3" / "W3-SYNTH" / "receipt.json").read_text(encoding="utf-8")
    )
    binding = receipt["head_source_bindings"]["HEAD-01"]
    assert binding["source_key"] == "A07"
    assert binding["version"] == "v0.7"
    assert binding["research_method"] == "UNKNOWN"
    assert binding["content_sha256"] == hashlib.sha256(source_path.read_bytes()).hexdigest().upper()
    head_return = next(x for x in receipt["head_return_refs"] if x["head_id"] == "HEAD-01")
    assert head_return["research_method"] == "UNKNOWN"
    events = OpportunityGraphStore(storage).replay_events()
    head_event = next(x for x in events if x["event_id"] == head_return["event_id"])
    assert head_event["source_ref"] == "drive:test-a07"


def test_w3_idempotent_receipt_and_checkpoint_rejects_revision(tmp_path):
    storage = tmp_path / "stage"
    source = _write_packet(tmp_path, _synthetic_w3_packet())
    one = stage_research_packet(source, storage)
    two = stage_research_packet(source, storage)
    assert one == two
    changed = copy.deepcopy(_synthetic_w3_packet())
    changed["work_refs"][0]["title"] = "Changed title"
    with pytest.raises(ValueError, match="different immutable packet"):
        stage_research_packet(_write_packet(tmp_path, changed), storage)


def test_unsupported_schema_fails_without_storage_mutation(tmp_path):
    storage = tmp_path / "stage"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema": "TRM073_W4_FUTURE_V1", "case_id": "x", "wave_id": "y"}), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported research packet schema"):
        stage_research_packet(path, storage)
    assert not storage.exists()


def test_register_future_schema_without_copying_w2_logic(tmp_path):
    def _noop_stager(packet: dict, raw: bytes, storage: Path) -> dict:
        return {"status": "noop", "bytes": len(raw)}

    register_packet_stager("TRM073_W4_STUB_V1", _noop_stager)
    path = tmp_path / "w4.json"
    path.write_text(
        json.dumps({"schema": "TRM073_W4_STUB_V1", "case_id": "c", "wave_id": "w"}),
        encoding="utf-8",
    )
    assert stage_research_packet(path, tmp_path / "s")["status"] == "noop"


@pytest.mark.skipif(not OWNER_W3.is_file(), reason="owner W3 packet not on host")
def test_owner_w3_real_packet_counts_and_idempotency(tmp_path, monkeypatch):
    raw = OWNER_W3.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == OWNER_W3_SHA
    if OWNER_W1_MANIFEST.is_file():
        monkeypatch.setenv("TRM073_W1_SOURCE_MANIFEST", str(OWNER_W1_MANIFEST))
        monkeypatch.setenv("TRM073_ORIGINAL_HEAD_SOURCES", _owner_head_bindings_json(OWNER_W1_MANIFEST))
    storage = tmp_path / "owner-w3"
    one = stage_research_packet(OWNER_W3, storage)
    two = stage_research_packet(OWNER_W3, storage)
    assert one == two
    receipt = json.loads(Path(one["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["counts"]["publisher_references"] == 16
    assert receipt["counts"]["scholarly_route_challenges"] == 9
    assert receipt["counts"]["field_reopen_proposals"] == 2
    assert receipt["counts"]["proposed_routes"] == 9
    assert receipt["counts"]["w12_equivalent_routes"] == 0
    assert "W3-R03" in receipt["unresolved_refs"]
    readback = json.loads(Path(one["readback_path"]).read_text(encoding="utf-8"))
    assert readback["per_route_edges_verified"] is True
    graph = OpportunityGraphStore(storage)
    assert len(graph.list_records("Evidence")) == 16
    assert graph.list_records("ArticleSeed") == []
    assert graph.list_records("OpportunityRoute") == []
    assert graph.list_records("Journal") == []
    for candidate in graph.list_records("JournalDiscoveryCandidate"):
        assert not candidate.get("official_url")
    if OWNER_W1_MANIFEST.is_file():
        bindings = receipt["head_source_bindings"]
        assert bindings["HEAD-01"]["source_key"] == "A07"
        assert bindings["HEAD-03"]["source_key"] == "C04"
        for head_id, family, key in (("HEAD-01", "A", "A07"), ("HEAD-03", "C", "C04")):
            manifest = json.loads(OWNER_W1_MANIFEST.read_text(encoding="utf-8"))
            source = next(s for s in manifest["sources"] if s["family"] == family and s["key"] == key)
            expected = hashlib.sha256(Path(source["local_path"]).read_bytes()).hexdigest().upper()
            assert bindings[head_id]["content_sha256"] == expected
        assert bindings["HEAD-01"]["binding_verification"] == "VERIFIED_BYTES"
        assert bindings["HEAD-03"]["binding_verification"] == "VERIFIED_BYTES"
        for head_ref in receipt["head_return_refs"]:
            assert head_ref["research_method"] == "UNKNOWN"


@pytest.mark.skipif(not OWNER_W2.is_file(), reason="owner W2 packet not on host")
def test_owner_w2_real_packet_remains_idempotent(tmp_path):
    raw = OWNER_W2.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == OWNER_W2_SHA
    storage = tmp_path / "owner-w2"
    one = stage_research_packet(OWNER_W2, storage)
    two = stage_research_packet(OWNER_W2, storage)
    assert one == two
    receipt = json.loads(Path(one["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["counts"]["publisher_works"] == 8
    assert receipt["counts"]["scientific_objections"] == 6
    assert receipt["counts"]["field_reopen_proposals"] == 6


def _stage_bound_w3(tmp_path: Path) -> tuple[Path, Path]:
    source_path = tmp_path / "head-a.txt"
    source_path.write_text("synthetic bound head source for cold readback\n", encoding="utf-8")
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest().upper()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "schema": "TRM074_COLD_CASE_V1",
        "case_id": "CASE-RB",
        "publication_send": "DISALLOWED",
        "sources": [{
            "family": "A",
            "key": "A07",
            "source_id": "fixture:a07",
            "kind": "SPEECH_SCRIPT",
            "version": "v0.7",
            "local_path": str(source_path),
        }],
    }), encoding="utf-8")
    payload = _synthetic_w3_packet()
    payload["w1_source_manifest_path"] = str(manifest_path)
    payload["original_head_sources"] = [{
        "head_id": "HEAD-01",
        "source_family": "A",
        "source_key": "A07",
        "expected_content_sha256": digest,
    }]
    storage = tmp_path / "rb-stage"
    packet_path = _write_packet(tmp_path, payload)
    stage_research_packet(packet_path, storage)
    return storage, source_path


def test_readback_rehashes_w1_sources_and_rejects_post_stage_tamper(tmp_path):
    storage, source_path = _stage_bound_w3(tmp_path)
    readback_research_stage(storage, "CASE-W3", "W3-SYNTH")
    source_path.write_text("tampered after staging\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no longer match pinned"):
        readback_research_stage(storage, "CASE-W3", "W3-SYNTH")


def test_readback_rejects_verified_bytes_without_manifest_path(tmp_path):
    storage, _source_path = _stage_bound_w3(tmp_path)
    receipt_path = storage / "research_stage" / "CASE-W3" / "W3-SYNTH" / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["w1_source_manifest_path"] = None
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="requires accessible w1_source_manifest_path"):
        readback_research_stage(storage, "CASE-W3", "W3-SYNTH")


def test_readback_detects_tampered_journal_candidate_name(tmp_path):
    storage, _ = _stage_bound_w3(tmp_path)
    graph = OpportunityGraphStore(storage)
    candidate = next(c for c in graph.list_records("JournalDiscoveryCandidate"))
    record_path = storage / "kairon_provider" / "opportunity_graph" / "records"
    for path in record_path.glob("*.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("id") == candidate["id"]:
            row["canonical_name"] = "Tampered Journal"
            path.write_text(json.dumps(row), encoding="utf-8")
            break
    with pytest.raises(ValueError, match="journal discovery candidate name mismatch"):
        readback_research_stage(storage, "CASE-W3", "W3-SYNTH")


def test_readback_detects_tampered_opponent_doi(tmp_path):
    storage, _ = _stage_bound_w3(tmp_path)
    graph = OpportunityGraphStore(storage)
    evidence = next(e for e in graph.list_records("Evidence") if e.get("publisher_ref"))
    record_path = storage / "kairon_provider" / "opportunity_graph" / "records"
    for path in record_path.glob("*.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("id") == evidence["id"]:
            row["publisher_ref"]["doi"] = "10.9999/tampered"
            path.write_text(json.dumps(row), encoding="utf-8")
            break
    with pytest.raises(ValueError, match="opponent evidence DOI mismatch"):
        readback_research_stage(storage, "CASE-W3", "W3-SYNTH")


def test_readback_detects_tampered_field_reopen_level(tmp_path):
    storage, _ = _stage_bound_w3(tmp_path)
    graph = OpportunityGraphStore(storage)
    reopen = next(e for e in graph.replay_events() if e["kind"] == "FIELD_REOPEN_PROPOSAL")
    event_path = storage / "kairon_provider" / "opportunity_graph" / "events"
    for path in event_path.glob("*.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("event_id") == reopen["event_id"]:
            row["reopen_level"] = "L5"
            path.write_text(json.dumps(row), encoding="utf-8")
            break
    with pytest.raises(ValueError, match="reopen level mismatch"):
        readback_research_stage(storage, "CASE-W3", "W3-SYNTH")


def test_readback_detects_tampered_evidence_read_depth(tmp_path):
    storage, _ = _stage_bound_w3(tmp_path)
    graph = OpportunityGraphStore(storage)
    evidence = next(
        e for e in graph.list_records("Evidence")
        if e.get("read_depth") == "ABSTRACT" and not e.get("full_text_certified")
    )
    record_path = storage / "kairon_provider" / "opportunity_graph" / "records"
    for path in record_path.glob("*.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("id") == evidence["id"]:
            row["read_depth"] = "FULL_TEXT"
            path.write_text(json.dumps(row), encoding="utf-8")
            break
    with pytest.raises(ValueError, match="read_depth mismatch"):
        readback_research_stage(storage, "CASE-W3", "W3-SYNTH")


def test_readback_detects_tampered_field_reopen_next_question(tmp_path):
    storage, _ = _stage_bound_w3(tmp_path)
    graph = OpportunityGraphStore(storage)
    reopen = next(e for e in graph.replay_events() if e["kind"] == "FIELD_REOPEN_PROPOSAL")
    event_path = storage / "kairon_provider" / "opportunity_graph" / "events"
    for path in event_path.glob("*.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("event_id") == reopen["event_id"]:
            row["next_question"] = "Tampered reopen question without author review?"
            path.write_text(json.dumps(row), encoding="utf-8")
            break
    with pytest.raises(ValueError, match="next_question mismatch"):
        readback_research_stage(storage, "CASE-W3", "W3-SYNTH")


def test_readback_rejects_tampered_manifest_source_identity(tmp_path):
    storage, _ = _stage_bound_w3(tmp_path)
    readback_research_stage(storage, "CASE-W3", "W3-SYNTH")
    receipt_path = storage / "research_stage" / "CASE-W3" / "W3-SYNTH" / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    manifest_path = Path(receipt["w1_source_manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["source_id"] = "fixture:tampered-source-id"
    manifest["sources"][0]["version"] = "v9.9"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest source_id mismatch vs staged binding"):
        readback_research_stage(storage, "CASE-W3", "W3-SYNTH")


def test_readback_rejects_removed_evidence_item_hash(tmp_path):
    storage, _ = _stage_bound_w3(tmp_path)
    records_path = storage / "kairon_provider" / "opportunity_graph" / "records"
    changed = False
    for path in records_path.glob("*.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        anchors = row.get("passage_anchors") or []
        if row.get("id", "").startswith("trm073-w3-evidence-") and anchors and anchors[0].get("packet_item_sha256"):
            anchors[0].pop("packet_item_sha256")
            path.write_text(json.dumps(row), encoding="utf-8")
            changed = True
            break
    assert changed, "fixture must corrupt one persisted W3 Evidence item hash"
    with pytest.raises(ValueError, match="packet_item_sha256 mismatch"):
        readback_research_stage(storage, "CASE-W3", "W3-SYNTH")


def test_readback_rejects_removed_field_reopen_question(tmp_path):
    storage, _ = _stage_bound_w3(tmp_path)
    event_path = storage / "kairon_provider" / "opportunity_graph" / "events"
    changed = False
    for path in event_path.glob("*.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("kind") == "FIELD_REOPEN_PROPOSAL" and "next_question" in row:
            row.pop("next_question")
            path.write_text(json.dumps(row), encoding="utf-8")
            changed = True
            break
    assert changed, "fixture must remove a persisted held reopen question"
    with pytest.raises(ValueError, match="next_question mismatch"):
        readback_research_stage(storage, "CASE-W3", "W3-SYNTH")


def test_readback_rejects_manifest_version_change_alone(tmp_path):
    storage, _ = _stage_bound_w3(tmp_path)
    receipt_path = storage / "research_stage" / "CASE-W3" / "W3-SYNTH" / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    manifest_path = Path(receipt["w1_source_manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["version"] = "v-new-with-unchanged-source-id-and-bytes"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest version mismatch vs staged binding"):
        readback_research_stage(storage, "CASE-W3", "W3-SYNTH")


def test_owner_w3_cli_cold_process_when_packet_present(tmp_path):
    if not OWNER_W3.is_file():
        pytest.skip("owner W3 packet not on host")
    storage = tmp_path / "cli-w3"
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_trm073_research_stage.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    first = stage_research_packet(OWNER_W3, storage)
    cold = subprocess.run(
        [sys.executable, str(script), "--research-packet", str(OWNER_W3), "--storage-root", str(storage)],
        env=env,
        text=True,
        check=True,
        capture_output=True,
    )
    assert json.loads(cold.stdout) == first
