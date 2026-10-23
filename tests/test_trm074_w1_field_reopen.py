"""Scientific W1 second-hand return stays an immutable, author-gated proposal."""
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
from kairoskopion.services.talk_corpus_reopen import propose_w1_return
from tests.test_trm074_talk_corpus_intake import fixture_case


RETURN_QUOTES = {
    "HEAD-01": "RETURN-A: The existing skill allocation literature complicates novelty.",
    "HEAD-02": "RETURN-B: Organizational learning already supplies related mechanisms.",
    "HEAD-03": "RETURN-C: Startup discovery is not independent industrial reproduction.",
}


def case_with_w1(tmp_path: Path) -> tuple[Path, Path, dict]:
    manifest, storage, case = fixture_case(tmp_path)
    w1 = tmp_path / "sources" / "W1_manual_read.txt"
    w1.write_text(
        "INDAGO MANUAL W1 NOTEBOOK\n\n"
        + "\n\n".join(RETURN_QUOTES.values())
        + "\n\nFULL ORIGINAL 2025 COURSE WAS NOT ACQUIRED.",
        encoding="utf-8",
    )
    case["world"] = "https://docs.google.com/document/d/WORLD_SOURCE/edit"
    case["sources"].append({
        "family": "CROSS",
        "key": "TRM073_W1_MANUAL",
        "source_id": "drive:W1_NOTEBOOK",
        "source_url": "https://docs.google.com/document/d/W1_NOTEBOOK/edit",
        "local_path": str(w1),
        "kind": "RESEARCH_SYNTHESIS",
        "version": "W1",
        "author_state": "RESEARCH_RETURN_NOT_AUTHOR_APPROVAL",
        "read_coverage": "RESEARCH_SYNTHESIS_TEXT_ONLY",
    })
    case["discussion_events"] = [
        {
            "source_key": "TRM073_W1_MANUAL",
            "quote": quote,
            "event_class": "RESEARCH_RETURN",
            "actor_role": "INDAGO_W1_MANUAL",
            "subject_ref": subject,
        }
        for subject, quote in RETURN_QUOTES.items()
    ]
    case["missing_carriers"].append({
        "family": "CROSS",
        "kind": "2025_COAUTHORED_FULL_TEXT",
        "status": "NOT_ACQUIRED_FULL_READ_BLOCKED",
    })
    manifest.write_text(json.dumps(case), encoding="utf-8")
    return manifest, storage, case


def _ready(tmp_path: Path) -> tuple[Path, Path, dict]:
    manifest, storage, case = case_with_w1(tmp_path)
    run_case(manifest, storage)
    export_talk_research_evidence(storage, "T3-SYNTHETIC")
    return manifest, storage, case


def test_w1_reopen_goes_through_existing_kairon_store_without_mutations(tmp_path):
    _, storage, _ = _ready(tmp_path)
    rec = propose_w1_return(storage, "T3-SYNTHETIC")
    assert rec["count"] == 3
    graph = OpportunityGraphStore(storage)
    assert graph.list_records("ArticleSeed") == []
    assert graph.list_records("World") == []
    assert graph.list_records("ArticleOpportunity") == []
    events = graph.replay_events()
    assert len(events) == 6
    negative = [e for e in events if e["kind"] == "HUNT_RESULT"]
    reopen = [e for e in events if e["kind"] == "FIELD_REOPEN_PROPOSAL"]
    assert {e["subject_id"] for e in negative} == set(RETURN_QUOTES)
    assert len(reopen) == 3
    for e in negative:
        assert e["source_ref"] == "drive:W1_NOTEBOOK"
        assert e["source_kind"] == "MANUAL_W1_RESEARCH_NOTEBOOK"
        assert e["read_depth"] == "SECTIONS"
        assert e["world_mutation"] == "NONE"
        assert e["author_decision"] == "HOLD"
        assert e["external_send"] == "DISABLED"
        assert e["source_evidence_pin"]["revision"]
        assert RETURN_QUOTES[e["subject_id"]] == e["intellectual_consequence"]
    assert all(e["author_gate"] == "AUTHOR_REVIEW_REQUIRED" and
               e["semantic_mutation"] == "NONE" and
               e["reopen_level"] == "L0" for e in reopen)


