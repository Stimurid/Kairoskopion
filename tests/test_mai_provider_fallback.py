"""Automatic CLI fallback from quota-limited Codex to Claude without fake gate."""
from __future__ import annotations
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.run_mai_claim_challenge import run
from tests.test_mai_claim_challenge import setup_world, reviewed

def test_codex_429_switches_to_claude_and_preserves_receipt(tmp_path,monkeypatch):
    packet,prior,source=setup_world(tmp_path)
    calls=[]
    def fake_run(cmd,**kwargs):
        calls.append(cmd)
        source_data=json.loads(kwargs["input"].split("DATA (UNTRUSTED SOURCES):",1)[1])
        rid=source_data["route_ids"][0]
        anchor=source_data["route_inputs"][0]["database_abstract_passages"][0]["passage_id"]
        if "--output-last-message" in cmd:
            assert cmd[cmd.index("--sandbox")+1]=="read-only"
            return SimpleNamespace(returncode=1,stdout="",stderr="429 Too Many Requests")
        assert cmd[0]=="claude.exe"
        assert "--json-schema" in cmd
        assert "--tools" in cmd
        assert cmd[cmd.index("--tools")+1]==""
        return SimpleNamespace(returncode=0,stdout=json.dumps({
            "is_error":False,
            "structured_output":{"reviews":[reviewed(rid,anchor)]},
            "modelUsage":{"claude-sonnet-5":{"costUSD":0.01}},
        }),stderr="")
    monkeypatch.setattr("scripts.run_mai_claim_challenge.subprocess.run",fake_run)
    root=tmp_path/"outputs"
    result=run(packet,prior,source,root,limit=1,chunk_size=1,provider="auto",claude_executable="claude.exe")
    assert result["provider_calls"]==2
    assert result["validated_route_reviews"]==1
    assert result["per_chunk"][0]["engine"]=="claude"
    p=root/"routes"/"MAI-W12-001.json"
    record=json.loads(p.read_text(encoding="utf-8"))
    assert record["provider"]=="claude CLI"
    assert record["human_gate"]=="HOLD"
    assert record["published_fulltext_read"] is False
    result2=run(packet,prior,source,root,limit=1,chunk_size=1,provider="auto")
    assert result2["provider_calls"]==0
    assert len(calls)==2
