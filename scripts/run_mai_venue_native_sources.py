"""Kairon exact DOI + same-venue ORIGINAL PUBLISHER HTML source admission.

Upstream venue-native works are selected by an independent research manifest;
discovery is not implied by the W12 route page or its secondary DOI list.
Reuses the existing fetch_mai_prior_art.query + fetch_mai_venue_pages.obtain
producers. A publisher HTML text capture is SOURCE AVAILABLE, not scholarly FULL
READ or validated original contribution, and grants no author/editorial gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

if __package__:
    from .fetch_mai_prior_art import query,normalize_doi
else:
    from fetch_mai_prior_art import query,normalize_doi
if __package__:
    from .fetch_mai_venue_pages import obtain
else:
    from fetch_mai_venue_pages import obtain
if __package__:
    from .run_mai_kairon_policy_claims import load,sha,stable,write
else:
    from run_mai_kairon_policy_claims import load,sha,stable,write

SCHEMA="MAI_KAIRON_NATIVE_PUBLISHER_WORK_SOURCE_v1"

def canonical_venue(s:str)->str:
    return " ".join(s.casefold().replace("&","and").split())

def native_source(
    packets:Path,output:Path,record:dict[str,Any],source_hash:str
)->dict[str,Any]:
    rid=record["route_id"]
    doi=normalize_doi(str(record["doi"]))
    url=str(record["publisher_article_url"])
    parsed=urlparse(url)
    if (parsed.scheme!="https" or parsed.hostname not in (
        "link.springer.com","www.tandfonline.com","academic.oup.com",
        "journals.sagepub.com","onlinelibrary.wiley.com")
            or doi not in parsed.path.lower()
            or parsed.username or parsed.password):
        raise ValueError("not an exact journal-publisher DOI URL "+rid+" "+doi)
    w=load(packets/"routes"/(rid+".json"))["route"]
    db=query("crossref",doi,output/"doi_provider_cache")
    meta=db.get("parsed") or {}
    if (db.get("http_status")!=200
            or meta.get("doi_identity_match") is not True
            or not meta.get("venue")):
        raise ValueError("Crossref venue/DOI identity not verified "+rid+" "+doi)
    venue_matches=canonical_venue(meta["venue"])==canonical_venue(w["journal"])
    web=obtain(url,output/"url_capture_cache",timeout=22)
    if web.get("requested_url")!=url:
        raise ValueError("publisher source URL/bytes mismatch "+rid)
    original=output/"url_capture_cache"/sha(url.encode())[:24]
    if web.get("raw_sha256"):
        raw=original/"source.bin"
        if not raw.is_file() or sha(raw.read_bytes())!=web["raw_sha256"]:
            raise ValueError("publisher HTML raw source cannot be read back "+rid)
    publisher_host_matches=(urlparse(web.get("final_url",url)).hostname==parsed.hostname)
    if web["status"]=="FETCHED_TEXT" and web.get("visible_text_sha256"):
        p=original/"visible_text.txt"
        if not p.is_file() or sha(p.read_text(encoding="utf-8").rstrip("\r\n").encode())!=web["visible_text_sha256"]:
            raise ValueError("publisher HTML visible text source SHA drift "+rid)
    work={
        "schema":SCHEMA,"route_id":rid,
        "source_W12_sha256":source_hash,"W12_venue":w["journal"],
        "W12_meaning_version":w["variant"],
        "DOI":doi,"original_publisher_url":url,
        "discovery_channel":record["discovery_channel"],
        "discovery_ref":record["discovery_ref"],
        "crossref_source_receipt_sha256":sha(stable({k:v for k,v in db.items() if k!="from_cache"})),
        "crossref_DOI_identity_match":True,
        "crossref_published_venue":meta["venue"],
        "is_native_in_target_journal_by_Crossref":venue_matches,
        "title":meta.get("title",""),
        "publisher_source_receipt_sha256":sha(stable({k:v for k,v in web.items() if k!="cached"})),
        "publisher_html_state":web["status"],
        "publisher_html_raw_sha256":web.get("raw_sha256"),
        "publisher_html_visible_text_sha256":web.get("visible_text_sha256"),
        "publisher_html_chars":web.get("visible_chars",0),
        "publisher_host_observed_same":publisher_host_matches,
        "read_depth":"PUBLISHER_VISIBLE_HTML_TEXT_CAPTURED_NOT_SCHOLARLY_FULL_READ" if
                     web["status"]=="FETCHED_TEXT" else "NOT_READ_PUBLISHER_HTML",
        "genre_peer_research_verified":False,
        "research_claims_evaluated":False,
        "venue_current_policy_verified":False,
        "artikl_author_decision":"HOLD",
        "journal_submission_actions":0,
    }
    write(output/"routes"/rid/(sha(doi.encode())[:16]+".json"),work)
    return work

def run(packets:Path,manifest:Path,output:Path)->dict[str,Any]:
    original=load(packets/"manifest.json")
    source=load(manifest)
    if (source.get("schema")!="MAI_KAIRON_NATIVE_PUBLISHER_CANDIDATE_MANIFEST_v1"
            or source.get("source_W12_sha256")!=original.get("source_jsonl_sha256")):
        raise ValueError("native publisher research manifest/source W12 mismatch")
    entries=source.get("candidates",[])
    if not isinstance(entries,list) or not 1<=len(entries)<=150:
        raise ValueError("publisher candidate manifest count invalid")
    seen=set();done=[]
    for item in entries:
        pair=(item["route_id"],normalize_doi(item["doi"]))
        if pair in seen:raise ValueError("duplicate publisher candidate DOI/route")
        seen.add(pair)
        done.append(native_source(packets,output,item,original["source_jsonl_sha256"]))
    result={
        "schema":"MAI_KAIRON_NATIVE_PUBLISHER_WORK_BATCH_v1",
        "source_W12_sha256":original["source_jsonl_sha256"],
        "input_candidate_count":len(entries),
        "publisher_html_available_count":sum(x["publisher_html_state"]=="FETCHED_TEXT" for x in done),
        "crossref_native_venue_verified":sum(x["is_native_in_target_journal_by_Crossref"] for x in done),
        "publisher_visibly_same_host":sum(x["publisher_host_observed_same"] for x in done),
        "read_depth_certified_scholarly_full_text":0,
        "original_research_genre_accepted":0,
        "independent_scholarly_adjudication_accepted":0,
        "editorial_current_policy_accepted":0,
        "author_decisions_accepted":0,"journal_send_count":0,
        "work_receipts":[{"route_id":x["route_id"],"doi":x["DOI"],"title":x["title"],
                         "native_venue_metadata_match":x["is_native_in_target_journal_by_Crossref"],
                         "publisher_html":x["publisher_html_state"],
                         "source_receipt":x["publisher_html_raw_sha256"]} for x in done],
    }
    write(output/"native_work_batch_receipt.json",result)
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packets",type=Path,required=True)
    p.add_argument("--source-list",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(run(a.packets,a.source_list,a.output),ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
