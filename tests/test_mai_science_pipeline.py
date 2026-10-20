"""MAI one-command pipeline preserves REAL source attestations and HOLD."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from scripts import run_mai_science_pipeline as workflow
from scripts import fetch_mai_prior_art as fetcher
from tests.test_mai_prior_art_fetch import make_world, APIResponse

SHA="a"*64

def mini(tmp:Path):
    p=tmp/"packets"
    s=tmp/"science"
    p.mkdir();s.mkdir()
    (p/"manifest.json").write_text(json.dumps({
        "schema":"MAI_W12_BATCH_OUTPUT_MANIFEST_v1",
        "records":53,"source_jsonl_sha256":SHA,
    }),encoding="utf-8")
    (s/"science_index.json").write_text(json.dumps({
        "schema":"MAI_W12_PRIOR_RESEARCH_INDEX_V1",
        "source_W12_sha256":SHA,
    }),encoding="utf-8")
    return p,s

def test_one_command_uses_existing_organs_and_preserves_human_holds(tmp_path,monkeypatch):
    packets,science=mini(tmp_path)
    seen={}
    def fake_fetch(p,s,out,**kw):
        seen["fetch"]=True
        assert p==packets and s==science
        assert kw["limit"]==53
        return {"route_count":53,"unique_requested_doi":24,
                "abstracts_retrieved_route_bindings":178,
                "provider_queries":48,"cache_hits":0}
    def fake_model(p,s,source,out,**kw):
        seen["model"]=True
        assert kw["limit"]==53
        return {"provider_calls":11}
    def fake_merge(p,source,roots,out):
        seen["merge"]=True
        assert roots==[tmp_path/"model"]
        workflow.put(out/"merged_challenge_receipt.json",{"records":53})
        return {"model_reviews_validated":53,
                "objections_with_abstract_passage":52,
                "research_abstentions":1,"missing_routes":[]}
    monkeypatch.setattr(workflow,"get_prior_art",fake_fetch)
    monkeypatch.setattr(workflow,"run_criticism",fake_model)
    monkeypatch.setattr(workflow,"merge_criticism",fake_merge)
    root=tmp_path/"merged"
    receipt=workflow.run_workflow(
        packets,science,tmp_path/"papers",tmp_path/"model",root)
    assert sorted(seen)==["fetch","merge","model"]
    assert receipt["model_reviews_validated"]==53
    assert receipt["author_gates_ready"]==0
    assert receipt["external_submission_actions"]==0
    assert receipt["scientific_provider_calls_this_invocation"]==11
    assert workflow.load(root/"workflow_receipt.json")==receipt

def test_source_hash_drift_rejected_before_provider_execution(tmp_path,monkeypatch):
    p,s=mini(tmp_path)
    index=workflow.load(s/"science_index.json")
    index["source_W12_sha256"]="b"*64
    workflow.put(s/"science_index.json",index)
    def forbid(*a,**kw):raise AssertionError("fetch should not be invoked")
    monkeypatch.setattr(workflow,"get_prior_art",forbid)
    with pytest.raises(ValueError,match="mismatch"):
        workflow.run_workflow(p,s,tmp_path/"papers",tmp_path/"model",tmp_path/"merged")

def test_raw_crossref_cache_hash_is_verified_before_offline_replay(tmp_path,monkeypatch):
    packet,science=make_world(tmp_path)
    def fake(url,timeout=18):
        doi="10.1007/paper-a" if "paper-a" in url.full_url else "10.1007/test"
        if "crossref" in url.full_url:
            return APIResponse({"message":{
                "DOI":doi,"title":["Test"],"container-title":["Test Journal"],
                "abstract":"<p>A publication-level challenge with exact source provenance.</p>"
            }})
        return APIResponse({
            "doi":"https://doi.org/"+doi,"title":"Test",
            "abstract_inverted_index":{"Publication":[0],"test":[1]},
            "primary_location":{"source":{"display_name":"Test Journal"}}
        })
    monkeypatch.setattr(fetcher,"urlopen",fake)
    root=tmp_path/"published"
    fetcher.execute(packet,science,root,limit=1)
    assert workflow.attest_reusable_publications(root,packet)["route_count"]==1
    doi="10.1007/paper-a"
    token=hashlib.sha256(doi.encode("utf-8")).hexdigest()[:20]
    tampered=root/"published_work_cache"/token/"crossref.response.json"
    tampered.write_bytes(b"forged replacement of Crossref API response")
    with pytest.raises(ValueError,match="raw Crossref/OpenAlex response SHA drift"):
        workflow.attest_reusable_publications(root,packet)

def test_venue_raw_source_attestation_fails_closed(tmp_path,monkeypatch):
    from scripts import fetch_mai_venue_pages as venue_capture
    from tests.test_mai_venue_pages import WebResponse
    from tests.test_mai_w12_indago_bind import prepare
    packets,_,_=prepare(tmp_path)
    route_file=packets/"routes"/"MAI-W12-001.json"
    route=json.loads(route_file.read_text(encoding="utf-8"))
    route["route"]["official_url"]="https://example.org/cfp"
    route_file.write_text(json.dumps(route),encoding="utf-8")
    monkeypatch.setattr(venue_capture,"_request",lambda url,timeout:WebResponse(url))
    root=tmp_path/"venues"
    venue_capture.capture(packets,root,limit=1)
    assert workflow.attest_reusable_venues(root,packets)["routes_requested"]==1
    key=hashlib.sha256(b"https://example.org/cfp").hexdigest()[:24]
    raw=root/"url_capture_cache"/key/"source.bin"
    raw.write_bytes(b"FORGED HTML")
    with pytest.raises(ValueError,match="stale raw publisher HTML"):
        workflow.attest_reusable_venues(root,packets)
