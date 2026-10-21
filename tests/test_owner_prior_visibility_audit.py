"""Independent Claude P1/P2 cases: no private source data, synthetic only."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from kairoskopion.services.owner_prior_research_bridge import (
    import_owner_prior_science, readback_owner_prior_science,
)
from tests.test_owner_prior_research_bridge import (
    _json, _seed_synthetic_owner_science,
)


def test_untagged_reserved_evidence_never_receipt_verified(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    import_owner_prior_science(source, legacy, storage)
    graph = OpportunityGraphStore(storage)
    graph.put("Evidence", {
        "id": "trm074-l3-ref-FORGED", "revision": "r1",
        "source_ref": "doi:10.0000/forged", "source_kind": "PUBLISHED_ARTICLE",
        "read_depth": "FULL_TEXT", "full_text_certified": True,
        "author_approved": True, "passage_anchors": [{"kind": "FAKE"}],
    })
    assert readback_owner_prior_science(storage)["verified"] is True
    result = graph.consumer_snapshot(include_owner_prior=True)
    assert result["status"] == "INCOMPLETE_OR_UNVERIFIED"
    assert result["records"] == [] and result["events"] == []


def test_untagged_reserved_hunttrace_never_receipt_verified(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    import_owner_prior_science(source, legacy, storage)
    graph = OpportunityGraphStore(storage)
    graph.put("HuntTrace", {
        "id": "trm074-owner-science-L3-CORPUS-20261020-forged",
        "revision": "unknown", "source_ref": "faked:source",
        "author_approved": True, "deep_qualified": True,
    })
    assert readback_owner_prior_science(storage)["verified"] is True
    result = graph.consumer_snapshot(include_owner_prior=True)
    assert result["status"] == "INCOMPLETE_OR_UNVERIFIED"
    assert result["records"] == [] and result["events"] == []


def test_second_unknown_case_quarantines_first_completed_case(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    import_owner_prior_science(source, legacy, storage)
    graph = OpportunityGraphStore(storage)
    graph.append_event({
        "event_id": "OTHER:OBJECTION", "kind": "SOURCE_CONTRADICTION",
        "subject_id": "other", "source_ref": "other:source",
        "result": "CONTRADICTS", "intellectual_consequence": "different work",
        "next_action": "review", "owner_prior_receipt_case": "OTHER-CASE",
    })
    result = graph.consumer_snapshot(include_owner_prior=True)
    assert result["status"] == "INCOMPLETE_OR_UNVERIFIED"
    assert result["records"] == [] and result["events"] == []


def test_corrupted_receipt_wrong_json_root_returns_private_quarantine(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    import_owner_prior_science(source, legacy, storage)
    path = (storage / "research_stage" / "L3-CORPUS-20261020"
            / "L3-PRIOR-SCIENCE-IMPORT" / "receipt.json")
    _json(path, ["not", "a", "mapping"])
    result = OpportunityGraphStore(storage).consumer_snapshot(include_owner_prior=True)
    assert result["status"] == "INCOMPLETE_OR_UNVERIFIED"
    assert result["records"] == [] and result["events"] == []
    assert result["status_reason"].startswith("READBACK_")


def test_snapshot_byte_read_disagrees_with_later_verified_disk(tmp_path, monkeypatch):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    import_owner_prior_science(source, legacy, storage)
    graph = OpportunityGraphStore(storage)
    evidence_path = next(
        p for p in graph.records.glob("*.json")
        if json.loads(p.read_text(encoding="utf-8")).get("owner_prior_receipt_case")
        and json.loads(p.read_text(encoding="utf-8"))["kind"] == "Evidence"
    )
    original = evidence_path.read_bytes()
    corrupt = json.loads(original.decode("utf-8"))
    corrupt["read_depth"] = "FULL_TEXT"
    corrupt["full_text_certified"] = True
    _json(evidence_path, corrupt)
    import kairoskopion.services.owner_prior_research_bridge as bridge
    real = bridge.readback_owner_prior_science

    def restore_then_verify(*args, **kwargs):
        evidence_path.write_bytes(original)
        return real(*args, **kwargs)

    monkeypatch.setattr(bridge, "readback_owner_prior_science", restore_then_verify)
    result = graph.consumer_snapshot(include_owner_prior=True)
    assert result["status"] == "INCOMPLETE_OR_UNVERIFIED"
    assert result["records"] == [] and result["events"] == []


def test_legacy_and_factory_root_must_not_overlap(tmp_path):
    source, legacy, storage, _ = _seed_synthetic_owner_science(tmp_path)
    with pytest.raises(ValueError, match="root.*isolated"):
        import_owner_prior_science(source, legacy, legacy)
