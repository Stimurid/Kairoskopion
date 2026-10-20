"""Evidence-aware MAI board never promotes publications or author gates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

from kairoskopion.kairon_provider.w12_packets import materialize
from tests.test_w12_packets import setup_source

def fixture(tmp:Path):
    source,snapshot=setup_source(tmp)
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    pub=tmp/"published"
    (pub/"routes").mkdir(parents=True)
    rid="MAI-W12-001"
    abstract=("Extended moral agency may distribute normative mediation across human-machine arrangements "
              "while the legitimate decision authority remains asymmetrically human.")
    phrase=abstract[:120]
    anchor="10.1007/s44163-026-02130-1#"+hashlib.sha256(phrase.encode()).hexdigest()[:12]
    record={
        "schema":"MAI_PRIOR_ART_AUTHENTICATED_API_EVIDENCE_v1",
        "route_id":rid,"W12_source_sha256":sha,"scientific_family":"A",
        "science_gate":"HOLD","human_author_gate":"CLOSED",
        "external_send_count":0,"publisher_fulltexts_read":0,
        "operation_status":"ABSTRACTS_ACQUIRED_NEEDS_SCHOLARLY_INTERPRETATION",
        "published_work_count":1,"database_abstract_count":1,
        "published_works":[{
            "doi":"10.1007/s44163-026-02130-1",
            "abstract":{"read_depth":"DATABASE_ABSTRACT",
                        "abstract_text":abstract,"doi_identity_match":True}
        }],
    }
    (pub/"routes"/(rid+".json")).write_text(json.dumps(record),encoding="utf-8")
    model=tmp/"model"
    (model/"routes").mkdir(parents=True)
    saved={
        "schema":"MAI_W12_SOURCE_LINKED_PROVISIONAL_SCHOLARLY_CHALLENGE_v1",
        "route_id":rid,"human_gate":"HOLD","journal_send_count":0,
        "published_fulltext_read":False,
        "scientific_stage":"PROVISIONAL_MODEL_ABSTRACT_CHALLENGE",
        "review":{
            "route_id":rid,"status":"ABSTRACT_SUPPORTED_CHALLENGE",
            "scientific_claim_accepted":False,
            "source_anchor_id":anchor,
            "source_passage":{
                "doi":"10.1007/s44163-026-02130-1","passage_id":anchor,
                "text":phrase,
            },
            "primary_objection":"Status of normative authority is ambiguous",
        }
    }
    (model/"routes"/(rid+".json")).write_text(json.dumps(saved),encoding="utf-8")
    return source,snapshot,pub,model,rid

def test_real_source_and_model_critique_visible_but_author_not_ready(tmp_path):
    source,snap,pub,model,rid=fixture(tmp_path)
    out=tmp_path/"out"
    data=materialize(source,snap,out,publisher_root=pub,model_root=model)
    assert data["published_source_indexed_count"]==1
    assert data["provisional_model_critique_count"]==1
    assert data["ready_for_human_send"]==0
    assert data["ready_for_author_rework"]==0
    card=json.loads((out/"routes"/(rid+".json")).read_text(encoding="utf-8"))
    assert card["published_source_evidence"]["abstracts"]==1
    assert card["model_scientific_critique"]["status"]=="ABSTRACT_LINKED_PROVISIONAL_CRITIQUE"
    assert card["ready_for_human_send"] is False
    assert (out/"reviews"/(rid+".json")).is_file()
    assert (out/"published"/(rid+".json")).is_file()
    assert "Критика Codex" in (out/"index.html").read_text(encoding="utf-8")

def test_model_source_quote_drift_rejected(tmp_path):
    source,snap,pub,model,rid=fixture(tmp_path)
    p=model/"routes"/(rid+".json")
    v=json.loads(p.read_text())
    v["review"]["source_passage"]["text"]="An entirely invented assertion nowhere in a published abstract"
    p.write_text(json.dumps(v),encoding="utf-8")
    with pytest.raises(ValueError,match="unverified abstract anchor"):
        materialize(source,snap,tmp_path/"invalid",publisher_root=pub,model_root=model)

def test_model_without_published_source_rejected(tmp_path):
    source,snap,pub,model,rid=fixture(tmp_path)
    with pytest.raises(ValueError,match="independently held published source"):
        materialize(source,snap,tmp_path/"invalid",publisher_root=None,model_root=model)

def test_source_gate_or_send_bypass_rejected(tmp_path):
    source,snap,pub,model,rid=fixture(tmp_path)
    p=pub/"routes"/(rid+".json")
    v=json.loads(p.read_text())
    v["external_send_count"]=1
    p.write_text(json.dumps(v),encoding="utf-8")
    with pytest.raises(ValueError,match="cannot promote"):
        materialize(source,snap,tmp_path/"invalid",publisher_root=pub,model_root=model)
