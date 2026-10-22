"""TRM-074: no manuscript promotion across actual LitOps -> WhiteCrow intake."""
from __future__ import annotations

import json

import pytest

from kairoskopion.integrations.litops_bridge import (
    build_talk_corpus_litops_staging_pack,
    admit_talk_context_into_installed_litops,
)
from kairoskopion.services.talk_corpus_intake import run_case
from kairoskopion.services.talk_corpus_research_bridge import export_talk_research_evidence
from tests.test_trm074_talk_corpus_intake import fixture_case


def _ready(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    run_case(manifest, storage)
    export_talk_research_evidence(storage, "T3-SYNTHETIC")
    return manifest, storage, case


def test_source_capture_id_preserves_exact_drive_identity_and_author_limits(tmp_path):
    _, storage, _ = _ready(tmp_path)
    a = build_talk_corpus_litops_staging_pack(storage, "T3-SYNTHETIC")
    b = build_talk_corpus_litops_staging_pack(storage, "T3-SYNTHETIC")
    assert a == b
    assert a["schema"] == "TRM074_TO_INSTALLED_LITOPS_CONTEXT_PACK_V1"
    assert len(a["source_records"]) == 10
    assert len(a["artifact_records"]) == 3
    ids = {s["source_id"] for s in a["source_records"]}
    assert len(ids) == 10
    for source in a["source_records"]:
        assert source["source_document_id"].startswith("drive:")
        assert source["source_capture_sha256"]
        assert source["processing_state"] == "text_extracted"
        assert source["capture_mode"] == "manual_upload"
        assert source["semantic_acceptance"] == "NOT_ASSESSED"
        assert source["external_send"] == "DISABLED"
    accepted = next(x for x in a["source_records"]
                    if x["source_document_id"] == "drive:B001")
    assert accepted["source_author_state"] == "USER_ACCEPTED_CONCEPTS_ONLY"
    assert accepted["semantic_acceptance"] == "NOT_ASSESSED"


def test_context_packs_are_source_pointers_without_article_authority(tmp_path):
    _, storage, _ = _ready(tmp_path)
    payload = build_talk_corpus_litops_staging_pack(storage, "T3-SYNTHETIC")
    sources = {s["source_id"] for s in payload["source_records"]}
    for artifact in payload["artifact_records"]:
        assert artifact["artifact_type"] == "context_pack"
        assert artifact["status"] == "HOLD_SOURCE_PROVENANCE_ONLY"
        assert not artifact["field_ready"]
        assert not artifact["whitecrow_candidate"]
        assert not artifact["author_approved"]
        assert artifact["manuscript_status"] == "NOT_CREATED"
        assert artifact["organ_run_id"] == ""
        assert artifact["source_ids"]
        assert set(artifact["source_ids"]).issubset(sources)
        assert artifact["world_ref"] is None or isinstance(artifact["world_ref"], str)
        assert artifact["external_send"] == "DISABLED"


def test_homonymous_source_names_and_version_labels_do_not_merge(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    one, two = case["sources"][0:2]
    # Two different Drive documents can share both the same title and version.
    two["version"] = one["version"]
    manifest.write_text(json.dumps(case), encoding="utf-8")
    run_case(manifest, storage)
    export_talk_research_evidence(storage, "T3-SYNTHETIC")
    stage = build_talk_corpus_litops_staging_pack(storage, "T3-SYNTHETIC")
    got = [x for x in stage["source_records"]
           if x["source_document_id"] in {"drive:A001", "drive:A002"}]
    assert len(got) == 2
    assert len({x["source_id"] for x in got}) == 2
    assert len({x["source_document_id"] for x in got}) == 2


def test_tampered_source_content_digest_fails_closed(tmp_path):
    _, storage, _ = _ready(tmp_path)
    ledger_path = storage / "talk_corpora" / "T3-SYNTHETIC" / "case_ledger.json"
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    data["source_snapshots"][0]["content_sha256"] = "f" * 64
    ledger_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="research handoff not bound"):
        build_talk_corpus_litops_staging_pack(storage, "T3-SYNTHETIC")


def test_missing_existing_research_handoff_blocks_litops(tmp_path):
    _, storage, _ = _ready(tmp_path)
    (storage / "talk_corpora" / "T3-SYNTHETIC" /
     "research_stage_handoff.json").unlink()
    with pytest.raises(ValueError, match="corpus and Kairon research handoff required"):
        build_talk_corpus_litops_staging_pack(storage, "T3-SYNTHETIC")


def test_installed_litops_and_whitecrow_cold_replay_if_available(tmp_path, monkeypatch):
    pytest.importorskip("litops")
    pytest.importorskip("whitecrow.litops_import")
    from litops import config as litops_config
    from litops import registry as litops_registry
    from whitecrow.litops_import import build_import_pack

    _, storage, _ = _ready(tmp_path)
    private = tmp_path / "litops-isolated-root"
    monkeypatch.setenv("LITOPS_ROOT", str(private))
    monkeypatch.setenv("LITOPS_SKIP_DOTENV", "1")
    monkeypatch.setattr(litops_config, "_config_cache", None)
    first = admit_talk_context_into_installed_litops(
        storage, private, "T3-SYNTHETIC",
    )
    second = admit_talk_context_into_installed_litops(
        storage, private, "T3-SYNTHETIC",
    )
    assert first["source_records"] == 10
    assert first["context_packs"] == 3
    assert first["new_sources"] == 10
    assert first["new_context_packs"] == 3
    assert first["whitecrow_imported"] == 3
    assert second["new_sources"] == second["new_context_packs"] == 0
    assert first["sha256"] == second["sha256"]
    assert len({r["source_id"] for r in litops_registry.read_sources()}) == 10
    assert len({r["artifact_id"] for r in litops_registry.read_artifacts()
                if r.get("artifact_id")}) == 3
    assert len([r for r in build_import_pack(private).artifacts
                if r.litops_artifact_id.startswith("art-trm074-context-")]) == 3
    receipt = json.loads((storage / "talk_corpora" / "T3-SYNTHETIC" /
                          "litops_whitecrow_stage.json").read_text(encoding="utf-8"))
    assert receipt["whitecrow_status"] == "CONTEXT_ONLY_SCIENCE_AND_AUTHOR_GATE_HOLD"
    assert len(receipt["whitecrow_first_workset_context_ids"]) == 3
    assert receipt["whitecrow_first_workset_context_ids"] == receipt["whitecrow_imported_context_ids"]
    assert receipt["whitecrow_first_workset_manuscript"] is False
    assert receipt["whitecrow_w23_certification_available"] is False
    assert receipt["article_seed_created"] is False
    assert receipt["world_mutated"] is False
    assert receipt["external_send"] == "DISABLED"
    # Cold test uses new process-equivalent empty package cache.
    monkeypatch.setattr(litops_config, "_config_cache", None)


def test_litops_root_mismatch_refuses_to_touch_other_registry(tmp_path, monkeypatch):
    pytest.importorskip("litops")
    pytest.importorskip("whitecrow.litops_import")
    from litops import config as litops_config
    _, storage, _ = _ready(tmp_path)
    monkeypatch.setenv("LITOPS_ROOT", str(tmp_path / "authorized"))
    monkeypatch.setenv("LITOPS_SKIP_DOTENV", "1")
    monkeypatch.setattr(litops_config, "_config_cache", None)
    with pytest.raises(ValueError, match="does not match requested isolated target"):
        admit_talk_context_into_installed_litops(
            storage, tmp_path / "wrong-target", "T3-SYNTHETIC",
        )
    assert not (tmp_path / "wrong-target").exists()
