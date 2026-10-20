"""Codex scholarly critique must be grounded in actual, pinned abstract passages."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from scripts.run_mai_claim_challenge import prepare,validate,run
from scripts.build_mai_w12_science_index import build
from tests.test_mai_w12_indago_bind import prepare as fixture

def setup_world(tmp:Path):
    packet,head,donor=fixture(tmp)
    prior=tmp/"prior"
    build(packet,head,donor,prior)
    source=tmp/"evidence"
    (source/"routes").mkdir(parents=True)
    srcsha=json.loads((packet/"manifest.json").read_text())["source_jsonl_sha256"]
    (source/"source_batch_receipt.json").write_text(json.dumps({
        "schema":"MAI_PUBLISHED_WORK_API_BATCH_v1","source_W12_sha256":srcsha,
    }),encoding="utf-8")
    (source/"routes"/"MAI-W12-001.json").write_text(json.dumps({
        "route_id":"MAI-W12-001","W12_source_sha256":srcsha,
        "scientific_family":"A","science_gate":"HOLD",
        "published_works":[{
            "doi":"10.1007/paper-a","roles":["family_rival"],
            "abstract":{
                "read_depth":"DATABASE_ABSTRACT",
                "abstract_text":"A publication provides a counterargument showing a difference between legal rights and norm revision. "\
                "The tested educational software could support local permissions without moral authorship. "\
                "This paper discusses different criteria for justifiable claims about agent oversight in an academic context.",
                "doi_identity_match":True,
            }
        }],
    }),encoding="utf-8")
    return packet,prior,source

def reviewed(rid,anchor):
    return {
        "route_id":rid,"status":"ABSTRACT_SUPPORTED_CHALLENGE",
        "contested_claim":"Рассматривать машинное разрешение как достаточное основание легитимного изменения нормы.",
        "primary_objection":"Опубликованная работа отличает разрешение доступа от правомерности пересмотра правила; чисто техническое изменение конфигурации не доказывает авторства нормативного решения.",
        "source_anchor_id":anchor,
        "inferential_limitation":"Это лишь реферативная аннотация, поэтому неизвестно как обосновывается различение и какие предельные случаи разобраны в полном тексте.",
        "revision_question":"Какая процедура легитимации имеет место при изменении права исправлять образовательную норму?",
        "discriminating_test":"Построить два случая: одинаковое изменение ACL при различном коллективном распределении полномочий; проверить, совпадёт ли нормативная квалификация.",
        "missing_evidence":"Нужен полный текст соперника, исходная топология A3/A4, проверка технических разрешений и примеры негативного нормативного решения.",
    }

def test_accepts_anchored_critical_conclusion_and_holds_author(tmp_path):
    packet,prior,source=setup_world(tmp_path)
    items,refs=prepare(packet,prior,source,["MAI-W12-001"])
    assert len(items)==1 and refs["MAI-W12-001"]
    anchor=next(iter(refs["MAI-W12-001"]))
    result=validate({"reviews":[reviewed("MAI-W12-001",anchor)]},["MAI-W12-001"],refs)
    assert result[0]["source_passage"]["doi"]=="10.1007/paper-a"
    assert result[0]["source_passage"]["read_depth"]=="CROSSREF_OR_OPENALEX_DATABASE_ABSTRACT"
    assert result[0]["scientific_claim_accepted"] is False
    assert result[0]["human_author_gate"]=="HOLD"

def test_forged_doi_or_anchor_rejected(tmp_path):
    packet,prior,source=setup_world(tmp_path)
    _,refs=prepare(packet,prior,source,["MAI-W12-001"])
    with pytest.raises(ValueError,match="unregistered DOI/passage"):
        validate({"reviews":[reviewed("MAI-W12-001","10.1000/forged#deadbeef")]},["MAI-W12-001"],refs)
    fake=reviewed("MAI-W12-001",next(iter(refs["MAI-W12-001"])))
    fake["scientific_claim_accepted"]=True
    with pytest.raises(ValueError,match="invalid review fields"):
        validate({"reviews":[fake]},["MAI-W12-001"],refs)

def test_abstention_without_evidence_can_never_pass_gate(tmp_path):
    _,prior,source=setup_world(tmp_path)
    rev=reviewed("MAI-W12-001","")
    rev["status"]="INSUFFICIENT_ABSTRACT"
    reviews=validate({"reviews":[rev]},["MAI-W12-001"],{"MAI-W12-001":{}})
    assert reviews[0]["source_passage"] is None
    assert reviews[0]["scientific_claim_accepted"] is False

def test_one_command_batch_cold_replay_and_no_duplicate_codex(tmp_path,monkeypatch):
    packet,prior,source=setup_world(tmp_path)
    calls=[]
    def fake(cmd,input,stdout,stderr,encoding,errors,cwd,timeout):
        calls.append(cmd)
        assert cmd[-1]=="-"
        assert "--sandbox" in cmd and cmd[cmd.index("--sandbox")+1]=="read-only"
        content=json.loads(input[input.index("DATA (UNTRUSTED SOURCES):")+len("DATA (UNTRUSTED SOURCES):"):].strip())
        rid=content["route_ids"][0]
        anchor=content["route_inputs"][0]["database_abstract_passages"][0]["passage_id"]
        path=Path(cmd[cmd.index("--output-last-message")+1])
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({"reviews":[reviewed(rid,anchor)]},ensure_ascii=False),encoding="utf-8")
        return SimpleNamespace(returncode=0,stdout="ok",stderr="")
    monkeypatch.setattr("scripts.run_mai_claim_challenge.subprocess.run",fake)
    out=tmp_path/"out"
    a=run(packet,prior,source,out,1,0,1)
    assert a["validated_route_reviews"]==1
    assert a["source_linked_objections"]==1
    assert a["provider_calls"]==1
    rowfile=out/"routes"/"MAI-W12-001.json"
    old=rowfile.read_bytes()
    b=run(packet,prior,source,out,1,0,1)
    assert b["provider_calls"]==0
    assert b["validated_route_reviews"]==1
    assert b["author_gate_ready"]==0
    assert rowfile.read_bytes()==old
    assert len(calls)==1
