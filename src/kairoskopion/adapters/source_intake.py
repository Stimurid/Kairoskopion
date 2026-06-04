"""Local source intake adapter (spec §26.2, §27.3).

Registers local files (markdown, text, PDF placeholders) as sources,
creates SourceSnapshot and EvidenceItems. No network access.
"""

from __future__ import annotations

import hashlib
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
    UNKNOWN = "unknown"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _detect_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".html": "text/html",
    }.get(suffix, "application/octet-stream")


def register_local_source(
    file_path: Path | str,
    *,
    role: SourceRole = SourceRole.UNKNOWN,
    source_id: str | None = None,
    notes: str | None = None,
) -> tuple[SourceSnapshot, str]:
    """Register a local file as a source. Returns (snapshot, text_content).

    Reads the file, creates a SourceSnapshot with content hash and
    extraction status. Returns the snapshot and raw text for further
    processing.

    For binary files (PDF, DOCX), text is empty and extraction_status
    is 'not_extracted' — a real extractor adapter is needed later.
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
    is_text = content_type.startswith("text/") or content_type == "application/json"

    if is_text:
        text = path.read_text(encoding="utf-8")
        extraction_status = "extracted"
    else:
        text = ""
        extraction_status = "not_extracted"

    sid = source_id or f"local:{path.name}"

    snapshot = SourceSnapshot(
        snapshot_id=source_snapshot_id(),
        source_id=sid,
        url=str(path.resolve()),
        retrieved_at=_now(),
        content_hash=_content_hash(text) if text else None,
        content_type=content_type,
        parser_used="local_file_read",
        text_ref=str(path.resolve()) if is_text else None,
        extraction_status=extraction_status,
        extraction_errors=[] if is_text else [f"Binary format {content_type} — extractor needed"],
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
