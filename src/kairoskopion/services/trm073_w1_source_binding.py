"""Optional W1 manifest bindings for TRM-073 head discovery returns.

Resolves versioned original sources from a local TRM074 cold-case manifest.
No network I/O; does not read source text into receipts.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA = "TRM074_COLD_CASE_V1"
W3_HEADS = frozenset({"HEAD-01", "HEAD-02", "HEAD-03"})


def enrich_packet_from_env(packet: dict[str, Any]) -> dict[str, Any]:
    """Apply optional operator env overlays without mutating the on-disk packet."""
    out = dict(packet)
    manifest_path = os.environ.get("TRM073_W1_SOURCE_MANIFEST")
    bindings_json = os.environ.get("TRM073_ORIGINAL_HEAD_SOURCES")
    if manifest_path and not out.get("w1_source_manifest_path"):
        out["w1_source_manifest_path"] = manifest_path
    if bindings_json and not out.get("original_head_sources"):
        out["original_head_sources"] = json.loads(bindings_json)
    return out


def load_w1_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("W1 source manifest must be a regular local file")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("unsupported W1 source manifest schema")
    return manifest


def _source_index(manifest: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for source in manifest.get("sources") or []:
        if not isinstance(source, dict):
            continue
        family = str(source.get("family") or "").strip()
        key = str(source.get("key") or "").strip()
        if family and key:
            index[(family, key)] = source
    return index


def _content_digest(source: dict[str, Any]) -> tuple[str | None, str]:
    local_path = str(source.get("local_path") or "").strip()
    if not local_path:
        return None, "NO_LOCAL_PATH"
    path = Path(local_path)
    if not path.is_file() or path.is_symlink():
        return None, "LOCAL_FILE_MISSING"
    digest = sha256(path.read_bytes()).hexdigest().upper()
    return digest, "LOCAL_FILE_DIGEST"


def resolve_head_bindings(
    packet: dict[str, Any],
    manifest: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """Map all three T3 talk heads to manifest source rows when packet supplies bindings."""
    bindings_in = packet.get("original_head_sources") or []
    if not bindings_in:
        return {}
    if manifest is None:
        raise ValueError("original_head_sources requires w1_source_manifest_path")
    index = _source_index(manifest)
    resolved: dict[str, dict[str, Any]] = {}
    for row in bindings_in:
        if not isinstance(row, dict):
            raise ValueError("original_head_sources entries must be objects")
        head_id = str(row.get("head_id") or "").strip()
        if head_id not in W3_HEADS:
            raise ValueError("original_head_sources head_id must be HEAD-01, HEAD-02 or HEAD-03")
        family = str(row.get("source_family") or "").strip()
        key = str(row.get("source_key") or "").strip()
        if not family or not key:
            raise ValueError(f"{head_id} binding requires source_family and source_key")
        source = index.get((family, key))
        if source is None:
            raise ValueError(f"W1 manifest has no source for family={family} key={key}")
        content_sha256, digest_status = _content_digest(source)
        expected_sha = str(row.get("expected_content_sha256") or "").strip().upper()
        expected_source_id = str(row.get("expected_source_id") or "").strip()
        expected_version = str(row.get("expected_version") or "").strip()
        if expected_source_id and str(source.get("source_id") or "").strip() != expected_source_id:
            raise ValueError(f"{head_id} expected_source_id does not match W1 manifest row")
        if expected_version and str(source.get("version") or "").strip() != expected_version:
            raise ValueError(f"{head_id} expected_version does not match W1 manifest row")
        binding_verification = "PENDING_NO_EXPECTED_HASH"
        if expected_sha:
            if content_sha256 is None:
                binding_verification = "PENDING_BYTES_UNAVAILABLE"
            elif content_sha256 != expected_sha:
                raise ValueError(f"{head_id} local source bytes do not match expected_content_sha256")
            else:
                binding_verification = "VERIFIED_BYTES"
        elif content_sha256 is not None:
            binding_verification = "DIGEST_ONLY_NO_PINNED_EXPECTATION"
        method = str(row.get("research_method") or source.get("research_method") or "UNKNOWN").strip()
        if not method:
            method = "UNKNOWN"
        resolved[head_id] = {
            "head_id": head_id,
            "source_family": family,
            "source_key": key,
            "source_id": source.get("source_id"),
            "version": source.get("version"),
            "kind": source.get("kind"),
            "author_state": source.get("author_state"),
            "content_sha256": content_sha256,
            "content_digest_status": digest_status,
            "expected_content_sha256": expected_sha or None,
            "binding_verification": binding_verification,
            "research_method": method,
            "passage_anchor_status": "SOURCE_ANCHOR_PENDING",
        }
    return resolved


def manifest_for_packet(packet: dict[str, Any]) -> dict[str, Any] | None:
    path_text = str(packet.get("w1_source_manifest_path") or "").strip()
    if not path_text:
        return None
    return load_w1_manifest(Path(path_text))


def verify_persisted_head_bindings_on_readback(
    manifest_path: Path | None,
    bindings: dict[str, dict[str, Any]] | None,
) -> None:
    """Re-hash W1 manifest source files on cold readback; do not trust stored digests alone."""
    if not bindings:
        return
    needs_manifest = any(
        row.get("binding_verification") == "VERIFIED_BYTES"
        for row in bindings.values()
        if isinstance(row, dict)
    )
    if not needs_manifest:
        return
    if manifest_path is None or not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("readback VERIFIED_BYTES requires accessible w1_source_manifest_path")
    manifest = load_w1_manifest(manifest_path)
    index = _source_index(manifest)
    for head_id, binding in bindings.items():
        if not isinstance(binding, dict):
            raise ValueError("readback head_source_bindings entries must be objects")
        if binding.get("binding_verification") != "VERIFIED_BYTES":
            continue
        expected = str(binding.get("expected_content_sha256") or "").strip().upper()
        if not expected:
            raise ValueError(f"readback {head_id} VERIFIED_BYTES lacks expected_content_sha256")
        family = str(binding.get("source_family") or "").strip()
        key = str(binding.get("source_key") or "").strip()
        source = index.get((family, key))
        if source is None:
            raise ValueError(f"readback manifest missing source for {head_id} family={family} key={key}")
        content_sha256, _digest_status = _content_digest(source)
        if content_sha256 is None:
            raise ValueError(f"readback cannot re-hash original source bytes for {head_id}")
        if content_sha256 != expected:
            raise ValueError(f"readback {head_id} source bytes no longer match pinned expected_content_sha256")
        staged_source_id = str(binding.get("source_id") or "").strip()
        if staged_source_id:
            manifest_source_id = str(source.get("source_id") or "").strip()
            if manifest_source_id != staged_source_id:
                raise ValueError(f"readback {head_id} manifest source_id mismatch vs staged binding")
        staged_version = str(binding.get("version") or "").strip()
        if staged_version:
            manifest_version = str(source.get("version") or "").strip()
            if manifest_version != staged_version:
                raise ValueError(f"readback {head_id} manifest version mismatch vs staged binding")
        persisted = str(binding.get("content_sha256") or "").strip().upper()
        if persisted and content_sha256 != persisted:
            raise ValueError(f"readback {head_id} persisted content_sha256 stale vs filesystem")
