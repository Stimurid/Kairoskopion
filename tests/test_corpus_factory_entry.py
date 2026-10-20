"""FACTORY-FIRST: one manifest/command for source research on the actual runtime."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from kairoskopion.services.corpus_factory_entry import execute_factory_source_stage
from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from tests.test_trm074_talk_corpus_intake import fixture_case
from tests.test_trm073_research_stage import packet


def new_unrelated_case(tmp_path: Path):
    manifest, storage, case = fixture_case(tmp_path)
    sources = [s for s in case["sources"] if s["key"] in {"A06", "A07"}]
    for index, source in enumerate(sources):
        source["family"] = "Z"
        source["key"] = f"Z{index:02}"
        source["author_state"] = "NOT_VERIFIED"
    case["case_id"] = "NEW-CORPUS-001"
    case["sources"] = sources
    case["version_edges"] = [{
        "before": "Z00", "after": "Z01",
        "relation": "REGISTERED_SEQUENCE_NOT_PROVEN_DERIVATION",
    }]
    case["delta_pairs"] = [["Z00", "Z01"]]
    case["decision_events"] = []
    case["discussion_events"] = []
    case["missing_carriers"] = []
    case["world"] = "https://docs.google.com/document/d/UNRELATED-WORLD/edit"
    manifest.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
    return manifest, storage, case


def test_next_unrelated_corpus_uses_one_entry_and_no_manual_w1(tmp_path):
    manifest, storage, _ = new_unrelated_case(tmp_path)
    first = execute_factory_source_stage(manifest, storage)
    second = execute_factory_source_stage(manifest, storage)
    assert first["source_count"] == 2
    assert first["kairon_evidence_count"] == 2
    assert first["manual_w1_proposals"] == first["w2_proposals"] == 0
    assert first["new_source_snapshots"] == 2
    assert second["new_source_snapshots"] == 0
    assert first["receipt_sha256"] == second["receipt_sha256"]
    receipt = json.loads(Path(first["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["case_id"] == "NEW-CORPUS-001"
    assert receipt["whitecrow_status"] == "NOT_RUN"
    assert receipt["indago_new_hunt"] == "NOT_RUN_EXISTING_MANUAL_RESEARCH_ONLY"
    assert receipt["article_seed_created"] == 0
    assert not receipt["world_mutated"]
    assert receipt["external_send"] == "DISABLED"
    assert OpportunityGraphStore(storage).list_records("ArticleSeed") == []
    assert OpportunityGraphStore(storage).list_records("OpportunityRoute") == []


def test_new_case_with_existing_w2_research_packet_is_still_provisional(tmp_path):
    manifest, storage, _ = new_unrelated_case(tmp_path)
    research = packet()
    research["case_id"] = "NEW-CORPUS-001"
    w2_path = tmp_path / "W2.json"
    w2_path.write_text(json.dumps(research, ensure_ascii=False), encoding="utf-8")
    one = execute_factory_source_stage(
        manifest, storage, research_packet_path=w2_path,
    )
    two = execute_factory_source_stage(
        manifest, storage, research_packet_path=w2_path,
    )
    assert one["receipt_sha256"] == two["receipt_sha256"]
    assert one["kairon_evidence_count"] == 10
    assert one["w2_proposals"] == 6
    assert two["new_source_snapshots"] == 0
    graph = OpportunityGraphStore(storage)
    assert len(graph.list_records("Evidence")) == 10
    assert graph.list_records("World") == []
    assert graph.list_records("ArticleSeed") == []
    assert graph.list_records("OpportunityRoute") == []
    assert graph.list_records("JournalIssue")[0]["live_call"] is False


def test_case_mismatch_fails_before_any_mutation(tmp_path):
    manifest, storage, _ = new_unrelated_case(tmp_path)
    w2_path = tmp_path / "W2.json"
    w2_path.write_text(json.dumps(packet()), encoding="utf-8")
    with pytest.raises(ValueError, match="different case"):
        execute_factory_source_stage(
            manifest, storage, research_packet_path=w2_path,
        )
    assert not storage.exists()


def test_source_bytes_changed_while_manifest_unchanged_fail_closed(tmp_path):
    manifest, storage, case = new_unrelated_case(tmp_path)
    execute_factory_source_stage(manifest, storage)
    original = Path(case["sources"][0]["local_path"])
    original.write_text(original.read_text(encoding="utf-8") +
                        "\n\nNew unauthorized source claim.", encoding="utf-8")
    with pytest.raises(ValueError, match="source content changed"):
        execute_factory_source_stage(manifest, storage)
    assert len(OpportunityGraphStore(storage).list_records("Evidence")) == 2


def test_partial_input_failure_is_resumable_without_duplication(tmp_path):
    manifest, storage, case = new_unrelated_case(tmp_path)
    missing = Path(case["sources"][1]["local_path"])
    saved = missing.read_text(encoding="utf-8")
    missing.unlink()
    with pytest.raises(ValueError, match="not fully read"):
        execute_factory_source_stage(manifest, storage)
    missing.write_text(saved, encoding="utf-8")
    first = execute_factory_source_stage(manifest, storage)
    second = execute_factory_source_stage(manifest, storage)
    assert first["source_count"] == second["source_count"] == 2
    assert second["new_source_snapshots"] == 0
    assert first["receipt_sha256"] == second["receipt_sha256"]


def test_independent_subprocess_cold_replay_one_command(tmp_path):
    manifest, storage, _ = new_unrelated_case(tmp_path)
    first = execute_factory_source_stage(manifest, storage)
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_factory_source_stage.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run([
        sys.executable, str(script), "--manifest", str(manifest),
        "--storage-root", str(storage),
    ], check=True, capture_output=True, text=True, env=env)
    cold = json.loads(result.stdout)
    assert cold["receipt_sha256"] == first["receipt_sha256"]
    assert cold["new_source_snapshots"] == 0


def test_installed_whitecrow_supports_new_unrelated_family(tmp_path, monkeypatch):
    pytest.importorskip("litops")
    pytest.importorskip("whitecrow.litops_import")
    from litops import config as litops_config
    manifest, storage, _ = new_unrelated_case(tmp_path)
    litops_root = tmp_path / "private-litops"
    monkeypatch.setenv("LITOPS_ROOT", str(litops_root))
    monkeypatch.setenv("LITOPS_SKIP_DOTENV", "1")
    monkeypatch.setattr(litops_config, "_config_cache", None)
    first = execute_factory_source_stage(manifest, storage, litops_root=litops_root)
    again = execute_factory_source_stage(manifest, storage, litops_root=litops_root)
    assert first["whitecrow_context_packs"] == 1
    assert first["new_whitecrow_sources"] == 2
    assert first["new_whitecrow_contexts"] == 1
    assert again["new_whitecrow_sources"] == again["new_whitecrow_contexts"] == 0
    assert first["receipt_sha256"] == again["receipt_sha256"]
    receipt = json.loads((storage / "talk_corpora" / "NEW-CORPUS-001" /
                          "litops_whitecrow_stage.json").read_text(encoding="utf-8"))
    assert len(receipt["whitecrow_first_workset_context_ids"]) == 1
    assert not receipt["whitecrow_first_workset_manuscript"]
    assert not receipt["whitecrow_w23_certification_available"]


def test_w1_not_silently_inferred_for_unrelated_case(tmp_path):
    manifest, storage, _ = new_unrelated_case(tmp_path)
    with pytest.raises(ValueError, match="2025 course fulltext limitation"):
        execute_factory_source_stage(manifest, storage, manual_w1_reopen=True)
    # Partial source-stage registry is recoverable with W1 explicitly disabled.
    good = execute_factory_source_stage(manifest, storage)
    assert good["new_source_snapshots"] == 0
    assert good["manual_w1_proposals"] == 0


def _multiwave_packets(tmp_path: Path):
    from tests.test_trm073_w3_discovery import _synthetic_w3_packet
    w2 = packet()
    w2["case_id"] = "NEW-CORPUS-001"
    w3 = _synthetic_w3_packet()
    w3["case_id"] = "NEW-CORPUS-001"
    w2_path = tmp_path / "W2-packet.json"
    w3_path = tmp_path / "W3-packet.json"
    w2_path.write_text(json.dumps(w2, ensure_ascii=False), encoding="utf-8")
    w3_path.write_text(json.dumps(w3, ensure_ascii=False), encoding="utf-8")
    return w2_path, w3_path


def test_one_factory_entry_runs_both_independent_wave_schemas_with_cold_replay(tmp_path):
    manifest, storage, _ = new_unrelated_case(tmp_path)
    w2, w3 = _multiwave_packets(tmp_path)
    first = execute_factory_source_stage(
        manifest, storage, research_packet_paths=[w2, w3],
    )
    second = execute_factory_source_stage(
        manifest, storage, research_packet_paths=[w2, w3],
    )
    assert first["research_wave_count"] == 2
    assert first["w2_proposals"] == 6
    assert first["w3_proposed_unqualified_routes"] == 3
    assert first["w3_proposals"] == 2
    assert first["receipt_sha256"] == second["receipt_sha256"]
    assert second["new_source_snapshots"] == 0
    receipt = json.loads(Path(first["receipt_path"]).read_text(encoding="utf-8"))
    assert [r["wave_id"] for r in receipt["research_packet_pins"]] == [
        "W2", "W3-SYNTH"
    ] or len(set(r["wave_id"] for r in receipt["research_packet_pins"])) == 2
    assert len(receipt["research_wave_receipts"]) == 2
    assert receipt["w12_equivalent_routes"] == 0
    assert receipt["article_seed_created"] == 0
    assert not receipt["world_mutated"]
    assert receipt["external_send"] == "DISABLED"
    graph = OpportunityGraphStore(storage)
    assert graph.list_records("ArticleSeed") == []
    assert graph.list_records("OpportunityRoute") == []
    assert len(graph.list_records("Evidence")) > 10


def test_multiwave_input_different_case_fails_before_source_intake(tmp_path):
    manifest, storage, _ = new_unrelated_case(tmp_path)
    w2, w3 = _multiwave_packets(tmp_path)
    data = json.loads(w3.read_text(encoding="utf-8"))
    data["case_id"] = "ANOTHER-CASE"
    w3.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="different case"):
        execute_factory_source_stage(
            manifest, storage, research_packet_paths=[w2, w3],
        )
    assert not storage.exists()


def test_multiwave_repeated_wave_id_rejected_before_source_intake(tmp_path):
    manifest, storage, _ = new_unrelated_case(tmp_path)
    w2, w3 = _multiwave_packets(tmp_path)
    data = json.loads(w3.read_text(encoding="utf-8"))
    first = json.loads(w2.read_text(encoding="utf-8"))
    data["wave_id"] = first["wave_id"]
    w3.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate research-wave ID"):
        execute_factory_source_stage(
            manifest, storage, research_packet_paths=[w2, w3],
        )
    assert not storage.exists()


def test_existing_multiwave_checkpoint_rejects_changed_w3_bytes(tmp_path):
    manifest, storage, _ = new_unrelated_case(tmp_path)
    w2, w3 = _multiwave_packets(tmp_path)
    baseline = execute_factory_source_stage(
        manifest, storage, research_packet_paths=[w2, w3],
    )
    obj = json.loads(w3.read_text(encoding="utf-8"))
    obj["route_candidates"][0]["required_next_test"] += " Another hypothesis."
    w3.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="immutable case checkpoint"):
        execute_factory_source_stage(
            manifest, storage, research_packet_paths=[w2, w3],
        )
    assert Path(baseline["receipt_path"]).is_file()
    assert len(OpportunityGraphStore(storage).list_records("ArticleSeed")) == 0


def test_unknown_future_wave_schema_fails_closed_preflight(tmp_path):
    manifest, storage, _ = new_unrelated_case(tmp_path)
    w2, w3 = _multiwave_packets(tmp_path)
    obj = json.loads(w3.read_text(encoding="utf-8"))
    obj["schema"] = "W4_CONJECTURAL_UNSUPPORTED"
    w3.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported research packet schema"):
        execute_factory_source_stage(
            manifest, storage, research_packet_paths=[w2, w3],
        )
    assert not storage.exists()
