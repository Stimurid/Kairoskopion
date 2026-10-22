"""Bounded W3-to-W12 batch operator; inherited scholarly gates are not mocked."""
from __future__ import annotations
from pathlib import Path
import json
import os
import subprocess
import sys
import pytest

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from kairoskopion.services.trm073_w12_route_stage import stage_w12_candidate_wave
from tests.test_trm073_w12_route_stage import fixture_route


def test_real_stage_is_called_and_second_wave_run_replays_idempotently(tmp_path):
    packet, path, stage, *_ = fixture_route(tmp_path)
    first = stage_w12_candidate_wave(
        case_id="CASE-SYNTH", storage_root=stage, packet_paths=[path]
    )
    second = stage_w12_candidate_wave(
        case_id="CASE-SYNTH", storage_root=stage, packet_paths=[path]
    )
    assert first["receipt_sha256"] == second["receipt_sha256"]
    for key, expected in {
        "JOURNALS_DISCOVERED": 1, "ROUTES_PROPOSED": 1,
        "W3_PROPOSED": 1, "W3_OPPONENT_RESOLVED": 1,
        "W12_PACKETS_SUPPLIED": 1, "W12_EQUIVALENT_HELD": 1,
        "DEEP_QUALIFIED": 0, "ARTICLE_SEED_CREATED": 0,
        "AUTHOR_APPROVED": 0, "EXTERNAL_SEND": 0,
        "SUBMISSION_READY": 0, "W12_HOLD_OR_BLOCKED": 0,
        "PENDING_W3_OPPONENT": 0, "PENDING_W12_PACKET": 0,
        "BLOCKED_EVIDENCE_OR_POLICY": 0,
    }.items():
        assert first["counts"][key] == expected
    assert first["routes"][0]["route_candidate_id"] == packet["route_candidate_id"]
    assert first["routes"][0]["status"] == "W12_EQUIVALENT_HELD"
    assert json.loads(Path(first["receipt_path"]).read_text())["counts"]["W12_EQUIVALENT_HELD"] == 1
    graph = OpportunityGraphStore(stage)
    assert len(graph.list_records("HuntTrace")) == 1
    assert graph.list_records("ArticleSeed") == []
    assert graph.list_records("OpportunityRoute") == []


def test_existing_unresolved_w3_is_held_not_autofilled(tmp_path):
    _, path, stage, *_ = fixture_route(tmp_path)
    graph = OpportunityGraphStore(stage)
    graph.append_event({
        "event_id": "CASE-SYNTH:W3:route:SECOND",
        "kind": "SCHOLARLY_ROUTE_CHALLENGE",
        "route_candidate_id": "SECOND", "subject_id": "HEAD-01",
        "journal_id": "journal-SYNTH-OTHER", "source_ref": "doi:unverified",
        "opponent_resolved": False, "w12_equivalent": False,
    })
    out = stage_w12_candidate_wave(
        case_id="CASE-SYNTH", storage_root=stage, packet_paths=[path]
    )
    assert out["counts"]["W3_PROPOSED"] == 2
    assert out["counts"]["W3_OPPONENT_RESOLVED"] == 1
    assert out["counts"]["W12_EQUIVALENT_HELD"] == 1
    assert out["counts"]["W12_HOLD_OR_BLOCKED"] == 1
    by_id = {r["route_candidate_id"]: r for r in out["routes"]}
    assert by_id["SECOND"]["status"] == "WAITING_W3_OPPONENT"


def test_without_w12_publisher_packet_does_not_inflate_count(tmp_path):
    _, _, stage, *_ = fixture_route(tmp_path)
    out = stage_w12_candidate_wave(
        case_id="CASE-SYNTH", storage_root=stage, packet_paths=[]
    )
    assert out["counts"]["W12_EQUIVALENT_HELD"] == 0
    assert out["routes"][0]["status"] == "WAITING_W12_SOURCE_VENUE_PACKET"
    assert OpportunityGraphStore(stage).list_records("HuntTrace") == []


def test_wrong_w3_journal_and_duplicate_packet_rejected_before_stage(tmp_path):
    packet, path, stage, *_ = fixture_route(tmp_path)
    with pytest.raises(ValueError, match="duplicate W12 packet"):
        stage_w12_candidate_wave(
            case_id="CASE-SYNTH", storage_root=stage, packet_paths=[path, path]
        )
    packet["journal_id"] = "different-journal"
    path.write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(ValueError, match="journal not identical"):
        stage_w12_candidate_wave(
            case_id="CASE-SYNTH", storage_root=stage, packet_paths=[path]
        )
    assert OpportunityGraphStore(stage).list_records("HuntTrace") == []


def test_changed_original_source_holds_route_and_preserves_first_wave(tmp_path):
    _, path, stage, src, *_ = fixture_route(tmp_path)
    first = stage_w12_candidate_wave(case_id="CASE-SYNTH", storage_root=stage, packet_paths=[path])
    original = Path(first["receipt_path"]).read_bytes()
    src.write_text(src.read_text() + "changed after scientific packet\n", encoding="utf-8")
    second = stage_w12_candidate_wave(case_id="CASE-SYNTH", storage_root=stage, packet_paths=[path])
    assert second["counts"]["W12_EQUIVALENT_HELD"] == 0
    assert second["routes"][0]["status"] == "BLOCKED_W12_EVIDENCE_OR_POLICY"
    assert first["receipt_sha256"] != second["receipt_sha256"]
    assert Path(first["receipt_path"]).read_bytes() == original
    assert second["author_gate"] == "HOLD" and second["external_send"] == "DISABLED"


def test_cli_cold_process_accepts_one_wave_without_chat(tmp_path):
    _, packet, stage, *_ = fixture_route(tmp_path)
    script=Path(__file__).parents[1] / "scripts" / "run_trm073_w12_venue_route.py"
    env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    cmd=[sys.executable, str(script), "--wave-case-id", "CASE-SYNTH",
         "--storage-root", str(stage), "--packet", str(packet)]
    first=subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    assert first.returncode == 0, first.stderr
    second=subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    assert second.returncode == 0, second.stderr
    a=json.loads(first.stdout); b=json.loads(second.stdout)
    assert a["receipt_sha256"]==b["receipt_sha256"]
    assert a["counts"]["W12_EQUIVALENT_HELD"]==1
    assert a["counts"]["ARTICLE_SEED_CREATED"]==0
    assert a["counts"]["EXTERNAL_SEND"]==0