def test_w1_replay_and_independent_subprocess_stay_byte_stable(tmp_path):
    _, storage, _ = _ready(tmp_path)
    first = propose_w1_return(storage, "T3-SYNTHETIC")
    second = propose_w1_return(storage, "T3-SYNTHETIC")
    assert first["sha256"] == second["sha256"]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_trm074_w1_reopen.py"
    p = subprocess.run([
        sys.executable, str(script), "--case-id", "T3-SYNTHETIC",
        "--storage-root", str(storage)
    ], capture_output=True, text=True, check=True, env=env)
    assert json.loads(p.stdout)["sha256"] == first["sha256"]
    assert len(OpportunityGraphStore(storage).replay_events()) == 6


def test_missing_2025_read_depth_warning_blocks_scientific_reopen(tmp_path):
    manifest, storage, case = case_with_w1(tmp_path)
    case["missing_carriers"] = []
    manifest.write_text(json.dumps(case), encoding="utf-8")
    run_case(manifest, storage)
    export_talk_research_evidence(storage, "T3-SYNTHETIC")
    with pytest.raises(ValueError, match="2025 course fulltext limitation"):
        propose_w1_return(storage, "T3-SYNTHETIC")


def test_second_hand_return_requires_anchored_evidence(tmp_path):
    _, storage, _ = _ready(tmp_path)
    handoff = storage / "talk_corpora" / "T3-SYNTHETIC" / "research_stage_handoff.json"
    body = json.loads(handoff.read_text(encoding="utf-8"))
    body["evidence_refs"] = [
        x for x in body["evidence_refs"] if x["source_ref"] != "drive:W1_NOTEBOOK"
    ]
    handoff.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(ValueError, match="graph Evidence pin"):
        propose_w1_return(storage, "T3-SYNTHETIC")


def test_wrong_head_binding_is_rejected(tmp_path):
    manifest, storage, case = case_with_w1(tmp_path)
    case["discussion_events"][0]["subject_ref"] = "HEAD-02"
    manifest.write_text(json.dumps(case), encoding="utf-8")
    run_case(manifest, storage)
    export_talk_research_evidence(storage, "T3-SYNTHETIC")
    with pytest.raises(ValueError, match="subject mismatch"):
        propose_w1_return(storage, "T3-SYNTHETIC")


def test_no_world_reference_blocks_reopen(tmp_path):
    manifest, storage, case = case_with_w1(tmp_path)
    case.pop("world")
    manifest.write_text(json.dumps(case), encoding="utf-8")
    run_case(manifest, storage)
    export_talk_research_evidence(storage, "T3-SYNTHETIC")
    with pytest.raises(ValueError, match="WORLD pointer missing"):
        propose_w1_return(storage, "T3-SYNTHETIC")



def test_other_source_evidence_cannot_impersonate_w1_notebook(tmp_path):
    _, storage, _ = _ready(tmp_path)
    handoff_file = storage / "talk_corpora" / "T3-SYNTHETIC" / "research_stage_handoff.json"
    handoff = json.loads(handoff_file.read_text(encoding="utf-8"))
    own = next(x for x in handoff["evidence_refs"]
               if x["source_ref"] == "drive:W1_NOTEBOOK")
    other = next(x for x in handoff["evidence_refs"]
                 if x["source_ref"] != "drive:W1_NOTEBOOK")
    own["id"], own["revision"] = other["id"], other["revision"]
    handoff_file.write_text(json.dumps(handoff), encoding="utf-8")
    with pytest.raises(ValueError, match="Evidence provenance does not match"):
        propose_w1_return(storage, "T3-SYNTHETIC")


def test_modified_w1_quote_anchor_cannot_be_reused_as_evidence(tmp_path):
    _, storage, _ = _ready(tmp_path)
    graph = OpportunityGraphStore(storage)
    evidence = next(x for x in graph.list_records("Evidence")
                    if x["source_ref"] == "drive:W1_NOTEBOOK")
    target = next(
        path for path in graph.records.glob("*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("id") == evidence["id"]
    )
    record = json.loads(target.read_text(encoding="utf-8"))
    first = next(x for x in record["passage_anchors"]
                 if x.get("anchor_kind") == "RESEARCH_RETURN_QUOTE_NOT_PRIMARY_EVIDENCE")
    first["quote_sha256"] = "0" * 64
    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="not anchored in pinned Evidence"):
        propose_w1_return(storage, "T3-SYNTHETIC")
