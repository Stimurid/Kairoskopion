"""MAI W12 source-to-packet materialization does not imply scientific QA."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from kairoskopion.kairon_provider.w12_packets import materialize

SHEET_ID = "1ryG1wsEJWyJMnK-QM5v-AluNc_yXL6NU_T3a55t-Y1U"


def setup_source(tmp_path: Path) -> tuple[Path, Path]:
    header = [
        "№", "Журнал", "Семейство", "Версия", "Тема", "Аннотация",
        "Тип входа", "Дедлайн", "Официальная страница",
        "Литература", "Примечание", "Приоритет", "Контакт",
    ]
    rows = [
        ["1", "Test Venue A", "A", "A-NORM", "Тема А", "Русская аннотация А",
         "abstract", "2026-11-01", "https://example.org/a", "", "", "high", ""],
        ["2", "Test Venue B", "B", "B-VALIDITY", "Тема Б", "Русская аннотация Б",
         "full manuscript only", None, "", "", "", "", ""],
    ]
    snapshot = {
        "source_id": SHEET_ID, "source_name": "53_МАРШРУТА",
        "headers": header, "rows": rows,
    }
    source = tmp_path / "source.jsonl"
    records=[]
    for i,row in enumerate(rows,2):
        records.append({
            "seed_family":row[2],"meaning_version":row[3],
            "source_spreadsheet_id":SHEET_ID,
            "source_fields":{h:str(v or "") for h,v in zip(header,row)},
            "source_row_index":i,"route_label":row[1],
        })
    source.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in records)+"\n",encoding="utf-8")
    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(snapshot,ensure_ascii=False),encoding="utf-8")
    return source,snap


def test_preserves_source_text_and_does_not_mark_qa_complete(tmp_path):
    src,snap=setup_source(tmp_path)
    out=tmp_path/"out"
    manifest=materialize(src,snap,out)
    assert manifest["records"] == 2
    assert manifest["ready_for_author_rework"] == 0
    assert manifest["ready_for_human_send"] == 0
    assert manifest["external_actions_performed"] == 0
    a=json.loads((out/"routes"/"MAI-W12-001.json").read_text(encoding="utf-8"))
    assert a["route"]["abstract_ru"] == "Русская аннотация А"
    assert a["scientific_state"] == "SOURCE_DRAFT_ONLY"
    assert a["quality_receipts"] == {}
    assert not a["ready_for_author_rework"]
    assert not a["ready_for_human_send"]
    assert len(list((out/"routes").glob("*.md"))) == 2
    assert "Публикационный фронт МАИ" in (out/"index.html").read_text(encoding="utf-8")


def test_source_snapshot_tampering_is_detected(tmp_path):
    src,snap=setup_source(tmp_path)
    records=[json.loads(line) for line in src.read_text(encoding="utf-8").splitlines()]
    records[0]["source_fields"]["Аннотация"]="ОТЛИЧНАЯ АННОТАЦИЯ"
    src.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in records)+"\n",encoding="utf-8")
    with pytest.raises(ValueError,match="source field mismatch"):
        materialize(src,snap,tmp_path/"out")


def test_outreach_status_requires_explicit_event(tmp_path):
    src,snap=setup_source(tmp_path)
    events=[
        {"route_id":"MAI-W12-001","status":"RECEIPT_CONFIRMED","event_id":"gmail-msg-1"},
        {"route_id":"MAI-W12-002","status":"FORM_PREPARE","event_id":"form-1"},
    ]
    p=tmp_path/"outreach.json"
    p.write_text(json.dumps(events),encoding="utf-8")
    out=tmp_path/"out"
    stats=materialize(src,snap,out,p)["status_counts"]
    assert stats=={"RECEIPT_CONFIRMED":1,"FORM_PREPARE":1}
    a=json.loads((out/"routes"/"MAI-W12-001.json").read_text(encoding="utf-8"))
    assert a["editorial_status"]=="RECEIPT_CONFIRMED"
    assert not a["ready_for_human_send"]
    with pytest.raises(ValueError,match="orphan outreach"):
        p.write_text(json.dumps([{"route_id":"MAI-W12-999","status":"DRAFT","event_id":"bad"}]),encoding="utf-8")
        materialize(src,snap,tmp_path/"other",p)


def test_repeated_export_produces_identical_packets(tmp_path):
    src,snap=setup_source(tmp_path)
    a=tmp_path/"a"
    b=tmp_path/"b"
    materialize(src,snap,a)
    materialize(src,snap,b)
    for name in ("manifest.json","kanban.json","kanban.csv","index.html",
                 "routes/MAI-W12-001.json","routes/MAI-W12-002.md"):
        assert (a/name).read_bytes()==(b/name).read_bytes()
