"""Source quoted Kairon policy candidates cannot fabricate journal decisions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_mai_kairon_policy_claims as stage
from scripts import fetch_mai_venue_pages as fetch
from tests.test_mai_w12_indago_bind import prepare

QUOTE="Abstracts of no more than 750 words should be submitted by Monday 2 November 2026 (by 18.00 GMT)."
TEXT=("Call for Papers. The politics of assessment. The journal Teaching in Higher Education " +
      "is inviting manuscripts for a special issue about assessment and social justice. "+
      QUOTE+" Please submit the abstract via the special issue online form. "+
      "Abstracts without strong theorisation will not be considered. "+
      "Full manuscripts are invited after abstract assessment.")

def fixture(tmp:Path):
    packets,_,_=prepare(tmp)
    source=stage.load(packets/"manifest.json")
    out=tmp/"capture"
    (out/"routes").mkdir(parents=True)
    copy=stage.load(packets/"routes"/"MAI-W12-001.json")
    copy["route"]["route_id"]="MAI-W12-002"
    stage.write(packets/"routes"/"MAI-W12-002.json",copy)
    for rid in ("MAI-W12-001","MAI-W12-002"):
        packet=stage.load(packets/"routes"/(rid+".json"))
        w=packet["route"]
        w["official_url"]="https://example.org/cfp/"+rid.lower()
        w.setdefault("journal","Example Journal")
        w.setdefault("family","A")
        w.setdefault("variant","A-NORM")
        packet["route"]=w
        stage.write(packets/"routes"/(rid+".json"),packet)
        url=w["official_url"]
        is_read=rid.endswith("001")
        web={
            "status":"FETCHED_TEXT" if is_read else "HTTP_REJECTED",
            "requested_url":url,"final_url":url,
            "raw_sha256":None,"visible_text_sha256":None,"visible_chars":0,
            "submission_policy_verified":False,"cfp_deadline_verified":False,
            "ai_authorship_policy_verified":False,"official_publisher_status_verified":False,
        }
        if is_read:
            directory=out/"url_capture_cache"/stage.sha(url.encode())[:24]
            directory.mkdir(parents=True)
            data=b"<html><body>"+TEXT.encode("utf-8")+b"</body></html>"
            (directory/"source.bin").write_bytes(data)
            (directory/"visible_text.txt").write_text(TEXT+"\n",encoding="utf-8")
            web["raw_sha256"]=stage.sha(data)
            web["visible_text_sha256"]=stage.sha(TEXT.encode("utf-8"))
            web["visible_chars"]=len(TEXT)
        capture={
            "schema":"MAI_KAIRON_OFFICIAL_VENUE_WEB_CAPTURE_v1",
            "route_id":rid,"W12_source_sha256":source["source_jsonl_sha256"],
            "journal":w["journal"],"family":w["family"],"variant":w["variant"],
            "w12_listed_official_url":url,
            "web_source":web,"web_source_receipt_sha256":stage.sha(stage.stable(web)),
            "source_read_state":web["status"],
            "official_rules_acceptance":"HOLD","author_gate":"CLOSED",
            "send_count":0,
        }
        stage.write(out/"routes"/(rid+".json"),capture)
    stage.write(out/"venue_acquisition_receipt.json",{
        "schema":"MAI_KAIRON_VENUE_WEB_ACQUISITION_BATCH_v1",
        "source_W12_sha256":source["source_jsonl_sha256"],
    })
    return packets,out

def model(rid:str,quote:str=QUOTE):
    return {"routes":[{
        "route_id":rid,"page_kind":"PUBLISHER_CFP_LANDING",
        "route_stage":"FORMAL_ABSTRACT_CFP_CANDIDATE",
        "issue_title":"The politics of assessment",
        "claims":[{
            "kind":"ABSTRACT_DEADLINE",
            "value":"2 November 2026, 18:00 GMT",
            "exact_quote":quote,
            "limitation":"CFP page snapshot, no independent currentness or full journal rights evaluation"
        }],
        "critical_unresolved_questions":"Need to verify official authority, updates, and authorship policy."
    }]}

def test_exact_provenance_and_hold(tmp_path):
    packets,capture=fixture(tmp_path)
    source=stage.read_sources(packets,capture,"MAI-W12-001")
    accepted=stage.validate(model("MAI-W12-001"),["MAI-W12-001"],{"MAI-W12-001":source})
    assert accepted[0]["cited_claims"][0]["quote_offset"]==TEXT.index(QUOTE)
    assert accepted[0]["cited_claims"][0]["passage_id"].startswith("MAI-W12-001#")
    assert accepted[0]["official_publisher_policy_accepted"] is False
    assert accepted[0]["web_page_currentness_accepted"] is False
    assert accepted[0]["human_author_gate"]=="HOLD"

def test_invented_deadline_quote_rejected(tmp_path):
    packets,capture=fixture(tmp_path)
    source=stage.read_sources(packets,capture,"MAI-W12-001")
    with pytest.raises(ValueError,match="model quote absent"):
        stage.validate(model("MAI-W12-001","Abstracts deadline 15 July 2029"),
                       ["MAI-W12-001"],{"MAI-W12-001":source})

def test_raw_html_tamper_rejected(tmp_path):
    packets,capture=fixture(tmp_path)
    w=stage.load(packets/"routes"/"MAI-W12-001.json")["route"]
    root=capture/"url_capture_cache"/stage.sha(w["official_url"].encode())[:24]
    (root/"source.bin").write_text("FORGED PAGE",encoding="utf-8")
    with pytest.raises(ValueError,match="raw publisher web response drift"):
        stage.read_sources(packets,capture,"MAI-W12-001")

def test_batch_complete_blocked_record_and_bit_identical_replay(tmp_path,monkeypatch):
    packets,capture=fixture(tmp_path)
    calls=[]
    def fake(provider,prompt,schema_file,response,logs,**kwargs):
        calls.append(provider)
        data=json.loads(prompt.split("UNTRUSTED ROUTE/PAGE DATA:",1)[1].strip())
        rid=data["route_inputs"][0]["route_id"]
        return model(rid),"claude"
    monkeypatch.setattr(stage,"call_structured",fake)
    out=tmp_path/"output"
    first=stage.run(packets,capture,out,limit=2,chunk_size=1)
    assert first["route_policy_citations_validated"]==1
    assert first["source_blocked_count"]==1
    assert first["route_evidence_claim_count"]==1
    assert first["total_model_calls_this_run"]==1
    a=(out/"routes"/"MAI-W12-001.json").read_bytes()
    b=(out/"routes"/"MAI-W12-002.json").read_bytes()
    second=stage.run(packets,capture,out,limit=2,chunk_size=1)
    assert second["total_model_calls_this_run"]==0
    assert second["missing_routes"]==[]
    assert (out/"routes"/"MAI-W12-001.json").read_bytes()==a
    assert (out/"routes"/"MAI-W12-002.json").read_bytes()==b
    assert calls==["claude"]

def test_only_declared_route_ids_are_accepted(tmp_path):
    packets,capture=fixture(tmp_path)
    original=stage.read_sources(packets,capture,"MAI-W12-001")
    with pytest.raises(ValueError,match="route set mismatch"):
        stage.validate(model("MAI-W12-050"),["MAI-W12-001"],
                       {"MAI-W12-001":original})

def test_no_formal_route_from_contextless_claim(tmp_path):
    packets,capture=fixture(tmp_path)
    original=stage.read_sources(packets,capture,"MAI-W12-001")
    value=model("MAI-W12-001")
    value["routes"][0]["claims"]=[]
    with pytest.raises(ValueError,match="formal abstract stage claimed without"):
        stage.validate(value,["MAI-W12-001"],{"MAI-W12-001":original})


def _unfinished_model_chunk(tmp_path,mutate=False):
    from scripts import rescue_mai_kairon_model_chunks as recovery
    packets,capture=fixture(tmp_path)
    data=stage.read_sources(packets,capture,"MAI-W12-001")
    envelope={
        "schema":"MAI_KAIRON_WEB_POLICY_INPUT_v1",
        "source_W12_sha256":stage.load(packets/"manifest.json")["source_jsonl_sha256"],
        "route_inputs":[stage.prompt_item(data)],
    }
    key=stage.sha(stage.stable(envelope))
    folder=tmp_path/"output"
    chunk=folder/"chunks"/("failed_001_"+key[:12])
    stage.write(chunk/"input.json",envelope)
    row=model("MAI-W12-001")
    if mutate:row["routes"][0]["claims"][0]["exact_quote"]="Invented special issue editor quote"
    stage.write(chunk/"model_output.json",row)
    return packets,capture,folder

def test_recovery_reuses_individually_valid_model_row_without_new_provider(tmp_path,monkeypatch):
    from scripts.rescue_mai_kairon_model_chunks import salvage
    packets,capture,output=_unfinished_model_chunk(tmp_path)
    result=salvage(packets,capture,output)
    assert result["zero_new_provider_calls"] is True
    assert result["salvaged_valid_source_quoted_route_ids"]==["MAI-W12-001"]
    route=stage.load(output/"routes"/"MAI-W12-001.json")
    assert stage.check_cached_policy_record(stage.read_sources(packets,capture,"MAI-W12-001"),output)==route
    monkeypatch.setattr(stage,"call_structured",lambda *a,**kw:(_ for _ in ()).throw(AssertionError("unexpected external provider")))
    rerun=stage.run(packets,capture,output,limit=2,chunk_size=1)
    assert rerun["total_model_calls_this_run"]==0
    assert rerun["route_policy_citations_validated"]==1
    assert rerun["replayed_verified_route_count"]==1

def test_recovery_never_salvages_fake_publisher_citation(tmp_path):
    from scripts.rescue_mai_kairon_model_chunks import salvage
    packets,capture,output=_unfinished_model_chunk(tmp_path,mutate=True)
    result=salvage(packets,capture,output)
    assert result["salvaged_valid_source_quoted_route_ids"]==[]
    assert result["still_invalid_route_claims"][0]["route_id"]=="MAI-W12-001"
    assert not (output/"routes"/"MAI-W12-001.json").exists()
