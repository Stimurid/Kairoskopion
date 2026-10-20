"""Batch review join requires operation provenance + exact published passage."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts.merge_mai_scholarly_reviews import run as merge
from scripts.run_mai_claim_challenge import run as challenge
from tests.test_mai_claim_challenge import setup_world, reviewed

def setup(tmp_path:Path,monkeypatch):
    packets,prior,published=setup_world(tmp_path)
    def fake(command,**kwargs):
        body=json.loads(kwargs["input"].split("DATA (UNTRUSTED SOURCES):",1)[1].strip())
        rid=body["route_ids"][0]
        anchor=body["route_inputs"][0]["database_abstract_passages"][0]["passage_id"]
        dest=Path(command[command.index("--output-last-message")+1])
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps({"reviews":[reviewed(rid,anchor)]},ensure_ascii=False),encoding="utf-8")
        return SimpleNamespace(returncode=0,stdout="",stderr="")
    monkeypatch.setattr("scripts.run_mai_claim_challenge.subprocess.run",fake)
    folder=tmp_path/"batch1"
    assert challenge(packets,prior,published,folder,limit=1,chunk_size=1)["validated_route_reviews"]==1
    return packets,published,folder

def test_merges_real_cited_provisionally_held_review(tmp_path,monkeypatch):
    pkt,pub,folder=setup(tmp_path,monkeypatch)
    dest=tmp_path/"merged"
    result=merge(pkt,pub,[folder],dest)
    assert result["model_reviews_validated"]==1
    assert result["route_total"]==1
    assert result["objections_with_abstract_passage"]==1
    assert not result["missing_routes"]
    assert result["human_author_gate_ready"]==0
    assert result["publisher_fulltext_read_here"]==0
    assert result["journal_send_actions"]==0
    first=(dest/"merged_challenge_receipt.json").read_bytes()
    assert (dest/"routes"/"MAI-W12-001.json").is_file()
    merge(pkt,pub,[folder],dest)
    assert (dest/"merged_challenge_receipt.json").read_bytes()==first

def test_rejects_tampered_passage_not_in_real_abstract(tmp_path,monkeypatch):
    pkt,pub,folder=setup(tmp_path,monkeypatch)
    target=folder/"routes"/"MAI-W12-001.json"
    raw=json.loads(target.read_text(encoding="utf-8"))
    raw["review"]["source_passage"]["text"]="Fabricated competitor published abstract"
    target.write_text(json.dumps(raw),encoding="utf-8")
    with pytest.raises(ValueError,match="invalid source passage anchor|review differs"):
        merge(pkt,pub,[folder],tmp_path/"bad")

def test_rejects_unknown_or_duplicate_route(tmp_path,monkeypatch):
    pkt,pub,folder=setup(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match="duplicate route"):
        merge(pkt,pub,[folder,folder],tmp_path/"double")
