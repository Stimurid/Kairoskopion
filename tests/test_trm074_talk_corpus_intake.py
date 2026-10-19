"""TRM-074 privacy-safe fixtures. No user documents or private source bytes."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from kairoskopion.services.talk_corpus_intake import run_case
from kairoskopion.registry import read_all


SPEC = (
    ("A", "A06", "A001", "SPEECH_SCRIPT", "v0.6", "NOT_VERIFIED",
     "Common Talk Title\n\nOriginal example on organizational boundary."),
    ("A", "A07", "A002", "SPEECH_SCRIPT", "v0.7", "NOT_VERIFIED",
     "Common Talk Title\n\nRevised example with a qualified boundary."),
    ("A", "A_SOURCE_TRANSCRIPT", "A003", "SOURCE_TRANSCRIPT", "unversioned",
     "ORIGINAL_TEXT_ONLY_AUDIO_UNVERIFIED", "Speech transcription text."),
    ("A", "A_RECONSTRUCTED_TRANSCRIPT", "A004", "RECONSTRUCTED_TRANSCRIPT",
     "unversioned", "RECONSTRUCTION_NOT_PERFORMANCE",
     "Reconstructed speech text, not an audio recording."),
    ("B", "B_BASELINE", "B001", "CONCEPT_BASELINE", "2026-10-12",
     "USER_ACCEPTED_CONCEPTS_ONLY",
     "Concept proposal.\n\nOWNER ACCEPTED IDEAS.\n\nFuture drafts need approval."),
    ("B", "B01", "B002", "SPEECH_SCRIPT", "v0.1", "NOT_VERIFIED",
     "Firm cognition.\n\nHypothetical example is not empirical."),
    ("B", "B02", "B003", "SPEECH_SCRIPT", "v0.2", "NOT_VERIFIED",
     "Firm cognition.\n\nHypothetical comparison is not empirical."),
    ("C", "C03", "C001", "SPEECH_SCRIPT", "v0.3", "NOT_VERIFIED",
     "Entrepreneurial situations.\n\nPrevious institutional boundary."),
    ("C", "C04", "C002", "SPEECH_SCRIPT", "v0.4", "NOT_VERIFIED",
     "Entrepreneurial situations.\n\nUpdated organization of labor."),
    ("CROSS", "COMPARE47C", "X001", "EDITORIAL_COMPARISON", "2026-10-15",
     "AI_EDITORIAL_PROPOSAL_NOT_AUTHOR_APPROVAL",
     "Documents are unchanged.\n\nThis is an editorial comparison."),
)


def fixture_case(tmp_path: Path) -> tuple[Path, Path, dict]:
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    sources = []
    for family, key, short_id, kind, version, state, body in SPEC:
        path = sources_dir / (key + ".txt")
        path.write_text(body, encoding="utf-8")
        sources.append({
            "family": family, "key": key,
            "source_id": "drive:" + short_id,
            "source_url": f"https://docs.google.com/document/d/{short_id}/edit",
            "local_path": str(path),
            "kind": kind, "version": version, "author_state": state,
        })
    case = {
        "schema": "TRM074_COLD_CASE_V1",
        "case_id": "T3-SYNTHETIC",
        "publication_send": "DISALLOWED",
        "sources": sources,
        "version_edges": [
            {"before": "A06", "after": "A07", "relation": "PRECEDES"},
            {"before": "B01", "after": "B02", "relation": "PRECEDES"},
            {"before": "C03", "after": "C04", "relation": "PRECEDES"},
            {"before": "B_BASELINE", "after": "B01", "relation": "CONCEPTUAL"},
        ],
        "delta_pairs": [["A06", "A07"], ["B01", "B02"], ["C03", "C04"]],
        "decision_events": [
            {"artifact": "B_BASELINE", "role": "USER",
             "kind": "AUTHOR_ACCEPTED_CONCEPTUAL_CONTENT",
             "quote": "OWNER ACCEPTED IDEAS",
             "authority_scope": "B_BASELINE_ONLY"},
            {"artifact": "COMPARE47C", "role": "AI_EDITORIAL",
             "kind": "PROPOSAL_UNADOPTED",
             "quote": "Documents are unchanged.",
             "authority_scope": "INTERPRETATION_ONLY"},
        ],
        "missing_carriers": [
            {"family": "A", "kind": "ORIGINAL_AUDIO",
             "status": "NOT_LOCATED_NOT_ASSUMED"},
            {"family": "C", "kind": "RECORDED_PERFORMANCE",
             "status": "NOT_LOCATED_NOT_ASSUMED"},
        ],
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
    return manifest, tmp_path / "result", case


def _save(manifest: Path, content: dict) -> None:
    manifest.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")


def _ledger(storage: Path) -> dict:
    return json.loads((storage / "talk_corpora" / "T3-SYNTHETIC" /
                       "case_ledger.json").read_text(encoding="utf-8"))


def test_three_lines_deltas_with_exact_source_anchors_and_registry(tmp_path):
    manifest, storage, _ = fixture_case(tmp_path)
    receipt = run_case(manifest, storage)
    data = _ledger(storage)
    assert receipt["source_count"] == 10
    assert receipt["delta_families"] == ["A", "B", "C"]
    assert receipt["held_candidates"] == 3
    assert receipt["new_source_snapshots"] == 10
    assert len(read_all("source_snapshots", base_dir=storage / "registries")) == 10
    for delta in data["textual_deltas"]:
        assert delta["delta_status"] == "DIFFERENT"
        assert delta["changes"][0]["before_source_id"].startswith("drive:")
        assert delta["changes"][0]["after_source_id"].startswith("drive:")
        assert delta["changes"][0]["before_passage"]["paragraph_sha256"]
        assert delta["changes"][0]["after_passage"]["paragraph_sha256"]
    assert all(not x["article_seed_created"] for x in data["held_article_seed_envelopes"])


def test_replay_and_independent_cold_process_are_idempotent(tmp_path):
    manifest, storage, _ = fixture_case(tmp_path)
    first = run_case(manifest, storage)
    second = run_case(manifest, storage)
    assert first["ledger_sha256"] == second["ledger_sha256"]
    assert second["new_source_snapshots"] == 0
    assert len(read_all("source_snapshots", base_dir=storage / "registries")) == 10
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_trm074_three_talk_intake.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    proc = subprocess.run(
        [sys.executable, str(script), "--manifest", str(manifest),
         "--storage-root", str(storage)],
        check=True, capture_output=True, text=True, env=env,
    )
    assert json.loads(proc.stdout)["ledger_sha256"] == first["ledger_sha256"]
    assert (storage / "talk_corpora" / "T3-SYNTHETIC" / "case_ledger.json").read_bytes().endswith(b"\n")


def test_same_title_different_drive_id_remain_distinct(tmp_path):
    manifest, storage, _ = fixture_case(tmp_path)
    run_case(manifest, storage)
    records = _ledger(storage)["source_snapshots"]
    a = [r for r in records if r["family"] == "A" and r["kind"] == "SPEECH_SCRIPT"]
    assert len({x["source_id"] for x in a}) == 2
    assert len({x["content_sha256"] for x in a}) == 2


def test_latest_is_not_author_approval_and_transcripts_remain_typed(tmp_path):
    manifest, storage, _ = fixture_case(tmp_path)
    run_case(manifest, storage)
    ledger = _ledger(storage)
    lookup = {s["key"]: s for s in ledger["source_snapshots"]}
    assert lookup["B02"]["author_state"] == "NOT_VERIFIED"
    assert lookup["B_BASELINE"]["author_state"] == "USER_ACCEPTED_CONCEPTS_ONLY"
    assert lookup["A_SOURCE_TRANSCRIPT"]["kind"] == "SOURCE_TRANSCRIPT"
    assert lookup["A_RECONSTRUCTED_TRANSCRIPT"]["kind"] == "RECONSTRUCTED_TRANSCRIPT"
    assert ledger["missing_carriers"][0]["status"] == "NOT_LOCATED_NOT_ASSUMED"
    assert all(x["gate"].startswith("HOLD_") for x in ledger["held_article_seed_envelopes"])


def test_partial_failure_then_replay_recovers_without_duplicate_snapshots(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    missing_file = Path(case["sources"][6]["local_path"])
    body = missing_file.read_text(encoding="utf-8")
    missing_file.unlink()
    with pytest.raises(ValueError, match="source not fully read"):
        run_case(manifest, storage)
    assert not (storage / "talk_corpora" / "T3-SYNTHETIC" /
                "case_ledger.json").exists()
    missing_file.write_text(body, encoding="utf-8")
    run_case(manifest, storage)
    again = run_case(manifest, storage)
    assert again["new_source_snapshots"] == 0
    assert len(read_all("source_snapshots", base_dir=storage / "registries")) == 10


def test_unverified_owner_claim_is_not_promoted(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    case["sources"][6]["author_state"] = "USER_ACCEPTED_CONCEPTS_ONLY"
    _save(manifest, case)
    with pytest.raises(ValueError, match="author decision|approval cannot be broadened"):
        run_case(manifest, storage)


def test_author_quote_must_be_exact_and_source_anchored(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    case["decision_events"][0]["quote"] = "NOT PRESENT"
    _save(manifest, case)
    with pytest.raises(ValueError, match="unanchored"):
        run_case(manifest, storage)


def test_wrong_drive_identity_and_duplicate_id_fail_closed(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    case["sources"][0]["source_url"] = "https://docs.google.com/document/d/DIFFERENT/edit"
    _save(manifest, case)
    with pytest.raises(ValueError, match="identity/url mismatch"):
        run_case(manifest, storage)
    case["sources"][0]["source_url"] = "https://docs.google.com/document/d/A001/edit"
    case["sources"][1]["source_id"] = case["sources"][0]["source_id"]
    case["sources"][1]["source_url"] = case["sources"][0]["source_url"]
    _save(manifest, case)
    with pytest.raises(ValueError, match="duplicate source ID"):
        run_case(manifest, storage)


def test_cross_family_delta_and_cycle_are_rejected(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    case["delta_pairs"] = [["A06", "B01"]]
    _save(manifest, case)
    with pytest.raises(ValueError, match="cross-family"):
        run_case(manifest, storage)
    case["delta_pairs"] = [["A06", "A07"]]
    case["version_edges"].append(
        {"before": "A07", "after": "A06", "relation": "PRECEDES"}
    )
    _save(manifest, case)
    with pytest.raises(ValueError, match="cycle"):
        run_case(manifest, storage)


def test_external_send_must_be_disallowed(tmp_path):
    manifest, storage, case = fixture_case(tmp_path)
    case["publication_send"] = "YES"
    _save(manifest, case)
    with pytest.raises(ValueError, match="sends must be disallowed"):
        run_case(manifest, storage)
