"""Regression for previously researched MAI source -> Factory -> INDAGO review index."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

from scripts.build_mai_w12_factory_case import build_case
from scripts.build_mai_w12_science_index import build, extract_heads, PROVENANCE_ID

SHEET="1ryG1wsEJWyJMnK-QM5v-AluNc_yXL6NU_T3a55t-Y1U"

def prepare(tmp_path:Path):
    p=tmp_path/"packets"
    (p/"routes").mkdir(parents=True)
    r={
        "route_id":"MAI-W12-001",
        "original_spreadsheet_id":SHEET,
        "source_cell_range":"A2:M2","family":"A","variant":"A-NORM",
        "journal":"Test Venue","title_ru":"Авторский вопрос о нормах",
        "abstract_ru":"Авторская аннотация только исходного маршрута",
        "source_authority":"LIVE_AUTHENTICATED_GOOGLE_SHEET_DERIVED",
        "not_original_xlsx_bytes":True,
        "target_status":"POLICY_UNVERIFIED",
        "literature_url":"https://doi.org/10.1007/test",
    }
    obj={"schema":"MAI_W12_BATCH_RESEARCH_PACKET_v1","source_jsonl_sha256":"a"*64,"route":r}
    (p/"routes"/"MAI-W12-001.json").write_text(json.dumps(obj,ensure_ascii=False),encoding="utf-8")
    (p/"routes"/"MAI-W12-001.md").write_text("# SOURCE W12\n\noriginal material",encoding="utf-8")
    (p/"manifest.json").write_text(json.dumps({
        "schema":"MAI_W12_BATCH_OUTPUT_MANIFEST_v1","source_jsonl_sha256":"a"*64,
        "records":1}),encoding="utf-8")
    # The real Indago head has these six sections; this fixture has a
    # minimal but correctly delimited version and one DOI per family.
    head="\r\n".join(
        f"{family} / TITLE FAMILY {family}\r\n"
        +f"Rivals DOI10.1007/paper-{family.lower()}. This is previous research, "
        +"source text not independently read in this test. "*4
        for family in "ABCDEF"
    )+"\r\nDECISION / RESEARCH GATES\r\n"
    headpath=tmp_path/"indago08.txt"
    headpath.write_bytes(head.encode("utf-8"))
    authorfile=tmp_path/"author-a.txt"
    authorfile.write_text("Авторский оригинал — текстовое представление",encoding="utf-8")
    donors=[
        {"key":"IH08","family":"CROSS","kind":"RESEARCH_SYNTHESIS","version":"W69",
         "drive_file_id":PROVENANCE_ID,
         "url":f"https://docs.google.com/document/d/{PROVENANCE_ID}/edit",
         "local_path":str(headpath),"read_coverage":"RESEARCH_SYNTHESIS_TEXT_ONLY",
         "author_state":"RESEARCH_RETURN_NOT_AUTHOR_APPROVAL",
         "source_scope":"MAI_INDAGO_HEADS_CONNECTOR_TEXT_PROJECTION",
         "provider_original_bytes_verified":False},
        {"key":"AUTHOR_A","family":"A","kind":"CONCEPT_BASELINE","version":"source-v1",
         "drive_file_id":"1RnE42iT0_z5yNlSrbczHg6Q5IjXNPURPTkK-9FmfkkQ",
         "url":"https://docs.google.com/document/d/1RnE42iT0_z5yNlSrbczHg6Q5IjXNPURPTkK-9FmfkkQ/edit",
         "local_path":str(authorfile),"read_coverage":"TEXT_EXTRACT_ONLY",
         "author_state":"NOT_VERIFIED",
         "source_scope":"MAI_AUTHOR_CONCEPTUAL_SOURCE_CONNECTOR_TEXT_PROJECTION",
         "provider_original_bytes_verified":False},
    ]
    donorfile=tmp_path/"donors.json"
    donorfile.write_text(json.dumps({"schema":"MAI_INDAGO_DONOR_TEXT_PROJECTIONS_v1","sources":donors}),encoding="utf-8")
    return p,headpath,donorfile

def test_derived_w12_row_and_original_donor_remain_distinct(tmp_path):
    packets,head,donors=prepare(tmp_path)
    case=build_case(packets,donors,"MAI-TEST-20261020")
    assert len(case["sources"])==3
    route,indago,author=case["sources"]
    assert route["source_id"]==f"w12-sheet:{SHEET}:A2:M2:MAI-20261020"
    assert route["source_url"].endswith("#range=A2:M2")
    assert route["scope"]=="W12_SECONDARY_RESEARCH_SYNTHESIS_ONLY"
    assert route["author_state"]=="RESEARCH_RETURN_NOT_AUTHOR_APPROVAL"
    assert indago["source_id"]=="drive:"+PROVENANCE_ID
    assert indago["read_coverage"]=="RESEARCH_SYNTHESIS_TEXT_ONLY"
    assert author["family"]=="A"
    assert author["read_coverage"]=="TEXT_EXTRACT_ONLY"
    assert author["provider_original_bytes_verified"] is False
    assert case["publication_send"]=="DISALLOWED"
    assert not case["decision_events"]

def test_donor_raw_provider_bytes_cannot_be_self_certified(tmp_path):
    p,head,donors=prepare(tmp_path)
    raw=json.loads(donors.read_text(encoding="utf-8"))
    raw["sources"][0]["provider_original_bytes_verified"]=True
    donors.write_text(json.dumps(raw),encoding="utf-8")
    with pytest.raises(ValueError,match="raw-byte verification"):
        build_case(p,donors,"MAI-TEST-20261020")

def test_forged_spreadsheet_provenance_rejected(tmp_path):
    p,head,donors=prepare(tmp_path)
    target=p/"routes"/"MAI-W12-001.json"
    raw=json.loads(target.read_text(encoding="utf-8"))
    raw["route"]["source_authority"]="FAKE_CLAIM"
    target.write_text(json.dumps(raw),encoding="utf-8")
    with pytest.raises(ValueError,match="W12 sheet provenance"):
        build_case(p,donors,"MAI-TEST-20261020")

def test_six_head_index_and_route_hold_cold_replay(tmp_path):
    p,head,donors=prepare(tmp_path)
    output1=tmp_path/"research1"
    output2=tmp_path/"research2"
    a=build(p,head,donors,output1)
    b=build(p,head,donors,output2)
    assert a["route_count"]==b["route_count"]==1
    assert a["head_count"]==6
    assert a["route_author_ready_count"]==0
    assert a["real_research_operations_this_wave"]==0
    assert a["external_send_count"]==0
    packet=json.loads((output1/"routes"/"MAI-W12-001.json").read_text(encoding="utf-8"))
    assert packet["scholarly_execution_state"]=="HOLD_UNTIL_REAL_ARTIKL_INDAGO_OPERATION"
    assert packet["science_provenance"]["prior_art_doi_candidates"]==["10.1007/paper-a"]
    assert packet["science_provenance"]["author_source_text_projections"][0]["source_id"].startswith("drive:")
    assert packet["author_ready"] is False
    for relative in ("routes/MAI-W12-001.json","science_index.json","family_heads_index.json"):
        assert (output1/relative).read_bytes()==(output2/relative).read_bytes()

def test_prior_index_rejects_route_provenance_drift(tmp_path):
    p,head,donors=prepare(tmp_path)
    source=p/"routes"/"MAI-W12-001.json"
    raw=json.loads(source.read_text(encoding="utf-8"))
    raw["source_jsonl_sha256"]="b"*64
    source.write_text(json.dumps(raw),encoding="utf-8")
    with pytest.raises(ValueError,match="source authority mismatch"):
        build(p,head,donors,tmp_path/"research")

def test_indago_head_requires_six_sections(tmp_path):
    assert not extract_heads is None
    with pytest.raises(ValueError,match="A-F header set"):
        extract_heads("A / ONLY\nRivals summary\nDECISION / RESEARCH GATES")
