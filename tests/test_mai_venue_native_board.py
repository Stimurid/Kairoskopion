"""Native same-journal publisher HTML sources are visible, never scientific FULL_READ."""
from __future__ import annotations
from pathlib import Path
import json
import pytest

from kairoskopion.kairon_provider.w12_packets import materialize,sha
from tests.test_w12_packets import setup_source

def stable(x):
    return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")

DOI="10.1007/test-original-1"
URL="https://link.springer.com/article/"+DOI

def setup(tmp_path):
    source,snapshot=setup_source(tmp_path)
    initial=json.loads(source.read_text(encoding="utf-8").splitlines()[0])["source_fields"]
    journal=initial["Журнал"]
    root=tmp_path/"native"
    crossref=root/"doi_provider_cache"/sha(DOI.encode())[:20]
    crossref.mkdir(parents=True)
    provider={
        "backend":"crossref","requested_doi":DOI,
        "parsed":{"doi_identity_match":True,"venue":journal,"title":"Native original"},
    }
    (crossref/"crossref.json").write_bytes(stable(provider))
    html=root/"url_capture_cache"/sha(URL.encode())[:24]
    html.mkdir(parents=True)
    raw=b"<html>Publisher article body (not yet scientifically evaluated)</html>"
    (html/"source.bin").write_bytes(raw)
    capture={"raw_sha256":sha(raw),"status":"FETCHED_TEXT"}
    (html/"capture.json").write_bytes(stable(capture))
    row={
        "schema":"MAI_KAIRON_NATIVE_PUBLISHER_WORK_SOURCE_v1",
        "route_id":"MAI-W12-001",
        "source_W12_sha256":sha(source.read_bytes()),
        "W12_venue":journal,
        "W12_meaning_version":initial["Версия"],
        "DOI":DOI,"original_publisher_url":URL,
        "crossref_DOI_identity_match":True,
        "crossref_source_receipt_sha256":sha(stable(provider)),
        "is_native_in_target_journal_by_Crossref":True,
        "publisher_host_observed_same":True,
        "publisher_html_state":"FETCHED_TEXT",
        "publisher_html_raw_sha256":sha(raw),
        "read_depth":"PUBLISHER_VISIBLE_HTML_TEXT_CAPTURED_NOT_SCHOLARLY_FULL_READ",
        "title":"Native original",
        "genre_peer_research_verified":False,
        "research_claims_evaluated":False,
        "venue_current_policy_verified":False,
        "artikl_author_decision":"HOLD",
        "journal_submission_actions":0,
    }
    dest=root/"routes"/"MAI-W12-001"/"native.json"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(stable(row))
    return source,snapshot,root,dest,html

def test_real_native_work_rendered_as_source_never_as_approved_scholarship(tmp_path):
    src,snap,root,_,_=setup(tmp_path)
    output=tmp_path/"board"
    report=materialize(src,snap,output,venue_native_root=root)
    assert report["venue_native_publication_source_count"]==1
    assert report["venue_native_scholarly_full_texts_certified"]==0
    assert report["ready_for_human_send"]==0
    route=json.loads((output/"routes"/"MAI-W12-001.json").read_text(encoding="utf-8"))
    assert route["venue_native_publisher_sources"]["count"]==1
    assert route["venue_native_publisher_sources"]["scholarly_full_texts_accepted"]==0
    assert "Native journal works: " in (output/"index.html").read_text(encoding="utf-8")
    assert (output/"venue_native"/"MAI-W12-001"/"index.json").is_file()

def test_publisher_html_mutation_rejected_by_board(tmp_path):
    src,snap,root,_,html=setup(tmp_path)
    (html/"source.bin").write_bytes(b"fake publisher source")
    with pytest.raises(ValueError,match="original HTML byte digest"):
        materialize(src,snap,tmp_path/"board",venue_native_root=root)

def test_fake_native_journal_approval_rejected(tmp_path):
    src,snap,root,record,_=setup(tmp_path)
    item=json.loads(record.read_text(encoding="utf-8"))
    item["genre_peer_research_verified"]=True
    record.write_text(json.dumps(item),encoding="utf-8")
    with pytest.raises(ValueError,match="cannot promote source"):
        materialize(src,snap,tmp_path/"board",venue_native_root=root)
