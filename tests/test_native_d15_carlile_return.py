"""F4 Carlile D15 Wave2 native WhiteCrow bridge regressions; no model calls."""
from pathlib import Path
import json
from unittest import mock
import pytest

from kairoskopion.kairon_provider import native_d15_carlile_return as m
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked, sha256

ROOT=Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\F4_D15_NEAREST_WAVE2_20261104")
MANIFEST=ROOT/"F4_Carlile_wave2_pinned_return_manifest.json"
WHITE=Path(r"C:\projects\whitecrow-antonova-direct-20261019")


def test_new_carlile_readbacks_real_sources_only(tmp_path):
    digest=sha256(MANIFEST.read_bytes())
    receipt=m.run(manifest_path=MANIFEST,manifest_sha=digest,whitecrow_root=WHITE,out=tmp_path)
    assert receipt["schema"]==m.SCHEMA
    assert len(receipt["five_read_bodies"])==5
    assert receipt["verified_primary_passages"]>=70
    assert receipt["coverage_status"]=="PARTIAL"
    assert receipt["research_readiness"]=="BLOCKED_ON_DUE_DILIGENCE"
    assert receipt["field_novelty_accepted"] is False
    assert receipt["field_saturation_accepted"] is False
    assert receipt["new_indago_hunts"]==0 and receipt["new_artikl_rewrites"]==0
    assert receipt["d25_manuscript_go"] is False
    assert receipt["author_gate"]=="HOLD"
    assert receipt["send"] is False and receipt["world_mutation"] is False
    report=tmp_path/"whitecrow_d24_after_five_primary_reads.json"
    assert sha256(report.read_bytes())==receipt["whitecrow_source_report_sha256"]
    data=json.loads(report.read_text(encoding="utf-8"))
    assert len(data["read_bodies"])==5
    assert data["nearest_precedent_grounded"] is True
    assert data["strongest_known_objection_grounded"] is True
    assert data["field_saturation_class"]=="EVIDENCE_INSUFFICIENT"
    # Must not re-run native model, overwrite same SHA, or change science.
    again=m.run(manifest_path=MANIFEST,manifest_sha=digest,whitecrow_root=WHITE,out=tmp_path)
    assert again==receipt


def test_changed_manifest_hash_fail_closed(tmp_path):
    wrong="0"*64
    with pytest.raises(EvidenceBlocked):
        m.run(manifest_path=MANIFEST,manifest_sha=wrong,
              whitecrow_root=WHITE,out=tmp_path)
    assert not list(tmp_path.glob("*"))


@pytest.mark.parametrize("field",[
    "source_pdf_sha256","source_text_sha256","carrier_sha256",
    "audit_sha256","check_sha256","errata_sha256",
    "stderr_sha256","exit_sha256"])
def test_forged_carlile_input_blocks_before_whitecrow(field):
    config=json.loads(MANIFEST.read_text(encoding="utf-8"))["sources"]["2004"]
    fake=dict(config,**{field:"0"*64})
    with pytest.raises(EvidenceBlocked):
        m._source_read("2004",fake)


def test_trusted_whitecrow_checkout_mandatory(tmp_path):
    digest=sha256(MANIFEST.read_bytes())
    with pytest.raises((EvidenceBlocked,FileNotFoundError,OSError)):
        m.run(manifest_path=MANIFEST,manifest_sha=digest,
            whitecrow_root=tmp_path,out=tmp_path/"out")
