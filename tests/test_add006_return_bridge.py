"""Exact WhiteCrow ADD006 research-return bridge acceptance, no live hunt in tests."""
import copy
import hashlib
import json
from pathlib import Path
import pytest

from kairoskopion.kairon_provider.add006_return_bridge import bridge,_admit
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked

H="a"*64
REQ="T3-F236-807df2a6d8f0-4867fa881a36:research-request"
EVENT=REQ+":dispatch"
RUN="INDAGO:RUN:d427e0184c3c5639:staging-dry1"
def sha(b):return hashlib.sha256(b).hexdigest()
def ev():
    return {"schema":"indago.add006.evidence_return.v1","research_request_id":REQ,
     "dispatch_event_id":EVENT,"research_run_id":RUN,"semantic_action_mode":"CRITIQUE",
     "transport_sha256":H,"execution_mode":"ONE_SHOT_RESEARCH_REQUEST",
     "writeback_destination":"INDAGO_HUNT_LEDGER_AND_HUNT_HISTORY",
     "claim_state":"COMPLETED","run_status":"PARTIAL","provider_calls":4,
     "hunt":{"hunt_id":"h-20261103T130000Z-legal-research-test-abcdef123"},
     "read_depth":"METADATA_OR_LOCATOR","author_gate":"HOLD","send":False,
     "world_mutation":False,"article_seed":False}

def req():return {"research_request_id":REQ,"dispatch_event_id":EVENT,"semantic_action_mode":"CRITIQUE"}
def test_weak_results_not_a_complete_scholarly_return():
    with pytest.raises(EvidenceBlocked,match="no_real_hunt_witness"):
        x=ev();x["hunt"]=None;_admit(x,req(),H)
    with pytest.raises(EvidenceBlocked,match="add006_old_hunt_splice_forbidden"):
        x=ev();x["hunt"]["hunt_id"]="h-20261003-m108-old";_admit(x,req(),H)
    with pytest.raises(EvidenceBlocked,match="add006_semantic_escalation_forbidden"):
        x=ev();x["semantic_action_mode"]="REASONING";_admit(x,req(),H)
    with pytest.raises(EvidenceBlocked,match="add006_transport_sha_conflict"):
        _admit(ev(),req(),"b"*64)
    with pytest.raises(EvidenceBlocked,match="add006_request_id_conflict"):
        x=ev();x["research_request_id"]="forged";_admit(x,req(),H)
def test_genuine_blocked_hunt_not_science():
    x=ev();x["claim_state"]="BLOCKED";x["run_status"]="LIVE_HUNT_BLOCKED";x["provider_calls"]=0;x["hunt"]=None
    _admit(x,req(),H)
    x["provider_calls"]=1
    with pytest.raises(EvidenceBlocked,match="interrupted_nonzero_provider"):
        _admit(x,req(),H)
def test_author_and_world_protected():
    for k,val in (("author_gate","GO"),("send",True),("world_mutation",True),("article_seed",True)):
        x=ev();x[k]=val
        with pytest.raises(EvidenceBlocked):_admit(x,req(),H)
