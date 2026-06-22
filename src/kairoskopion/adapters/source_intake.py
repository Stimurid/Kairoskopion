"""Local source intake adapter (spec §26.2, §27.3).

Registers local files (markdown, text, HTML, JSON, PDF, DOCX) as sources,
creates SourceSnapshot and EvidenceItems. No network access.

PDF extraction requires ``pypdf`` (optional dependency).
DOCX extraction requires ``python-docx`` (optional dependency).
"""

from __future__ import annotations

import hashlib
import os
from enum import Enum
from pathlib import Path
from typing import Any

from ..enums import EvidenceStatus
from ..ids import evidence_item_id, source_snapshot_id
from ..schema import EvidenceItem, SourceSnapshot, _now


class SourceRole(str, Enum):
    """Recognized source roles for Kairoskopion (spec §13.4)."""
    ARTICLE_INPUT = "article_input"
    VENUE_GUIDELINES = "venue_guidelines"
    AUTHOR_GUIDELINES = "author_guidelines"
    AIMS_SCOPE = "aims_scope"
    POLICY_PAGE = "policy_page"
    EDITORIAL_BOARD = "editorial_board"
    SUBMISSION_INFO = "submission_info"
    ISSUE_PAGE = "issue_page"
    SPECIAL_ISSUE_CFP = "special_issue_cfp"
    PUBLISHED_ARTICLE = "published_article"
    REVIEW_LETTER = "review_letter"
    USER_NOTE = "user_note"
    COMPLIANCE_GUIDELINE = "compliance_guideline"
    BACKGROUND_RESEARCH = "background_research"
    UNKNOWN = "unknown"


# ---- Extraction status taxonomy ----

EXTRACTION_STATUSES = (
    "extracted",
    "partially_extracted",
    "unsupported",
    "failed",
    "binary_not_extracted",
    "needs_ocr",
    "encrypted_or_unreadable",
    "file_not_found",
    "unknown",
)


# ---- Helpers ----

def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _file_metadata(path: Path) -> dict[str, Any]:
    """Gather file metadata without reading content."""
    stat = path.stat()
    return {
        "filename": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "modified_at": _now(),
    }


def _detect_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".html": "text/html",
        ".htm": "text/html",
    }.get(suffix, "application/octet-stream")


# ---- PDF extraction ----

