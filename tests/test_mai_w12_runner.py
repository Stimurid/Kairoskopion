"""The existing Kairoskopion run-local is called in bulk, without sending."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from kairoskopion.kairon_provider.mai_w12_runner import run, prepare_input


def setup_packets(tmp_path: Path) -> Path:
    root=tmp_path/"packets"
    d=root/"routes";d.mkdir(parents=True)
    for i in (1,2):
        obj={
            "schema":"MAI_W12_BATCH_RESEARCH_PACKET_v1",
            "source_jsonl_sha256":"a"*64,
            "route":{
                "route_id":f"MAI-W12-{i:03d}","title_ru":f"Тема {i}",
                "abstract_ru":f"Аннотация {i}","journal":f"Venue {i}",
                "route_raw":"PRECHECK", "deadline_raw":"2026-11-02",
                "official_url":"https://example.test/cfp",
                "original_spreadsheet_id":"sheet","source_cell_range":f"A{i}:M{i}",
            },
        }
        (d/f"MAI-W12-{i:03d}.json").write_text(json.dumps(obj,ensure_ascii=False),encoding="utf-8")
    return root


def test_scenarios_explicitly_mark_source_and_policy_unverified(tmp_path):
    p={"route":{
        "title_ru":"Тест","abstract_ru":"Авторская аннотация",
        "journal":"Test Journal","route_raw":"maybe",
        "original_spreadsheet_id":"sheet","source_cell_range":"A2:M2",
        "deadline_raw":"","official_url":"https://example.test","literature_url":"https://example.test/1",
    }}
    res=prepare_input(p,tmp_path)
    manuscript=Path(res["article_path"]).read_text(encoding="utf-8")
    guide=Path(res["venue_path"]).read_text(encoding="utf-8")
    scenario=json.loads(Path(res["scenario_path"]).read_text(encoding="utf-8"))
    assert "NOT A COMPLETE MANUSCRIPT" in manuscript
    assert "UNVERIFIED" in guide
    assert scenario["rewrite_depth"]=="none"
    assert scenario["field_core_preservation"]=="strict"


def test_batch_calls_existing_cli_and_replays_without_calls(tmp_path,monkeypatch):
    source=setup_packets(tmp_path)
    calls=[]
    def fake_run(command,**kwargs):
        calls.append(command)
        assert "run-local" in command
        assert command[command.index("run-local")+1]=="--manuscript"
        assert "submission" not in command
        return SimpleNamespace(returncode=0,stdout="run completed",stderr="")
    monkeypatch.setattr("kairoskopion.kairon_provider.mai_w12_runner.subprocess.run",fake_run)
    result=run(source,tmp_path/"out",limit=2)
    assert result["by_result"]=={"LOCAL_DIAGNOSTIC_COMPLETED":2}
    assert len(calls)==2
    again=run(source,tmp_path/"out",limit=2)
    assert again["by_result"]=={"CACHED":2}
    assert len(calls)==2
    receipts=list((tmp_path/"out").glob("MAI-W12-*/receipt.json"))
    assert len(receipts)==2
    for p in receipts:
        x=json.loads(p.read_text(encoding="utf-8"))
        assert x["author_gate"]=="CLOSED"
        assert x["outbound_send_count"]==0
        assert x["scientific_qa_status"]=="NOT_YET_VERIFIED"


def test_failed_route_is_preserved_and_no_green(tmp_path,monkeypatch):
    source=setup_packets(tmp_path)
    def error(*args,**kwargs):
        return SimpleNamespace(returncode=2,stdout="",stderr="policy unavailable")
    monkeypatch.setattr("kairoskopion.kairon_provider.mai_w12_runner.subprocess.run",error)
    result=run(source,tmp_path/"out",limit=1)
    assert result["by_result"]=={"LOCAL_DIAGNOSTIC_FAILED":1}
    rr=json.loads((tmp_path/"out"/"MAI-W12-001"/"receipt.json").read_text(encoding="utf-8"))
    assert rr["status"]=="LOCAL_DIAGNOSTIC_FAILED"
    assert rr["exit_code"]==2
    assert rr["author_gate"]=="CLOSED"
