"""W12 bounded scholarly route: real graph, synthetically pinned carrier evidence."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import copy
import pytest
from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from kairoskopion.services.trm073_w12_route_stage import (
    stage_w12_research_route, readback_w12_research_route,
)


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def fixture_route(tmp_path: Path):
    stage = tmp_path / "factory"
    graph = OpportunityGraphStore(stage)
    src = tmp_path / "c04.txt"
    text = (
        "Title of synthetic industrial talk\n"
        "Existing industrial relationships are not the same as an emerging"
        " division of labor; new shared instruments and repeatable functions must form.\n"
    )
    src.write_bytes(text.encode("utf-8"))
    source_id="drive:SYNTH-C04"
    ledger = stage / "talk_corpora" / "CASE-SYNTH" / "case_ledger.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({
        "case_id": "CASE-SYNTH",
        "source_snapshots": [{
            "source_id": source_id, "version": "v0.4",
            "key": "C04", "family": "C",
            "content_sha256": _sha(src.read_bytes()),
            "author_state": "NOT_VERIFIED",
        }],
    }), encoding="utf-8")
    graph.put("Evidence", {
        "id": "synthetic-source-evidence",
        "revision": "r1",
        "source_ref": source_id,
        "source_kind": "SPEECH_SCRIPT",
        "read_depth": "SECTIONS",
        "passage_anchors": [],
    })
    graph.append_event({
        "event_id":"CASE-SYNTH:W3:route:C-TEST",
        "kind":"SCHOLARLY_ROUTE_CHALLENGE",
        "route_candidate_id":"C-TEST",
        "subject_id":"HEAD-03",
        "journal_id":"journal-RMS-SYNTH",
        "source_ref":"doi:10.1007/synth",
        "opponent_resolved":True,
        "w12_equivalent":False,
    })
    graph.append_event({
        "event_id":"CASE-SYNTH:W3:HEAD-03:DISCOVERY-RETURN",
        "kind":"SOURCE_CONTRADICTION",
        "subject_id":"HEAD-03",
        "source_ref":source_id,
        "original_source_binding":{
            "source_id":source_id,
            "version":"v0.4",
            "content_sha256":_sha(src.read_bytes()),
            "binding_verification":"VERIFIED_BYTES",
        },
    })

    artifact_root = tmp_path / "provider"
    artifact_root.mkdir()
    pages = {
        "SCOPE": (
            "<html><body><h1>Aims and scope</h1><p>"
            "We publish rigorous original business research, conceptual "
            "and empirical work across different industrial settings."
            "</p></body></html>"
        ),
        "GUIDELINES": (
            "<html><body><h1>Submission policy</h1><p>"
            "Regular manuscripts are submitted via a publisher portal"
            " and must not be simultaneously under consideration elsewhere."
            "</p></body></html>"
        ),
        "OPPONENT": (
            "<html><body><h1>A published study</h1><p>"
            "The published study uses surveys of individual managers"
            " to establish configurations of opportunity exploitation."
            "</p><p>doi:10.1007/synth</p></body></html>"
        ),
    }
    caps={}
    for key,html in pages.items():
        path=artifact_root/(key+".html")
        path.write_bytes(html.encode("utf-8"))
        sha=_sha(path.read_bytes())
        caps[key]={
            "status":"validated", "validation":{"valid":True,"reason":"html_shape_ok"},
            "path":str(path), "sha256":sha, "readback_sha256":sha,
            "content_type":"text/html",
            "url":"https://link.springer.com/"+key.lower(),
        }
    cap_path=artifact_root/"captures.json"
    cap_path.write_text(json.dumps(caps),encoding="utf-8")
    lengthy_en = " ".join(["A distinct industrial research question compares lasting collective "
        "standards with temporary individual opportunity exploitation."]*9)
    lengthy_ru = " ".join(["Исследовательская постановка различает воспроизводимое совместное средство "
        "и временную индивидуальную возможность действия."]*9)
    analysis = {name:"A negative case could refute this narrow claim, and historical "
        "multiple case evidence must be collected before any manuscript or author approval." for name in (
            "strongest_objection","source_distinction","empirical_falsifier",
            "methodological_plan","admissible_source_change","negative_evidence"
        )}
    packet={
        "schema":"TRM073_W12_SOURCE_VENUE_ROUTE_INPUT_V1",
        "case_id":"CASE-SYNTH","wave_id":"W4-TEST",
        "route_candidate_id":"C-TEST","head_id":"HEAD-03",
        "claim_version_id":"C04-v0.4-CLAIM-SYNTH",
        "journal_name":"Review of Managerial Science",
        "journal_id":"journal-RMS-SYNTH",
        "route_type":"REGULAR_ROLLING","venue_submission_type":"REGULAR_MANUSCRIPT",
        "current_cfp":False,"deadline":None,"author_gate":"HOLD",
        "author_decision":"HOLD","coauthor_consent":"UNVERIFIED",
        "rights_gate":"OWNER_REVIEW_PENDING",
        "scientific_status":"OPPONENT_GROUNDED_AUTHOR_REVIEW_PENDING",
        "original_source":{
            "source_id":source_id,"source_version":"v0.4",
            "path":str(src),"sha256":_sha(src.read_bytes()),
            "anchor_line":2,"anchor_quote":text.splitlines()[1],
        },
        "capture_manifest":str(cap_path),
        "official_host":"link.springer.com",
        "official_evidence":{
            kind:{"capture_key":key,"url":caps[key]["url"],
                  "anchor_quote":pages[key].split("<p>")[1].split("</p>")[0]}
            for kind,key in (("scope","SCOPE"),("submission_policy","GUIDELINES"),
                             ("published_opponent","OPPONENT"))
        },
        "opponent_doi":"10.1007/synth",
        "opponent_url":"https://link.springer.com/opponent",
        "publisher_observed_date":"2026-10-20",
        "target_thesis":{"en":lengthy_en,"ru":lengthy_ru},
        "opponent_analysis":analysis,
        "article_seed_created":False,"world_mutation":False,"external_send":"DISABLED",
    }
    packet["opponent_url"]=caps["OPPONENT"]["url"]
    file=tmp_path/"packet.json"
    file.write_text(json.dumps(packet,ensure_ascii=False),encoding="utf-8")
    return packet,file,stage,src,caps,cap_path


def test_w12_research_route_provenance_held_and_replay(tmp_path):
    _, path, stage, _, _, _ = fixture_route(tmp_path)
    a=stage_w12_research_route(path,stage)
    b=stage_w12_research_route(path,stage)
    assert a["receipt_sha256"]==b["receipt_sha256"]
    assert a["counts"]["W12_EQUIVALENT_HELD"]==1
    assert a["readback"]["verified"]
    graph=OpportunityGraphStore(stage)
    assert len(graph.list_records("HuntTrace"))==1
    assert graph.list_records("OpportunityRoute")==[]
    assert graph.list_records("ArticleSeed")==[]
    assert graph.list_records("World")==[]


def test_fails_if_source_byte_changes_after_admission(tmp_path):
    _, path, stage, src, _, _ = fixture_route(tmp_path)
    stage_w12_research_route(path,stage)
    src.write_text(src.read_text()+"fabricated addition\n",encoding="utf-8")
    with pytest.raises(ValueError,match="SHA mismatch"):
        readback_w12_research_route(path,stage)


def test_fails_if_publisher_policy_html_mutates(tmp_path):
    _, path, stage, _, caps, _ = fixture_route(tmp_path)
    stage_w12_research_route(path,stage)
    Path(caps["GUIDELINES"]["path"]).write_text("fake rules",encoding="utf-8")
    with pytest.raises(ValueError,match="SHA mismatch"):
        readback_w12_research_route(path,stage)


def test_fails_if_route_source_not_verified_by_actual_w3(tmp_path):
    _, path, stage, _, _, _ = fixture_route(tmp_path)
    graph=OpportunityGraphStore(stage)
    event=next(x for x in graph.replay_events() if x.get("kind")=="SOURCE_CONTRADICTION")
    for f in graph.events.glob("*.json"):
        obj=json.loads(f.read_text(encoding="utf-8"))
        if obj.get("event_id")==event["event_id"]:
            obj["original_source_binding"]["binding_verification"]="DIGEST_ONLY"
            f.write_text(json.dumps(obj),encoding="utf-8")
    with pytest.raises(ValueError,match="binding not verified"):
        stage_w12_research_route(path,stage)


def test_fails_if_author_or_cfp_authority_widened(tmp_path):
    packet,path,stage,_,_,_=fixture_route(tmp_path)
    packet["author_gate"]="ACCEPT"
    packet["current_cfp"]=True
    path.write_text(json.dumps(packet),encoding="utf-8")
    with pytest.raises(ValueError,match="author approval"):
        stage_w12_research_route(path,stage)


def test_fails_if_scholarly_comparator_wrong_doi(tmp_path):
    packet,path,stage,_,_,_=fixture_route(tmp_path)
    packet["opponent_doi"]="10.1007/wrong"
    path.write_text(json.dumps(packet),encoding="utf-8")
    with pytest.raises(ValueError,match="opponent DOI mismatch"):
        stage_w12_research_route(path,stage)


def test_prevents_same_pair_rewrite_without_mutating_prior_graph(tmp_path):
    packet,path,stage,_,_,_=fixture_route(tmp_path)
    a=stage_w12_research_route(path,stage)
    packet["opponent_analysis"]["strongest_objection"]+=" Additional claim."
    path.write_text(json.dumps(packet),encoding="utf-8")
    with pytest.raises(ValueError,match="already pins different input bytes"):
        stage_w12_research_route(path,stage)
    assert len(OpportunityGraphStore(stage).list_records("HuntTrace"))==1
    assert Path(a["receipt_path"]).is_file()


def test_unsupported_future_observation_date_fails_closed(tmp_path):
    packet,path,stage,_,_,_=fixture_route(tmp_path)
    packet["publisher_observed_date"]="2099-01-01"
    path.write_text(json.dumps(packet),encoding="utf-8")
    with pytest.raises(ValueError,match="future"):
        stage_w12_research_route(path,stage)



def test_abstract_only_opponent_page_cannot_masquerade_as_fulltext(tmp_path):
    packet,path,stage,_,_,_=fixture_route(tmp_path)
    packet["official_evidence"]["published_opponent"]["read_depth"]="ABSTRACT_ONLY"
    path.write_text(json.dumps(packet),encoding="utf-8")
    out=stage_w12_research_route(path,stage)
    stored=json.loads(Path(out["receipt_path"]).read_text(encoding="utf-8"))
    assert stored["opponent_read_depth"]=="ABSTRACT_ONLY_NOT_CERTIFIED_FULL_TEXT"
    assert stored["counts"]["DEEP_QUALIFIED"]==0
    assert stored["counts"]["W12_EQUIVALENT_HELD"]==1


def test_unattested_fulltext_opponent_claim_fails_before_route_write(tmp_path):
    packet,path,stage,_,_,_=fixture_route(tmp_path)
    packet["official_evidence"]["published_opponent"]["read_depth"]="FULL_TEXT_CERTIFIED"
    path.write_text(json.dumps(packet),encoding="utf-8")
    with pytest.raises(ValueError,match="opponent read depth not supported"):
        stage_w12_research_route(path,stage)
    assert OpportunityGraphStore(stage).list_records("HuntTrace")==[]
