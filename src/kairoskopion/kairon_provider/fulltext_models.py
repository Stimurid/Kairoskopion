"""Inspect acquired article full text and extract transparent structural models."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..adapters.source_intake import SourceRole, register_local_source
from .models import CorpusArtifactManifest

_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+.+$")
_NUMBERED_HEADING_RE = re.compile(
    r"^(\d+(?:\.\d+)*)(?:[.)])?\s+(.{3,140})$"
)
_ALLCAPS_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 ,:&/\-]{5,100}$")
_PAGE_HEADER_RE = re.compile(r"^\d+\s+Page\s+\d+\s+of\s+\d+$", re.I)
_SECTION_KIND = {
    "introduction": ("introduction", "background"),
    "literature": ("literature review", "related work", "theoretical background"),
    "methods": ("method", "methodology", "materials and methods"),
    "results": ("results", "findings"),
    "discussion": ("discussion",),
    "limitations": ("limitations", "limitations and future"),
    "conclusion": ("conclusion", "conclusions"),
}
_MOVE_MARKERS = {
    "problem": ("problem", "gap", "challenge", "however", "yet"),
    "claim": ("we argue", "we claim", "this paper argues", "we propose", "we show"),
    "comparison": ("in contrast", "compared with", "whereas", "unlike"),
    "critique": ("fails to", "problematic", "limitation", "critique", "insufficient"),
    "evidence": ("evidence", "data", "results", "findings", "case study"),
    "implication": ("implication", "therefore", "suggests that", "consequently"),
}


def _is_heading(text: str) -> bool:
    """Conservative heading detector for extracted scholarly PDFs.

    PDF text extraction frequently promotes page headers, page numbers and
    numbered footnotes into standalone lines. Keep explicit markdown/all-caps
    headings and numbered section headings, but reject common page/header and
    prose-footnote shapes.
    """
    if _PAGE_HEADER_RE.match(text):
        return False
    if _MARKDOWN_HEADING_RE.match(text) or _ALLCAPS_HEADING_RE.match(text):
        return True
    m = _NUMBERED_HEADING_RE.match(text)
    if not m:
        return False
    number, title = m.groups()
    try:
        first = int(number.split(".", 1)[0])
    except ValueError:
        return False
    if first > 30:
        return False
    if title.rstrip().endswith((".", ";")):
        return False
    if len(title.split()) > 18:
        return False
    if re.search(r"\bPage\s+\d+\s+of\s+\d+\b", title, re.I):
        return False
    return True


def _classify_heading(text: str) -> str:
    low = text.lower().strip("# 0123456789.)")
    for kind, terms in _SECTION_KIND.items():
        if any(term in low for term in terms):
            return kind
    return "other"


def model_article_text(text: str, *, source_ref: str | None = None) -> dict[str, Any]:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    headings = [line for line in lines if _is_heading(line)][:80]
    section_sequence = [
        {"heading": h, "kind": _classify_heading(h)}
        for h in headings
    ]
    low = text.lower()
    moves = []
    for kind, markers in _MOVE_MARKERS.items():
        hits = [m for m in markers if m in low]
        if hits:
            moves.append({"move": kind, "markers": hits, "evidence_status": "fulltext_observation"})
    citation_tokens = len(re.findall(r"\([A-Z][A-Za-z\-]+,?\s+(?:19|20)\d{2}[a-z]?\)", text))
    numeric_citations = len(re.findall(r"\[(?:\d+[,;\- ]*)+\]", text))
    return {
        "source_ref": source_ref,
        "word_count": len(re.findall(r"\w+", text)),
        "headings": headings,
        "section_sequence": section_sequence,
        "argument_moves": moves,
        "citation_marker_count": citation_tokens + numeric_citations,
        "has_explicit_methods": any(s["kind"] == "methods" for s in section_sequence),
        "has_explicit_limitations": any(s["kind"] == "limitations" for s in section_sequence),
        "has_explicit_conclusion": any(s["kind"] == "conclusion" for s in section_sequence),
        "evidence_status": "fulltext_observation",
    }


def extract_fulltext_article_models(manifest: CorpusArtifactManifest) -> dict[str, Any]:
    models: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for artifact in manifest.artifacts:
        if not artifact.local_ref:
            continue
        path = Path(artifact.local_ref)
        snapshot, text = register_local_source(
            path,
            role=SourceRole.PUBLISHED_ARTICLE,
            source_id=artifact.source_ref,
        )
        if not text or snapshot.extraction_status not in ("extracted", "partially_extracted"):
            failures.append({
                "source_ref": artifact.source_ref,
                "status": snapshot.extraction_status,
                "detail": "; ".join(snapshot.extraction_errors or []),
            })
            continue
        model = model_article_text(text, source_ref=artifact.source_ref)
        model["source_snapshot_id"] = snapshot.snapshot_id
        model["content_hash"] = snapshot.content_hash
        models.append(model)
    return {
        "article_models": models,
        "failures": failures,
        "modeled": len(models),
        "attempted": len(models) + len(failures),
    }