def test_original_request_to_whitecrow_real_code(tmp_path):
    root=Path(r"C:/projects/trimurti/_ops/T3-TALK-20261019/F238_WHITECROW_ANCHORED_D24")
    wc=Path(r"C:/projects/whitecrow-antonova-direct-20261019")
    expected_commit="0bd96d098a65c2f6063d682e4f9e3e97c8034227"
    modsha="265216755b06926414ff09ad38f1c79de531345a5d93b397cd7468141a0401af"
    stage=root/"whitecrow_stage_receipt.json"
    request=root/"research_request_pending.json"
    trans=Path(r"C:/Users/Homee/.openclaw/hestia-body/INDAGO_STATE/add006_ops/F237_indago_one_shot_task_PENDING.txt")
    baseline=root/"due_diligence_report.json"
    sha_transport="b0e4b15dcc7a03addf9e652a44c9ef374c64f837848f44dec1ab7c9ada6b4e29"
    assert sha(trans.read_bytes())==sha_transport
    actual=_ev=ev()
    actual["transport_sha256"]=sha_transport
    path=tmp_path/"evidence.json";path.write_text(json.dumps(actual),encoding="utf-8")
    claim_file=tmp_path/"claim.json"
    claim_file.write_text(json.dumps({"state":"COMPLETED",
        "research_request_id":REQ,"dispatch_event_id":EVENT,
        "research_run_id":RUN,"transport_sha256":sha_transport,
        "native_hunt_id":actual["hunt"]["hunt_id"]}),encoding="utf-8")
    ledger_file=tmp_path/"ledger.jsonl"
    ledger_file.write_text("[INDAGO_RUNTIME] "+json.dumps({
        "kind":"direct_hunt_completed","research_request_id":REQ,
        "dispatch_event_id":EVENT,"research_run_id":RUN,
        "native_hunt_id":actual["hunt"]["hunt_id"]})+"\n",encoding="utf-8")
    kw=dict(evidence_path=path,request_path=request,transport_path=trans,
        whitecrow_root=wc,trusted_whitecrow_commit=expected_commit,
        trusted_whitecrow_module_sha=modsha,expected_evidence_sha=sha(path.read_bytes()),
        expected_request_sha=sha(request.read_bytes()),
        expected_transport_sha=sha_transport,baseline_path=baseline,
        stage_receipt_path=stage,expected_stage_receipt_sha=sha(stage.read_bytes()),
        native_claim_path=claim_file,expected_native_claim_sha=sha(claim_file.read_bytes()),
        native_ledger_path=ledger_file,expected_native_ledger_sha=sha(ledger_file.read_bytes()),
        output_root=tmp_path/"out")
    first=bridge(**kw)
    assert first["status"]=="REQUALIFIED_RESEARCH_MORE_D15_HOLD"
    assert first["whitecrow_admission"]=="REAL_FIELDCORE_D24"
    assert first["independent_primary_read_verified"] is False
    again=bridge(**kw)
    assert first==again
    report=json.loads((tmp_path/"out/whitecrow_d24_after_add006.json").read_text(encoding="utf-8"))
    assert report["research_readiness"]=="BLOCKED_ON_DUE_DILIGENCE"
    assert report["coverage_status"]!="HIGH"
    modified=dict(kw)
    modified["expected_evidence_sha"]="0"*64
    with pytest.raises(EvidenceBlocked,match="source_hash_mismatch"):bridge(**modified)
    blocked=dict(actual);blocked["claim_state"]="BLOCKED";blocked["run_status"]="LIVE_HUNT_BLOCKED";blocked["provider_calls"]=0;blocked["hunt"]=None
    blocked_dir=tmp_path/"blocked-case";blocked_dir.mkdir()
    bp=blocked_dir/"evidence_return.json";bp.write_text(json.dumps(blocked),encoding="utf-8")
    bc=blocked_dir/"claim.json"
    bc.write_text(json.dumps({"state":"BLOCKED","research_request_id":REQ,
        "dispatch_event_id":EVENT,"research_run_id":RUN,
        "transport_sha256":sha_transport}),encoding="utf-8")
    bl=blocked_dir/"ledger.jsonl"
    bl.write_text("[INDAGO_RUNTIME] "+json.dumps({"kind":"direct_hunt_failed",
        "dispatch_event_id":EVENT,"research_run_id":RUN,"status":"LIVE_HUNT_BLOCKED"})+"\n",encoding="utf-8")
    blocked_kw=dict(kw,evidence_path=bp,expected_evidence_sha=sha(bp.read_bytes()),
        native_claim_path=bc,expected_native_claim_sha=sha(bc.read_bytes()),
        native_ledger_path=bl,expected_native_ledger_sha=sha(bl.read_bytes()),
        output_root=tmp_path/"blocked-out")
    hold=bridge(**blocked_kw)
    assert hold["status"]=="NATIVE_HUNT_BLOCKED_NOT_A_SCIENCE_RETURN"
    assert hold["whitecrow_admission"]=="NOT_ADMITTED_HUNT_BLOCKED"
    assert not (tmp_path/"blocked-out/whitecrow_d24_after_add006.json").exists()

def test_f241_two_complete_original_pdfs_are_byte_and_page_bound_but_not_novelty():
    from kairoskopion.kairon_provider.add006_return_bridge import _verify_bounded_source_carriers
    p=Path(r"C:/projects/trimurti/_ops/T3-TALK-20261019/F241_ONE_BOUNDED_CYCLE/source_carrier_packet.json")
    if not p.exists():
        pytest.skip("owner-private F241 original fulltext acquisition not present here")
    correct=sha(p.read_bytes())
    assert correct=="9528844ac82456dc1945ea271c38fd5d35cb58b371be59a8ce1b786cd2f88e04"
    r=_verify_bounded_source_carriers(
        p,correct,"dcd4da42833caf48d74e553f3493326294120d96b93c1ce7a3b163989ee0bb19")
    assert r["full_primary_bytes_extracted_count"]==2
    assert r["independent_source_semantic_read_accepted"] is False
    assert {x["doi"] for x in r["source_originals_verified"]}=={
        "10.1111/jems.12492","10.3386/w23180"}
    assert all(x["verified_page_anchors_count"]==8 for x in r["source_originals_verified"])
    with pytest.raises(EvidenceBlocked,match="source_carrier_packet_unpinned_or_mutated"):
        _verify_bounded_source_carriers(p,"0"*64,None)


