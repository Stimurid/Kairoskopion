"""P3g: scientific source IDs must come from existing Factory receipt readback."""
from hashlib import sha256
import json

import pytest

from kairoskopion.services.factory_scientific_source_pin import (
    readback_factory_scientific_source_pin,
)


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n").encode()


def fixture(tmp_path, *, raw=True):
    case = "AI4SCI-C-TEST"
    source = b"original model-independent scientific source bytes\n"
    digest = sha256(source).hexdigest()
    snapshot = {
        "source_id": "drive:SCI-SOURCE",
        "snapshot_id": "snap-science-original",
        "extraction_status": "extracted",
        "read_coverage": "FULL_FETCHED_TEXT_ONLY",
        "content_sha256": digest,
    }
    if raw:
        snapshot["raw_source_sha256"] = digest
    ledger = {
        "schema": "TRM074_COLD_CASE_LEDGER_V1",
        "case_id": case, "publication_send": "DISALLOWED",
        "source_snapshots": [snapshot],
    }
    ledger_path = tmp_path / "talk_corpora" / case / "case_ledger.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_bytes(encoded(ledger))
    receipt = {
        "schema": "FACTORY_SOURCE_RESEARCH_STAGE_V1",
        "case_id": case, "source_ledger_sha256": sha256(encoded(ledger)).hexdigest(),
        "article_seed_created": 0,
        "author_approved": False, "world_mutated": False,
        "external_send": "DISABLED",
    }
    receipt_path = (tmp_path / "factory_research_cases" / case /
                    "source_stage_receipt.json")
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_bytes(encoded(receipt))
    args = {
        "factory_storage_root": tmp_path,
        "case_id": case, "source_id": "drive:SCI-SOURCE",
        "source_bytes": source,
        "owner_expected_stage_receipt_sha256": sha256(encoded(receipt)).hexdigest(),
    }
    return args, ledger_path, receipt_path


def test_actual_source_pin_follows_owner_factory_stage_receipt(tmp_path):
    args, _, _ = fixture(tmp_path)
    first = readback_factory_scientific_source_pin(**args)
    assert first == readback_factory_scientific_source_pin(**args)
    assert first["pin_kind"] == "RAW_SOURCE"
    assert first["source_sha256"] == sha256(args["source_bytes"]).hexdigest()
    assert first["independent_numerical_oracle"] == "NOT_VERIFIED"
    assert first["scientific_claim_admitted"] is False
    assert first["article_seed_created"] is False
    assert first["author_gate"] == "HOLD"
    assert first["external_send"] == "DISABLED"


def test_projection_stays_separate_from_original_raw_bytes(tmp_path):
    args, _, _ = fixture(tmp_path, raw=False)
    readback = readback_factory_scientific_source_pin(**args)
    assert readback["pin_kind"] == "TEXT_PROJECTION"
    assert readback["scientific_claim_admitted"] is False


@pytest.mark.parametrize("field,value", [
    ("case_id", "OTHER"),
    ("source_id", "drive:UNREGISTERED"),
    ("source_bytes", b"modified original bytes\n"),
    ("owner_expected_stage_receipt_sha256", "0"*64),
    ("owner_expected_stage_receipt_sha256", None),
    ("source_bytes", None),
])
def test_reject_foreign_case_source_model_pin_or_missing_bytes(tmp_path, field, value):
    args, _, _ = fixture(tmp_path)
    args[field] = value
    with pytest.raises(ValueError):
        readback_factory_scientific_source_pin(**args)


def test_replaced_source_ledger_is_not_independent_witness(tmp_path):
    args, ledger_path, _ = fixture(tmp_path)
    ledger_path.write_bytes(ledger_path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="ledger lost immutable receipt binding"):
        readback_factory_scientific_source_pin(**args)


@pytest.mark.parametrize("bad", [
    {"author_approved": True},
    {"article_seed_created": 1},
    {"world_mutated": True},
    {"external_send": "SENT"},
])
def test_science_readback_never_licenses_factory_mutation(tmp_path, bad):
    args, _, path = fixture(tmp_path)
    receipt = json.loads(path.read_bytes())
    receipt.update(bad)
    path.write_bytes(encoded(receipt))
    args["owner_expected_stage_receipt_sha256"] = sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="authority or case mismatch"):
        readback_factory_scientific_source_pin(**args)


def test_not_all_carriers_are_original_scientific_source(tmp_path):
    args, path, receipt_path = fixture(tmp_path)
    ledger = json.loads(path.read_bytes())
    ledger["source_snapshots"][0]["read_coverage"] = "CHAT_LOG_TEXT_ONLY"
    path.write_bytes(encoded(ledger))
    receipt = json.loads(receipt_path.read_bytes())
    receipt["source_ledger_sha256"] = sha256(path.read_bytes()).hexdigest()
    receipt_path.write_bytes(encoded(receipt))
    args["owner_expected_stage_receipt_sha256"] = sha256(receipt_path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="reading scope"):
        readback_factory_scientific_source_pin(**args)


def test_trusted_receipt_cannot_be_replaced_with_symlink(tmp_path):
    args, _, receipt_path = fixture(tmp_path)
    saved = receipt_path.read_bytes()
    receipt_path.unlink()
    other = tmp_path / "untrusted.json"
    other.write_bytes(saved)
    try:
        receipt_path.symlink_to(other)
    except OSError:
        pytest.skip("platform does not support file symlinks")
    with pytest.raises(ValueError, match="symlinked"):
        readback_factory_scientific_source_pin(**args)
