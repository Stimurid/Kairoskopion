"""F4 D15: real WhiteCrow readback, physical source tampering and authority bounds."""
import json
from pathlib import Path
import pytest

from kairoskopion.kairon_provider import native_d15_readback as m
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked, sha256


def test_real_three_originals_requalified_by_real_pinned_d24(tmp_path):
    d=m.requalify(Path(r"C:\projects\whitecrow-antonova-direct-20261019"),tmp_path)
    assert d["schema"]==m.SCHEMA
    assert d["whitecrow_actual_module_invoked"] is True
    assert len(d["read_bodies"])==3
    assert d["verified_primary_passages"]>=60
    assert d["whitecrow_coverage_status"]=="PARTIAL"
    assert d["whitecrow_research_readiness"]=="BLOCKED_ON_DUE_DILIGENCE"
    assert d["nearest_precedent_grounded"] is True
    assert d["strongest_objection_grounded"] is True
    assert d["field_wide_novelty_accepted"] is False
    assert d["d25_manuscript_go"] is False
    assert d["author_gate"]=="HOLD"
    assert d["send"] is False and d["world_mutation"] is False
    assert d["new_indago_hunts"]==0 and d["new_artikl_rewrites"]==0
    report=tmp_path/"whitecrow_d24_after_verified_d15_reads.json"
    assert sha256(report.read_bytes())==d["whitecrow_report_sha256"]
    raw=json.loads(report.read_text(encoding="utf-8"))
    assert raw["nearest_precedent_grounded"] is True
    assert raw["strongest_known_objection_grounded"] is True
    assert raw["research_readiness"]=="BLOCKED_ON_DUE_DILIGENCE"
    assert raw["coverage_status"]=="PARTIAL"
    # A byte-identical retry is not a second provider execution or mutation.
    again=m.requalify(Path(r"C:\projects\whitecrow-antonova-direct-20261019"),tmp_path)
    assert again==d


@pytest.mark.parametrize("bad",[
    {"audit_sha":"0"*64},
    {"check_sha":"0"*64},
    {"errata_sha":"0"*64},
    {"pdf_sha":"0"*64},
    {"text_sha":"0"*64},
    {"pages":35},
])
def test_forged_or_broken_primary_source_does_not_pass(bad):
    spec=dict(m.SOURCES[1],**bad)
    with pytest.raises(EvidenceBlocked):
        m._run_source(spec)


def test_unverified_codex_terminal_status_blocks(tmp_path):
    x=dict(m.SOURCES[2],exit=tmp_path/"exit.txt")
    (tmp_path/"exit.txt").write_text("1",encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="terminal_receipt"):
        m._run_source(x)


def test_no_trusted_whitecrow_checkout_blocks(tmp_path):
    with pytest.raises((EvidenceBlocked,FileNotFoundError,OSError)):
        m.requalify(tmp_path,tmp_path/"out")
