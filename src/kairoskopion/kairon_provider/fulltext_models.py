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


def _heading_score(title: str) -> float:
    """Score title-likeness of a numbered PDF line.

    Real section headings tend to be short and title-like; PDF footnotes tend
    to be sentence-like continuations. This is intentionally transparent and
    conservative rather than an opaque classifier.
    """
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ’'\-]*", title)
    if not words:
        return -10.0
    low = title.lower()
    if any(x in low for x in (
        "university of", "department of", "institute for", "corresponding author",
        "page ", "http://", "https://",
    )):
        return -8.0
    if title.rstrip().endswith((".", ";")):
        return -5.0
    if len(words) > 18:
        return -4.0
    probe = title.lower()
    known_section = any(
        term in probe for terms in _SECTION_KIND.values() for term in terms
    )
    if len(words) < 2 and not known_section:
        return -3.0
    capped = sum(1 for w in words if w[:1].isupper() or w.isupper())
    ratio = capped / len(words)
    score = ratio * 5.0
    if 2 <= len(words) <= 12:
        score += 1.0
    if title.endswith("?"):
        score += 0.5
    # Known scholarly section labels are strong anchors.
    if known_section:
        score += 4.0
    return score


def _extract_headings(lines: list[str]) -> list[str]:
    """Select structural headings while suppressing PDF footnote/header noise."""
    explicit = [x for x in lines if _MARKDOWN_HEADING_RE.match(x)]
    if explicit:
        return explicit[:80]

    allcaps = [x for x in lines if _ALLCAPS_HEADING_RE.match(x) and not _PAGE_HEADER_RE.match(x)]

    numbered: list[tuple[int, str, str, float, int]] = []
    for pos, line in enumerate(lines):
        if _PAGE_HEADER_RE.match(line):
            continue
        m = _NUMBERED_HEADING_RE.match(line)
        if not m:
            continue
        number, title = m.groups()
        try:
            major = int(number.split(".", 1)[0])
        except ValueError:
            continue
        if major > 30:
            continue
        score = _heading_score(title)
        if score < 1.5:
            continue
        numbered.append((major, number, line, score, pos))

    # Pick the strongest top-level candidate for each major section number.
    # Footnotes commonly repeat section-like numbers; the best title-shape is
    # markedly more stable than "first numeric line wins".
    top: dict[int, tuple[int, str, str, float, int]] = {}
    for item in numbered:
        major, number, line, score, pos = item
        if "." in number:
            continue
        prev = top.get(major)
        if prev is None or score > prev[3]:
            top[major] = item

    selected = list(top.values())
    selected.sort(key=lambda x: x[4])
    selected_lines = [x[2] for x in selected]

    # Keep high-confidence decimal subsections whose parent major survived.
    parent_majors = set(top)
    subs = [
        x for x in numbered
        if "." in x[1] and x[0] in parent_majors and x[3] >= 2.0
    ]
    merged = [(x, lines.index(x)) for x in selected_lines]
    merged.extend((x[2], x[4]) for x in subs)
    merged.extend((x, lines.index(x)) for x in allcaps)
    ordered = [x for x, _ in sorted(dict(merged).items(), key=lambda kv: kv[1])][:80]

    # A recognized Conclusion is a strong end-of-article structural anchor.
    # Numeric footnotes/references after it must not re-open the section graph.
    for i, heading in enumerate(ordered):
        if _classify_heading(heading) == "conclusion":
            return ordered[: i + 1]
    return ordered


def _classify_heading(text: str) -> str:
    low = text.lower().strip("# 0123456789.)")
    for kind, terms in _SECTION_KIND.items():
        if any(term in low for term in terms):
            return kind
    return "other"


def model_article_text(text: str, *, source_ref: str | None = None) -> dict[str, Any]:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    headings = _extract_headings(lines)
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
