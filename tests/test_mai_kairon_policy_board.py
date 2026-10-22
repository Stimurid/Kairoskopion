"""The 53-card board may display quote-attested Kairon candidates, never approve them."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from kairoskopion.kairon_provider.w12_packets import materialize,sha,kairon_policy_candidates_for_route
from tests.test_mai_venue_board import make_world,stable

def build(tmp_path:Path):
    src,snapshot,cap,rec=make_world(tmp_path)
    output=tmp_path/"policy"
    rid="MAI-W12-001"
    source_id=sha(src.read_bytes())
    w12=json.loads(src.read_text(encoding="utf-8").splitlines()[0])["source_fields"]
    phrase="Authentic publisher webpage text collected from verified HTTP response."
    value={
        "kind":"ABSTRACT_CHANNEL",
        "value":"A hypothetical CFP submission channel only, not authorized",
        "exact_quote":phrase,"limitation":"No actual publisher rules certified",
        "quote_offset":0,"passage_id":rid+"#"+sha(phrase.encode())[:16],
        "source_read_depth":"BOUNDED_VISIBLE_WEB_HTML",
        "candidate_not_authoritatively_confirmed":True,
    }
    reviewed={
        "route_id":rid,"route_type_candidate":"FORMAL_ABSTRACT_CFP_CANDIDATE",
        "cited_claims":[value],"page_kind_candidate":"PUBLISHER_CFP_LANDING",
        "issue_title_model_guess":"Hypothetical",
        "unresolved":"Actual instructions unavailable",
        "web_page_currentness_accepted":False,
        "official_publisher_policy_accepted":False,
        "journal_send_count":0,"human_author_gate":"HOLD",
    }
    input_key="a"*64
    (output/"chunks"/"test").mkdir(parents=True)
    operation={
        "schema":"MAI_KAIRON_POLICY_OPERATION_RECEIPT_v1",
        "input_digest":input_key,"all_policy_authority_gates":"HOLD",
        "human_author_gate":"HOLD","external_submission_count":0,
        "verified_policy_claims":[reviewed],
    }
    op=output/"chunks"/"test"/"accepted.json"
    op.write_bytes(stable(operation))
    row={
        "schema":"MAI_KAIRON_QUOTE_ANCHORED_POLICY_CANDIDATE_v1",
        "route_id":rid,"source_W12_sha256":source_id,
        "captured_web_receipt_sha256":sha(stable(rec)),
        "status":"QUOTED_POLICY_CANDIDATES_PROVISIONAL",
        "web_source_state":"FETCHED_TEXT",
        "route_type_candidate":"FORMAL_ABSTRACT_CFP_CANDIDATE",
        "cited_claims":[value],
        "model_operation_input_digest":input_key,
        "model_operation_receipt_sha256":sha(op.read_bytes()),
        "official_publisher_policy_accepted":False,
        "web_page_currentness_accepted":False,
        "journal_send_count":0,"human_author_gate":"HOLD",
    }
    policy=output/"routes"/(rid+".json")
    policy.parent.mkdir(parents=True)
    policy.write_bytes(stable(row))
    return src,snapshot,cap,output,policy

def test_quote_attested_policy_candidate_visible_no_authority(tmp_path):
    src,snap,cap,model,policy=build(tmp_path)
    dest=tmp_path/"board"
    result=materialize(src,snap,dest,venue_web_root=cap,venue_policy_root=model)
    assert result["records"]==2
    assert result["venue_policy_candidate_count"]==1
    assert result["venue_policy_cited_claim_count"]==1
    assert result["venue_policies_certified_count"]==0
    assert result["ready_for_human_send"]==0
    card=json.loads((dest/"routes"/"MAI-W12-001.json").read_text(encoding="utf-8"))
    assert card["venue_policy_candidates"]["authority_gate"]=="HOLD"
    assert "Цитаты и требования" in (dest/"index.html").read_text(encoding="utf-8")
    assert (dest/"policies"/"MAI-W12-001.json").read_bytes()==policy.read_bytes()

def test_tampered_original_publisher_page_refused(tmp_path):
    src,snap,cap,model,policy=build(tmp_path)
    urls=list((cap/"url_capture_cache").glob("*/visible_text.txt"))
    assert len(urls)==1
    urls[0].write_text("Forged page.\n",encoding="utf-8")
    with pytest.raises(ValueError,match="source text raw passage SHA mismatch"):
        materialize(src,snap,tmp_path/"board",venue_web_root=cap,venue_policy_root=model)

def test_semantic_promotion_flag_rejected(tmp_path):
    src,snap,cap,model,policy=build(tmp_path)
    body=json.loads(policy.read_text(encoding="utf-8"))
    body["official_publisher_policy_accepted"]=True
    policy.write_text(json.dumps(body),encoding="utf-8")
    with pytest.raises(ValueError,match="authority promotion"):
        materialize(src,snap,tmp_path/"board",venue_web_root=cap,venue_policy_root=model)

def test_altered_model_receipt_rejected(tmp_path):
    src,snap,cap,model,policy=build(tmp_path)
    data=json.loads(policy.read_text(encoding="utf-8"))
    data["cited_claims"][0]["exact_quote"]="fake added text"
    policy.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError,match="disagree with producer evidence"):
        materialize(src,snap,tmp_path/"board",venue_web_root=cap,venue_policy_root=model)
