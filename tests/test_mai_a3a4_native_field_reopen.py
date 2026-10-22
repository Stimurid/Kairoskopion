"""Three independent native arguments are prerequisites for a World-return candidate."""
from __future__ import annotations
from pathlib import Path
import json
import pytest

from scripts import run_mai_native_scholarly_read as read
from scripts import run_mai_a_education_field_reopen as field
from tests.test_mai_native_scholarly_read import fixture, review

def built(tmp:Path,monkeypatch):
    packets,native,book=fixture(tmp)
    def provider(prompt,schema_file,out,**kwargs):
        source=json.loads(prompt.split("UNTRUSTED SCHOLARLY MATERIAL:",1)[1].strip())
        return review(source),"TEST_SOURCE_LINKED_MODEL"
    monkeypatch.setattr(read,"request",provider)
    source=tmp/"scientific"
    result=read.run(packets,native,book,source,limit=3)
    assert result["machine_source_grounded_papers_reviewed"]==3
    return packets,native,book,source

def proposed(data):
    sample=("The delegated activity and its epistemic success do not themselves imply "
            "legal or philosophical entitlement to revise the public educational criterion. "
            "To distinguish these it is necessary to identify the body competent to authorize "
            "a change, the right of appeal, and a genuinely falsifying comparison case.")
    papers=data["three_published_native_paper_evidence"]
    items=[{
       "doi":p["doi"],
       "role_against_A3A4":"The paper directly challenges the claim that an educational norm may be changed by efficiency. "+sample,
       "retained_MAI_difference_if_any":"The author's residual position requires second-order authority and a contestable governance act. "+sample,
    } for p in papers]
    anchors=[{"doi":p["doi"],"quote_sha256":p["source_anchors"][0]["quote_sha256"],
              "why_this_proves_the_claim":"The published source demonstrates a stated normative limitation of algorithmic activity. "+sample}
             for p in papers]
    return {
        "route_id":"MAI-W12-009","decision_candidate":"REVISE_SOURCE_CANDIDATE",
        "three_source_distinctions":items,
        **{k:sample for k in field.FIELDS},
        "source_anchor_ids":anchors,
    }

def test_real_3_paper_research_returns_only_reversible_author_proposal(tmp_path,monkeypatch):
    packets,native,book,reads=built(tmp_path,monkeypatch)
    source=field.build_input(packets,native,book,reads)
    assert len(source["three_published_native_paper_evidence"])==3
    parsed=field.validate_synthesis(proposed(source),source)
    assert parsed["field_reopen_proposal_kind"]=="FIELD_REOPEN_PROPOSAL"
    assert parsed["author_world_change_approved"] is False
    assert parsed["journal_venue_policy_certified"] is False
    assert parsed["external_send_count"]==0
    calls=[]
    def provider(prompt,schema_file,output,**kw):
        calls.append(True)
        body=json.loads(prompt.split("UNTRUSTED SOURCED RESEARCH MATERIAL:",1)[1].strip())
        result=proposed(body)
        field.write(output/"model_output.json",result)
        (output/"model_stdout.log").write_text("model generated fixture\n",encoding="utf-8")
        return result
    monkeypatch.setattr(field,"call_provider",provider)
    target=tmp_path/"proposals"
    first=field.execute(packets,native,book,reads,target)
    assert first["model_calls"]==1
    assert first["proposal"]["source_anchor_count"]==3
    second=field.execute(packets,native,book,reads,target)
    assert second["state"]=="CACHED"
    assert second["model_calls"]==0
    assert len(calls)==1

def test_invented_third_paper_anchor_blocks_world_return(tmp_path,monkeypatch):
    packets,native,book,reads=built(tmp_path,monkeypatch)
    source=field.build_input(packets,native,book,reads)
    fake=proposed(source)
    fake["source_anchor_ids"][-1]["quote_sha256"]="e"*64
    with pytest.raises(ValueError,match="invented cross-paper citation"):
        field.validate_synthesis(fake,source)

def test_two_sources_cannot_certify_three_paper_field_reopen(tmp_path,monkeypatch):
    packets,native,book,reads=built(tmp_path,monkeypatch)
    source=field.build_input(packets,native,book,reads)
    fake=proposed(source)
    fake["three_source_distinctions"].pop()
    with pytest.raises(ValueError,match="one or more authentic"):
        field.validate_synthesis(fake,source)

def test_original_publisher_source_drift_cannot_reuse_model(tmp_path,monkeypatch):
    packets,native,book,reads=built(tmp_path,monkeypatch)
    source=field.build_input(packets,native,book,reads)
    doi=source["three_published_native_paper_evidence"][0]["doi"]
    receipt=reads/"papers"/field.sha(doi.encode("utf-8"))[:20]/"accepted_challenge.json"
    x=field.load(receipt)
    x["verified_review"]["paper_thesis"]="CLAIM CHANGED WITHOUT ANOTHER ARTICLE READ"
    field.write(receipt,x)
    with pytest.raises(ValueError,match="source/model review provenance|quote provenance altered"):
        field.build_input(packets,native,book,reads)
