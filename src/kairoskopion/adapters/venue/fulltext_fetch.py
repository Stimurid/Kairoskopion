"""Bounded direct full-text acquisition for known article locators.

This adapter does not search the web or bypass access controls. It only fetches
an explicit HTTP(S) locator already present in evidence, caps bytes, stores the
artifact, and validates transport/content shape.
"""

from __future__ import annotations

import hashlib
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
import ipaddress
import socket
from pathlib import Path
from typing import Any

DEFAULT_UA = (
    "Kairoskopion/0.2 "
    "(https://github.com/Stimurid/Kairoskopion; mailto:kairoskopion@proton.me)"
)

# This adapter is explicitly for article full text, not arbitrary HTML pages.
# Publisher bot/interstitial pages are commonly small, syntactically valid
# HTML and must never be promoted to validated full-text artifacts.
MIN_HTML_FULLTEXT_BYTES = 5_000
_HTML_INTERSTITIAL_MARKERS = (
    b"just a moment",
    b"enable javascript and cookies",
    b"verify you are human",
    b"checking your browser",
    b"captcha",
    b"cf-chl-",
    b"access denied",
)


def _public_http_target(url: str) -> tuple[bool, str | None]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, "unsupported_scheme"
    host = (parsed.hostname or "").strip().lower()
    if not host or host in {"localhost", "localhost.localdomain"}:
        return False, "local_or_missing_host"
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except OSError:
        return False, "dns_resolution_failed"
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False, f"non_public_address:{ip}"
    return True, None


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
    if (
        path.suffix.lower() in (".html", ".htm")
        or "text/html" in ct
        or "application/xhtml+xml" in ct
    ):
        probe = data[:16_384].lower()
        if any(marker in probe for marker in _HTML_INTERSTITIAL_MARKERS):
            return {"valid": False, "reason": "html_interstitial_or_challenge"}
        if len(data) < MIN_HTML_FULLTEXT_BYTES:
            return {"valid": False, "reason": "html_too_small_for_fulltext"}
        ok = b"<html" in probe or b"<!doctype html" in probe
        return {
            "valid": ok,
            "reason": "html_shape_ok" if ok else "html_shape_uncertain",
        }
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
    if fixture_bytes is None:
        allowed, reason = _public_http_target(url)
        if not allowed:
            return {
                "status": "blocked",
                "url": url,
                "error_code": str(reason or "blocked"),
                "error": reason,
            }
    elif parsed.scheme not in ("http", "https"):
        return {
            "status": "blocked",
            "url": url,
            "error_code": "unsupported_scheme",
            "error": "unsupported_scheme",
        }

    content_type = fixture_content_type
    data = fixture_bytes
    if data is None:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type")
                declared = response.headers.get("Content-Length")
                if declared and int(declared) > max_bytes:
                    return {
                        "status": "blocked",
                        "url": url,
                        "error_code": "declared_size_over_limit",
                        "error": "declared_size_over_limit",
                    }
                data = response.read(max_bytes + 1)
        except urllib.error.HTTPError as exc:
            return {
                "status": "failed",
                "url": url,
                "error_code": f"http_{exc.code}",
                "http_status": int(exc.code),
                "error": f"HTTPError: HTTP Error {exc.code}",
            }
        except urllib.error.URLError as exc:
            return {
                "status": "failed",
                "url": url,
                "error_code": "network_error",
                "error": f"URLError: {exc.reason}",
            }
        except TimeoutError as exc:
            return {
                "status": "failed",
                "url": url,
                "error_code": "timeout",
                "error": f"TimeoutError: {exc}",
            }
        except Exception as exc:
            return {
                "status": "failed",
                "url": url,
                "error_code": "transport_error",
                "error": f"{type(exc).__name__}: {exc}",
            }

    if data is None:
        return {
            "status": "failed",
            "url": url,
            "error_code": "no_data",
            "error": "no_data",
        }
    if len(data) > max_bytes:
        return {
            "status": "blocked",
            "url": url,
            "error_code": "download_size_over_limit",
            "error": "download_size_over_limit",
        }

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
