"""Registered Artikl post-D15 decision: grounded source pins, self-choice and HOLD."""
from pathlib import Path
from unittest import mock
import pytest

from kairoskopion.kairon_provider import native_d15_artikl_decision as m
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked


def response(choice:str="MORE_RESEARCH",rev:bool=False)->dict:
    return {
      "schema":m.SCHEMA,"agent_id":"artikl",
      "current_release":"ARTIKL 1.0.0-rc9",
      "canon_read":"PARTIAL",
      "manuscript_sha256":m.MANUSCRIPT_SHA,
      "whitecrow_sha256":m.WHITE_SHA,
      "source_audit_sha256s":[sh for _,sh in m.AUDITS],
      "decision":choice,"reason":"Source overlap requires further nearest work",
      "closest_anticipated_contributions":[],
      "potential_independently_testable_delta":[],
      "next_sources_and_tests":["Full primary commissioning nearest literature"],
      "revision_allowed_now":rev,
      "scientific_novelty_accepted":False,"d25_manuscript_go":False,
      "author_gate":"HOLD","send":False,"world_mutation":False,
    }


def test_preflight_three_actual_originals_and_real_d24():
    report,proof,audits=m.preflight()
    assert len(audits)==3
    assert report["coverage_status"]=="PARTIAL"
    assert len(report["primary_passages"])>=60
    assert proof["whitecrow_actual_module_invoked"] is True


def test_manifest_hash_tamper_blocks_before_native_agent(monkeypatch,tmp_path):
    monkeypatch.setattr(m,"WHITE_SHA","0"*64)
    with mock.patch.object(m,"native_call",side_effect=AssertionError("agent must not run")):
        with pytest.raises(EvidenceBlocked):
            m.run(tmp_path)


def test_author_choice_respected_without_autorevision(tmp_path):
    fake=response()
    att={"gateway_sha256":"a"*64,"tool_summary":{"calls":1},"gateway_run_id":"run-test"}
    with mock.patch.object(m,"native_call",return_value=fake) as call,\
         mock.patch.object(m,"_native_stage_attestation",return_value=att):
        receipt=m.run(tmp_path)
        assert call.call_count==1
        assert receipt["decision"]=="MORE_RESEARCH"
        assert receipt["revision_allowed_now"] is False
        assert receipt["author_gate"]=="HOLD"
        assert receipt["send"] is False
        assert receipt["no_autonomous_rewrite"] is True
    with mock.patch.object(m,"native_call",side_effect=AssertionError("no repeat")):
        replay=m.run(tmp_path)
    assert receipt==replay


@pytest.mark.parametrize("malformed",[
    {"decision":"REVISION_CANDIDATE","revision_allowed_now":False},
    {"decision":"MORE_RESEARCH","revision_allowed_now":True},
    {"scientific_novelty_accepted":True},
    {"d25_manuscript_go":True},
    {"send":True},
    {"world_mutation":True},
    {"whitecrow_sha256":"0"*64},
])
def test_forged_permission_fails_even_if_gateway_claims_ok(malformed,tmp_path):
    obj=dict(response(),**malformed)
    with mock.patch.object(m,"native_call",return_value=obj),\
         mock.patch.object(m,"_native_stage_attestation",
                           side_effect=AssertionError("should not reach")):
        with pytest.raises(EvidenceBlocked,match="boundary_or_identity"):
            m.run(tmp_path)
