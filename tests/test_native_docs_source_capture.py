"""Native Docs -> Factory verified transport seam; private documents never in tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from kairoskopion.integrations.native_docs_capture import (
    STRUCTURAL_TEXT_SCOPE, _identity, capture_native_doc, verify_native_source,
)
from kairoskopion.services.talk_corpus_intake import run_case
from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore


def _doc(docid: str, text: str) -> dict:
    end = len(text)
    return {
        "documentId": docid, "revisionId": "REV-1", "title": "Same title",
        "tabs": [{
            "tabProperties": {
                "tabId": "tab.main", "title": "Main",
                "index": 0, "nestingLevel": 0,
            },
            "documentTab": {
                "body": {"content": [{
                    "startIndex": 0, "endIndex": end,
                    "paragraph": {
                        "elements": [{
                            "startIndex": 0, "endIndex": end,
                            "textRun": {"content": text, "textStyle": {}},
                        }],
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                    },
                }]},
                "documentStyle": {"pageSize": {}},
                "namedStyles": {"styles": []},
                "lists": {},
            },
        }],
    }


def _capture(tmp_path: Path, docid: str, text: str):
    pytest.importorskip("trimurti.native_docs_transport")
    from trimurti.docs_api_client import StaticDocsApiClient
    from trimurti.acquisition_store import TrustedAcquisitionStore
    from trimurti.native_docs_transport import NativeGoogleDocsTransport

    root = tmp_path / "owner-private"
    store = TrustedAcquisitionStore(root / "trusted_native_docs")
    reader = NativeGoogleDocsTransport(
        client=StaticDocsApiClient({docid: _doc(docid, text)}),
        snapshot_store=store,
    )
    url = f"https://docs.google.com/document/d/{docid}/edit"
    return capture_native_doc("drive:" + docid, url, root, reader=reader)


def test_pinned_native_docs_identity_requires_exact_original_drive_id():
    assert _identity("drive:DOC-A", "https://docs.google.com/document/d/DOC-A/edit") == "DOC-A"
    with pytest.raises(ValueError, match="Drive ID and URL disagree"):
        _identity("drive:DOC-A", "https://docs.google.com/document/d/DOC-B/edit")
    with pytest.raises(ValueError, match="pinned Drive source ID"):
        _identity("local:DOC-A", "https://docs.google.com/document/d/DOC-A/edit")


def test_mock_provider_native_capture_independently_verifies_text_and_bound_revision(tmp_path):
    captured = _capture(
        tmp_path, "DOC-NATIVE-A",
        "Original synthetic scholarly paragraph on work organization.\n",
    )
    native = verify_native_source(captured)
    assert captured["read_coverage"] == STRUCTURAL_TEXT_SCOPE
    assert captured["comments_coverage"] == "NOT_ACQUIRED"
    assert captured["external_send"] == "DISABLED"
    assert native["native_provider_revision_id"] == "REV-1"
    assert native["native_structural_sha256"] == captured["native_structural_sha256"]
    assert native["projection_text_sha256"] == captured["projection_text_sha256"]
    assert len(Path(captured["local_path"]).read_bytes()) > 32


def test_structural_source_projection_enters_actual_case_and_kairon(tmp_path):
    a = _capture(tmp_path, "DOC-NATIVE-01", "Existing method of production is insufficient.\n")
    b = _capture(tmp_path, "DOC-NATIVE-02", "New method of production requires explicit testing.\n")
    source_a = dict(a, key="A01", family="A", kind="SPEECH_SCRIPT", version="v0.1")
    source_b = dict(b, key="A02", family="A", kind="SPEECH_SCRIPT", version="v0.2")
    manifest = {
        "schema": "TRM074_COLD_CASE_V1",
        "case_id": "NATIVE-TEST-001",
        "publication_send": "DISALLOWED",
        "sources": [source_a, source_b],
        "version_edges": [{"before": "A01", "after": "A02", "relation": "PRECEDES"}],
        "delta_pairs": [["A01", "A02"]],
        "discussion_events": [],
        "decision_events": [],
        "missing_carriers": [{"family": "A", "kind": "COMMENT_BODY", "status": "NOT_ACQUIRED"}],
    }
    file = tmp_path / "manifest.json"
    file.write_text(json.dumps(manifest), encoding="utf-8")
    stage = tmp_path / "stage"
    first = run_case(file, stage)
    second = run_case(file, stage)
    assert first["source_count"] == 2
    assert second["new_source_snapshots"] == 0
    ledger = json.loads((stage / "talk_corpora" / "NATIVE-TEST-001" /
                         "case_ledger.json").read_text(encoding="utf-8"))
    assert len(ledger["textual_deltas"]) == 1
    assert all(x["read_coverage"] == STRUCTURAL_TEXT_SCOPE
               for x in ledger["source_snapshots"])
    assert all(x["native_structural_attestation"]["native_snapshot_ref"]
               for x in ledger["source_snapshots"])
    assert OpportunityGraphStore(stage).list_records("ArticleSeed") == []


def test_forged_local_text_does_not_override_trusted_provider_content(tmp_path):
    cap = _capture(tmp_path, "DOC-CORRUPT-TEXT",
                   "Original trustworthy synthetic source paragraph.\n")
    path = Path(cap["local_path"])
    path.write_text("A replacement with invented scientific claims.", encoding="utf-8")
    with pytest.raises(ValueError, match="text projection diverged"):
        verify_native_source(cap)


def test_wrong_provider_id_or_forged_snapshot_ref_is_rejected(tmp_path):
    cap = _capture(tmp_path, "DOC-BIND-A",
                   "Author source with exact provider binding verified.\n")
    forged = copy.deepcopy(cap)
    forged["source_id"] = "drive:DOC-BIND-B"
    forged["source_url"] = "https://docs.google.com/document/d/DOC-BIND-B/edit"
    with pytest.raises(ValueError, match="receipt identity"):
        verify_native_source(forged)
    path = Path(cap["native_receipt_path"])
    content = json.loads(path.read_text(encoding="utf-8"))
    content["native_snapshot_ref"] = "SNAP:FORGED"
    path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(ValueError, match="trusted snapshot provider binding missing"):
        verify_native_source(cap)


def test_incomplete_native_doc_cannot_be_claimed_as_full_read(tmp_path):
    pytest.importorskip("trimurti.native_docs_transport")
    from trimurti.docs_api_client import StaticDocsApiClient
    from trimurti.acquisition_store import TrustedAcquisitionStore
    from trimurti.native_docs_transport import NativeGoogleDocsTransport

    root = tmp_path / "owner-private"
    docid = "INCOMPLETE-TAB"
    no_text = {
        "documentId": docid, "revisionId": "REV-1",
        "tabs": [{"tabProperties": {"tabId": "t", "index": 0}}],
    }
    reader = NativeGoogleDocsTransport(
        client=StaticDocsApiClient({docid: no_text}),
        snapshot_store=TrustedAcquisitionStore(root / "trusted_native_docs"),
    )
    with pytest.raises(ValueError, match="authority/coverage or revision gate blocked"):
        capture_native_doc(
            "drive:" + docid,
            "https://docs.google.com/document/d/" + docid + "/edit",
            root, reader=reader,
        )
