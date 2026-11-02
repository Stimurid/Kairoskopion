"""Real-input operator seam tests. Fixture examples are not article credentials."""
import hashlib
import json
from pathlib import Path

import pytest

from kairoskopion.kairon_provider.manuscript_draft_intake import ingest
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked


def _hash(data: bytes):
    return hashlib.sha256(data).hexdigest()


def case(tmp_path: Path):
    inputs=tmp_path/"inputs"
    inputs.mkdir()
    source=("Original author source. " * 45).encode("utf-8")
    science=json.dumps({"author_gate":"HOLD","W12_added":0,"external_send":False,
                        "critical_source_objection":"Evidence not accepted."},sort_keys=True).encode("utf-8")
    science += b" " * 550
    draft=("# Draft academic article\n\n## Theory\n" + "Strong, provisional academic argument. " * 145 + "\n## Method\n" + "No empirical claim. "*70).encode("utf-8")
    artifacts={}
    for key,b in {"source":source,"science":science,"draft":draft}.items():
        (inputs/(key+".txt")).write_bytes(b)
        artifacts[key]={"path":key+".txt","sha256":_hash(b)}
    manifest={"schema":"trimurti-manuscript-draft-intake-v1","case_id":"T3-TEST",
              "claim_id":"C04-GUARMEAS","route_id":"C-GUARMEAS-TEST",
              "producer_ref":"independent_writer:local:test","evidence_mode":"REAL",
              "author_gate":"HOLD","submission_enabled":False,
              "scientific_novelty_accepted":False,"article_seed_author_approved":False,
              "source_original_sha256":_hash(source),"artifacts":artifacts}
    path=tmp_path/"manifest.json"
    path.write_text(json.dumps(manifest,sort_keys=True),encoding="utf-8")
    return inputs,path,manifest


def _ingest(p, inputs, out, *, source_sha=None, science_sha=None):
    # Here the test harness acts as the outside trusted source registry.
    m=json.loads(p.read_text(encoding="utf-8"))
    return ingest(manifest_path=p,input_root=inputs,output_root=out,
                  trusted_source_sha256=source_sha or m["source_original_sha256"],
                  trusted_science_sha256=science_sha or m["artifacts"]["science"]["sha256"])


def test_real_bounded_source_draft_intake_and_replay(tmp_path):
    inputs,p,_=case(tmp_path)
    out=tmp_path/"out"
    a=_ingest(p,inputs,out)
    b=_ingest(p,inputs,out)
    assert a==b
    assert a["draft_utf8_word_count"] > 600
    assert a["status"]=="DRAFT_CAPTURED_AUTHOR_REVIEW_REQUIRED"
    assert a["new_w12_routes"]==0 and not a["manuscript_go"]
    assert not a["external_send"] and not a["article_seed_author_approved"]


def test_tampered_author_source_fails_before_receipt(tmp_path):
    inputs,p,_=case(tmp_path)
    (inputs/"source.txt").write_bytes(b"tampered"*200)
    with pytest.raises(EvidenceBlocked):
        _ingest(p,inputs,tmp_path/"out")
    assert not (tmp_path/"out"/"draft-intake-receipt.json").exists()


@pytest.mark.parametrize("key,value",[
    ("author_gate","GO"),
    ("submission_enabled",True),
    ("scientific_novelty_accepted",True),
    ("article_seed_author_approved",True),
    ("evidence_mode","FIXTURE"),
])
def test_unsafe_control_is_blocked(tmp_path,key,value):
    inputs,p,m=case(tmp_path)
    m[key]=value
    p.write_text(json.dumps(m),encoding="utf-8")
    with pytest.raises(EvidenceBlocked):
        _ingest(p,inputs,tmp_path/"out")


def test_traversal_source_is_blocked(tmp_path):
    inputs,p,m=case(tmp_path)
    m["artifacts"]["draft"]["path"]="../untrusted.txt"
    p.write_text(json.dumps(m),encoding="utf-8")
    with pytest.raises((EvidenceBlocked,OSError)):
        _ingest(p,inputs,tmp_path/"out")


def test_fake_scientific_acceptance_is_blocked(tmp_path):
    inputs,p,m=case(tmp_path)
    science=json.dumps({"author_gate":"APPROVED","W12_added":7,"external_send":True}).encode()
    (inputs/"science.txt").write_bytes(science+b" "*600)
    m["artifacts"]["science"]["sha256"]=_hash(science+b" "*600)
    p.write_text(json.dumps(m),encoding="utf-8")
    with pytest.raises(EvidenceBlocked):
        _ingest(p,inputs,tmp_path/"out")


def test_immutable_receipt_does_not_silently_change(tmp_path):
    inputs,p,m=case(tmp_path)
    out=tmp_path/"out"
    _ingest(p,inputs,out)
    m["producer_ref"]="fake-new-reviewer"
    p.write_text(json.dumps(m),encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="immutable_existing_draft_receipt_conflict"):
        _ingest(p,inputs,out)

def test_model_self_certified_source_manifest_cannot_replace_trusted_authority(tmp_path):
    inputs,p,m=case(tmp_path)
    outside_original_sha=m["source_original_sha256"]
    forged=b"Different fake author source, made to look coherent."*30
    (inputs/"source.txt").write_bytes(forged)
    m["source_original_sha256"]=_hash(forged)
    m["artifacts"]["source"]["sha256"]=_hash(forged)
    p.write_text(json.dumps(m),encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="trusted_source_sha256_mismatch"):
        _ingest(p,inputs,tmp_path/"out",source_sha=outside_original_sha)


def test_model_self_certified_science_manifest_cannot_replace_trusted_science(tmp_path):
    inputs,p,m=case(tmp_path)
    outside_science_sha=m["artifacts"]["science"]["sha256"]
    forged=(json.dumps({"author_gate":"HOLD","external_send":False,"W12_added":0,
                        "critical_source_objection":"No such objection."}).encode()+b" "*600)
    (inputs/"science.txt").write_bytes(forged)
    m["artifacts"]["science"]["sha256"]=_hash(forged)
    p.write_text(json.dumps(m),encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="trusted_science_sha256_mismatch"):
        _ingest(p,inputs,tmp_path/"out",science_sha=outside_science_sha)
