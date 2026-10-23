"""Tests for the real W12 importer/adapter.

These tests verify:
* Fixture W12 loads with the FIXTURE_NOT_REAL_DATA label.
* Real bytes load when the path exists; permission-denied scenarios are
  recorded with an explicit ``BLOCKED_PERMISSION`` receipt and the exact
  failure detail.
* 6 seed families / 27 meaning versions / 53 routes shape is preserved
  for the canonical fixture, with non-fatal warnings if the source
  diverges from the advisory count.
* Stable IDs across rerun (deterministic SHA-256 from source bytes).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kairoskopion.kairon_provider import (
    SOURCE_KIND_BLOCKED,
    SOURCE_KIND_FIXTURE,
    SOURCE_KIND_REAL,
    W12_EXPECTED_MEANING_VERSIONS,
    W12_EXPECTED_ROUTES,
    W12_EXPECTED_SEED_FAMILIES,
    W12ImportReceipt,
    W12Record,
    build_fixture_w12,
    discover_w12_source,
    load_w12,
    route_event_hash,
)


def test_fixture_w12_loads_with_fixture_label_and_shape():
    records, receipt = build_fixture_w12()
    assert receipt.source_kind == SOURCE_KIND_FIXTURE
    assert receipt.status == SOURCE_KIND_FIXTURE
    assert receipt.records_count == W12_EXPECTED_ROUTES
    assert receipt.seed_family_count == W12_EXPECTED_SEED_FAMILIES
    assert receipt.meaning_version_count == W12_EXPECTED_MEANING_VERSIONS
    assert not receipt.shape_warnings
    assert len(records) == W12_EXPECTED_ROUTES
    for record in records:
        assert record.source_kind == SOURCE_KIND_FIXTURE
        assert record.source_first_bytes_sha256
        assert record.source_full_sha256


def test_fixture_records_are_not_marked_as_real_data():
    records, receipt = build_fixture_w12()
    assert all(r.source_kind != SOURCE_KIND_REAL for r in records)
    assert all(SOURCE_KIND_REAL not in (r.notes or []) for r in records)
    assert "fixture-only" in " ".join(receipt.notes).lower()


def test_real_bytes_load_when_path_exists(tmp_path: Path):
    payload = [
        {"seed_family": "S1", "meaning_version": "M1", "route_label": "R1"},
        {"seed_family": "S2", "meaning_version": "M2", "route_label": "R2"},
    ]
    src = tmp_path / "w12.jsonl"
    src.write_text(
        "\n".join(json.dumps(p) for p in payload) + "\n", encoding="utf-8"
    )
    records, receipt = load_w12(src, source_kind=SOURCE_KIND_REAL)
    assert receipt.status == SOURCE_KIND_REAL
    assert receipt.records_count == 2
    assert records[0].source_kind == SOURCE_KIND_REAL
    assert records[0].source_full_sha256 == receipt.source_full_sha256
    assert records[0].source_first_bytes_sha256 == receipt.source_first_bytes_sha256


def test_load_w12_records_permission_failure_when_path_missing(tmp_path: Path):
    missing = tmp_path / "absent.jsonl"
    records, receipt = load_w12(missing, source_kind=SOURCE_KIND_REAL)
    assert receipt.status == SOURCE_KIND_BLOCKED
    assert receipt.source_kind == SOURCE_KIND_BLOCKED
    assert "source path" in (receipt.permission_failure or "").lower()
    assert records == []


def test_load_w12_records_permission_failure_when_path_empty(tmp_path: Path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    records, receipt = load_w12(empty)
    assert receipt.status == SOURCE_KIND_BLOCKED
    assert receipt.permission_failure is not None
    assert records == []


def test_load_w12_records_permission_failure_on_unparseable_json(tmp_path: Path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text("this is not json\n", encoding="utf-8")
    records, receipt = load_w12(bad)
    assert receipt.status == SOURCE_KIND_BLOCKED
    assert "json" in (receipt.permission_failure or "").lower() or "decode" in (receipt.permission_failure or "").lower()
    assert records == []


def test_discover_w12_source_records_blocked_when_env_missing(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("MAI_W12_AUTHORIZED_PATH", raising=False)
    receipt = discover_w12_source()
    assert receipt.status == SOURCE_KIND_BLOCKED
    assert receipt.source_kind == SOURCE_KIND_BLOCKED
    assert receipt.authorization_env_var == "MAI_W12_AUTHORIZED_PATH"
    assert receipt.records_count == 0
    assert "MAI_W12_AUTHORIZED_PATH" in (receipt.permission_failure or "")


def test_discover_w12_source_records_blocked_when_path_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MAI_W12_AUTHORIZED_PATH", str(tmp_path / "no_such_file.jsonl"))
    receipt = discover_w12_source()
    assert receipt.status == SOURCE_KIND_BLOCKED
    assert receipt.source_path == str(tmp_path / "no_such_file.jsonl")
    assert "does not exist" in (receipt.permission_failure or "")


def test_discover_w12_source_returns_real_when_path_exists(tmp_path: Path, monkeypatch):
    src = tmp_path / "real.jsonl"
    src.write_text(json.dumps({"seed_family": "S1", "route_label": "R1"}) + "\n", encoding="utf-8")
    monkeypatch.setenv("MAI_W12_AUTHORIZED_PATH", str(src))
    receipt = discover_w12_source()
    assert receipt.status == SOURCE_KIND_REAL
    assert receipt.source_full_sha256 is not None


def test_w12_real_data_fingerprint_is_stable(tmp_path: Path):
    payload = [
        {"seed_family": "S1", "meaning_version": "M1", "route_label": "R1"},
        {"seed_family": "S1", "meaning_version": "M1", "route_label": "R2"},
    ]
    src = tmp_path / "stable.jsonl"
    src.write_text("\n".join(json.dumps(p) for p in payload) + "\n", encoding="utf-8")
    records_a, receipt_a = load_w12(src, source_kind=SOURCE_KIND_REAL)
    records_b, receipt_b = load_w12(src, source_kind=SOURCE_KIND_REAL)
    assert receipt_a.source_full_sha256 == receipt_b.source_full_sha256
    assert receipt_a.source_first_bytes_sha256 == receipt_b.source_first_bytes_sha256
    assert [r.route_id for r in records_a] == [r.route_id for r in records_b]
    assert [r.record_id for r in records_a] == [r.record_id for r in records_b]


def test_w12_route_event_hash_deterministic():
    record = W12Record(
        record_id="r1",
        route_id="route:r1",
        seed_family_id="seed:s1",
        meaning_version_id="meaning:m1",
        seed_label="S1",
        meaning_version_label="M1",
        route_type="targeted_target",
        route_kind="regular",
        raw_kind="fulltext",
        exclusive_venue_class="none",
        source_kind=SOURCE_KIND_FIXTURE,
        source_first_bytes_sha256="abc",
        source_full_sha256="def",
    )
    h1 = route_event_hash(record=record, phase="source_evidence", status="completed")
    h2 = route_event_hash(record=record, phase="source_evidence", status="completed")
    assert h1 == h2
    assert h1.startswith("tev_")


def test_w12_fixture_shape_warns_when_underfilled():
    records, receipt = build_fixture_w12(seed_count=2, meaning_count=3, route_count=4)
    assert receipt.seed_family_count == 2
    assert receipt.meaning_version_count == 3
    assert receipt.records_count == 4
    warning_text = " ".join(receipt.shape_warnings)
    assert "seed_family_count" in warning_text
    assert "meaning_version_count" in warning_text
    assert "route_count" in warning_text


def test_w12_records_are_isolated_by_source_bytes(tmp_path: Path):
    payload_a = [{"seed_family": "S1", "meaning_version": "M1", "route_label": "R1"}]
    payload_b = [{"seed_family": "S2", "meaning_version": "M2", "route_label": "R2"}]
    src_a = tmp_path / "a.jsonl"
    src_b = tmp_path / "b.jsonl"
    src_a.write_text("\n".join(json.dumps(p) for p in payload_a) + "\n", encoding="utf-8")
    src_b.write_text("\n".join(json.dumps(p) for p in payload_b) + "\n", encoding="utf-8")
    records_a, _ = load_w12(src_a, source_kind=SOURCE_KIND_REAL)
    records_b, _ = load_w12(src_b, source_kind=SOURCE_KIND_REAL)
    assert records_a[0].source_full_sha256 != records_b[0].source_full_sha256
    assert records_a[0].route_id != records_b[0].route_id


def test_w12_import_receipt_to_dict_is_json_safe():
    _, receipt = build_fixture_w12()
    blob = receipt.to_dict()
    assert isinstance(blob, dict)
    assert json.dumps(blob) is not None


def test_w12_records_round_trip_dict():
    records, receipt = build_fixture_w12()
    assert receipt.records_count == len(records)
    for record in records[:3]:
        d = record.to_dict()
        assert d["source_kind"] == SOURCE_KIND_FIXTURE
        assert d["source_full_sha256"]
        assert d["source_first_bytes_sha256"]