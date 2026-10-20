"""Native Google Docs manifest -> owner-private Factory in ONE bounded operator call."""
from __future__ import annotations

from collections import Counter
import copy
import json
from pathlib import Path

import pytest

from kairoskopion.services.corpus_factory_entry import execute_factory_source_stage
from kairoskopion.integrations import native_docs_capture as capture
from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from tests.test_native_docs_source_capture import _doc


@pytest.fixture
def authorized_native_provider(monkeypatch):
    from trimurti.docs_api_client import StaticDocsApiClient
    from trimurti.acquisition_store import TrustedAcquisitionStore
    from trimurti.native_docs_transport import NativeGoogleDocsTransport

    original = capture.capture_native_doc
    invoked = Counter()
    failed = set()
    content = {
        "NATIVE-ONE-001": "Prior author text and methodological assumptions.\n",
        "NATIVE-TWO-002": "Later author text including a revised conceptual distinction.\n",
    }

    def authorized(source_id, source_url, owner_capture_root):
        docid = source_id[6:]
        invoked[docid] += 1
        if docid in failed:
            raise ValueError("simulated native provider temporary 429")
        root = Path(owner_capture_root)
        reader = NativeGoogleDocsTransport(
            client=StaticDocsApiClient({docid: _doc(docid, content[docid])}),
            snapshot_store=TrustedAcquisitionStore(root / "trusted_native_docs"),
        )
        return original(source_id, source_url, root, reader=reader)

    monkeypatch.setattr(capture, "capture_native_doc", authorized)
    return invoked, failed, content


def build_manifest(tmp_path: Path, *, case_id="MANIFEST-BATCH-001") -> Path:
    src = []
    for number, (docid, version) in enumerate((
        ("NATIVE-ONE-001", "v0.1"), ("NATIVE-TWO-002", "v0.2"),
    ), 1):
        src.append({
            "key": f"Z0{number}",
            "family": "Z",
            "kind": "SPEECH_SCRIPT",
            "version": version,
            "source_id": "drive:" + docid,
            "source_url": f"https://docs.google.com/document/d/{docid}/edit",
            "author_state": (
                "AI_EDITORIAL_PROPOSAL_NOT_AUTHOR_APPROVAL" if number == 1
                else "NOT_VERIFIED"
            ),
            "capture_transport": "native_docs",
        })
    manifest = {
        "schema": "TRM074_COLD_CASE_V1",
        "case_id": case_id,
        "publication_send": "DISALLOWED",
        "sources": src,
        "version_edges": [{"before":"Z01","after":"Z02",
                           "relation":"REGISTERED_SEQUENCE_NOT_PROVEN_DERIVATION"}],
        "delta_pairs": [["Z01", "Z02"]],
        "discussion_events": [], "decision_events": [],
        "missing_carriers": [
            {"family":"Z","kind":"NATIVE_DOCS_COMMENTS","status":"NOT_ACQUIRED"}
        ],
    }
    path = tmp_path / "owner-manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


