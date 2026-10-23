"""Scientific-read index overlay is never a passed scholarly gate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from kairoskopion.kairon_provider.w12_packets import materialize
from kairoskopion.kairon_provider.mai_w12_runner import run
from tests.test_w12_packets import setup_source
from tests.test_mai_w12_runner import setup_packets


def make_index(tmp_path:Path, source:Path, route_ids=("MAI-W12-001","MAI-W12-002"))->Path:
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    root=tmp_path/"science"
    (root/"routes").mkdir(parents=True,exist_ok=True)
    cards=[]
    for rid in route_ids:
        family="A" if rid.endswith("001") else "B"
        card={
            "route_id":rid,"family":family,
            "source_jsonl_sha256":source_hash,
            "author_ready":False,
            "journal_send_authorized":False,
            "scholarly_execution_state":"HOLD_UNTIL_REAL_ARTIKL_INDAGO_OPERATION",
        }
        (root/"routes"/(rid+".json")).write_text(json.dumps(card),encoding="utf-8")
        cards.append({
            "route_id":rid,"opponents_indexed_from_prior_indago":2,
            "research_status":"HOLD_UNTIL_REAL_ARTIKL_INDAGO_OPERATION",
        })
    index={
        "schema":"MAI_W12_PRIOR_RESEARCH_INDEX_V1",
        "source_W12_sha256":source_hash,
        "real_research_operations_this_wave":0,
        "route_author_ready_count":0,
        "external_send_count":0,
        "review_cards":cards,
    }
    p=root/"science_index.json"
    p.write_text(json.dumps(index),encoding="utf-8")
    return p


def test_science_source_overlay_visible_without_qualifying_any_article(tmp_path):
    source,snapshot=setup_source(tmp_path)
    science=make_index(tmp_path,source)
    root=tmp_path/"board"
    result=materialize(source,snapshot,root,science_index_path=science)
    assert result["science_indexed_count"]==2
    assert result["ready_for_author_rework"]==0
    assert result["ready_for_human_send"]==0
    card=json.loads((root/"routes"/"MAI-W12-001.json").read_text(encoding="utf-8"))
    assert card["science_index"]["status"]=="PREEXISTING_FAMILY_OPPOSITION_INDEXED"
    assert card["science_index"]["opponents"]==2
    assert card["scientific_state"]=="SOURCE_DRAFT_ONLY"
    assert card["ready_for_human_send"] is False
    assert (root/"science"/"MAI-W12-001.json").exists()
    html=(root/"index.html").read_text(encoding="utf-8")
    assert "Индаго:" in html
    assert "Научные возражения" in html


def test_science_index_refuses_author_ready_and_unknown_route(tmp_path):
    source,snapshot=setup_source(tmp_path)
    sci=make_index(tmp_path,source)
    obj=json.loads(sci.read_text(encoding="utf-8"))
    obj["route_author_ready_count"]=1
    sci.write_text(json.dumps(obj),encoding="utf-8")
    with pytest.raises(ValueError,match="cannot promote"):
        materialize(source,snapshot,tmp_path/"bad",science_index_path=sci)
    sci=make_index(tmp_path,source)
    obj=json.loads(sci.read_text(encoding="utf-8"))
    obj["review_cards"][0]["route_id"]="MAI-W12-999"
    sci.write_text(json.dumps(obj),encoding="utf-8")
    with pytest.raises(ValueError,match="route IDs mismatch"):
        materialize(source,snapshot,tmp_path/"bad2",science_index_path=sci)


def test_route_science_reply_changes_do_not_rerun_local_diagnostics(tmp_path,monkeypatch):
    src=setup_packets(tmp_path)
    out=tmp_path/"runs"
    calls=[]
    def fake_run(cmd,**kw):
        calls.append(cmd)
        return SimpleNamespace(returncode=0,stdout="success",stderr="")
    monkeypatch.setattr("kairoskopion.kairon_provider.mai_w12_runner.subprocess.run",fake_run)
    a=run(src,out,limit=2)
    assert a["by_result"]=={"LOCAL_DIAGNOSTIC_COMPLETED":2}
    packet=src/"routes"/"MAI-W12-001.json"
    obj=json.loads(packet.read_text(encoding="utf-8"))
    obj["science_index"]={"status":"HOLD"}
    obj["editorial_status"]="DRAFT"
    obj["outreach_events"]=[{"event_id":"draft-1"}]
    packet.write_text(json.dumps(obj),encoding="utf-8")
    b=run(src,out,limit=2)
    assert b["by_result"]=={"CACHED":2}
    assert len(calls)==2
    obj["route"]["abstract_ru"]="A GENUINE CHANGED ARTICLE ABSTRACT"
    packet.write_text(json.dumps(obj),encoding="utf-8")
    c=run(src,out,limit=2)
    assert c["by_result"]=={"CACHED":1,"LOCAL_DIAGNOSTIC_COMPLETED":1}
    assert len(calls)==3
