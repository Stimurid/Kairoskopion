"""Full task/case-bound Indago hunt lead transport with no false citations."""
import json

import pytest

from kairoskopion.services import citation_indago_hunt_leads as bridge
from kairoskopion.services.citation_intake_z0 import persist_audit

TASK="TRM_CITE_G6_R3_LIVE_SOURCE_20261023"
HID="h-20261023T000134Z-trm_cite_g6_r3_live_source_20261023-test001"


def _setup(tmp_path):
    manuscript=tmp_path/"synthetic.md"
    manuscript.write_text("Research provenance claim (Frolov 2026).\n",encoding="utf-8")
    _,audit=persist_audit(manuscript,tmp_path/"z0")
    queue=audit.parent/"citation_work_orders.jsonl"
    order=json.loads(queue.read_text(encoding="utf-8").splitlines()[0])
    meta={
        "hunt_id":HID,"task_id":TASK,"status":"PARTIAL",
        "finished_at":"2026-10-23T01:10:00Z",
        "stop_reason":"PROVIDER_SATURATION",
        "counts":{"new_verified":2,"hypotheses":1}}
    candidates={
        "hunt_id":HID,
        "new_verified":[{
            "title":"Chubarov article retrieved metadata",
            "url":"https://doi.org/10.2298/FID2204765C",
            "identifiers":["doi:10.2298/FID2204765C"],
            "why_relevant":"Current P3 requires original full text",
            "evidence_ids":["E1.3"],
            "is_hypothesis":False,
            "provenance":{"provider":"crossref","evidence_id":"E1.3"}
        },{
            "title":"Same known work (duplicate record)",
            "url":"https://publisher.example.org/article/123",
            "identifiers":["doi:10.2298/FID2204765C"],
            "why_relevant":"Duplicate discovery",
            "evidence_ids":["E2.1"],
            "is_hypothesis":False
        }],
        "new_unverified":[],
        "hypotheses":[{
            "title":"Possible Logos Benjamin predecessor",
            "url":None,"identifiers":[],
            "why_relevant":"Only a title",
            "is_hypothesis":True
        }],
        "known_rediscovered":[],
        "not_found":[{"query":"DOISerbia publisher PDF","status":"TIMEOUT"}],
        "unexecuted_provider_requests":["unvisited source due wave cap"],
    }
    m=tmp_path/"meta.json"
    c=tmp_path/"candidates.json"
    m.write_text(json.dumps(meta,ensure_ascii=False),encoding="utf-8")
    c.write_text(json.dumps(candidates,ensure_ascii=False),encoding="utf-8")
    return audit,queue,order,m,c,meta,candidates


def _run(tmp_path, setup=None):
    a,q,order,m,c,_,_=setup or _setup(tmp_path)
    return bridge.import_hunt_leads(
        audit_path=a,queue_path=q,meta_path=m,candidates_path=c,
        work_order_id=order["work_order_id"],expected_task_id=TASK,
        output_dir=tmp_path/"leads")


def test_stages_three_real_shape_candidates_without_scientific_promotion(tmp_path):
    result=_run(tmp_path)
    assert result.replayed is False
    assert result.receipt["lead_count"]==3
    assert result.receipt["bucket_counts"]["new_verified"]==2
    assert result.receipt["bucket_counts"]["hypotheses"]==1
    assert len(result.receipt["not_found"])==1
    assert len(result.receipt["unexecuted_provider_requests"])==1
    assert all(x["read_depth"]=="PROVIDER_ITEM_NOT_FULLTEXT" for x in result.leads)
    assert all(x["source_evidence"]==[] for x in result.leads)
    assert all(x["source_bytes_attested"] is False for x in result.leads)
    assert all(x["publication_ready"] is False for x in result.leads)
    assert all(x["V1_V5"]==["NOT_CHECKED"]*5 for x in result.leads)
    assert result.receipt["R1_bytes_attested"] is False


def test_duplicate_identity_is_preserved_with_explicit_pointer(tmp_path):
    result=_run(tmp_path)
    assert result.leads[1]["duplicate_of"]==result.leads[0]["lead_id"]
    assert result.leads[2]["duplicate_of"] is None
    assert len({x["lead_id"] for x in result.leads})==3


