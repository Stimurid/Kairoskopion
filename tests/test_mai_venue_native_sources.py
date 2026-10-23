"""Exact DOI, same venue and source-retrieval semantics for true TargetWorld exemplars."""
from __future__ import annotations
from pathlib import Path
import json
import pytest
from scripts import run_mai_venue_native_sources as stage
from tests.test_mai_w12_indago_bind import prepare

DOI="10.1007/s11217-026-10100-4"
URL="https://link.springer.com/article/"+DOI

def source(tmp_path:Path):
    packets,_,_=prepare(tmp_path)
    sheet=stage.load(packets/"manifest.json")
    rec=stage.load(packets/"routes"/"MAI-W12-001.json")
    journal=rec["route"]["journal"]
    manifest=tmp_path/"native.json"
    stage.write(manifest,{
        "schema":"MAI_KAIRON_NATIVE_PUBLISHER_CANDIDATE_MANIFEST_v1",
        "source_W12_sha256":sheet["source_jsonl_sha256"],
        "candidates":[{
            "route_id":"MAI-W12-001","doi":DOI,"publisher_article_url":URL,
            "discovery_channel":"PUBLISHER_WEBSITE","discovery_ref":"https://link.springer.com"
        }],
    })
    return packets,manifest,journal

def fake_provider(monkeypatch,journal):
    def provider(backend,doi,cache):
        assert backend=="crossref"
        assert doi==DOI
        return {"http_status":200,"backend":"crossref","requested_doi":doi,
                "parsed":{"doi_identity_match":True,"venue":journal,"title":"Original example"}}
    def html(url,root,timeout):
        raw=b"<html>Readable source with abstract, introduction, method and conclusion</html>"
        home=root/stage.sha(url.encode())[:24]
        home.mkdir(parents=True,exist_ok=True)
        (home/"source.bin").write_bytes(raw)
        (home/"visible_text.txt").write_text("Readable source with abstract, introduction, method and conclusion\n",encoding="utf-8")
        return {
            "requested_url":url,"final_url":url,"status":"FETCHED_TEXT",
            "raw_sha256":stage.sha(raw),
            "visible_text_sha256":stage.sha(b"Readable source with abstract, introduction, method and conclusion"),
            "visible_chars":len(raw),
        }
    monkeypatch.setattr(stage,"query",provider)
    monkeypatch.setattr(stage,"obtain",html)

def test_real_styled_native_source_still_requires_scholarly_read(tmp_path,monkeypatch):
    packets,manifest,journal=source(tmp_path)
    fake_provider(monkeypatch,journal)
    result=stage.run(packets,manifest,tmp_path/"out")
    assert result["input_candidate_count"]==1
    assert result["crossref_native_venue_verified"]==1
    assert result["publisher_html_available_count"]==1
    assert result["read_depth_certified_scholarly_full_text"]==0
    assert result["original_research_genre_accepted"]==0
    assert result["author_decisions_accepted"]==0
    p=next((tmp_path/"out"/"routes"/"MAI-W12-001").glob("*.json"))
    info=stage.load(p)
    assert info["read_depth"]=="PUBLISHER_VISIBLE_HTML_TEXT_CAPTURED_NOT_SCHOLARLY_FULL_READ"
    assert info["artikl_author_decision"]=="HOLD"

def test_cross_venue_work_not_misclassified_as_native(tmp_path,monkeypatch):
    packets,manifest,journal=source(tmp_path)
    fake_provider(monkeypatch,"Other Journal")
    result=stage.run(packets,manifest,tmp_path/"out")
    assert result["crossref_native_venue_verified"]==0
    assert result["read_depth_certified_scholarly_full_text"]==0

def test_nondoi_and_nonpublisher_url_blocked_before_query(tmp_path,monkeypatch):
    packets,manifest,journal=source(tmp_path)
    data=stage.load(manifest)
    data["candidates"][0]["publisher_article_url"]="https://example.org/old-article/"
    stage.write(manifest,data)
    fake_provider(monkeypatch,journal)
    with pytest.raises(ValueError,match="exact journal-publisher DOI URL"):
        stage.run(packets,manifest,tmp_path/"out")

def test_invalid_w12_source_digest_rejected(tmp_path,monkeypatch):
    packets,manifest,journal=source(tmp_path)
    data=stage.load(manifest)
    data["source_W12_sha256"]="f"*64
    stage.write(manifest,data)
    fake_provider(monkeypatch,journal)
    with pytest.raises(ValueError,match="source W12 mismatch"):
        stage.run(packets,manifest,tmp_path/"out")