def test_single_manifest_hydrates_native_provider_and_pins_source_without_chat(
    tmp_path, authorized_native_provider,
):
    requests, _, _ = authorized_native_provider
    manifest = build_manifest(tmp_path)
    storage = tmp_path / "factory"
    capture_root = tmp_path / "owner-private-captures"
    first = execute_factory_source_stage(
        manifest, storage, native_capture_root=capture_root,
    )
    second = execute_factory_source_stage(
        manifest, storage, native_capture_root=capture_root,
    )
    assert sum(requests.values()) == 2  # first read only; replay uses pins
    assert first["new_native_captures"] == 2
    assert first["reused_native_captures"] == 0
    assert second["new_native_captures"] == 0
    assert second["reused_native_captures"] == 2
    assert first["receipt_sha256"] == second["receipt_sha256"]
    assert first["new_source_snapshots"] == 2
    assert second["new_source_snapshots"] == 0
    receipt = json.loads(Path(first["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["native_source_count"] == 2
    assert receipt["native_replay_policy"] == "IMMUTABLE_PIN_NO_PROVIDER_RECHECK"
    assert receipt["derived_manifest_sha256"]
    ledger = json.loads((storage / "talk_corpora" / "MANIFEST-BATCH-001" /
                         "case_ledger.json").read_text(encoding="utf-8"))
    assert ledger["source_snapshots"][0]["author_state"] == "AI_EDITORIAL_PROPOSAL_NOT_AUTHOR_APPROVAL"
    assert ledger["source_snapshots"][1]["author_state"] == "NOT_VERIFIED"
    assert len(ledger["textual_deltas"]) == 1
    assert all(x["native_structural_attestation"] for x in ledger["source_snapshots"])
    assert OpportunityGraphStore(storage).list_records("World") == []
    assert OpportunityGraphStore(storage).list_records("ArticleSeed") == []
    assert OpportunityGraphStore(storage).list_records("OpportunityRoute") == []


def test_partial_external_failure_resumes_only_missing_native_doc(
    tmp_path, authorized_native_provider,
):
    requests, failed, _ = authorized_native_provider
    manifest = build_manifest(tmp_path)
    stage = tmp_path / "factory"
    cap_root = tmp_path / "private-native"
    failed.add("NATIVE-TWO-002")
    with pytest.raises(ValueError, match="429"):
        execute_factory_source_stage(
            manifest, stage, native_capture_root=cap_root,
        )
    assert not stage.exists()
    assert requests == Counter({"NATIVE-ONE-001": 1, "NATIVE-TWO-002": 1})
    assert len(list((cap_root / "case_pins" / "MANIFEST-BATCH-001").glob("*.json"))) == 1

    failed.clear()
    result = execute_factory_source_stage(
        manifest, stage, native_capture_root=cap_root,
    )
    assert result["new_native_captures"] == 1
    assert result["reused_native_captures"] == 1
    assert requests == Counter({"NATIVE-ONE-001": 1, "NATIVE-TWO-002": 2})
    assert len(list((cap_root / "case_pins" / "MANIFEST-BATCH-001").glob("*.json"))) == 2
    assert len(OpportunityGraphStore(stage).list_records("Evidence")) == 2


def test_provider_changed_after_checkpoint_is_not_silently_substituted(
    tmp_path, authorized_native_provider,
):
    requests, _, content = authorized_native_provider
    manifest = build_manifest(tmp_path)
    stage = tmp_path / "factory"
    cap_root = tmp_path / "captures"
    initial = execute_factory_source_stage(
        manifest, stage, native_capture_root=cap_root,
    )
    content["NATIVE-ONE-001"] = "Changed online source, not accepted as same revision.\n"
    repeat = execute_factory_source_stage(
        manifest, stage, native_capture_root=cap_root,
    )
    assert initial["receipt_sha256"] == repeat["receipt_sha256"]
    assert sum(requests.values()) == 2
    assert repeat["new_native_captures"] == 0
    # Deliberately create a NEW author-input case to refresh the source.
    newcase = build_manifest(tmp_path, case_id="MANIFEST-BATCH-NEW")
    fresh = execute_factory_source_stage(
        newcase, tmp_path / "factory-new", native_capture_root=cap_root,
    )
    assert fresh["source_count"] == 2
    assert requests["NATIVE-ONE-001"] == 2


def test_tampered_cached_projection_fails_without_provider_or_factory_mutations(
    tmp_path, authorized_native_provider,
):
    requests, _, _ = authorized_native_provider
    manifest = build_manifest(tmp_path)
    storage = tmp_path / "factory"
    cap_root = tmp_path / "captures"
    initial = execute_factory_source_stage(
        manifest, storage, native_capture_root=cap_root,
    )
    sources = list((cap_root / "text").glob("NATIVE-ONE-001_*.txt"))
    assert len(sources) == 1
    sources[0].write_text("Unverified replacement text with fabricated assertions.", encoding="utf-8")
    with pytest.raises(ValueError, match="text projection diverged"):
        execute_factory_source_stage(
            manifest, storage, native_capture_root=cap_root,
        )
    assert sum(requests.values()) == 2
    assert Path(initial["receipt_path"]).is_file()
    assert len(OpportunityGraphStore(storage).list_records("Evidence")) == 2


def test_preflight_duplicate_and_unsafe_id_never_touch_provider(
    tmp_path, authorized_native_provider,
):
    requests, _, _ = authorized_native_provider
    manifest = build_manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["sources"][1]["source_id"] = payload["sources"][0]["source_id"]
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate or missing"):
        execute_factory_source_stage(
            manifest, tmp_path / "stage", native_capture_root=tmp_path / "captures",
        )
    assert not requests

    payload["sources"][1]["source_id"] = "drive:../../SECRET"
    payload["sources"][1]["source_url"] = "https://docs.google.com/document/d/../../SECRET/edit"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="safe fixed ID"):
        execute_factory_source_stage(
            manifest, tmp_path / "stage", native_capture_root=tmp_path / "captures",
        )
    assert not requests


def test_owner_explicit_private_capture_root_required(
    tmp_path, authorized_native_provider,
):
    requests, _, _ = authorized_native_provider
    manifest = build_manifest(tmp_path)
    with pytest.raises(ValueError, match="explicit private capture root"):
        execute_factory_source_stage(manifest, tmp_path / "factory")
    assert not requests
    with pytest.raises(ValueError, match="must be isolated"):
        execute_factory_source_stage(
            manifest, tmp_path / "factory",
            native_capture_root=tmp_path,
        )
    assert not requests



def test_user_accepted_state_cannot_be_attested_by_manifest_alone(
    tmp_path, authorized_native_provider,
):
    requests, _, _ = authorized_native_provider
    manifest = build_manifest(tmp_path)
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    doc["sources"][0]["author_state"] = "USER_ACCEPTED_CONCEPTS_ONLY"
    manifest.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="explicit author decision"):
        execute_factory_source_stage(
            manifest, tmp_path / "factory",
            native_capture_root=tmp_path / "private",
        )
    assert not requests
    assert not (tmp_path / "factory").exists()


def test_cached_native_receipt_cannot_be_substituted_from_other_real_id(
    tmp_path, authorized_native_provider,
):
    requests, _, _ = authorized_native_provider
    manifest = build_manifest(tmp_path)
    storage, root = tmp_path / "factory", tmp_path / "captures"
    execute_factory_source_stage(manifest, storage, native_capture_root=root)
    pins = [json.loads(p.read_text(encoding="utf-8"))
            for p in (root / "case_pins" / "MANIFEST-BATCH-001").glob("*.json")]
    assert len(pins) == 2
    first = next(p for p in pins if p["source_id"] == "drive:NATIVE-ONE-001")
    second = next(p for p in pins if p["source_id"] == "drive:NATIVE-TWO-002")
    pin_path = next(
        p for p in (root / "case_pins" / "MANIFEST-BATCH-001").glob("*.json")
        if json.loads(p.read_text(encoding="utf-8"))["source_id"] == first["source_id"]
    )
    first["source_receipt"] = second["source_receipt"]
    pin_path.write_text(json.dumps(first), encoding="utf-8")
    with pytest.raises(ValueError, match="substituted another Drive identity"):
        execute_factory_source_stage(manifest, storage, native_capture_root=root)
    assert sum(requests.values()) == 2


def test_mixed_local_and_native_inputs_keep_distinct_provenance(
    tmp_path, authorized_native_provider,
):
    requests, _, _ = authorized_native_provider
    manifest = build_manifest(tmp_path)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    local = tmp_path / "separate-local-record.txt"
    local.write_text("Locally copied owner material, not a native Docs read.\n", encoding="utf-8")
    raw["sources"].append({
        "key":"LOCAL-001", "family":"LOCAL", "kind":"SOURCE_TRANSCRIPT",
        "version":"original",
        "source_id":"drive:LOCAL-OWNER-001",
        "source_url":"https://docs.google.com/document/d/LOCAL-OWNER-001/edit",
        "author_state":"NOT_VERIFIED",
        "capture_transport":"local",
        "local_path":str(local),
        "read_coverage":"TEXT_EXTRACT_ONLY",
    })
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    result = execute_factory_source_stage(
        manifest, tmp_path / "factory",
        native_capture_root=tmp_path / "private",
    )
    assert result["source_count"] == 3
    assert result["new_native_captures"] == 2
    assert sum(requests.values()) == 2
    case = json.loads(
        (tmp_path / "factory" / "talk_corpora" / "MANIFEST-BATCH-001" / "case_ledger.json"
         ).read_text(encoding="utf-8"))
    own = next(x for x in case["source_snapshots"] if x["key"] == "LOCAL-001")
    assert own["native_structural_attestation"] is None
    assert own["read_coverage"] == "TEXT_EXTRACT_ONLY"
    assert all(x["native_structural_attestation"]
               for x in case["source_snapshots"] if x["key"] != "LOCAL-001")
