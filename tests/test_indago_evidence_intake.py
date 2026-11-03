import json
import hashlib
from pathlib import Path

import pytest

from kairoskopion.kairon_provider.indago_evidence_intake import import_hunt
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked

TASK="TRIMURTI_M108_C04_20261103"
PIN="a"*64


def write_json(p,data):
    p.write_text(json.dumps(data),encoding="utf-8")

def fixture(tmp_path,status="PARTIAL",providers=1,ok=True):
    root=tmp_path/"hunts"
    h=root/"h-20261103T092827Z-trimurti_m108_c04_20261103-e7bb49"
    h.mkdir(parents=True)
    ident=h.name
    counts={"waves_ok":int(ok),"waves_run":1,"new_verified":0,
            "new_unverified":0,"hypotheses":0,"known_rediscovered":0,
            "provider_calls":providers}
    write_json(h/"meta.json",{"hunt_id":ident,"task_id":TASK,"agent_id":"indago",
                "status":status,"counts":counts,"degradations":[],"reason_codes":[],
                "session_ids":["indago-"+ident+"-w1"]})
    write_json(h/"authority_fingerprints.json",{"hunt_id":ident,"authorities":
       {key:{"source":"LIVE","currentness":"LIVE_VERIFIED","sha256":PIN} for key in
        ("tasks_and_trails","living_current","source_ledger","candidate_queue","hunt_ledger")}})
    (h/"result.md").write_text("# Indago hunt "+ident+"\n- status: **"+status+"**",encoding="utf-8")
    (h/"trace.jsonl").write_text(json.dumps({"hunt_id":ident,"event":"HUNT_END","status":status})+"\n",encoding="utf-8")
    write_json(h/"candidates.json",{"hunt_id":ident,"new_verified":[],"new_unverified":[],
                                  "hypotheses":[],"known_rediscovered":[]})
    write_json(h/"wave-1.json",{"row":{"wave":1,"parse_ok":ok}})
    write_json(h/"wave-1.raw.json",{"runner_status":"OK" if ok else "TIMEOUT"})
    write_json(h/"wave-1.evidence.json",[
         {"id":"E1.1","provider":"crossref","query":"supplier qualification",
          "status":"OK","items":[{"title":"An original","doi":"10.0001/example"}]}
          for _ in range(providers)])
    return root,h


def attempt(root,h,tmp_path):
    return import_hunt(hunts_root=root,hunt_dir=h,output_root=tmp_path/"return",
      expected_task=TASK,trusted_original_sha=PIN,trusted_manuscript_sha=PIN,
      trusted_review_sha=PIN)


def test_scoped_native_return_requires_scholarly_acceptance(tmp_path):
    root,h=fixture(tmp_path)
    r=attempt(root,h,tmp_path)
    assert r["research_status"]=="SCOPED_NATIVE_EVIDENCE_REQUIRES_SCIENTIFIC_REVIEW"
    assert not r["novelty_accepted"] and not r["send"]
    assert r==attempt(root,h,tmp_path)


def test_genuine_blocked_run_preserved_not_promoted(tmp_path):
    root,h=fixture(tmp_path,"BLOCKED",providers=0,ok=False)
    r=attempt(root,h,tmp_path)
    assert r["research_status"]=="NATIVE_HUNT_NO_ADMISSIBLE_SCIENCE_RETURN"
    assert r["counts"]["provider_calls"]==0
    assert r["author_gate"]=="HOLD"


def test_no_status_forgery_or_tampered_artifacts(tmp_path):
    root,h=fixture(tmp_path)
    attempt(root,h,tmp_path)
    (h/"trace.jsonl").write_text('{"event":"HUNT_END","status":"PASS","hunt_id":"'+h.name+'"}')
    with pytest.raises(EvidenceBlocked,match="native_trace_not_finalized_or_status_mismatch"):
        attempt(root,h,tmp_path)


def test_no_mirror_masquerading_as_live(tmp_path):
    root,h=fixture(tmp_path)
    p=h/"authority_fingerprints.json"
    j=json.loads(p.read_text())
    j["authorities"]["living_current"]["source"]="MIRROR"
    write_json(p,j)
    with pytest.raises(EvidenceBlocked,match="native_authorities_not_live_verified"):
        attempt(root,h,tmp_path)


def test_hunt_dir_outside_trusted_root_rejected(tmp_path):
    root,h=fixture(tmp_path)
    other=tmp_path/"other"
    other.mkdir()
    with pytest.raises(EvidenceBlocked,match="outside_trusted_root"):
        attempt(other,h,tmp_path)


def test_native_counts_have_to_match_actual_provider_bytes(tmp_path):
    root,h=fixture(tmp_path,providers=1)
    write_json(h/"wave-1.evidence.json",[])
    with pytest.raises(EvidenceBlocked,match="native_count_not_byte_consistent"):
        attempt(root,h,tmp_path)
