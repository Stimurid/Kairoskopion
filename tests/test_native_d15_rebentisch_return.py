"""Wave3 D15: actual source-pinned six-primary FieldCore return, fail-closed QA."""
import json
from pathlib import Path

import pytest

from kairoskopion.kairon_provider import native_d15_rebentisch_return as m
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked,sha256

OUTROOT=Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\F4_D15_NEAREST_WAVE3_20261104")
MANIFEST=OUTROOT/"Carlile_Rebentisch_2003_pinned_return_manifest.json"
WHITE=Path(r"C:\projects\whitecrow-antonova-direct-20261019")


def test_preexisting_five_read_whitecrow_is_exact_pinned_original():
    prev=m._load(m.PREVIOUS_REPORT,m.PREVIOUS_REPORT_SHA)
    receipt=m._load(m.PREVIOUS_RECEIPT,m.PREVIOUS_RECEIPT_SHA)
    assert len(prev["read_bodies"])==5
    assert len(prev["primary_passages"])==83
    assert receipt["whitecrow_source_report_sha256"]==m.PREVIOUS_REPORT_SHA
    assert prev["coverage_status"]=="PARTIAL"
    assert prev["research_readiness"]=="BLOCKED_ON_DUE_DILIGENCE"


def test_synthetic_bogus_hash_rejected(tmp_path):
    obj={"schema":"T3_F4_D15_CARLILE_REBENTISCH_2003_RETURN_MANIFEST_V1",
         "manuscript_sha256":m.MANUSCRIPT_SHA,
         "author_gate":"HOLD","send":False,"world_mutation":False,
         "pins":{"audit_sha256":"0"*64,"readback_sha256":"0"*64}}
    path=tmp_path/"untrusted.json"
    path.write_text(json.dumps(obj),encoding="utf-8")
    with pytest.raises(EvidenceBlocked):
        m.run(path,"0"*64,WHITE,tmp_path/"out")
    assert not (tmp_path/"out").exists()


@pytest.mark.parametrize("part",[
    ("source","0"*64),("report","0"*64),
])
def test_direct_byte_hash_mismatch_blocks(part):
    path=m.OPS/(m.BASE+".full_text.txt") if part[0]=="source" else m.PREVIOUS_REPORT
    with pytest.raises(EvidenceBlocked):
        m._expect(path,part[1])


def test_wrong_whitecrow_source_checkout_blocks(tmp_path):
    if not MANIFEST.is_file():
        pytest.skip("Awaiting independent source reading")
    with pytest.raises((EvidenceBlocked,OSError,FileNotFoundError)):
        m.run(MANIFEST,sha256(MANIFEST.read_bytes()),tmp_path,tmp_path/"out")


def test_real_six_source_return_is_consistent_and_idempotent(tmp_path):
    if not MANIFEST.is_file():
        pytest.skip("Awaiting independent source reading")
    rec=m.run(MANIFEST,sha256(MANIFEST.read_bytes()),WHITE,tmp_path/"out")
    assert rec["independent_read_source_count"]==6
    assert rec["verified_unique_primary_passages"]>=95
    assert rec["whitecrow_research_readiness"]=="BLOCKED_ON_DUE_DILIGENCE"
    assert rec["whitecrow_coverage_status"]=="PARTIAL"
    assert rec["field_science_novelty_accepted"] is False
    assert rec["field_saturation_accepted"] is False
    assert rec["independent_C04_empirical_program_completed"] is False
    assert rec["d25_manuscript_go"] is False
    assert rec["author_gate"]=="HOLD"
    assert rec["send"] is False and rec["world_mutation"] is False
    report=tmp_path/"out"/"whitecrow_d24_after_six_primary_reads.json"
    assert sha256(report.read_bytes())==rec["whitecrow_report_sha256"]
    again=m.run(MANIFEST,sha256(MANIFEST.read_bytes()),WHITE,tmp_path/"out")
    assert rec==again
