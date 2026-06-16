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

    if suffix == ".rtf":
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            return "", "failed", [f"RTF read error: {exc}"]
        # Naive stdlib RTF-to-plain-text: strip control words + groups.
        # Good enough for academic source lists; not a full RTF parser.
        import re
        # Drop binary objects
        s = re.sub(r"\\bin\d+\s.*?(?=\\|$)", " ", raw, flags=re.DOTALL)
        # Drop control words like \rtf1 \pard \fs24 etc.
        s = re.sub(r"\\[a-zA-Z]+-?\d*\s?", " ", s)
        # Drop \' hex escapes (encoded Cyrillic) -> we lose those chars
        # but still keep the structure.
        s = re.sub(r"\\'[0-9a-fA-F]{2}", "", s)
        # Drop braces
        s = s.replace("{", " ").replace("}", " ")
        # Collapse whitespace
        s = re.sub(r"\s+", " ", s).strip()
        if not s:
            return "", "failed", ["RTF stripped to empty text"]
        return s, "extracted", []

    if suffix == ".doc":
        # Old binary .doc — stdlib can't parse. Tell the user clearly.
        return "", "unsupported", [
            "Старый формат .doc (Word 97-2003) не поддерживается. "
            "Сохраните файл как .docx через 'Файл → Сохранить как → "
            "Документ Word (.docx)' и загрузите его снова."
        ]

    return "", "unsupported", [f"Unsupported format: {suffix}"]
