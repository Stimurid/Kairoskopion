"""Kairon HTML/HTTP captures are provenance, never certified journal rules."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest
from kairoskopion.kairon_provider.w12_packets import materialize,venue_web_source_for_route,sha
from tests.test_w12_packets import setup_source

def stable(x):
    return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")

def make_world(tmp:Path):
    source,snapshot=setup_source(tmp)
    source_sha=sha(source.read_bytes())
    raw=json.loads(source.read_text(encoding="utf-8").splitlines()[0])
    route=raw["source_fields"]
    url=route["Официальная страница"]
    rid="MAI-W12-001"
    visible="Authentic publisher webpage text collected from verified HTTP response. "*8
    urlcache=tmp/"capture"/"url_capture_cache"/sha(url.encode("utf-8"))[:24]
    urlcache.mkdir(parents=True)
    (urlcache/"visible_text.txt").write_text(visible+"\n",encoding="utf-8")
    src={
        "requested_url":url,"final_url":url,"status":"FETCHED_TEXT",
        "http_status":200,"visible_chars":len(visible),
        "visible_text_sha256":sha(visible.encode("utf-8")),
        "read_depth":"WEB_HTML_TEXT_EXTRACT",
        "submission_policy_verified":False,"cfp_deadline_verified":False,
        "ai_authorship_policy_verified":False,"official_publisher_status_verified":False,
    }
    data={
        "schema":"MAI_KAIRON_OFFICIAL_VENUE_WEB_CAPTURE_v1",
        "route_id":rid,"W12_source_sha256":source_sha,
        "journal":"Test Venue A","family":"A","variant":"A-NORM",
        "w12_listed_official_url":url,
        "web_source":src,
        "web_source_receipt_sha256":sha(stable(src)),
        "source_read_state":"FETCHED_TEXT",
        "official_rules_acceptance":"HOLD",
        "author_gate":"CLOSED","send_count":0,
        "venue_page_domain_alone_is_not_policy_acceptance":True,
        "policy_freshness_verified":False,
    }
    folder=tmp/"capture"/"routes"
    folder.mkdir()
    (folder/(rid+".json")).write_text(json.dumps(data),encoding="utf-8")
    return source,snapshot,tmp/"capture",data

def test_board_links_exact_web_captured_text_but_keeps_all_editorial_policies_closed(tmp_path):
    source,snap,root,_=make_world(tmp_path)
    board=tmp_path/"board"
    manifest=materialize(source,snap,board,venue_web_root=root)
    assert manifest["venue_pages_acquired_count"]==1
    assert manifest["venue_web_text_readable_count"]==1
    assert manifest["venue_policies_certified_count"]==0
    assert manifest["ready_for_human_send"]==0
    card=json.loads((board/"routes"/"MAI-W12-001.json").read_text(encoding="utf-8"))
    assert card["venue_web_evidence"]["venue_policy_gate"]=="HOLD"
    assert card["venue_web_evidence"]["text"].startswith("venue_text/")
    assert (board/"venue_text"/"MAI-W12-001.txt").is_file()
    assert "Кайрон / ответ сайта" in (board/"index.html").read_text(encoding="utf-8")

def test_changed_venue_policy_flag_fails_closed(tmp_path):
    source,snap,root,rec=make_world(tmp_path)
    rec["web_source"]["submission_policy_verified"]=True
    rec["web_source_receipt_sha256"]=sha(stable(rec["web_source"]))
    (root/"routes"/"MAI-W12-001.json").write_text(json.dumps(rec),encoding="utf-8")
    with pytest.raises(ValueError,match="publisher policy promotion"):
        materialize(source,snap,tmp_path/"board",venue_web_root=root)

def test_changed_webpage_passage_fails_original_capture_sha(tmp_path):
    source,snap,root,rec=make_world(tmp_path)
    url=rec["w12_listed_official_url"]
    text=root/"url_capture_cache"/sha(url.encode())[:24]/"visible_text.txt"
    text.write_text("A forged HTML replacement of original research provenance.",encoding="utf-8")
    with pytest.raises(ValueError,match="source text raw passage SHA mismatch"):
        materialize(source,snap,tmp_path/"board",venue_web_root=root)
