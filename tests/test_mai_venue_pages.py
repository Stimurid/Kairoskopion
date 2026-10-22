"""Official-looking URLs and website text do not auto-certify venue rules."""
from __future__ import annotations

from pathlib import Path
import json
from types import SimpleNamespace

import pytest
from scripts import fetch_mai_venue_pages as mod
from tests.test_mai_w12_indago_bind import prepare

class WebResponse:
    status=200
    headers={"Content-Type":"text/html; charset=UTF-8"}
    def __init__(self,url:str):
        self.url=url
        self.content=(
            "<html><head><title>Call for Papers</title><script>INJECT_NOT_CONTENT</script></head>"
            "<body><h1>Special Issue</h1><p>"
            +"Published submission requirements and editorial rationale. "*18
            +"</p></body></html>"
        ).encode("utf-8")
    def geturl(self):return self.url
    def read(self,n):return self.content[:n]
    def __enter__(self):return self
    def __exit__(self,*args):return False

def test_html_source_is_persisted_and_policy_stays_unverified(tmp_path,monkeypatch):
    requested=[]
    def fake(url,timeout):
        requested.append(url)
        return WebResponse(url)
    monkeypatch.setattr(mod,"_request",fake)
    url="https://example.org/cfp/special-issue"
    snap=mod.obtain(url,tmp_path/"pages")
    assert snap["status"]=="FETCHED_TEXT"
    assert snap["visible_chars"]>300
    assert snap["read_depth"]=="WEB_HTML_TEXT_EXTRACT"
    assert snap["cfp_deadline_verified"] is False
    assert snap["submission_policy_verified"] is False
    assert snap["ai_authorship_policy_verified"] is False
    record=tmp_path/"pages"/mod.sha(url.encode())[:24]
    assert (record/"source.bin").is_file()
    assert "INJECT_NOT_CONTENT" not in (record/"visible_text.txt").read_text(encoding="utf-8")
    after=mod.obtain(url,tmp_path/"pages")
    assert after["cached"] is True
    assert requested==[url]

def test_raw_capture_is_verified_from_cache(tmp_path,monkeypatch):
    monkeypatch.setattr(mod,"_request",lambda url,timeout:WebResponse(url))
    url="https://example.org/cfp"
    mod.obtain(url,tmp_path/"pages")
    raw=tmp_path/"pages"/mod.sha(url.encode())[:24]/"source.bin"
    raw.write_bytes(b"forged editorial call")
    with pytest.raises(ValueError,match="hash mismatch"):
        mod.obtain(url,tmp_path/"pages")

@pytest.mark.parametrize("url",[
    "http://example.org/","https://localhost/admin",
    "https://192.168.1.1/config","https://example.local/secret",
    "file:///C:/secrets","javascript:alert(1)",
])
def test_disallowed_private_non_https_urls(url,tmp_path):
    snap=mod.obtain(url,tmp_path/"pages")
    assert snap["status"]=="URL_DISALLOWED_OR_INVALID"
    assert snap["read_depth"]=="NOT_READ"
    assert snap["raw_sha256"] is None

def test_real_source_packet_to_venue_acquisition_without_author_promotion(tmp_path,monkeypatch):
    packets,_,_=prepare(tmp_path)
    row=packets/"routes"/"MAI-W12-001.json"
    packet=mod.load(row)
    packet["route"]["official_url"]="https://example.org/cfp"
    row.write_text(json.dumps(packet,ensure_ascii=False),encoding="utf-8")
    monkeypatch.setattr(mod,"_request",lambda url,timeout:WebResponse(url))
    out=mod.capture(packets,tmp_path/"venues",limit=1)
    assert out["routes_requested"]==1
    assert out["policies_certified"]==0
    assert out["cfp_deadlines_verified"]==0
    assert out["external_submissions"]==0
    target=tmp_path/"venues"/"routes"/"MAI-W12-001.json"
    record=mod.load(target)
    assert record["source_read_state"]=="FETCHED_TEXT"
    assert record["author_gate"]=="CLOSED"
    assert record["policy_freshness_verified"] is False
