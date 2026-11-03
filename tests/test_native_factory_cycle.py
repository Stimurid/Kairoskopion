"""Synthetic F2/F3 native boundary tests, no provider or model operations."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked
from kairoskopion.kairon_provider import native_factory_cycle as n

H="a"*64
HUNT="h-20261103T093402Z-trimurti_m108_c04_20261103-e65d8a"

def artifacts(tmp_path):
    p=tmp_path/"private"
    p.mkdir()
    f={}
    for k in ("original","draft","review"):
        f[k]=p/(k+".json")
        text=json.dumps({"author_gate":"HOLD","material":"SYNTHETIC_ONLY","k":k},sort_keys=True)
        f[k].write_text(text,encoding="utf-8")
    z=p/"canon"/"SOURCE_ARTIKL"
    z.mkdir(parents=True)
    for name in n.REQUIRED_ARTIKL_DOCS:
        text=("canonical "+name+"\n")*120
        if name=="ENTRY_MANIFEST.md":
            text+="\nCURRENT_RELEASE = ARTIKL 1.0.0-rc9\n"
        if name=="RELEASE_MANIFEST.md":
            text+="\nCURRENT_RELEASE remains ARTIKL 1.0.0-rc9\n"
        (z/name).write_text(text,encoding="utf-8")
    m=p/"manifest.json"
    cfg={"schema":n.SCHEMA,"evidence_mode":"REAL","case_id":"T3-TALK-20261019",
         "route_id":"C-GUARMEAS-JIBE-CRESTI","task_id":"TRIMURTI_M108_C04_20261103",
         "mode":"REUSE_VERIFIED_NATIVE_HUNT","historical_hunt_id":HUNT,
         "artikl_release":"ARTIKL 1.0.0-rc9","author_gate":"HOLD",
         "submit":False,"article_seed_accepted":False}
    m.write_text(json.dumps(cfg),encoding="utf-8")
    trust={k:n.sha256(v.read_bytes()) for k,v in f.items()}
    args=dict(manifest_path=m,original=f["original"],draft=f["draft"],review=f["review"],
              port_root=p,humts_root=p,artikl_workspace=z.parent,output_root=p/"out",
              trusted_source_sha=trust["original"],trusted_draft_sha=trust["draft"],
              trusted_review_sha=trust["review"])
    args["hunts_root"]=args.pop("humts_root")
    return args,cfg

def test_artikl_source_local_full_docs_and_rc9(tmp_path):
    a,_=artifacts(tmp_path)
    manifest,docs=n.preflight_inputs(manifest=a["manifest_path"],original=a["original"],
        draft=a["draft"],review=a["review"],trusted_source_sha=a["trusted_source_sha"],
        trusted_draft_sha=a["trusted_draft_sha"],trusted_review_sha=a["trusted_review_sha"],
        artikl_source_root=a["artikl_workspace"]/"SOURCE_ARTIKL")
    assert manifest["mode"]=="REUSE_VERIFIED_NATIVE_HUNT"
    assert len(docs)==6
    assert all(len(v["sha256"])==64 for v in docs.values())

def test_no_model_or_approval_promotions(tmp_path):
    a,m=artifacts(tmp_path)
    m["submit"]=True
    a["manifest_path"].write_text(json.dumps(m),encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="author_boundary"):
        n.preflight_inputs(manifest=a["manifest_path"],original=a["original"],
          draft=a["draft"],review=a["review"],trusted_source_sha=a["trusted_source_sha"],
          trusted_draft_sha=a["trusted_draft_sha"],trusted_review_sha=a["trusted_review_sha"],
          artikl_source_root=a["artikl_workspace"]/"SOURCE_ARTIKL")

def test_pinned_source_tamper_rejected(tmp_path):
    a,_=artifacts(tmp_path)
    a["draft"].write_text("tampered",encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="trusted_draft_sha256_mismatch"):
        n.preflight_inputs(manifest=a["manifest_path"],original=a["original"],
          draft=a["draft"],review=a["review"],trusted_source_sha=a["trusted_source_sha"],
          trusted_draft_sha=a["trusted_draft_sha"],trusted_review_sha=a["trusted_review_sha"],
          artikl_source_root=a["artikl_workspace"]/"SOURCE_ARTIKL")

def test_invalid_reuse_or_hunt_identity_rejected(tmp_path):
    a,m=artifacts(tmp_path)
    m["historical_hunt_id"]="../../other"
    a["manifest_path"].write_text(json.dumps(m),encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="historical_hunt_id"):
        n.preflight_inputs(manifest=a["manifest_path"],original=a["original"],
          draft=a["draft"],review=a["review"],trusted_source_sha=a["trusted_source_sha"],
          trusted_draft_sha=a["trusted_draft_sha"],trusted_review_sha=a["trusted_review_sha"],
          artikl_source_root=a["artikl_workspace"]/"SOURCE_ARTIKL")

def test_artikl_stale_release_rejected(tmp_path):
    a,m=artifacts(tmp_path)
    m["artikl_release"]="ARTIKL 1.0.0-rc8"
    a["manifest_path"].write_text(json.dumps(m),encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="stale_artikl_release"):
        n.preflight_inputs(manifest=a["manifest_path"],original=a["original"],
          draft=a["draft"],review=a["review"],trusted_source_sha=a["trusted_source_sha"],
          trusted_draft_sha=a["trusted_draft_sha"],trusted_review_sha=a["trusted_review_sha"],
          artikl_source_root=a["artikl_workspace"]/"SOURCE_ARTIKL")

def test_model_bad_approvals_are_not_acceptable(tmp_path,monkeypatch):
    a,_=artifacts(tmp_path)
    def fake_plan(**k):return {"result":"ADMITTED_FOR_SEPARATE_NATIVE_HUNT"}
    def fake_import(**k):
        k["output_root"].mkdir(parents=True,exist_ok=True)
        (k["output_root"]/("indago-intake-"+HUNT+".json")).write_text("SYNTHETIC",encoding="utf-8")
        return {"native_hunt_id":HUNT,"native_status":"PARTIAL",
                "counts":{"provider_calls":8,"new_verified":0},
                "evidence_depth":"NATIVE_PROVIDER_RETURNS_NOT_INDEPENDENT_FULL_PRIMARY_READ"}
    def fake_artikl(**k):
        root=k["root"]
        (root/"artikl-native.stdout.json").write_text('{"fake":"host"}',encoding="utf-8")
        return ({"cold_reentry":"FULL_SIX_SOURCES_READ"},
                {"agent":"artikl","native_gateway":{"runId":"SYNTHETIC","toolSummary":{"calls":3}},
                 "stdout_sha256":"0"*64,"stderr_sha256":"0"*64})
    monkeypatch.setattr(n,"native_indago_plan",fake_plan)
    monkeypatch.setattr(n,"import_hunt",fake_import)
    monkeypatch.setattr(n,"_native_artikl",fake_artikl)
    first=n.run(**a)
    second=n.run(**a)
    assert first==second
    assert first["status"]=="SCIENTIFIC_RESEARCH_NEED_HOLD"
    assert first["f2"]=="SOURCE_DEPTH_HOLD"
    assert first["f4"]=="NOT_PASSED"
    assert not first["hunt_executed_in_this_cycle"] and not first["send"]
    state=json.loads(Path(first["state_path"]).read_text(encoding="utf-8"))
    assert state["whitecrow_native"]=="NOT_INVOKED"
    assert state["new_w12_routes"]==0

def test_artikl_reply_must_be_native_gateway_shape():
    with pytest.raises(EvidenceBlocked,match="native_artikl_gateway_failed"):
        n._parse_openclaw(b'{"status":"error","result":{}}')
    with pytest.raises(EvidenceBlocked,match="native_artikl_reply_not_json"):
        n._parse_openclaw(b'{"status":"ok","result":{"payloads":[{"text":"not json"}]}}')

def test_hunt_id_no_path_traversal():
    assert n._safe_hunt_name(HUNT)
    assert not n._safe_hunt_name("../etc/passwd")
    assert not n._safe_hunt_name("h-123")


def test_native_hunt_executes_real_port_contract_once_then_reuses(tmp_path):
    from types import SimpleNamespace
    calls=[]
    loc=tmp_path/"hunts"/HUNT
    loc.mkdir(parents=True)
    def executor(command,**kwargs):
        calls.append(command)
        assert command[:4]==[n.sys.executable,"-m","indago_port","hunt"]
        assert "--task" in command and command[command.index("--task")+1]=="TRIMURTI_M108_C04_20261103"
        assert "--force" not in command and "--offline" not in command
        return SimpleNamespace(returncode=10,
           stdout=json.dumps({"status":"PARTIAL","paths":{"dir":str(loc)}}),stderr="")
    root=tmp_path/"out"
    root.mkdir()
    name,receipt=n._native_hunt(port_root=tmp_path,task_id="TRIMURTI_M108_C04_20261103",
                                root=root,executor=executor,timeout=225)
    assert name==HUNT and receipt["native_status"]=="PARTIAL"
    assert receipt["hunt_executed_in_this_cycle"]
    name2,receipt2=n._native_hunt(port_root=tmp_path,task_id="TRIMURTI_M108_C04_20261103",
                                root=root,executor=executor,timeout=225)
    assert name2==name and receipt2==receipt and len(calls)==1

def test_unreceipted_native_hunt_is_never_silently_retried(tmp_path):
    from types import SimpleNamespace
    (tmp_path/"native-hunt.started").write_text("INVOKED_NATIVE_INDAGO_ONCE")
    with pytest.raises(EvidenceBlocked,match="native_hunt_orphan_requires_operator_triage"):
        n._native_hunt(port_root=tmp_path,task_id="TRIMURTI_M108_C04_20261103",
                        root=tmp_path,timeout=225)

def test_artikl_claiming_publish_privilege_is_blocked(tmp_path,monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(n.shutil,"which",lambda name:"openclaw.cmd")
    m={"task_id":"TRIMURTI_M108_C04_20261103","case_id":"T3-TALK-20261019",
       "route_id":"C-GUARMEAS-JIBE-CRESTI"}
    evidence={"native_hunt_id":HUNT,"native_status":"PARTIAL",
              "counts":{"provider_calls":8,"new_verified":0}}
    body={"schema":n.ARTIKL_CONTRACT,"task_id":m["task_id"],"agent_id":"artikl",
       "organ_not_actor":True,"current_release":"ARTIKL 1.0.0-rc9",
       "research_disposition":"EVIDENCE_DEPTH_HOLD",
       "d25_state":"MANUSCRIPT_GO_FORBIDDEN",
       "research_need":{"reason":"Missing primary sources","missing_evidence":["passage"]},
       "can_proceed_to_full_manuscript":True,"author_gate":"HOLD",
       "send":False,"world_mutation":False}
    outer={"status":"ok","result":{"payloads":[{"text":json.dumps(body)}],
           "meta":{"toolSummary":{"calls":1,"tools":["read"]}}}}
    def executor(*args,**kwargs):
        return SimpleNamespace(returncode=0,stdout=json.dumps(outer),stderr="")
    with pytest.raises(EvidenceBlocked,match="native_artikl_untrusted_d25_claim"):
        n._native_artikl(m=m,evidence=evidence,need={},root=tmp_path,
          artikl_workspace=tmp_path,source_sha=H,draft_sha=H,review_sha=H,
          executor=executor)


def test_historical_native_reuse_allowed_under_provider_block_only():
    x={"result":"BLOCKED_NATIVE_HUNT","native_plan_status":"BLOCKED",
       "native_authorities_live_verified":True,"native_task_eligible":True,
       "native_agent_isolated":True,"native_agent_block":None,
       "native_agent_violations":[]}
    assert n._native_plan_access(x,"REUSE_VERIFIED_NATIVE_HUNT")=="HISTORICAL_REPLAY_ONLY_CURRENT_HUNT_BLOCKED"
    with pytest.raises(EvidenceBlocked,match="not_admitted"):
        n._native_plan_access(x,"EXECUTE_BOUNDED_NATIVE_HUNT")
    x["native_agent_block"]="AGENT_NOT_ISOLATED"
    with pytest.raises(EvidenceBlocked,match="not_admitted"):
        n._native_plan_access(x,"REUSE_VERIFIED_NATIVE_HUNT")
    x["native_agent_block"]=None
    x["native_authorities_live_verified"]=False
    with pytest.raises(EvidenceBlocked,match="not_admitted"):
        n._native_plan_access(x,"REUSE_VERIFIED_NATIVE_HUNT")
