"""Bounded direct full-text acquisition for known article locators.

This adapter does not search the web or bypass access controls. It only fetches
an explicit HTTP(S) locator already present in evidence, caps bytes, stores the
artifact, and validates transport/content shape.
"""

from __future__ import annotations

import hashlib
import mimetypes
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_UA = (
    "Kairoskopion/0.2 "
    "(https://github.com/Stimurid/Kairoskopion; mailto:kairoskopion@proton.me)"
)


def _safe_ext(content_type: str | None, url: str) -> str:
    ct = (content_type or "").split(";", 1)[0].strip().lower()
    if ct == "application/pdf":
        return ".pdf"
    if ct in ("text/html", "application/xhtml+xml"):
        return ".html"
    if ct.startswith("text/"):
        return ".txt"
    path_ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return path_ext if path_ext in {".pdf", ".html", ".htm", ".txt"} else ".bin"


def validate_download(path: Path, content_type: str | None = None) -> dict[str, Any]:
    data = path.read_bytes()
    ct = (content_type or "").lower()
    if not data:
        return {"valid": False, "reason": "empty_file"}
    if path.suffix.lower() == ".pdf" or "application/pdf" in ct:
        return {
            "valid": data.startswith(b"%PDF"),
            "reason": "pdf_magic_ok" if data.startswith(b"%PDF") else "pdf_magic_missing",
        }
    if path.suffix.lower() in (".html", ".htm") or "text/html" in ct:
        prefix = data[:2048].lower()
        ok = b"<html" in prefix or b"<!doctype html" in prefix
        return {"valid": ok, "reason": "html_shape_ok" if ok else "html_shape_uncertain"}
    return {"valid": True, "reason": "nonempty_transport_artifact"}


def acquire_explicit_fulltext(
    url: str,
    *,
    output_dir: str | Path,
    max_bytes: int = 25 * 1024 * 1024,
    timeout: int = 30,
    fixture_bytes: bytes | None = None,
    fixture_content_type: str | None = None,
) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {"status": "blocked", "url": url, "error": "unsupported_scheme"}

    content_type = fixture_content_type
    data = fixture_bytes
    if data is None:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type")
                declared = response.headers.get("Content-Length")
                if declared and int(declared) > max_bytes:
                    return {"status": "blocked", "url": url, "error": "declared_size_over_limit"}
                data = response.read(max_bytes + 1)
        except Exception as exc:
            return {"status": "failed", "url": url, "error": f"{type(exc).__name__}: {exc}"}

    if data is None:
        return {"status": "failed", "url": url, "error": "no_data"}
    if len(data) > max_bytes:
        return {"status": "blocked", "url": url, "error": "download_size_over_limit"}

    digest = hashlib.sha256(data).hexdigest()
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    ext = _safe_ext(content_type, url)
    path = root / f"{digest}{ext}"
    path.write_bytes(data)
    validation = validate_download(path, content_type)
    return {
        "status": "validated" if validation["valid"] else "acquired_unvalidated",
        "url": url,
        "path": str(path),
        "content_type": content_type,
        "size_bytes": len(data),
        "sha256": digest,
        "validation": validation,
    }
