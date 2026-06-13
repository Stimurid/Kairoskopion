"""Thin wrapper around source_intake extractors for the file upload endpoint."""

from __future__ import annotations

from pathlib import Path

from ..adapters.source_intake import (
    _extract_pdf_text,
    _extract_docx_text,
    _extract_html_text,
)


def extract_text_from_file(path: Path) -> tuple[str, str, list[str]]:
    """Extract text from an uploaded file. Returns (text, status, errors)."""
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        try:
            text = path.read_text(encoding="utf-8")
            return text, "extracted", []
        except UnicodeDecodeError:
            return "", "failed", ["UTF-8 decode error"]

    if suffix == ".pdf":
        return _extract_pdf_text(path)

    if suffix == ".docx":
        return _extract_docx_text(path)

    if suffix in (".html", ".htm"):
        try:
            raw = path.read_text(encoding="utf-8")
            text = _extract_html_text(raw)
            return text, "extracted", []
        except UnicodeDecodeError:
            return "", "failed", ["UTF-8 decode error"]

    if suffix == ".json":
        try:
            text = path.read_text(encoding="utf-8")
            return text, "extracted", []
        except UnicodeDecodeError:
            return "", "failed", ["UTF-8 decode error"]

    return "", "unsupported", [f"Unsupported format: {suffix}"]
