"""Second-real-corpus bridge: identity, full byte provenance and held XLSX."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import pytest

from kairoskopion.integrations.owner_corpus_manifest_bridge import convert_owner_corpus_manifest
from kairoskopion.services.corpus_factory_entry import execute_factory_source_stage, _auxiliary_binary_pins


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def fixture_archive(tmp_path: Path):
    root = tmp_path / "old-provider"
    root.mkdir()
    items = [
        ("F01_B09", "AAA_1", b"Philosophy article title\n" + b"Arguments and evidence discussion. " * 36, "MANUSCRIPT_V1_HUMAN_REVIEW_REQUIRED"),
        ("F02_ACD_gate", "BBB_2", b"Author comments gate\n" + b"A C D remain under review. " * 30, "A_C_D_HOLD_B_E_F_RESOLVED"),
    ]
    docs = []
    caps = []
    for key, provider, raw, status in items:
        path = root / (key + ".txt")
        path.write_bytes(raw)
        docs.append({
            "key": key, "provider_id": provider, "sha256": digest(raw),
            "local_path": str(path), "source_format": "DRIVE_NATIVE_TXT_EXPORT",
        })
        caps.append({
            "key": key, "source_id": "drive:" + provider,
            "sha256": digest(raw), "path": str(path),
            "result": "FETCHED", "author_state": status,
        })
    filepaths = []
    for key, provider, filename, raw, ext, current in [
        ("L3-ORIGINAL-DOCX", "CCC_3", "corpus.docx", b"mocked-original-docx-carrier", "docx", None),
        ("L3-VAK-2023", "DDD_4", "historical.xlsx", b"mocked-old-spreadsheet-carrier", "xlsx", "HISTORICAL_2023_NOT_VAK_2026"),
    ]:
        path = root / filename
        path.write_bytes(raw)
        filepaths.append({
            "source_id": key, "provider_id": provider,
            "sha256": digest(raw), "local_path": str(path),
            "currentness": current,
        })
        caps.append({
            "key": key, "source_id": "drive:" + provider,
            "sha256": digest(raw), "path": str(path),
            "result": "FETCHED", "author_state": "NOT_VERIFIED",
        })
    owner = {
        "schema": "TRIMURTI_L3_REAL_SOURCE_MANIFEST_v0.3",
        "case_id": "CORPUS-OTHER", "no_external_send": True,
        "no_world_mutation": True, "mode": "DRY_RUN",
        "drive_sources": docs, "source_files": filepaths,
    }
    capture = {"schema": "L3_DRIVE_CAPTURE_V2",
               "case_id": "CORPUS-OTHER", "sources": caps}
    owner_file = root / "owner.json"
    cap_file = root / "capture.json"
    owner_file.write_text(json.dumps(owner), encoding="utf-8")
    cap_file.write_text(json.dumps(capture), encoding="utf-8")
    return owner, capture, owner_file, cap_file, root


def convert(tmp_path: Path):
    owner, capture, owner_file, cap_file, root = fixture_archive(tmp_path)
    out = root / "FACTORY-READY.json"
    response = convert_owner_corpus_manifest(owner_file, cap_file, output_manifest=out)
    return owner, capture, owner_file, cap_file, root, out, response


def test_converts_owner_source_captures_without_fabricating_scholarship(tmp_path):
    _, _, owner_file, cap_file, root, out, response = convert(tmp_path)
    obj = json.loads(out.read_text(encoding="utf-8"))
    assert response["total_verified_provider_captures"] == 4
    assert response["source_text_n"] == 3
    assert response["binary_held_n"] == 1
    assert len(obj["sources"]) == 3
    assert obj["version_edges"] == []
    assert obj["delta_pairs"] == []
    assert obj["decision_events"] == []
    assert obj["publication_send"] == "DISALLOWED"
    assert obj["sources"][0]["owner_author_state_detail"] == "MANUSCRIPT_V1_HUMAN_REVIEW_REQUIRED"
    assert obj["sources"][1]["owner_author_state_detail"] == "A_C_D_HOLD_B_E_F_RESOLVED"
    assert all(x["author_state"] == "NOT_VERIFIED" for x in obj["sources"][:2])
    assert obj["sources"][2]["kind"] == "WORD_EXTRACTED_TEXT"
    assert obj["sources"][2]["read_coverage"] == "DOCX_BODY_TEXT_COMMENTS_UNREAD"
    assert obj["auxiliary_sources"][0]["currentness"] == "HISTORICAL_2023_NOT_VAK_2026"
    assert obj["auxiliary_sources"][0]["read_coverage"] == "BINARY_HELD_NO_SCIENTIFIC_EXTRACTION"
    assert convert_owner_corpus_manifest(owner_file, cap_file, output_manifest=out)["manifest_sha256"] == response["manifest_sha256"]


def test_source_same_human_title_keeps_two_different_provider_ids(tmp_path):
    owner, capture, owner_file, cap_file, root = fixture_archive(tmp_path)
    p1 = root / "F01_B09.txt"
    p2 = root / "F02_ACD_gate.txt"
    renamed = root / "other-folder" / p1.name
    renamed.parent.mkdir()
    renamed.write_bytes(p2.read_bytes())
    owner["drive_sources"][1]["local_path"] = str(renamed)
    capture["sources"][1]["path"] = str(renamed)
    owner_file.write_text(json.dumps(owner), encoding="utf-8")
    cap_file.write_text(json.dumps(capture), encoding="utf-8")
    out = root / "ready.json"
    convert_owner_corpus_manifest(owner_file, cap_file, output_manifest=out)
    source_ids = [s["source_id"] for s in json.loads(out.read_text())["sources"]]
    assert len(source_ids) == len(set(source_ids)) == 3


def test_tampered_owner_source_prevents_conversion(tmp_path):
    owner, cap, owner_file, cap_file, root = fixture_archive(tmp_path)
    Path(owner["drive_sources"][0]["local_path"]).write_bytes(b"spurious replacement")
    with pytest.raises(ValueError, match="frozen owner source SHA mismatch"):
        convert_owner_corpus_manifest(owner_file, cap_file, output_manifest=root/"out.json")


def test_provider_id_substitution_prevents_conversion(tmp_path):
    owner, cap, owner_file, cap_file, root = fixture_archive(tmp_path)
    owner["drive_sources"][0]["provider_id"] = "WRONG_1234"
    owner_file.write_text(json.dumps(owner), encoding="utf-8")
    with pytest.raises(ValueError, match="byte/provider identity mismatch"):
        convert_owner_corpus_manifest(owner_file, cap_file, output_manifest=root/"out.json")


def test_unauthorized_world_or_external_send_prevents_conversion(tmp_path):
    owner, cap, owner_file, cap_file, root = fixture_archive(tmp_path)
    owner["no_external_send"] = False
    owner_file.write_text(json.dumps(owner), encoding="utf-8")
    with pytest.raises(ValueError, match="safety gates"):
        convert_owner_corpus_manifest(owner_file, cap_file, output_manifest=root/"out.json")


def test_one_unaccounted_original_capture_is_not_silently_dropped(tmp_path):
    owner, cap, owner_file, cap_file, root = fixture_archive(tmp_path)
    cap["sources"].append(dict(cap["sources"][0],key="EXTRA-OWNER-SOURCE"))
    cap_file.write_text(json.dumps(cap), encoding="utf-8")
    with pytest.raises(ValueError, match="source count mismatch"):
        convert_owner_corpus_manifest(owner_file, cap_file, output_manifest=root/"out.json")


def _factory_case(tmp_path: Path):
    root = tmp_path/"factory-case"
    root.mkdir()
    sources=[]
    for key,provider in (("ONE","AAAAA"),("TWO","BBBBB")):
        p=root/(key+".txt")
        p.write_text("Verified source content. "*40,encoding="utf-8")
        sources.append({
            "key":key,"family":"F01","kind":"RESEARCH_CONTEXT",
            "author_state":"NOT_VERIFIED","version":"source-key:"+key,
            "read_coverage":"TEXT_EXTRACT_ONLY",
            "source_id":"drive:"+provider,
            "source_url":f"https://docs.google.com/document/d/{provider}/edit",
            "local_path":str(p),"raw_sha256":digest(p.read_bytes()),
        })
    spreadsheet=root/"historical.xlsx"
    spreadsheet.write_bytes(b"not semantically parsed workbook in this test")
    aux={
        "source_id":"drive:CCCCC",
        "source_url":"https://drive.google.com/file/d/CCCCC/view",
        "local_path":str(spreadsheet),
        "raw_sha256":digest(spreadsheet.read_bytes()),
        "source_mime":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "read_coverage":"BINARY_HELD_NO_SCIENTIFIC_EXTRACTION",
        "currentness":"HISTORICAL_2023_NOT_VAK_2026",
    }
    m={"schema":"TRM074_COLD_CASE_V1","case_id":"CORPUS-TWO",
       "publication_send":"DISALLOWED","sources":sources,
       "auxiliary_sources":[aux],"version_edges":[],"delta_pairs":[],
       "discussion_events":[],"decision_events":[]}
    path=root/"manifest.json"
    path.write_text(json.dumps(m),encoding="utf-8")
    return m,path,root,spreadsheet


def test_another_source_corpus_uses_same_factory_and_keeps_binary_held(tmp_path):
    m,path,root,spreadsheet = _factory_case(tmp_path)
    storage=root/"storage"
    first=execute_factory_source_stage(path,storage)
    second=execute_factory_source_stage(path,storage)
    assert first["source_count"]==2
    assert first["auxiliary_binary_count"]==1
    assert first["total_provider_pins"]==3
    assert first["new_source_snapshots"]==2
    assert second["new_source_snapshots"]==0
    assert first["receipt_sha256"]==second["receipt_sha256"]
    receipt=json.loads(Path(first["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["auxiliary_binary_count"]==1
    assert receipt["auxiliary_binary_pins"][0]["read_coverage"]=="BINARY_HELD_NO_SCIENTIFIC_EXTRACTION"
    assert receipt["article_seed_created"]==0
    assert receipt["world_mutated"] is False


def test_changed_held_spreadsheet_cannot_survive_cold_restart(tmp_path):
    m,path,root,spreadsheet = _factory_case(tmp_path)
    storage=root/"storage"
    baseline=execute_factory_source_stage(path,storage)
    spreadsheet.write_bytes(spreadsheet.read_bytes()+b"MUTATED")
    with pytest.raises(ValueError,match="auxiliary binary raw byte SHA mismatch"):
        execute_factory_source_stage(path,storage)
    assert Path(baseline["receipt_path"]).is_file()


def test_changed_raw_text_byte_not_reconciled_by_filename(tmp_path):
    m,path,root,spreadsheet = _factory_case(tmp_path)
    storage=root/"storage"
    execute_factory_source_stage(path,storage)
    source=Path(m["sources"][0]["local_path"])
    source.write_bytes(source.read_bytes()+b" REPLACED")
    with pytest.raises(ValueError,match="source raw byte SHA mismatch"):
        execute_factory_source_stage(path,storage)


def test_binary_attachment_drive_url_cannot_be_a_fake_doc(tmp_path):
    m,path,root,spreadsheet=_factory_case(tmp_path)
    m["auxiliary_sources"][0]["source_url"]="https://docs.google.com/document/d/CCCCC/edit"
    path.write_text(json.dumps(m),encoding="utf-8")
    with pytest.raises(ValueError,match="auxiliary file URL/Drive identity mismatch"):
        execute_factory_source_stage(path,root/"storage")
    assert not (root/"storage").exists()



def test_legacy_case_without_auxiliary_does_not_change_receipt_schema(tmp_path):
    m,path,root,spreadsheet = _factory_case(tmp_path)
    m.pop("auxiliary_sources")
    path.write_text(json.dumps(m), encoding="utf-8")
    storage=root/"storage"
    first=execute_factory_source_stage(path,storage)
    second=execute_factory_source_stage(path,storage)
    assert first["auxiliary_binary_count"] == 0
    assert first["total_provider_pins"] == 2
    assert first["receipt_sha256"] == second["receipt_sha256"]
    receipt=json.loads(Path(first["receipt_path"]).read_text(encoding="utf-8"))
    assert "auxiliary_binary_pins" not in receipt
    assert "auxiliary_binary_count" not in receipt
