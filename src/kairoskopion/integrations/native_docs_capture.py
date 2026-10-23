"""Existing TRM040 native Docs transport -> authenticated Kairoskopion source.

No OAuth implementation, no shell commands, no chat-mediated document bytes.
Consumes installed WhiteCrow/Trimurti NativeGoogleDocsTransport and its
provider-bound TrustedAcquisitionStore. Works only on Google-native Docs.
This adapter produces an explicitly scoped *text-run projection*. Its source
receipt records what was NOT acquired: comments or external object bytes.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any

STRUCTURAL_TEXT_SCOPE = "STRUCTURAL_TEXT_PROJECTION_COMMENTS_NOT_ACQUIRED"


def _digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _identity(source_id: str, url: str) -> str:
    if not source_id.startswith("drive:") or len(source_id) <= 6:
        raise ValueError("native Docs requires pinned Drive source ID")
    import re
    document_id = source_id[6:]
    if not re.fullmatch(r"[A-Za-z0-9_-]{5,200}", document_id):
        raise ValueError("native Docs provider object ID is not a safe fixed ID")
    expected = "https://docs.google.com/document/d/" + document_id + "/"
    if not url.startswith(expected):
        raise ValueError("native source Drive ID and URL disagree")
    return document_id


def _project(raw: bytes) -> bytes:
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("schema") != "trimurti/native_docs_structural/v1":
        raise ValueError("unrecognized native Docs structural payload")
    nodes = (payload.get("projection") or {}).get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("native Docs projection nodes missing")
    parts = []
    for node in nodes:
        if node.get("kind") == "text_run":
            value = node.get("text")
            if not isinstance(value, str):
                raise ValueError("native Docs text run is not text")
            parts.append(value)
    data = "".join(parts).encode("utf-8")
    if len(data) < 32:
        raise ValueError("native Docs source projection contains no usable text")
    return data


def _snapshot_store(root: Path) -> Any:
    # Installed Trimurti trusted implementation is the authority; missing
    # runtime dependency must FAIL CLOSED, not emulate its approval flags.
    from trimurti.acquisition_store import TrustedAcquisitionStore
    return TrustedAcquisitionStore(root)


def _assert_provider_snapshot(store: Any, receipt: Any, docid: str) -> bytes:
    from trimurti.acquisition_store import (
        COMPLETENESS_STRUCTURAL_FULL_TRAVERSAL, REVISION_STABLE,
    )
    from trimurti.source_receipt import FULL_CONTENT_READ
    if (receipt.resolution_state != FULL_CONTENT_READ
            or receipt.completeness_proof != COMPLETENESS_STRUCTURAL_FULL_TRAVERSAL
            or receipt.revision_consistency != REVISION_STABLE
            or not receipt.snapshot_verified
            or receipt.provider != "google_drive"
            or receipt.provider_object_id != docid
            or not receipt.content_hash_sha256
            or not receipt.provider_revision_id):
        raise ValueError("native Docs authority/coverage or revision gate blocked")
    record = store.get(receipt.snapshot_ref)
    if record is None:
        raise ValueError("native Docs trusted provider snapshot missing")
    if (record.provider_object_id != docid
            or record.provider != "google_drive"
            or record.content_hash_sha256 != receipt.content_hash_sha256
            or record.provider_revision_id != receipt.provider_revision_id
            or record.completeness_proof != COMPLETENESS_STRUCTURAL_FULL_TRAVERSAL
            or record.revision_consistency != REVISION_STABLE):
        raise ValueError("native Docs snapshot bound to wrong provider/revision")
    verdict = store.verify_record(record)
    if not verdict.verified:
        raise ValueError("native Docs independently verified snapshot failed")
    raw = Path(record.blob_path).read_bytes()
    if _digest(raw) != receipt.content_hash_sha256:
        raise ValueError("native structural source SHA-256 mismatch")
    return raw


def capture_native_doc(
    source_id: str, source_url: str, owner_capture_root: Path | str,
    *,
    reader: Any | None = None,
) -> dict[str, Any]:
    """Read on the authorized host; return a manifest source patch.

    Raw text and structural payload NEVER leave this owner-private root.
    The caller may merge the returned dictionary into a PRIVATE manifest.
    """
    docid = _identity(source_id, source_url)
    root = Path(owner_capture_root).resolve()
    store_root = root / "trusted_native_docs"
    store = _snapshot_store(store_root)
    if reader is None:
        from trimurti.native_docs_transport import NativeGoogleDocsTransport
        reader = NativeGoogleDocsTransport(snapshot_store=store)
    unavailable = reader.available()
    if unavailable:
        raise ValueError("native Docs existing transport unavailable")
    receipt = reader.fetch(
        source_ref=source_id,
        source_role="background_research",
        provider_object_id=docid,
    )
    raw = _assert_provider_snapshot(store, receipt, docid)
    text = _project(raw)
    text_sha = _digest(text)
    text_file = root / "text" / f"{docid}_{text_sha[:16]}.txt"
    text_file.parent.mkdir(parents=True, exist_ok=True)
    if text_file.exists():
        if text_file.read_bytes() != text:
            raise ValueError("existing native Docs projection bytes changed")
    else:
        temp = text_file.with_suffix(".tmp")
        temp.write_bytes(text)
        os.replace(temp, text_file)

    output = {
        "schema": "TRM074_NATIVE_DOCS_MATERIALIZED_SOURCE_V1",
        "source_id": source_id,
        "source_url": source_url,
        "native_snapshot_ref": receipt.snapshot_ref,
        "native_store_root": str(store_root),
        "native_structural_sha256": receipt.content_hash_sha256,
        "native_provider_revision_id": receipt.provider_revision_id,
        "native_coverage": receipt.completeness_proof,
        "revision_consistency": receipt.revision_consistency,
        "comments_coverage": receipt.comments_coverage or "NOT_ACQUIRED",
        "unresolved_embedded_object_count": receipt.unresolved_embedded_object_count,
        "local_path": str(text_file),
        "projection_text_sha256": text_sha,
        "projection_text_bytes": len(text),
        "read_coverage": STRUCTURAL_TEXT_SCOPE,
        "source_mime": "application/vnd.google-apps.document",
        "author_state": "NOT_VERIFIED",
        "scientific_approval": "NONE",
        "external_send": "DISABLED",
    }
    meta_file = root / "receipts" / f"{docid}_{receipt.content_hash_sha256[:16]}.json"
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if meta_file.exists() and meta_file.read_bytes() != encoded:
        raise ValueError("immutable native Docs receipt identity reused with changed values")
    if not meta_file.exists():
        meta_file.write_bytes(encoded)
    output["native_receipt_path"] = str(meta_file)
    return output


def verify_native_source(source: dict[str, Any]) -> dict[str, str]:
    """Independently verify native structural source on every Factory admission."""
    if source.get("read_coverage") != STRUCTURAL_TEXT_SCOPE:
        raise ValueError("not a native structurally verified source")
    docid = _identity(str(source["source_id"]), str(source["source_url"]))
    receipt_path = Path(str(source.get("native_receipt_path") or ""))
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise ValueError("native structural receipt unavailable")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (receipt.get("source_id") != source["source_id"]
            or receipt.get("source_url") != source["source_url"]
            or receipt.get("read_coverage") != STRUCTURAL_TEXT_SCOPE
            or receipt.get("comments_coverage") != "NOT_ACQUIRED"
            or receipt.get("external_send") != "DISABLED"):
        raise ValueError("native Docs receipt identity or scope mismatch")
    if Path(str(receipt.get("local_path"))).resolve() != Path(source["local_path"]).resolve():
        raise ValueError("native text projection path changed")
    store = _snapshot_store(Path(str(receipt["native_store_root"])))
    record = store.get(str(receipt.get("native_snapshot_ref") or ""))
    if record is None or record.provider != "google_drive" or record.provider_object_id != docid:
        raise ValueError("native Docs trusted snapshot provider binding missing")
    if (record.content_hash_sha256 != receipt.get("native_structural_sha256")
            or record.provider_revision_id != receipt.get("native_provider_revision_id")
            or record.completeness_proof != "STRUCTURAL_FULL_TRAVERSAL"
            or record.revision_consistency != "STABLE"
            or not store.verify_record(record).verified):
        raise ValueError("native Docs revision/hash/completeness proof failed")
    structural = Path(record.blob_path).read_bytes()
    if _digest(structural) != record.content_hash_sha256:
        raise ValueError("native Docs stored payload corrupted")
    projected = _project(structural)
    captured = Path(source["local_path"]).read_bytes()
    if (_digest(projected) != receipt.get("projection_text_sha256")
            or captured != projected):
        raise ValueError("native Docs text projection diverged from its trusted snapshot")
    return {
        "native_snapshot_ref": record.snapshot_id,
        "native_provider_revision_id": record.provider_revision_id,
        "native_structural_sha256": record.content_hash_sha256,
        "projection_text_sha256": _digest(projected),
        "read_coverage": STRUCTURAL_TEXT_SCOPE,
    }



# ---------------------------------------------------------------------------
# Owner-authorized pinned multi-document collection for Factory case input
# ---------------------------------------------------------------------------


def materialize_native_manifest(
    case: dict[str, Any],
    original_manifest_sha256: str,
    capture_root: Path | str,
) -> tuple[Path, int, int, int]:
    """Use existing TRM040 to hydrate all native_docs sources in one bounded call.

    Each successfully captured source is durably pinned *before* starting the
    next document. On partial failure, a retry verifies and reuses those
    provider-bound snapshots. A replay deliberately does not claim that the
    provider has not changed since the pinned read; author must create a
    new case/wave for refresh rather than rewriting scientific provenance.
    """
    import copy
    import re

    sources = case.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 200:
        raise ValueError("native manifest source list must be bounded and nonempty")
    case_id = str(case.get("case_id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}", case_id):
        raise ValueError("invalid case identity")
    if case.get("publication_send") != "DISALLOWED":
        raise ValueError("external send must remain DISALLOWED")
    if not isinstance(original_manifest_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", original_manifest_sha256
    ):
        raise ValueError("source manifest immutable SHA-256 missing")
    if not isinstance(capture_root, (str, Path)):
        raise ValueError("explicit owner-private capture root required")

    keys: set[str] = set()
    ids: set[str] = set()
    count = 0
    # Preflight *all* entries before any external reads.
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("manifest source is not an object")
        key, source_id = str(source.get("key") or ""), str(source.get("source_id") or "")
        if not key or key in keys or not source_id or source_id in ids:
            raise ValueError("duplicate or missing source key/Drive identity")
        keys.add(key)
        ids.add(source_id)
        mode = source.get("capture_transport")
        if mode not in (None, "local", "native_docs"):
            raise ValueError("unsupported source capture transport")
        if mode == "native_docs":
            _identity(source_id, str(source.get("source_url") or ""))
            if source.get("local_path"):
                raise ValueError("native manifest may not predeclare source local_path")
            if not source.get("family") or not source.get("kind") or not source.get("version"):
                raise ValueError("native source needs family, carrier kind and version")
            if source.get("author_state") == "USER_ACCEPTED_CONCEPTS_ONLY":
                has_decision = any(
                    event.get("role") == "USER" and event.get("artifact") == key
                    for event in case.get("decision_events", [])
                )
                if not has_decision:
                    raise ValueError("author-accepted source lacks explicit author decision")
            count += 1
    if not count:
        raise ValueError("native batch contains no native_docs sources")

    root = Path(capture_root).resolve()
    derived_case = copy.deepcopy(case)
    new_count = reused_count = 0
    for item in derived_case["sources"]:
        if item.get("capture_transport") != "native_docs":
            continue
        item_id = str(item["source_id"])
        pin_sha = _digest(
            (case_id + "|" + original_manifest_sha256 + "|" + item_id).encode("utf-8")
        )
        pin_file = root / "case_pins" / case_id / f"{pin_sha}.json"
        native: dict[str, Any]
        if pin_file.is_file():
            pin = json.loads(pin_file.read_text(encoding="utf-8"))
            if (pin.get("schema") != "TRM074_NATIVE_DOCS_MANIFEST_PIN_V1"
                    or pin.get("manifest_sha256") != original_manifest_sha256
                    or pin.get("case_id") != case_id
                    or pin.get("source_id") != item_id
                    or pin.get("source_url") != item["source_url"]):
                raise ValueError("native Docs immutable case pin conflicts with manifest")
            native = pin.get("source_receipt")
            if not isinstance(native, dict):
                raise ValueError("native Docs existing source pin malformed")
            verify_native_source(native)
            reused_count += 1
        else:
            native = capture_native_doc(item_id, item["source_url"], root)
            verify_native_source(native)
            pin = {
                "schema": "TRM074_NATIVE_DOCS_MANIFEST_PIN_V1",
                "manifest_sha256": original_manifest_sha256,
                "case_id": case_id,
                "source_id": item_id,
                "source_url": item["source_url"],
                "source_receipt": native,
            }
            pin_file.parent.mkdir(parents=True, exist_ok=True)
            encoded_pin = (
                json.dumps(pin, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            ).encode("utf-8")
            if pin_file.exists():
                raise ValueError("concurrent native Docs case pin appeared")
            temp = pin_file.with_suffix(".tmp")
            temp.write_bytes(encoded_pin)
            os.replace(temp, pin_file)
            new_count += 1
        if native.get("source_id") != item_id or native.get("source_url") != item["source_url"]:
            raise ValueError("native source pin substituted another Drive identity")
        if Path(str(native.get("native_store_root") or "")).resolve() != (root / "trusted_native_docs").resolve():
            raise ValueError("native case pin points outside authorized trusted store")
        if (not Path(str(native.get("local_path") or "")).resolve().is_relative_to(root)
                or not Path(str(native.get("native_receipt_path") or "")).resolve().is_relative_to(root)):
            raise ValueError("native case pin projects outside owner-private capture root")
        prior_author = item.get("author_state", "NOT_VERIFIED")
        item.update(native)
        item["author_state"] = prior_author
        item["source_mime"] = "application/vnd.google-apps.document"
        item["scope"] = "PROVIDER_BOUND_NATIVE_DOCS_TEXT_COMMENT_AND_MEDIA_UNREAD"
        # Private source manifest is now locally pinned; an explicit second
        # execution may reuse it with independent verify_native_source.
        item["capture_transport"] = "local"
        item["captured_from_transport"] = "native_docs"

    payload = (json.dumps(derived_case, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    derived_path = root / "manifests" / f"{case_id}_{_digest(payload)[:20]}.json"
    derived_path.parent.mkdir(parents=True, exist_ok=True)
    if derived_path.exists():
        if derived_path.read_bytes() != payload:
            raise ValueError("native derived manifest immutable collision")
    else:
        temp = derived_path.with_suffix(".tmp")
        temp.write_bytes(payload)
        os.replace(temp, derived_path)
    return derived_path, count, new_count, reused_count