def test_historical_provider_verified_never_means_fulltext(tmp_path):
    result=_run(tmp_path)
    assert result.leads[0]["provider_classification"]=="PROVIDER_GROUNDED_ITEM"
    assert result.leads[0]["work_identity_verified"] is False
    assert result.leads[0]["edition_identity_verified"] is False
    assert result.leads[0]["passage_verified"] is False
    assert result.leads[0]["next_action"]=="CHECK_OWNER_LIBRARY_THEN_EXACT_WORK_FULLTEXT"


def test_metadata_lead_replay_is_byte_identical(tmp_path):
    setup=_setup(tmp_path)
    first=_run(tmp_path,setup)
    second=_run(tmp_path,setup)
    assert second.replayed is True
    assert second.receipt["replay_status"]=="IDEMPOTENT_REPLAY"
    assert first.receipt["import_id"]==second.receipt["import_id"]


def test_wrong_task_scope_fails_before_write(tmp_path):
    a,q,order,m,c,meta,_=_setup(tmp_path)
    meta["task_id"]="OTHER_HUNT"
    m.write_text(json.dumps(meta),encoding="utf-8")
    with pytest.raises(bridge.HuntLeadImportRefusal) as ctx:
        _run(tmp_path,(a,q,order,m,c,meta,{}))
    assert ctx.value.code=="TASK_SCOPE_MISMATCH"


def test_mismatched_hunt_id_fail_closed(tmp_path):
    a,q,order,m,c,meta,cs=_setup(tmp_path)
    cs["hunt_id"]="h-different"
    c.write_text(json.dumps(cs),encoding="utf-8")
    with pytest.raises(bridge.HuntLeadImportRefusal) as ctx:
        _run(tmp_path,(a,q,order,m,c,meta,cs))
    assert ctx.value.code=="HUNT_IDENTITY_MISMATCH"


def test_running_hunt_not_imported_as_completed_evidence(tmp_path):
    a,q,order,m,c,meta,cs=_setup(tmp_path)
    meta["status"]="RUNNING"
    meta["finished_at"]=None
    m.write_text(json.dumps(meta),encoding="utf-8")
    with pytest.raises(bridge.HuntLeadImportRefusal) as ctx:
        _run(tmp_path,(a,q,order,m,c,meta,cs))
    assert ctx.value.code=="HUNT_NOT_COMPLETE"


def test_unchanged_task_reused_with_mutated_candidates_is_refused(tmp_path):
    setup=_setup(tmp_path)
    _run(tmp_path,setup)
    a,q,order,m,c,meta,cs=setup
    cs["new_verified"][0]["title"]="Changed after import"
    c.write_text(json.dumps(cs),encoding="utf-8")
    with pytest.raises(bridge.HuntLeadImportRefusal) as ctx:
        _run(tmp_path,(a,q,order,m,c,meta,cs))
    assert ctx.value.code=="IMPORT_CONFLICT"


def test_orphan_work_order_is_denied(tmp_path):
    a,q,_order,m,c,_,_=_setup(tmp_path)
    with pytest.raises(bridge.HuntLeadImportRefusal) as ctx:
        bridge.import_hunt_leads(
            audit_path=a,queue_path=q,meta_path=m,candidates_path=c,
            work_order_id="unknown_work_order",expected_task_id=TASK,
            output_dir=tmp_path/"leads")
    assert ctx.value.code=="WORK_ORDER_NOT_FOUND"


def test_hypothesis_not_auto_triggering_fulltext_certificate(tmp_path):
    result=_run(tmp_path)
    h=result.leads[-1]
    assert h["provider_bucket"]=="hypotheses"
    assert h["next_action"]=="VERIFY_BIBLIOGRAPHIC_IDENTITY"
    assert h["provider_hypothesis"] is True
    assert h["source_evidence"]==[]


def test_source_sha_is_bound_to_z0_queue(tmp_path):
    result=_run(tmp_path)
    # Every imported lead must keep the same immutable manuscript digest.
    assert len({x["manuscript_sha256"] for x in result.leads}) == 1
    assert len(result.leads[0]["manuscript_sha256"]) == 64