def test_native_recovery_completion_requires_real_typed_receipt_and_sha_lineage():
    from kairoskopion.kairon_provider.add006_return_bridge import _native_completion_attested
    x=ev()
    source_hashes={"wave1_evidence":"e"*64,"wave1_scene":"f"*64}
    x.update({
        "research_depth_profile":"NATIVE_INDAGO_PERPETUUM_RECOVERY",
        "recovered_locator_provider_calls":6,"new_provider_calls":2,
        "duplicate_provider_calls":0,"provider_calls":8,
        "recovery_source_hashes":source_hashes,
        "perpetuum_segments":[
            {"segment":1,"status":"INCOMPLETE_RECOVERED","provider_calls":6,
             "hunt_id":"h-stopped-before-model-answer"},
            {"segment":2,"status":"PARTIAL","provider_calls":2,
             "hunt_id":x["hunt"]["hunt_id"]}],
    })
    c={"state":"COMPLETED","native_hunt_id":x["hunt"]["hunt_id"],
       "recovery_source_hashes":source_hashes}
    done={"kind":"direct_hunt_recovery_completed","mode":"PERPETUUM_RECOVERY",
          "status":"PARTIAL","new_provider_calls":2,
          "duplicate_provider_calls":0,"author_gate":"HOLD"}
    assert _native_completion_attested([done],c,x)
    for name,wrong in [
        ("duplicate_provider_calls",1),
        ("provider_calls",7),
        ("recovered_locator_provider_calls",0),
        ("recovery_source_hashes",{"wave1_evidence":"0"*64}),
        ("research_depth_profile","NATIVE_INDAGO_PERPETUUM_MULTISEGMENT"),
    ]:
        changed=copy.deepcopy(x);changed[name]=wrong
        assert not _native_completion_attested([done],c,changed),name
    wrong_claim=dict(c,native_hunt_id="h-another-run")
    assert not _native_completion_attested([done],wrong_claim,x)
    wrong_claim=dict(c,recovery_source_hashes={"wave1_evidence":"0"*64})
    assert not _native_completion_attested([done],wrong_claim,x)
    for k,bad in [("kind","direct_hunt_completed"),("mode","OTHER"),
                  ("status","BLOCKED"),("new_provider_calls",3),
                  ("duplicate_provider_calls",1),("author_gate","GO")]:
        wrong=dict(done);wrong[k]=bad
        assert not _native_completion_attested([wrong],c,x),k
    assert _native_completion_attested([
        {"kind":"direct_hunt_completed","native_hunt_id":x["hunt"]["hunt_id"]}],
        c,x)


def test_f4_native_m117_whitecrow_handoff_is_pinned_without_forging_f238_stage():
    from kairoskopion.kairon_provider.add006_return_bridge import _validate_original_d24_stage
    root=Path(r"C:/projects/trimurti/_ops/T3-TALK-20261019/F4_REVIEW_RETURN_20261104/runtime_compact/more_research_handoff")
    stage=json.loads((root/"handoff_receipt.json").read_text(encoding="utf-8"))
    request=json.loads((root/"research_request_PENDING.json").read_text(encoding="utf-8"))
    whitecrow_sha=sha((root/"whitecrow_report.json").read_bytes())
    kwargs=dict(request_sha=sha((root/"research_request_PENDING.json").read_bytes()),
                transport_sha=sha((root/"indago_task_PENDING.txt").read_bytes()),
                baseline_sha=whitecrow_sha,
                whitecrow_commit="0bd96d098a65c2f6063d682e4f9e3e97c8034227",
                whitecrow_module_sha="265216755b06926414ff09ad38f1c79de531345a5d93b397cd7468141a0401af")
    assert kwargs["request_sha"]==stage["request_sha256"]
    assert kwargs["baseline_sha"]==stage["whitecrow_report_sha256"]
    _validate_original_d24_stage(stage,request,**kwargs)
    for name,bad in [
        ("status","DISPATCHED"),
        ("indago_deep_hunt_execution","DONE"),
        ("indago_transport_sha256","f"*64),
        ("whitecrow_report_sha256","f"*64),
        ("author_gate","GO"),
        ("new_native_hunts",1),
        ("not_a_science_approval",False),
    ]:
        modified=dict(stage);modified[name]=bad
        with pytest.raises(EvidenceBlocked,match="f4_d24_handoff_stage_not_pinned"):
            _validate_original_d24_stage(modified,request,**kwargs)
    altered=dict(stage);altered["whitecrow_code"]={"git_commit":"wrong","module_sha256":"f"*64,"dirty":True}
    with pytest.raises(EvidenceBlocked,match="f4_d24_handoff_stage_not_pinned"):
        _validate_original_d24_stage(altered,request,**kwargs)
