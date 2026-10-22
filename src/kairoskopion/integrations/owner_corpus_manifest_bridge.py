"""Convert owner-verified preexisting real-source captures to ONE Factory manifest.

Reuses a source archive instead of human copy/paste into a second workbench.
This bridge validates every provider/source identity and frozen backing byte
before emitting a TRM074_COLD_CASE_V1 manifest. Stored XLSX is held as
binary evidence WITHOUT claiming worksheet, formula, or 2026 policy coverage.
No source text, original blobs, credentials, scientific claims, article seeds or
journal submissions leave the owner-private host.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Any

OWNER_SCHEMA = "TRIMURTI_L3_REAL_SOURCE_MANIFEST_v0.3"
CAPTURE_SCHEMA = "L3_DRIVE_CAPTURE_V2"
OUTPUT_SCHEMA = "TRM074_COLD_CASE_V1"
MAX_RAW = 30_000_000


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _read_json(path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError("owner manifest/receipt missing or outside byte bounds")
    data = path.read_bytes()
    obj = json.loads(data.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("owner manifest/receipt must be JSON object")
    return obj, _sha(data)


def _source(provider_id: str, key: str, name: str, local_path: str, expected_sha: str) -> tuple[str, str]:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{5,200}", provider_id):
        raise ValueError("owner source provider ID invalid")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{2,100}", key):
        raise ValueError("owner source key invalid")
    path = Path(local_path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_RAW:
        raise ValueError(f"{key}: owner local file missing or untrusted")
    if path.name != name:
        raise ValueError(f"{key}: owner frozen path/name disagreement")
    raw = path.read_bytes()
    if _sha(raw) != str(expected_sha).lower():
        raise ValueError(f"{key}: frozen owner source SHA mismatch")
    return "drive:" + provider_id, _sha(raw)


def convert_owner_corpus_manifest(
    owner_manifest: str | Path,
    capture_receipt: str | Path,
    *,
    output_manifest: str | Path,
) -> dict[str, Any]:
    """Pure owner-source-version adapter, no journal, author or WORLD promotion."""
    source_file, owner_sha = _read_json(Path(owner_manifest))
    capture_file, capture_sha = _read_json(Path(capture_receipt))
    if source_file.get("schema") != OWNER_SCHEMA or capture_file.get("schema") != CAPTURE_SCHEMA:
        raise ValueError("unsupported owner L3/capture source schema")
    case_id = str(source_file.get("case_id") or "")
    if (case_id != capture_file.get("case_id")
            or not re.fullmatch(r"[a-zA-Z0-9_-]{3,100}", case_id)):
        raise ValueError("owner corpus/capture case ID mismatch")
    if (source_file.get("no_external_send") is not True
            or source_file.get("no_world_mutation") is not True
            or source_file.get("mode") != "DRY_RUN"):
        raise ValueError("owner corpus safety gates absent")
    documents = source_file.get("drive_sources") or []
    binary_files = source_file.get("source_files") or []
    captures = capture_file.get("sources") or []
    if not documents or not isinstance(documents, list) or not isinstance(binary_files, list):
        raise ValueError("unbounded or missing owner corpus sources")
    if len(documents) + len(binary_files) != len(captures) or len(captures) > 200:
        raise ValueError("source count mismatch: no silent omission permitted")
    by_key: dict[str, dict[str, Any]] = {}
    seen_provider: set[str] = set()
    for capture in captures:
        key = str(capture.get("key") or "")
        if key in by_key:
            raise ValueError("duplicate provider source key in capture receipt")
        by_key[key] = capture

    sources: list[dict[str, Any]] = []
    auxiliary: list[dict[str, Any]] = []
    for item in documents:
        key = str(item.get("key") or "")
        capture = by_key.pop(key, None)
        if capture is None:
            raise ValueError("owner Drive source missing in capture receipt")
        provider = str(item.get("provider_id") or "")
        srcid, raw_sha = _source(
            provider, key, Path(str(item.get("local_path") or "")).name,
            str(item.get("local_path") or ""), str(item.get("sha256") or ""),
        )
        if (capture.get("source_id") != srcid
                or capture.get("sha256") != raw_sha
                or capture.get("path") != item["local_path"]):
            raise ValueError("owner source and capture receipt byte/provider identity mismatch")
        if capture.get("result") not in {"FETCHED", "EXISTING_READBACK"}:
            raise ValueError("owner source was never captured")
        if item.get("source_format") != "DRIVE_NATIVE_TXT_EXPORT":
            raise ValueError("owner text source format not established")
        if not Path(item["local_path"]).suffix.lower() == ".txt":
            raise ValueError("owner native text projection suffix unsupported")
        if srcid in seen_provider:
            raise ValueError("duplicated provider ID across owner sources")
        seen_provider.add(srcid)
        family = key.split("_", 1)[0] if key.startswith(("F01_", "F02_")) else "L3_RESEARCH"
        sources.append({
            "key": key, "family": family, "source_id": srcid,
            "source_url": f"https://docs.google.com/document/d/{provider}/edit",
            "local_path": item["local_path"],
            "raw_sha256": raw_sha,
            "kind": "RESEARCH_CONTEXT",
            "source_mime": "text/plain",
            "version": "source-key:" + key,
            "author_state": "NOT_VERIFIED",
            "owner_author_state_detail": str(capture.get("author_state") or "UNVERIFIED"),
            "read_coverage": "TEXT_EXTRACT_ONLY",
            "scope": "EXISTING_OWNER_TEXT_CAPTURE_NO_NATIVE_REVISION",
        })

    for item in binary_files:
        key = str(item.get("source_id") or "")
        capture = by_key.pop(key, None)
        if capture is None:
            raise ValueError("original binary owner file missing in capture receipt")
        provider = str(item.get("provider_id") or "")
        path = str(item.get("local_path") or "")
        srcid, raw_sha = _source(provider, key, Path(path).name, path, str(item.get("sha256") or ""))
        if (capture.get("source_id") != srcid
                or capture.get("sha256") != raw_sha
                or capture.get("path") != path):
            raise ValueError("owner original binary file raw/provider SHA mismatch")
        if srcid in seen_provider:
            raise ValueError("original DOCX/XLSX provider ID duplicates a captured text")
        seen_provider.add(srcid)
        url = f"https://drive.google.com/file/d/{provider}/view"
        if Path(path).suffix.lower() == ".docx":
            sources.append({
                "key": key, "family": "L3_ORIGINAL", "source_id": srcid,
                "source_url": url, "local_path": path,
                "raw_sha256": raw_sha,
                "kind": "WORD_EXTRACTED_TEXT",
                "source_mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "version": "ORIGINAL_DOCX_UNVERSIONED",
                "author_state": "EXTRACTED_TEXT_EMBEDDED_COMMENTS_UNREAD",
                "owner_author_state_detail": "OWNER_PRIVATE_ORIGINAL_COMMENT_COVERAGE_UNVERIFIED",
                "read_coverage": "DOCX_BODY_TEXT_COMMENTS_UNREAD",
                "scope": "DOCX_BODY_EXTRACTED_NOT_DOCUMENT_FULL_COVERAGE",
            })
        elif Path(path).suffix.lower() == ".xlsx":
            auxiliary.append({
                "key": key, "source_id": srcid, "source_url": url,
                "local_path": path, "raw_sha256": raw_sha,
                "source_mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "read_coverage": "BINARY_HELD_NO_SCIENTIFIC_EXTRACTION",
                "currentness": str(item.get("currentness") or "UNVERIFIED"),
                "rights_gate": "OWNER_PRIVATE",
            })
        else:
            raise ValueError("owner binary type unsupported; no silent omission")

    if by_key:
        raise ValueError("owner capture contains unaccounted source keys")
    if len(sources) + len(auxiliary) != len(captures):
        raise ValueError("owner source coverage count lost")
    result = {
        "schema": OUTPUT_SCHEMA, "case_id": case_id,
        "publication_send": "DISALLOWED",
        "sources": sources, "auxiliary_sources": auxiliary,
        "version_edges": [], "delta_pairs": [],
        "decision_events": [], "discussion_events": [],
        "conversion_provenance": {
            "schema": "TRM074_OWNER_CAPTURE_CONVERSION_V1",
            "owner_manifest_sha256": owner_sha, "capture_receipt_sha256": capture_sha,
            "owner_authority": "OWNER_PRIVATE_ONLY",
            "source_n": len(sources), "binary_held_n": len(auxiliary),
            "owner_science_approval": "NONE", "world_mutation": "NONE",
            "external_send": "DISABLED",
            "version_edges": "UNKNOWN_NOT_INFERRED",
        },
    }
    target = Path(output_manifest)
    data = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if target.is_symlink() or (target.is_file() and target.read_bytes() != data):
        raise ValueError("existing converted owner manifest changed; use new versioned output path")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)
    if target.read_bytes() != data:
        raise ValueError("converted owner manifest failed byte readback")
    return {
        "schema": "TRM074_OWNER_CAPTURE_CONVERSION_RECEIPT_V1",
        "case_id": case_id,
        "manifest_path": str(target),
        "manifest_sha256": _sha(data),
        "source_text_n": len(sources),
        "binary_held_n": len(auxiliary),
        "total_verified_provider_captures": len(captures),
        "author_admitted_articles": 0, "external_send": "DISABLED",
    }