def _extract_pdf_text(path: Path) -> tuple[str, str, list[str]]:
    """Extract text from PDF. Returns (text, extraction_status, warnings)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return "", "binary_not_extracted", [
            "pypdf not installed. Install with: pip install kairoskopion[extract]"
        ]

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        return "", "encrypted_or_unreadable", [f"PDF read error: {exc}"]

    if reader.is_encrypted:
        return "", "encrypted_or_unreadable", ["PDF is encrypted"]

    pages_text: list[str] = []
    warnings: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
            pages_text.append(page_text)
        except Exception as exc:
            warnings.append(f"Page {i+1}: extraction error: {exc}")

    full_text = "\n\n".join(pages_text).strip()

    if not full_text:
        return "", "needs_ocr", [
            "PDF text extraction returned empty — may be scanned/image-only"
        ]

    status = "extracted"
    if warnings:
        status = "partially_extracted"

    return full_text, status, warnings


# ---- DOCX extraction ----

def _extract_docx_text(path: Path) -> tuple[str, str, list[str]]:
    """Extract text from DOCX. Returns (text, extraction_status, warnings)."""
    try:
        from docx import Document
    except ImportError:
        return "", "binary_not_extracted", [
            "python-docx not installed. Install with: pip install kairoskopion[extract]"
        ]

    try:
        doc = Document(str(path))
    except Exception as exc:
        return "", "failed", [f"DOCX read error: {exc}"]

    # Round II-B Track F: extract Title / Heading 1 paragraph style
    # so the article modeler (and structural title fallback) can read
    # the real title as a direct source fact instead of guessing.
    docx_title: str | None = None
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        try:
            style_name = (para.style.name if para.style is not None else "") or ""
        except Exception:  # noqa: BLE001
            style_name = ""
        sl = style_name.lower()
        if docx_title is None and (
            sl == "title"
            or sl.startswith("heading 1")
            or sl == "heading1"
        ):
            docx_title = text[:240]
        paragraphs.append(text)

    full_text = "\n\n".join(paragraphs).strip()

    if not full_text:
        return "", "partially_extracted", ["DOCX contained no paragraph text"]

    # Prepend an H1 markdown line so existing markdown-H1 detectors
    # (article modeler, structural-title fallback) pick it up.
    if docx_title and not full_text.lstrip().startswith("# "):
        full_text = f"# {docx_title}\n\n{full_text}"

    return full_text, "extracted", []


# ---- HTML text extraction ----

def _extract_html_text(raw: str) -> str:
    """Simple HTML tag stripping (no external dependency)."""
    import re
    # Remove script/style blocks
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', raw, flags=re.DOTALL | re.IGNORECASE)
    # Remove tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ---- Main registration ----

def register_local_source(
    file_path: Path | str,
    *,
    role: SourceRole = SourceRole.UNKNOWN,
    source_id: str | None = None,
    notes: str | None = None,
) -> tuple[SourceSnapshot, str]:
    """Register a local file as a source. Returns (snapshot, text_content).

    Reads the file, creates a SourceSnapshot with content hash and
    extraction status. Supports: .md, .txt, .json, .html, .pdf, .docx.

    For unsupported binary files, text is empty and extraction_status
    reflects the reason.
    """
    path = Path(file_path)
    if not path.exists():
        snapshot = SourceSnapshot(
            snapshot_id=source_snapshot_id(),
            source_id=source_id or f"local:{path.name}",
            url=str(path),
            retrieved_at=_now(),
            content_type=_detect_content_type(path),
            extraction_status="file_not_found",
            extraction_errors=[f"File not found: {path}"],
        )
        return snapshot, ""

    content_type = _detect_content_type(path)
    suffix = path.suffix.lower()
    meta = _file_metadata(path)
    sid = source_id or f"local:{path.name}"

    text = ""
    extraction_status = "unknown"
    extraction_errors: list[str] = []
    extraction_method = "local_file_read"
    extraction_warnings: list[str] = []

    if content_type.startswith("text/") or content_type == "application/json":
        # Plain text formats
        try:
            raw = path.read_text(encoding="utf-8")
            if suffix in (".html", ".htm"):
                text = _extract_html_text(raw)
                extraction_method = "html_tag_strip"
            else:
                text = raw
            extraction_status = "extracted"
        except UnicodeDecodeError:
            extraction_status = "failed"
            extraction_errors.append("UTF-8 decode error")
        except Exception as exc:
            extraction_status = "failed"
            extraction_errors.append(f"Read error: {exc}")

    elif suffix == ".pdf":
        text, extraction_status, extraction_warnings = _extract_pdf_text(path)
        extraction_method = "pypdf"
        extraction_errors.extend(extraction_warnings)

    elif suffix == ".docx":
        text, extraction_status, extraction_warnings = _extract_docx_text(path)
        extraction_method = "python-docx"
        extraction_errors.extend(extraction_warnings)

    else:
        # Unsupported binary format
        extraction_status = "unsupported"
        extraction_errors.append(
            f"Unsupported format: {suffix} ({content_type}). "
            "Supported: .md, .txt, .json, .html, .pdf, .docx"
        )

    snapshot = SourceSnapshot(
        snapshot_id=source_snapshot_id(),
        source_id=sid,
        url=str(path.resolve()),
        retrieved_at=_now(),
        content_hash=_content_hash(text) if text else None,
        content_type=content_type,
        parser_used=extraction_method,
        text_ref=str(path.resolve()) if text else None,
        extraction_status=extraction_status,
        extraction_errors=extraction_errors,
    )
    return snapshot, text


def create_evidence_from_source(
    snapshot: SourceSnapshot,
    *,
    claim: str,
    excerpt: str | None = None,
    section: str | None = None,
    status: EvidenceStatus = EvidenceStatus.FACT_FROM_SOURCE,
) -> EvidenceItem:
    """Create an EvidenceItem linked to a SourceSnapshot."""
    return EvidenceItem(
        evidence_id=evidence_item_id(),
        source_id=snapshot.source_id,
        source_type="local_file",
        url_or_file_ref=snapshot.url,
        retrieved_at=snapshot.retrieved_at,
        extracted_at=_now(),
        excerpt_or_locator=excerpt,
        page_or_section=section,
        claim_supported=claim,
        evidence_status=status.value,
        confidence="medium" if status == EvidenceStatus.FACT_FROM_SOURCE else "low",
    )


def register_text_input(
    text: str,
    *,
    role: SourceRole = SourceRole.ARTICLE_INPUT,
    title: str | None = None,
    source_id: str | None = None,
) -> SourceSnapshot:
    """Register raw text (e.g. pasted abstract, user note) as a source."""
    sid = source_id or f"text_input:{_content_hash(text)[:8]}"
    return SourceSnapshot(
        snapshot_id=source_snapshot_id(),
        source_id=sid,
        url=None,
        retrieved_at=_now(),
        content_hash=_content_hash(text),
        content_type="text/plain",
        parser_used="direct_text_input",
        text_ref=title or "inline text",
        extraction_status="extracted",
    )
