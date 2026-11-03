"""Synthetic protocol tests for actual Kairoskopion ADD-006 native operator."""
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace
import pytest

from kairoskopion.kairon_provider import native_add006_factory as f
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked
SHA="a"*64
REQ="T3-test:research-request"
EVENT=REQ+":dispatch"
RUN="INDAGO:RUN:1234567890abcdef:synthetic"
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def valid_reply():
    return {
        "schema":"trimurti-artikl-f240-research-vs-revision-decision-v1",
        "agent_id":"artikl","organ_not_actor":True,
        "current_release":"ARTIKL 1.0.0-rc9",
        "whitecrow_report_sha256":SHA,
        "real_indago_evidence_sha256":"b"*64,
        "decision":"MORE_RESEARCH",
        "reason":"Scientific source depth not sufficient",
        "next_research_questions":["Read closest original precedent"],
        "revision_allowed_now":False,
        "d25_manuscript_go":False,"source_novelty_accepted":False,
        "author_gate":"HOLD","send":False,"world_mutation":False}
def test_native_artikl_decision_never_self_promotes():
    x=valid_reply()
    assert f._assert_science_choice(x,{}, "b"*64,SHA)=="MORE_RESEARCH"
    for k,value in (("decision","REVISION_CANDIDATE"),("send",True),
                    ("d25_manuscript_go",True),("revision_allowed_now",True),
                    ("world_mutation",True),("current_release","ARTIKL 1.0.0-rc8"),
                    ("real_indago_evidence_sha256",SHA)):
        j=valid_reply();j[k]=value
        with pytest.raises(EvidenceBlocked):
            f._assert_science_choice(j,{},"b"*64,SHA)
def test_external_source_sha_tamper(tmp_path):
    p=tmp_path/"evidence.json"
    p.write_text('{"demo":"synthetic"}',encoding="utf-8")
    assert f._pin(p,digest(p))==p.read_bytes()
    with pytest.raises(EvidenceBlocked,match="trusted source pin mismatch"):
        f._pin(p,"0"*64)

def test_one_new_dispatch_runs_native_once_then_cold_replay(tmp_path,monkeypatch):
    d=tmp_path/"input";d.mkdir()
    out=tmp_path/"output"
    state=tmp_path/"native-state"
    native=tmp_path/"native-port";native.mkdir()
    reqfile=d/"request.json";reqfile.write_text(json.dumps({
        "research_request_id":REQ,"dispatch_event_id":EVENT,
        "semantic_action_mode":"CRITIQUE"}),encoding="utf8")
    transport=d/"transport.txt";transport.write_text(
        "research_request_id: "+REQ+"\ndispatch_event_id: "+EVENT+"\n",
        encoding="utf8")
    stage=d/"stage.json";stage.write_text('{"dispatch":"synthetic"}',encoding="utf8")
    base=d/"baseline.json";base.write_text('{"coverage":"UNKNOWN"}',encoding="utf8")
    manifest=d/"manifest.json";manifest.write_text(json.dumps({
        "schema":f.SCHEMA,"case_id":"T3-TALK-20261019",
        "research_request_id":REQ,"dispatch_event_id":EVENT,
        "author_gate":"HOLD","send":False,"world_mutation":False}),encoding="utf8")
    key=hashlib.sha256(EVENT.encode("utf8")).hexdigest()[:32]
    claimdir=state/"add006_claims"/key
    ledger=state/"add006_claims/runtime_receipts.jsonl"
    calls=[]
    def executor(cmd,**kwargs):
        calls.append(cmd)
        assert cmd[:3]==[f.sys.executable,"-m","indago_port"]
        assert cmd[3:5]==["--state-root",str(state)]
        assert "--force" not in cmd and "--offline" not in cmd
        claimdir.mkdir(parents=True)
        ledger.parent.mkdir(parents=True,exist_ok=True)
        (claimdir/"claim.json").write_text(json.dumps({
            "state":"COMPLETED","research_request_id":REQ,
            "dispatch_event_id":EVENT,"research_run_id":RUN,
            "transport_sha256":digest(transport)}),encoding="utf8")
        (claimdir/"evidence_return.json").write_text(json.dumps({
            "schema":"indago.add006.evidence_return.v1",
            "research_request_id":REQ,"dispatch_event_id":EVENT,
            "research_run_id":RUN,"run_status":"PARTIAL",
            "claim_state":"COMPLETED","provider_calls":3,
            "author_gate":"HOLD","send":False,
            "hunt":{"hunt_id":"h-synthetic-new"}}),encoding="utf8")
        ledger.write_text("native synthetic\n",encoding="utf8")
        return SimpleNamespace(returncode=10,stdout=b'{"run_status":"PARTIAL"}',
                               stderr=b'')
    def wc_stub(**kwargs):
        rr=kwargs["output_root"]
        rr.mkdir(parents=True,exist_ok=True)
        report=rr/"whitecrow_d24_after_add006.json"
        report.write_text('{"research_readiness":"BLOCKED_ON_DUE_DILIGENCE"}',encoding="utf8")
        return {"status":"REQUALIFIED_RESEARCH_MORE_D15_HOLD",
                "whitecrow_report_sha256":digest(report),
                "independent_primary_read_verified":False}
    def artikl_stub(**kwargs):
        root=kwargs["root"]
        (root/"native_artikl_stdout.json").write_text('{"synthetic":"not real agent"}',encoding="utf8")
        return {"decision":"MORE_RESEARCH"},{
            "stdout_sha256":digest(root/"native_artikl_stdout.json"),
            "invocation_class":"SYNTHETIC_TEST"}
    monkeypatch.setattr(f.subprocess,"run",executor)
    monkeypatch.setattr(f,"whitecrow_return",wc_stub)
    monkeypatch.setattr(f,"_native_artikl",artikl_stub)
    kw=dict(input_manifest=manifest,request_path=reqfile,transport_path=transport,
        stage_receipt=stage,baseline_path=base,
        trusted_request_sha=digest(reqfile),trusted_transport_sha=digest(transport),
        trusted_stage_sha=digest(stage),trusted_baseline_sha=digest(base),
        port_root=native,indago_state_root=state,
        whitecrow_root=tmp_path/"wc",trusted_wc_commit="0"*40,
        trusted_wc_module_sha="0"*64,output_root=out)
    first=f.run(**kw)
    assert first["status"]=="MORE_RESEARCH_AUTHOR_HOLD"
    assert first["native_indago_executed_this_command"] is True
    assert first["artikl_research_decision"]=="MORE_RESEARCH"
    assert first["f4_full_manuscript_closed_loop"]=="NOT_PASSED"
    assert len(calls)==1
    again=f.run(**kw)
    assert again["replay_status"]=="IDENTICAL_STATE_ZERO_NEW_MODELS_OR_HUNTS"
    assert len(calls)==1
    # Side-effect free replay must detect scientific artifact tamper.
    rp=next(out.glob("*/whitecrow/whitecrow_d24_after_add006.json"))
    rp.write_text('{"mutated":true}',encoding="utf8")
    with pytest.raises(EvidenceBlocked,match="whitecrow_report_replay_tampered"):
        f.run(**kw)
