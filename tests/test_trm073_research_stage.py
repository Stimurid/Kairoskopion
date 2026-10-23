"""Synthetic regressions for the bounded TRM-073 W2 runtime slice."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from kairoskopion.services.trm073_research_stage import stage_research_packet


def packet() -> dict:
    works = []
    for i in range(8):
        works.append({
            "source_id": f"SO-W2-{i+1:02}", "authors": ["Researcher"],
            "title": f"Work {i+1}", "doi": f"10.1000/test{i+1}",
            "kind": "EDITORIAL" if i >= 6 else "RESEARCH",
            "read_depth": "ABSTRACT_ONLY" if i in {2, 5, 7} else "SELECTED_FULL_HTML",
            "publisher_url": f"https://publisher.example/work/{i+1}",
            "venue": "Strategic Organization" if i != 5 else "External Journal",
            "actual_native_venue_verified": i != 5,
        })
    return {
        "schema": "TRM073_W2_SCIENCE_VENUE_RETURN_INPUT_V1",
        "case_id": "CASE", "wave_id": "W2", "head": "HEAD-02",
        "origin_surface": "CHAT_MANUAL_FALLBACK",
        "origin_authority": "PROVISIONAL_SOURCE_BASED_RESEARCH",
        "full_hunt_saturation": False, "runtime_executed": False,
        "world_ref": "world:test",
        "talk_sources": [
            {"work": "B47", "id": "drive:b47", "status": "READ_SELECTED_SECTIONS_SPEECH_SCRIPT"},
            {"work": "B52v2", "id": "drive:b52", "status": "LATER_DRAFT_UNVERIFIED_OWNER_ACCEPTANCE"},
        ],
        "targetworld": {
            "venue": "Strategic Organization", "publisher": "Sage",
            "native_issue": "Volume 24 Issue 2 May 2026", "issue_topic": "Technology",
            "issue_url": "https://publisher.example/toc/24/2",
            "current_special_issue_status": "PUBLISHED_NOT_ACTIVE_CFP",
            "normal_author_guidelines": "https://publisher.example/author-instructions",
            "qualification": "DEEP_FULLTEXT_PENDING",
        },
        "verified_publisher_works": works,
        "scientific_objections": [{
            "event_id": f"W2-OBJ-{i+1:02}", "published_work": f"SO-W2-{i+1:02}",
            "talk_source": "B47", "talk_anchor_approx_utf16": 10,
            "objection": f"Objection {i+1}",
            "source_epistemic_depth": works[i]["read_depth"],
            "verdict": f"REVISE_TEST_{i+1}",
        } for i in range(6)],
        "proposed_article_object": {
            "temporary_title": "Candidate", "claim": "Candidate claim",
            "claim_status": "CANDIDATE_NOT_ESTABLISHED", "author_gate": "HOLD",
            "whitecrow_artikl_gate": "UNTESTED", "world_change": "NONE",
            "journal_send": "DISABLED",
        },
        "negative_tests": ["ABSTRACT_NOT_FULL_READ"],
        "next_runtime_action": "bounded stage",
    }


def write_packet(tmp_path: Path, value: dict | None = None) -> Path:
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(value or packet(), ensure_ascii=False), encoding="utf-8")
    return path


def test_real_path_preserves_native_external_research_editorial_and_depth(tmp_path):
    storage = tmp_path / "stage"
    result = stage_research_packet(write_packet(tmp_path), storage)
    graph = OpportunityGraphStore(storage)
    evidence = graph.list_records("Evidence")
    assert result["counts"]["publisher_works"] == 8
    assert result["counts"]["research_works"] == 6
    assert result["counts"]["editorial_works"] == 2
    assert next(x for x in evidence if x["id"].endswith("06"))["venue_relation"] == "EXTERNAL_COMPARATOR"
    assert next(x for x in evidence if x["id"].endswith("03"))["read_depth"] == "ABSTRACT"
    assert next(x for x in evidence if x["id"].endswith("01"))["read_depth"] == "SECTIONS"
    assert all(not x["full_text_certified"] for x in evidence)
    assert {x["source_kind"] for x in evidence} == {"PUBLISHED_ARTICLE", "PUBLISHED_EDITORIAL"}


def test_historical_issue_author_hold_b52_and_zero_promotions(tmp_path):
    storage = tmp_path / "stage"
    result = stage_research_packet(write_packet(tmp_path), storage)
    receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["venue"]["special_issue_status"] == "PUBLISHED_NOT_ACTIVE_CFP"
    assert receipt["venue"]["live_call"] is False
    assert receipt["author_gate"] == "HOLD"
    assert receipt["b52_status"] == "NEWER_NOT_ADOPTED"
    assert receipt["counts"]["proposed_routes"] == 0
    assert receipt["counts"]["w12_equivalent_routes"] == 0
    assert receipt["counts"]["article_seeds_created"] == 0
    assert receipt["counts"]["external_sends"] == 0
    graph = OpportunityGraphStore(storage)
    assert graph.list_records("ArticleSeed") == []
    assert graph.list_records("OpportunityRoute") == []
    assert graph.list_records("World") == []


def test_six_objections_create_six_held_field_reopens(tmp_path):
    storage = tmp_path / "stage"
    stage_research_packet(write_packet(tmp_path), storage)
    events = OpportunityGraphStore(storage).replay_events()
    objections = [x for x in events if x["kind"] == "SOURCE_CONTRADICTION"]
    reopens = [x for x in events if x["kind"] == "FIELD_REOPEN_PROPOSAL"]
    assert len(objections) == len(reopens) == 6
    assert all(x["author_gate"] == "AUTHOR_REVIEW_REQUIRED" for x in reopens)
    assert all(x["semantic_mutation"] == "NONE" for x in reopens)


def test_stable_rerun_receipt_readback_and_cold_process(tmp_path):
    storage = tmp_path / "stage"
    source = write_packet(tmp_path)
    one = stage_research_packet(source, storage)
    inventory_one = sorted((str(p.relative_to(storage)), hashlib.sha256(p.read_bytes()).hexdigest())
                           for p in storage.rglob("*") if p.is_file())
    two = stage_research_packet(source, storage)
    inventory_two = sorted((str(p.relative_to(storage)), hashlib.sha256(p.read_bytes()).hexdigest())
                           for p in storage.rglob("*") if p.is_file())
    assert one == two
    assert inventory_one == inventory_two
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_trm073_research_stage.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    cold = subprocess.run([
        sys.executable, str(script), "--research-packet", str(source),
        "--storage-root", str(storage),
    ], env=env, text=True, check=True, capture_output=True)
    assert json.loads(cold.stdout) == one


def test_world_nonmutation_is_detected_against_preexisting_world(tmp_path):
    storage = tmp_path / "stage"
    graph = OpportunityGraphStore(storage)
    graph.put("World", {"id": "world", "revision": "r1", "note": "unchanged"})
    stage_research_packet(write_packet(tmp_path), storage)
    assert graph.list_records("World") == [{"kind": "World", "id": "world", "revision": "r1", "note": "unchanged"}]


def test_gate_bypass_and_unknown_objection_source_fail_closed(tmp_path):
    bad = packet()
    bad["proposed_article_object"]["author_gate"] = "ACCEPT"
    try:
        stage_research_packet(write_packet(tmp_path, bad), tmp_path / "stage")
        assert False, "gate bypass should fail"
    except ValueError as exc:
        assert "bypass" in str(exc)
    bad = packet()
    bad["scientific_objections"][0]["published_work"] = "MISSING"
    try:
        stage_research_packet(write_packet(tmp_path, bad), tmp_path / "other")
        assert False, "unknown source should fail"
    except ValueError as exc:
        assert "unknown publisher work" in str(exc)


def test_case_wave_checkpoint_rejects_packet_revision_without_partial_rewrite(tmp_path):
    storage = tmp_path / "stage"
    source = write_packet(tmp_path)
    stage_research_packet(source, storage)
    changed = copy.deepcopy(packet())
    changed["verified_publisher_works"][0]["title"] = "Changed metadata"
    try:
        stage_research_packet(write_packet(tmp_path, changed), storage)
        assert False, "changed packet should need a new wave/checkpoint"
    except ValueError as exc:
        assert "different immutable packet" in str(exc)
    records = [x for x in OpportunityGraphStore(storage).list_records("Evidence")
               if x["id"].endswith("01")]
    assert len(records) == 1
