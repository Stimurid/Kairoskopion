"""Fixture-only tests: do not commit W12's owner-private SQLite or author fields."""
import hashlib
from io import BytesIO
import json
import sqlite3
from zipfile import ZipFile

import pytest

from kairoskopion.kairon_provider.w12_private_runtime import (
    SOURCE_CLASSES, TABLE_COUNTS, W12AdmissionError,
    research_stage_projection, stage_private_research,
)

SOURCE_SHA = "a" * 64  # synthetic; not the verified W12 digest


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@pytest.fixture
def staged_fixture(tmp_path):
    db_path = tmp_path / "fixture.sqlite"
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        CREATE TABLE source(source_sha256 TEXT PRIMARY KEY, source_drive_id TEXT NOT NULL,
            source_url TEXT NOT NULL, bytes INTEGER NOT NULL, sheet_count INTEGER NOT NULL,
            admission_phase TEXT NOT NULL, full_text_qualified INTEGER NOT NULL);
        CREATE TABLE sheet(name TEXT PRIMARY KEY,ordinal INTEGER NOT NULL,data_rows INTEGER NOT NULL);
        CREATE TABLE row_snapshot(sheet TEXT NOT NULL,excel_row INTEGER NOT NULL,
            source_sha256 TEXT NOT NULL,row_digest TEXT NOT NULL,fields_json TEXT NOT NULL,
            PRIMARY KEY(sheet,excel_row),FOREIGN KEY(sheet) REFERENCES sheet(name));
        CREATE TABLE seed(seed_id TEXT PRIMARY KEY,excel_row INTEGER NOT NULL,author_authority TEXT NOT NULL);
        CREATE TABLE venue(venue_id TEXT PRIMARY KEY,excel_row INTEGER NOT NULL,canonical_name TEXT NOT NULL UNIQUE,
            current_policy_qualified INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE research_version(version_id TEXT PRIMARY KEY,seed_id TEXT NOT NULL,
            excel_row INTEGER NOT NULL,independent_article_certified INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(seed_id) REFERENCES seed(seed_id));
        CREATE TABLE route(route_id TEXT PRIMARY KEY,excel_row INTEGER NOT NULL,seed_id TEXT NOT NULL,
            version_id TEXT NOT NULL,venue_id TEXT NOT NULL,route_type TEXT NOT NULL,
            route_description TEXT NOT NULL,source_policy_qualified INTEGER NOT NULL DEFAULT 0,
            external_send_status TEXT NOT NULL,FOREIGN KEY(seed_id) REFERENCES seed(seed_id),
            FOREIGN KEY(version_id) REFERENCES research_version(version_id),
            FOREIGN KEY(venue_id) REFERENCES venue(venue_id));
        CREATE TABLE editorial_action(action_id TEXT PRIMARY KEY,route_id TEXT NOT NULL,
            excel_row INTEGER NOT NULL,source_status TEXT NOT NULL,
            FOREIGN KEY(route_id) REFERENCES route(route_id));
        CREATE TABLE evidence(evidence_id TEXT PRIMARY KEY,excel_row INTEGER NOT NULL,
            read_depth TEXT NOT NULL,full_text_qualified INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE event(event_id TEXT PRIMARY KEY,event_type TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,phase TEXT NOT NULL);
    """)
    db.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)", (
        SOURCE_SHA, "test-only", "fixture://w12", 251033, 21,
        "RESEARCH_STAGED_NOT_ARTIKL_ADMITTED", 0,
    ))
    names = ["06_МАРШРУТЫ", "fake_extra"] + [f"empty_{i}" for i in range(19)]
    for i, name in enumerate(names):
        count = 53 if i == 0 else 675 if i == 1 else 0
        db.execute("INSERT INTO sheet VALUES (?,?,?)", (name, i + 1, count))
        for row in range(2, count + 2):
            fields = {
                "Название для авторской вычитки": f"Фиктивный маршрут {row}",
                "Опубликованный противник": "Тестовый собеседник",
                "Давление журнала на идею": "Нужны доказательства",
            } if i == 0 else {"synthetic": row}
            raw = json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            db.execute("INSERT INTO row_snapshot VALUES (?,?,?,?,?)", (
                name, row, SOURCE_SHA, digest(raw.encode()), raw,
            ))
    for i in range(6):
        db.execute("INSERT INTO seed VALUES (?,?,?)", (
            f"MAI:{chr(65+i)}", i + 2, "INDAGO_RESEARCH_CANDIDATE",
        ))
    for i in range(81):
        db.execute("INSERT INTO venue VALUES (?,?,?,0)", (
            f"J{i+1:03}", i + 2, f"Synthetic Journal {i+1}",
        ))
    for i in range(27):
        db.execute("INSERT INTO research_version VALUES (?,?,?,0)", (
            f"V{i+1:03}", "MAI:A", i + 2,
        ))
    for i in range(53):
        db.execute("INSERT INTO route VALUES (?,?,?,?,?,?,?,?,?)", (
            f"W12:R{i+1:03}", i + 2, "MAI:A", "V001",
            f"J{i+1:03}", "POLICY_UNVERIFIED", "synthetic", 0, "NOT_SENT",
        ))
    for i in range(67):
        db.execute("INSERT INTO editorial_action VALUES (?,?,?,?)", (
            f"W12:A{i+1:03}", f"W12:R{i%53+1:03}", i + 2, "RESEARCH_ONLY",
        ))
    for i in range(43):
        db.execute("INSERT INTO evidence VALUES (?,?,?,0)", (
            f"W12:E{i+1:03}", i + 2,
            "ABSTRACT" if i < 31 else "SECTIONS" if i < 35 else "INDEX_ONLY",
        ))
    db.execute("INSERT INTO event VALUES (?,?,?,?)", (
        "W12_IMPORT:" + SOURCE_SHA, "SOURCE_BYTE_VERIFIED_AND_STAGED",
        SOURCE_SHA, "RESEARCH_STAGED_NOT_ARTIKL_ADMITTED",
    ))
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    db.commit()
    db.close()
    db_bytes = db_path.read_bytes()
    receipt = {
        "schema": "W12_PRIVATE_SOURCE_ADMISSION_v1", "source_sha256": SOURCE_SHA,
        "private_store_sha256": digest(db_bytes),
        "db_table_counts": TABLE_COUNTS,
        "declared_counts_verified": SOURCE_CLASSES,
        "source_sheet_count": 21, "byte_count": 251033,
        "admission_phase": "RESEARCH_STAGED_NOT_ARTIKL_ADMITTED",
        "full_text_qualified": 0, "source_policy_qualified": 0,
        "independent_article_promotions": 0, "external_submission_events": 0,
        "author_decisions_synthesized": 0,
    }
    zip_path = tmp_path / "fixture.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr("W12_MAI_PRIVATE_RESEARCH_STAGE.sqlite", db_bytes)
        archive.writestr("W12_MAI_IMPORT_RECEIPT.json", json.dumps(receipt))
        archive.writestr("w12_stage_private.py", "# fixture only")
    return zip_path, digest(zip_path.read_bytes()), SOURCE_SHA


def test_no_private_stage_is_not_a_successful_import(tmp_path):
    r = research_stage_projection(tmp_path / "users" / "user_abcdefabcdef")
    assert r["status"] == "RUNTIME_IMPORT_PENDING"
    assert r["rows"] == []
    assert r["artikl_articles_admitted"] == 0


def test_replay_idempotence_fifty_three_unqualified_and_user_isolation(staged_fixture, tmp_path):
    archive, pin, source = staged_fixture
    owner = tmp_path / "users" / "user_abcdefabcdef"
    other = tmp_path / "users" / "user_123456abcdef"
    a = stage_private_research(archive, owner, expected_archive_sha256=pin, expected_source_sha256=source)
    b = stage_private_research(archive, owner, expected_archive_sha256=pin, expected_source_sha256=source)
    assert a == b
    assert a["research_source_counts"]["row_snapshot"] == 728
    result = research_stage_projection(owner)
    assert result["status"] == "PRIVATE_RESEARCH_STAGED"
    assert result["researchRouteCount"] == len(result["rows"]) == 53
    assert result["artikl_articles_admitted"] == 0
    assert result["editorial_routes_qualified"] == 0
    assert result["external_submissions"] == 0
    assert all(x["routeType"] == "POLICY_UNVERIFIED" and x["authorDecision"] == "HOLD" for x in result["rows"])
    assert all(x["articleStatus"] == "NOT_ARTIKL_ADMITTED" for x in result["rows"])
    assert research_stage_projection(other)["rows"] == []
    assert not (owner / "kairon_provider" / "opportunity_graph" / "records").exists()


def test_pagination_preserves_private_source_row_provenance(staged_fixture, tmp_path):
    archive, pin, src = staged_fixture
    owner = tmp_path / "users" / "user_abcdefabcdef"
    stage_private_research(archive, owner, expected_archive_sha256=pin, expected_source_sha256=src)
    page = research_stage_projection(owner, offset=2, limit=4)
    assert [row["routeId"] for row in page["rows"]] == [f"W12:R{i:03}" for i in range(3, 7)]
    assert page["rows"][0]["sourceRowRef"] == "06_МАРШРУТЫ!4"
    assert page["rows"][0]["workingTitle"] == "Фиктивный маршрут 4"


def test_checksum_fail_closed_and_source_revisions_are_immutable(staged_fixture, tmp_path):
    archive, pin, src = staged_fixture
    owner = tmp_path / "users" / "user_abcdefabcdef"
    with pytest.raises(W12AdmissionError, match="ZIP sha256"):
        stage_private_research(archive, owner, expected_archive_sha256="f"*64, expected_source_sha256=src)
    with pytest.raises(W12AdmissionError, match="original W12 XLSX"):
        stage_private_research(archive, owner, expected_archive_sha256=pin, expected_source_sha256="f"*64)
    stage_private_research(archive, owner, expected_archive_sha256=pin, expected_source_sha256=src)
    with ZipFile(archive) as z:
        contents = {name: z.read(name) for name in z.namelist()}
    contents["w12_stage_private.py"] = b"# different"
    changed = tmp_path / "different.zip"
    with ZipFile(changed, "w") as z:
        for name, data in contents.items():
            z.writestr(name, data)
    with pytest.raises(W12AdmissionError, match="overwrite immutable"):
        stage_private_research(changed, owner, expected_archive_sha256=digest(changed.read_bytes()), expected_source_sha256=src)


def test_staged_file_tampering_and_symlink_blocked(staged_fixture, tmp_path):
    archive, pin, src = staged_fixture
    owner = tmp_path / "users" / "user_abcdefabcdef"
    stage_private_research(archive, owner, expected_archive_sha256=pin, expected_source_sha256=src)
    sqlite_file = owner / "kairon_provider" / "w12_private_research" / "stage.sqlite"
    with sqlite_file.open("ab") as fp:
        fp.write(b"unauthorized")
    with pytest.raises(W12AdmissionError, match="mutated"):
        research_stage_projection(owner)
    link = tmp_path / "shortcut"
    link.symlink_to(owner, target_is_directory=True)
    with pytest.raises(W12AdmissionError, match="symlink"):
        research_stage_projection(link)
