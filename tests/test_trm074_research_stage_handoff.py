"""TRM-074 bridge contract: real Kairoskopion opportunity graph, no promotion."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from kairoskopion.services.talk_corpus_intake import run_case
from kairoskopion.services.talk_corpus_research_bridge import export_talk_research_evidence
from tests.test_trm074_talk_corpus_intake import fixture_case, _ledger


def _handoff(storage: Path) -> dict:
    return json.loads((storage / "talk_corpora" / "T3-SYNTHETIC" /
                       "research_stage_handoff.json").read_text(encoding="utf-8"))


def test_corpus_evidence_enters_real_opportunity_graph_without_article_promotion(tmp_path):
    manifest, storage, _ = fixture_case(tmp_path)
    run_case(manifest, storage)
    result = export_talk_research_evidence(storage, "T3-SYNTHETIC")
    graph = OpportunityGraphStore(storage)
    refs = graph.list_records("Evidence")
    assert result["evidence_count"] >= 8
    assert len(refs) == result["evidence_count"]
    assert result["article_seed_created"] == 0
    assert graph.list_records("ArticleSeed") == []
    assert graph.list_records("ArticleOpportunity") == []
    for ref in refs:
        assert ref["read_depth"] == "SECTIONS"
        assert ref["source_ref"].startswith("drive:")
        assert ref["passage_anchors"]
        assert ref["qualified_for_article"] is False
        assert ref["qualified_as_journal_policy"] is False
        assert ref["author_approved"] is False
        assert ref["case_ledger_sha256"] == _handoff(storage)["source_ledger_sha256"]
        assert graph.get("Evidence", ref["id"], ref["revision"]) == ref
    assert _handoff(storage)["trm073_status"] == "RESEARCH_SOURCE_STAGE_ONLY_NOT_A_HUNT"


def test_replay_and_independent_cold_process_preserve_graph_state(tmp_path):
    manifest, storage, _ = fixture_case(tmp_path)
    run_case(manifest, storage)
    a = export_talk_research_evidence(storage, "T3-SYNTHETIC")
    b = export_talk_research_evidence(storage, "T3-SYNTHETIC")
    assert a["handoff_sha256"] == b["handoff_sha256"]
    assert a["evidence_count"] == b["evidence_count"]
    graph = OpportunityGraphStore(storage)
    assert len(graph.list_records("Evidence")) == a["evidence_count"]
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_trm074_research_stage_handoff.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run([
        sys.executable, str(script), "--case-id", "T3-SYNTHETIC",
        "--storage-root", str(storage),
    ], env=env, text=True, check=True, capture_output=True)
    assert json.loads(result.stdout)["handoff_sha256"] == a["handoff_sha256"]
    assert len(graph.list_records("Evidence")) == a["evidence_count"]


def test_missing_intake_source_or_tampered_revision_blocks_handoff(tmp_path):
    manifest, storage, _ = fixture_case(tmp_path)
    run_case(manifest, storage)
    regfile = storage / "registries" / "source_snapshots.jsonl"
    lines = regfile.read_text(encoding="utf-8").splitlines()
    regfile.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing from original intake registry"):
        export_talk_research_evidence(storage, "T3-SYNTHETIC")
    regfile.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ledgerfile = storage / "talk_corpora" / "T3-SYNTHETIC" / "case_ledger.json"
    ledger = _ledger(storage)
    ledger["source_snapshots"][0]["content_sha256"] = "0" * 64
    ledgerfile.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="missing from original intake registry"):
        export_talk_research_evidence(storage, "T3-SYNTHETIC")


def test_conceptual_author_acceptance_does_not_authorize_scientific_article(tmp_path):
    manifest, storage, _ = fixture_case(tmp_path)
    run_case(manifest, storage)
    export_talk_research_evidence(storage, "T3-SYNTHETIC")
    graph = OpportunityGraphStore(storage)
    baseline = next(x for x in graph.list_records("Evidence")
                    if x["source_ref"] == "drive:B001")
    assert baseline["author_state"] == "USER_ACCEPTED_CONCEPTS_ONLY"
    assert not baseline["author_approved"]
    assert any(x["anchor_kind"] == "DOCUMENTED_DECISION_WITH_LIMITED_SCOPE"
               for x in baseline["passage_anchors"])
    assert graph.list_records("ArticleSeed") == []


def test_slide_structure_remains_unread_outside_scientific_evidence(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    structure = tmp_path / "slides.json"
    structure.write_text(json.dumps({
        "source_id": "drive:SLIDE001", "slide_count": 1, "revision_id": "v1",
        "slides": [{"slide_object_id": "p", "image_count": 1, "text_characters": 0}],
    }), encoding="utf-8")
    case["related_media"] = [{
        "source_id": "drive:SLIDE001",
        "source_url": "https://docs.google.com/presentation/d/SLIDE001/edit",
        "read_state": "STRUCTURAL_ONLY_IMAGES_NOT_READ",
        "expected_slide_count": 1,
        "structure_path": str(structure),
    }]
    manifest.write_text(json.dumps(case), encoding="utf-8")
    run_case(manifest, storage)
    export_talk_research_evidence(storage, "T3-SYNTHETIC")
    handoff = _handoff(storage)
    assert handoff["unread_media"][0]["source_id"] == "drive:SLIDE001"
    assert "STRUCTURAL_ONLY" in handoff["unread_media"][0]["read_state"]
    assert all(x["source_ref"] != "drive:SLIDE001" for x in
               OpportunityGraphStore(storage).list_records("Evidence"))


def test_ledger_missing_or_wrong_case_fail_closed(tmp_path):
    manifest, storage, _ = fixture_case(tmp_path)
    run_case(manifest, storage)
    with pytest.raises(ValueError, match="ledger missing"):
        export_talk_research_evidence(storage, "ANOTHER-CASE")


def test_manual_w1_research_return_has_provisional_subject_not_primary_proof(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    w1 = tmp_path / "manual_w1.txt"
    quote = "RETURN-A: the author's claim needs a prior-art qualification."
    w1.write_text("Research W1\n\n" + quote +
                  "\n\nNO FULL SOURCE READ CLAIMED.", encoding="utf-8")
    case["sources"].append({
        "family": "CROSS", "key": "TRM073_W1",
        "source_id": "drive:W1_SYNTHETIC",
        "source_url": "https://docs.google.com/document/d/W1_SYNTHETIC/edit",
        "local_path": str(w1), "kind": "RESEARCH_SYNTHESIS",
        "version": "W1", "scope": "MANUAL_HUNT_RETURN_ONLY",
        "author_state": "RESEARCH_RETURN_NOT_AUTHOR_APPROVAL",
        "read_coverage": "RESEARCH_SYNTHESIS_TEXT_ONLY",
    })
    case["discussion_events"] = [{
        "source_key": "TRM073_W1",
        "quote": quote,
        "event_class": "RESEARCH_RETURN",
        "actor_role": "INDAGO_MANUAL",
        "subject_ref": "HEAD-01",
    }]
    manifest.write_text(json.dumps(case), encoding="utf-8")
    run_case(manifest, storage)
    export_talk_research_evidence(storage, "T3-SYNTHETIC")
    evidence = next(x for x in OpportunityGraphStore(storage).list_records("Evidence")
                    if x["source_ref"] == "drive:W1_SYNTHETIC")
    assert evidence["source_kind"] == "RESEARCH_SYNTHESIS"
    assert evidence["read_depth"] == "SECTIONS"
    assert not evidence["qualified_for_article"]
    anchor = evidence["passage_anchors"][0]
    assert anchor["anchor_kind"] == "RESEARCH_RETURN_QUOTE_NOT_PRIMARY_EVIDENCE"
    assert anchor["provisional_subject_ref"] == "HEAD-01"
    assert OpportunityGraphStore(storage).list_records("ArticleSeed") == []
    assert OpportunityGraphStore(storage).list_records("World") == []


def test_research_return_subject_cannot_invent_authorized_article(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    case["discussion_events"] = [{
        "source_key": "B01",
        "quote": "Hypothetical example is not empirical.",
        "event_class": "RESEARCH_RETURN",
        "actor_role": "AI_SYSTEM",
        "subject_ref": "HEAD-99",
    }]
    manifest.write_text(json.dumps(case), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown provisional subject_ref"):
        run_case(manifest, storage)


def test_discussion_event_identity_is_immutable_under_role_mutation(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    case["discussion_events"] = [{
        "source_key": "B01",
        "quote": "Hypothetical example is not empirical.",
        "event_class": "CHAT_UTTERANCE",
        "actor_role": "UNKNOWN",
    }]
    manifest.write_text(json.dumps(case), encoding="utf-8")
    run_case(manifest, storage)
    case["discussion_events"][0]["actor_role"] = "AUTHOR"
    manifest.write_text(json.dumps(case), encoding="utf-8")
    with pytest.raises(ValueError, match="immutable discussion event identity changed"):
        run_case(manifest, storage)
