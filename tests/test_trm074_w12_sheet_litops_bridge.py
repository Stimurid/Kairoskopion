"""W12 Google Sheets source-specific bridge into existing LitOps/WhiteCrow."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from kairoskopion.services.talk_corpus_intake import run_case
from kairoskopion.services.talk_corpus_research_bridge import export_talk_research_evidence
from kairoskopion.integrations.litops_bridge import build_talk_corpus_litops_staging_pack
from tests.test_trm074_talk_corpus_intake import fixture_case

SHEET_ID="1ryG1wsEJWyJMnK-QM5v-AluNc_yXL6NU_T3a55t-Y1U"
W12_ID=f"w12-sheet:{SHEET_ID}:A2:M2:MAI-20261020"
W12_URL=f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#range=A2:M2"


def _setup(tmp_path: Path, *, url: str=W12_URL,
           read_coverage: str="RESEARCH_SYNTHESIS_TEXT_ONLY",
           author_state: str="RESEARCH_RETURN_NOT_AUTHOR_APPROVAL",
           scope: str="W12_SECONDARY_RESEARCH_SYNTHESIS_ONLY"):
    manifest,storage,case=fixture_case(tmp_path)
    s=case["sources"][0]
    s.update({
        "source_id":W12_ID,"source_url":url,
        "kind":"RESEARCH_SYNTHESIS","read_coverage":read_coverage,
        "author_state":author_state,"scope":scope,
        "version":"A-NORM",
    })
    manifest.write_text(json.dumps(case,ensure_ascii=False),encoding="utf-8")
    run_case(manifest,storage)
    export_talk_research_evidence(storage,case["case_id"])
    return storage,case


def test_w12_sheet_source_accepts_only_secondary_research_kind(tmp_path):
    storage,case=_setup(tmp_path)
    result=build_talk_corpus_litops_staging_pack(storage,case["case_id"])
    sheet=next(s for s in result["source_records"] if s["source_document_id"]==W12_ID)
    assert sheet["source_document_url"]==W12_URL
    assert sheet["source_authority_kind"]=="W12_GOOGLE_SHEET_DERIVED"
    assert sheet["source_read_coverage"]=="RESEARCH_SYNTHESIS_TEXT_ONLY"
    assert sheet["source_author_state"]=="RESEARCH_RETURN_NOT_AUTHOR_APPROVAL"
    assert sheet["origin"]=="mixed"
    assert "w12-secondary-sheet-not-author-original" in sheet["tags"]
    assert sheet["semantic_acceptance"]=="NOT_ASSESSED"
    assert sheet["external_send"]=="DISABLED"
    assert not any(a.get("field_ready") or a.get("author_approved") for a in result["artifact_records"])


@pytest.mark.parametrize("url",[
    f"https://docs.google.com/document/d/{SHEET_ID}/edit",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#range=A3:M3",
    "https://example.org/forged",
])
def test_w12_sheet_identity_url_drift_is_rejected(tmp_path,url):
    storage,case=_setup(tmp_path,url=url)
    with pytest.raises(ValueError, match="incompatible provenance"):
        build_talk_corpus_litops_staging_pack(storage,case["case_id"])


def test_w12_wrong_read_depth_is_rejected(tmp_path):
    storage,case=_setup(tmp_path,read_coverage="FULL_FETCHED_TEXT_ONLY")
    with pytest.raises(ValueError,match="incompatible provenance"):
        build_talk_corpus_litops_staging_pack(storage,case["case_id"])


def test_w12_author_authorization_cannot_be_invented(tmp_path):
    # The upstream Factory admission gate rejects unsupported author claims
    # even before the LitOps sheet-source bridge gets a chance to inspect.
    with pytest.raises(ValueError,match="accepted carrier lacks its own anchored author decision"):
        _setup(tmp_path,author_state="USER_ACCEPTED_CONCEPTS_ONLY")
