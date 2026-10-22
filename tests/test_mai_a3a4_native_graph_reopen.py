"""MAI A3/A4 source-bounded field return must reuse actual OpportunityGraphStore."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from scripts import run_mai_a_education_field_reopen as synth
from scripts import publish_mai_a3a4_native_graph_reopen as importer
from tests.test_mai_a3a4_native_field_reopen import built,proposed


def _case(tmp_path:Path,monkeypatch):
    packets,native,book,reads=built(tmp_path,monkeypatch)
    output=tmp_path/"reopen"
    def model(prompt,schema_file,output,**kwargs):
        data=json.loads(prompt.split("UNTRUSTED SOURCED RESEARCH MATERIAL:",1)[1].strip())
        result=proposed(data)
        synth.write(output/"model_output.json",result)
        (output/"model_stdout.log").write_text("fixture response\n",encoding="utf-8")
        return result
    monkeypatch.setattr(synth,"call_provider",model)
    result=synth.execute(packets,native,book,reads,output)
    assert result["proposal"]["decision_candidate"]=="REVISE_SOURCE_CANDIDATE"
    return packets,native,book,reads,output


def test_existing_graph_store_receives_two_events_and_three_source_pins(tmp_path,monkeypatch):
    packets,native,book,reads,return_root=_case(tmp_path,monkeypatch)
    graph_root=tmp_path/"graph"
    first=importer.import_held_return(packets,native,book,reads,return_root,graph_root)
    second=importer.import_held_return(packets,native,book,reads,return_root,graph_root)
    assert first==second
    assert first["case_publisher_original_work_count"]==3
    assert first["science_anchor_count"]==3
    assert first["outbound_submissions"]==0
    assert first["world_mutations"]==0
    assert first["human_gate"]=="AUTHOR_REVIEW_REQUIRED"
    store=OpportunityGraphStore(graph_root)
    assert len(store.list_records("Evidence"))==3
    assert store.list_records("World")==[]
    assert store.list_records("ArticleSeed")==[]
    assert store.list_records("ArticleOpportunity")==[]
    events=store.replay_events()
    assert len(events)==2
    assert {x["kind"] for x in events}=={"HUNT_RESULT","FIELD_REOPEN_PROPOSAL"}
    negative=next(x for x in events if x["kind"]=="HUNT_RESULT")
    assert len(negative["source_evidence_pins"])==3
    assert negative["author_decision"]=="HOLD"
    assert negative["world_mutation"]=="NONE"
    reopen=next(x for x in events if x["kind"]=="FIELD_REOPEN_PROPOSAL")
    assert reopen["semantic_mutation"]=="NONE"
    assert reopen["author_gate"]=="AUTHOR_REVIEW_REQUIRED"
    assert reopen["source_event_id"]==negative["event_id"]


def test_unlinked_source_quote_blocks_real_graph_import(tmp_path,monkeypatch):
    packets,native,book,reads,return_root=_case(tmp_path,monkeypatch)
    p=return_root/"model_output.json"
    changed=json.loads(p.read_text(encoding="utf-8"))
    changed["source_anchor_ids"][1]["quote_sha256"]="0"*64
    p.write_text(json.dumps(changed),encoding="utf-8")
    with pytest.raises(ValueError,match="invented cross-paper citation"):
        importer.import_held_return(packets,native,book,reads,return_root,tmp_path/"graph")
    assert not (tmp_path/"graph"/"kairon_provider").exists()


def test_world_mutation_authority_cannot_be_promoted(tmp_path,monkeypatch):
    packets,native,book,reads,return_root=_case(tmp_path,monkeypatch)
    p=return_root/"field_reopen_proposal.json"
    x=json.loads(p.read_text(encoding="utf-8"))
    x["world_mutations"]=1
    p.write_text(json.dumps(x),encoding="utf-8")
    with pytest.raises(ValueError,match="author gate drift"):
        importer.import_held_return(packets,native,book,reads,return_root,tmp_path/"graph")


def test_publisher_article_review_tamper_blocks_graph_import(tmp_path,monkeypatch):
    packets,native,book,reads,return_root=_case(tmp_path,monkeypatch)
    proof=next((reads/"papers").glob("*/accepted_challenge.json"))
    data=json.loads(proof.read_text(encoding="utf-8"))
    data["verified_review"]["paper_thesis"]="unverified substitute argument"
    proof.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError,match="source/model review provenance|quote provenance altered"):
        importer.import_held_return(packets,native,book,reads,return_root,tmp_path/"graph")
