"""Bounded W12 publisher-evidence capture via the existing Kairon HTTP adapter.

Exact human/research supplied URLs only. No search, journal approval, ArticleSeed,
or semantic self-certification. Capture files + manifest live in owner-private
storage, never as committed source fixtures. Repeated calls use immutable verified
bytes and retry only failed/unvalidated targets; no silent provider freshness claim.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Any

from ..adapters.venue.fulltext_fetch import acquire_explicit_fulltext, validate_download


MAX_TARGETS = 24
MAX_MANIFEST_BYTES = 200_000
_CAPTURE_STATES = {"validated", "acquired_unvalidated", "blocked", "failed"}


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _normalize_targets(targets: dict[str, str]) -> dict[str, str]:
    if not isinstance(targets, dict) or not targets:
        raise ValueError("no capture targets supplied")
    if len(targets) > MAX_TARGETS:
        raise ValueError("too many publisher capture targets")
    clean: dict[str, str] = {}
    for raw_key, raw_url in targets.items():
        if not isinstance(raw_key, str) or not isinstance(raw_url, str):
            raise ValueError("capture target must be KEY=URL strings")
        key = raw_key.strip()
        if not key or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key):
            raise ValueError("capture target key must not be blank or unsafe")
        if key in clean:
            raise ValueError("duplicate normalized capture target key")
        url = raw_url.strip()
        if not url or len(url) > 1500:
            raise ValueError("capture URL must be bounded and explicit")
        clean[key] = url
    return clean


def _read_previous(path: Path, targets: dict[str, str]) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("existing capture manifest is unsafe")
    previous = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(previous, dict):
        raise ValueError("existing capture manifest must be a keyed JSON object")
    if set(previous) != set(targets):
        raise ValueError("capture manifest target-key set changed; use new versioned output")
    for key, row in previous.items():
        if not isinstance(row, dict) or row.get("url") != targets[key]:
            raise ValueError(f"{key}: pinned publisher URL changed; use new output")
        state = row.get("status")
        if state not in _CAPTURE_STATES:
            raise ValueError(f"{key}: invalid stored capture state")
        if state == "validated":
            f = Path(str(row.get("path") or ""))
            if f.is_symlink() or not f.is_file():
                raise ValueError(f"{key}: verified capture file disappeared")
            raw = f.read_bytes()
            sha = _digest(raw)
            if (sha != row.get("sha256") or sha != row.get("readback_sha256")
                    or not (row.get("validation") or {}).get("valid")):
                raise ValueError(f"{key}: immutable publisher capture byte SHA mismatch")
            actual = validate_download(f, str(row.get("content_type") or ""))
            if not actual.get("valid"):
                raise ValueError(f"{key}: frozen source ceased to be a validated HTML carrier")
    return previous


def build_capture_manifest(
    targets: dict[str, str],
    *,
    output_dir: str | Path,
    manifest_path: str | Path,
    fixture_bytes: dict[str, bytes] | None = None,
    fixture_content_types: dict[str, str] | None = None,
    max_bytes: int = 4 * 1024 * 1024,
) -> dict[str, Any]:
    """Return a version-pinned publisher capture manifest readable by W12.

    New requests call the existing fulltext adapter, reusing the adapter's
    blocked/CAPTCHA states. A second identical run re-hashes local validated
    captures instead of contacting the publisher. Partial runs retry only
    blocked or unvalidated targets. To re-fetch an accepted source, choose
    a NEW owner-private manifest path and retain the original evidence.
    """
    clean = _normalize_targets(targets)
    if not (5_000 <= max_bytes <= 25 * 1024 * 1024):
        raise ValueError("publisher byte bound outside supported acquisition policy")
    manifest = Path(manifest_path)
    previous = _read_previous(manifest, clean)
    root = Path(output_dir)
    captures: dict[str, dict[str, Any]] = {}
    report: dict[str, dict[str, Any]] = {}
    all_validated = True
    for key, url in clean.items():
        prior = previous.get(key) or {}
        if prior.get("status") == "validated":
            captures[key] = prior
            report[key] = {"status": "validated", "url": url,
                           "sha256": prior["sha256"], "reused": True}
            continue
        result = acquire_explicit_fulltext(
            url,
            output_dir=root,
            max_bytes=max_bytes,
            fixture_bytes=(fixture_bytes or {}).get(key),
            fixture_content_type=(fixture_content_types or {}).get(key),
        )
        state = str(result.get("status") or "failed")
        if state not in _CAPTURE_STATES:
            raise ValueError(f"{key}: unsupported publisher acquisition state")
        record: dict[str, Any] = {
            "status": state, "url": url,
            "error_code": result.get("error_code"),
        }
        if state in {"validated", "acquired_unvalidated"}:
            capture_path = Path(result["path"])
            if capture_path.is_symlink() or not capture_path.is_file():
                raise ValueError(f"{key}: acquired HTML backing file missing")
            raw = capture_path.read_bytes()
            if _digest(raw) != result.get("sha256"):
                raise ValueError(f"{key}: acquired artifact failed independent SHA readback")
            record.update({
                "validation": result["validation"],
                "path": str(capture_path), "sha256": result["sha256"],
                "readback_sha256": _digest(raw),
                "content_type": result.get("content_type"),
            })
        captures[key] = record
        report[key] = {
            "status": state, "url": url, "error_code": result.get("error_code"),
            "sha256": result.get("sha256"), "validation": result.get("validation"),
            "reused": False,
        }
        if state != "validated":
            all_validated = False

    encoded = (json.dumps(captures, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise ValueError("capture manifest would exceed bounded storage limit")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    if manifest.is_symlink():
        raise ValueError("capture manifest target symlink forbidden")
    if not manifest.is_file() or manifest.read_bytes() != encoded:
        tmp = manifest.with_name(manifest.name + ".tmp")
        if tmp.is_symlink():
            raise ValueError("capture manifest temporary path symlink forbidden")
        tmp.write_bytes(encoded)
        os.replace(tmp, manifest)
    readback = manifest.read_bytes()
    if readback != encoded:
        raise ValueError("capture manifest durable readback mismatch")
    return {
        "capture_manifest_path": str(manifest),
        "capture_manifest_sha256": _digest(readback),
        "all_validated": all_validated,
        "captures": report,
        "verified_reused": sum(1 for x in report.values() if x["reused"]),
        "newly_validated": sum(1 for x in report.values()
                               if x["status"] == "validated" and not x["reused"]),
    }
