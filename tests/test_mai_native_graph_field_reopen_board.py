"""Kairon dashboard consumes immutable OpportunityGraphStore return events, no invented state."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from kairoskopion.kairon_provider.w12_packets import native_kairon_graph_world_return_for_route,sha

def stable(x):
    return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")

def location(base:Path,obj,kind:str):
    key=sha(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8"))
    return base/"kairon_provider"/"opportunity_graph"/kind/(key+".json")

def write(path:Path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(stable(obj))

def fixture(tmp:Path):
    route={"route_id":"MAI-W12-009","journal":"Studies in Philosophy and Education"}
    w12_sha="d"*64
    graph=tmp/"graph"
    field=tmp/"field"
    field.mkdir()
    original=field/"field_reopen_proposal.json"
    original.write_bytes(b'{"schema":"PROPOSED_SCIENTIFIC_RETURN_ONLY","author_decision":"HOLD"}\n')
    pins=[]
    for i in range(3):
        doi=f"10.1007/original{i}"
        url="https://link.springer.com/article/"+doi
        pin={
            "id":"MAI-A-EDUCATION:PUBLISHER:"+str(i),
            "revision":str(i)*24,
            "doi":doi,"source_url":url,"sha256":str(i)*64,
        }
        pins.append(pin)
        evidence={
            "kind":"Evidence","id":pin["id"],"revision":pin["revision"],
            "source_doi":doi,"source_ref":url,"source_content_sha256":pin["sha256"],
            "read_depth":"SECTIONS","qualified_for_article":False,
            "author_approved":False,"author_gate":"HOLD",
            "passage_anchors":[{"quote_sha256":sha(f"publisher quote {i}".encode())}],
        }
        write(location(graph,["Evidence",pin["id"],pin["revision"]],"records"),evidence)
    negid="MAI-A3A4:source-pinned-fixture:negative"
    reid=negid+"/reopen/L0"
    negative={
        "kind":"HUNT_RESULT","event_id":negid,
        "subject_id":route["route_id"],
        "result":"REJECT_GENERAL_CLAIM",
        "author_decision":"HOLD","world_mutation":"NONE",
        "external_send":"DISABLED",
        "source_evidence_pins":pins,
        "synthesis_receipt_sha256":sha(original.read_bytes()),
    }
    reopen={
        "kind":"FIELD_REOPEN_PROPOSAL","event_id":reid,
        "source_event_id":negid,"subject_id":route["route_id"],
        "author_gate":"AUTHOR_REVIEW_REQUIRED","semantic_mutation":"NONE",
    }
    write(location(graph,negid,"events"),negative)
    write(location(graph,reid,"events"),reopen)
    receipt={
        "schema":"MAI_ARTIKL_A3A4_NATIVE_GRAPH_REOPEN_EVENT_IMPORT_v1",
        "source_route_id":route["route_id"],"source_W12_sha256":w12_sha,
        "case_publisher_original_work_count":3,
        "science_anchor_count":6,"human_gate":"AUTHOR_REVIEW_REQUIRED",
        "world_mutations":0,"outbound_submissions":0,
        "article_seeds_automatically_created":0,
        "implementation":"EXISTING_OPPORTUNITY_GRAPH_STORE",
        "source_original_reopen_sha256":sha(original.read_bytes()),
        "source_evidence_pins":pins,
        "research_negative_event_id":negid,"research_field_reopen_event_id":reid,
    }
    write(graph/"MAI_A_EDUCATION_A3A4_GRAPH_WORLD_RETURN_RECEIPT.json",receipt)
    return route,w12_sha,field,graph,receipt,pins

def test_graph_events_visible_as_proposals_not_authored_revisions(tmp_path):
    route,sha_w12,field,graph,_,pins=fixture(tmp_path)
    out=tmp_path/"board"
    first=native_kairon_graph_world_return_for_route(route,out,sha_w12,field,graph)
    assert first["pinned_evidence_count"]==3
    assert first["world_mutations"]==0
    assert first["author_gate"]=="HOLD"
    assert first["status"]=="EXISTING_KAIRON_GRAPH_EVENTS_SOURCE_ATTESTED"
    assert (out/first["detail"]).is_file()
    assert (out/first["event_link"]).is_file()
    assert first==native_kairon_graph_world_return_for_route(route,out,sha_w12,field,graph)

def test_no_readable_native_event_blocks_graph_status(tmp_path):
    route,sha_w12,field,graph,rec,pins=fixture(tmp_path)
    event=location(graph,rec["research_field_reopen_event_id"],"events")
    event.unlink()
    with pytest.raises(ValueError,match="events lost"):
        native_kairon_graph_world_return_for_route(route,tmp_path/"board",sha_w12,field,graph)

def test_author_approved_science_cannot_emerge_via_graph(tmp_path):
    route,sha_w12,field,graph,rec,pins=fixture(tmp_path)
    receipt=graph/"MAI_A_EDUCATION_A3A4_GRAPH_WORLD_RETURN_RECEIPT.json"
    rec["world_mutations"]=1
    write(receipt,rec)
    with pytest.raises(ValueError,match="owner authority mismatch"):
        native_kairon_graph_world_return_for_route(route,tmp_path/"board",sha_w12,field,graph)

def test_forged_third_publisher_doi_blocks_graph(tmp_path):
    route,sha_w12,field,graph,rec,pins=fixture(tmp_path)
    path=location(graph,["Evidence",pins[-1]["id"],pins[-1]["revision"]],"records")
    item=json.loads(path.read_text(encoding="utf-8"))
    item["source_doi"]="10.1007/forged-foreign-paper"
    write(path,item)
    with pytest.raises(ValueError,match="Evidence authority"):
        native_kairon_graph_world_return_for_route(route,tmp_path/"board",sha_w12,field,graph)
