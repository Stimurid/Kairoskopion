"""Bibliography parsing from manuscript text.

Heuristic extraction — no external API, no verification.
Extracts reference items from a references section, detects years,
DOI-like strings, and probable source kinds.
"""

from __future__ import annotations

import re
import statistics
from typing import Any

from ..enums import ReferenceSourceKind
from ..ids import reference_item_id
from ..schema import BibliographyProfile, ReferenceItem, _now


_REFERENCES_HEADER = re.compile(
    r"^#+\s*(references|bibliography|works\s+cited|литература|список\s+литературы)",
    re.IGNORECASE | re.MULTILINE,
)
_NEXT_SECTION = re.compile(r"^#+\s+", re.MULTILINE)

_YEAR_PATTERN = re.compile(r"\b(1[89]\d{2}|20[0-2]\d)\b")
_DOI_PATTERN = re.compile(r"10\.\d{4,}/[^\s,;)]+")

_BOOK_MARKERS = [
    "press", "publisher", "publications", "verlag",
    "university press", "mit press", "oxford", "cambridge",
    "springer", "routledge", "wiley", "elsevier",
]
_CONFERENCE_MARKERS = [
    "proceedings", "conference", "workshop", "symposium",
    "proc.", "conf.",
]
_CHAPTER_MARKERS = ["in:", "in ", "chapter", " eds.", " ed.", "(ed", "(eds"]
_THESIS_MARKERS = ["thesis", "dissertation", "phd", "doctoral"]
_WEB_MARKERS = ["http://", "https://", "www.", "accessed", "retrieved from"]
_PREPRINT_MARKERS = ["arxiv", "preprint", "biorxiv", "medrxiv", "ssrn"]
_JOURNAL_MARKERS = [
    "journal", "review", "quarterly", "annals", "bulletin",
    "transactions", "letters", "vol.", "volume", "issue",
    "pp.", "p.", "no.",
]


def extract_references_section(text: str) -> str | None:
    """Extract the references/bibliography section from manuscript text."""
    match = _REFERENCES_HEADER.search(text)
    if not match:
        return None
    start = match.end()
    rest = text[start:]
    next_section = _NEXT_SECTION.search(rest)
    if next_section:
        return rest[:next_section.start()].strip()
    return rest.strip()


def detect_reference_style(section_text: str) -> str:
    """Detect the reference citation style used in the section.

    Returns one of: 'apa', 'numbered', 'author_date', 'chicago_note',
    'vancouver', 'unknown'.
    """
    lines = [l.strip() for l in section_text.strip().splitlines() if l.strip()]
    if not lines:
        return "unknown"

    # Check for numbered style (1. ..., [1] ..., (1) ...)
    numbered_count = sum(1 for l in lines if re.match(r"^(\[?\d+\]?\.?\s|\(\d+\)\s)", l))
    if numbered_count > len(lines) * 0.6:
        # Distinguish Vancouver from generic numbered
        if any(";" in l and re.search(r"\d{4}", l) for l in lines[:5]):
            return "vancouver"
        return "numbered"

    # Check for APA style: Author, A. A. (Year).
    apa_count = sum(1 for l in lines if re.match(r"^[A-Z][a-z]+,?\s.*\(\d{4}", l))
    if apa_count > len(lines) * 0.5:
        return "apa"

    # Check for Chicago author-date: Author Year.
    chicago_count = sum(1 for l in lines if re.match(r"^[A-Z][a-z]+.*\d{4}\.", l))
    if chicago_count > len(lines) * 0.5:
        return "author_date"

    # Check for bullet/dash style
    bullet_count = sum(1 for l in lines if re.match(r"^[-•*–—]", l))
    if bullet_count > len(lines) * 0.5:
        return "author_date"

    return "unknown"


def split_references(section_text: str) -> list[str]:
    """Split a references section into individual reference strings.

    Handles multiple citation styles:
    - Bullet/dash lists (- Reference text)
    - Numbered lists (1. Reference text, [1] Reference text)
    - Plain paragraph-per-reference
    - Multi-line references (continuation lines joined)
    """
    lines = section_text.strip().splitlines()
    refs: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Blank line: flush current
            if current:
                joined = " ".join(current)
                if len(joined) > 10:
                    refs.append(joined)
                current = []
            continue

        # Check if this is a new reference start
        is_new_ref = bool(
            re.match(r"^[-•*–—]\s+", stripped) or     # bullet
            re.match(r"^\[?\d+\]?\.?\s", stripped) or  # numbered
            re.match(r"^\(\d+\)\s", stripped) or       # (1) style
            re.match(r"^[A-Z][a-z]+", stripped)        # capital start (typical author name)
        )

        if is_new_ref and current:
            joined = " ".join(current)
            if len(joined) > 10:
                refs.append(joined)
            current = []

        # Clean leading markers
        cleaned = re.sub(r"^[-•*–—]\s*", "", stripped).strip()
        cleaned = re.sub(r"^\[?\d+\]?\.?\s*", "", cleaned).strip()
        cleaned = re.sub(r"^\(\d+\)\s*", "", cleaned).strip()

        if cleaned:
            current.append(cleaned)

    # Flush last reference
    if current:
        joined = " ".join(current)
        if len(joined) > 10:
            refs.append(joined)

    return refs


def parse_reference(raw: str) -> ReferenceItem:
    """Parse a single reference string into a ReferenceItem."""
    years = _YEAR_PATTERN.findall(raw)
    year = int(years[0]) if years else None

    doi_match = _DOI_PATTERN.search(raw)
    doi = doi_match.group(0).rstrip(".") if doi_match else None

    source_kind = _detect_source_kind(raw)
    author_fragment = _extract_author_fragment(raw)
    title_fragment = _extract_title_fragment(raw)

    return ReferenceItem(
        reference_item_id=reference_item_id(),
        raw_text=raw,
        year=year,
        doi=doi,
        source_kind=source_kind,
        author_fragment=author_fragment,
        title_fragment=title_fragment,
        verification_status="not_verified",
    )


def _detect_source_kind(raw: str) -> str:
    lower = raw.lower()

    for marker in _PREPRINT_MARKERS:
        if marker in lower:
            return ReferenceSourceKind.PREPRINT.value

    for marker in _THESIS_MARKERS:
        if marker in lower:
            return ReferenceSourceKind.THESIS.value

    for marker in _CONFERENCE_MARKERS:
        if marker in lower:
            return ReferenceSourceKind.CONFERENCE_PAPER.value

    for marker in _WEB_MARKERS:
        if marker in lower:
            return ReferenceSourceKind.WEB_SOURCE.value

    for marker in _CHAPTER_MARKERS:
        if marker in lower:
            return ReferenceSourceKind.BOOK_CHAPTER.value

    has_journal = any(m in lower for m in _JOURNAL_MARKERS)
    has_book = any(m in lower for m in _BOOK_MARKERS)

    if has_journal and not has_book:
        return ReferenceSourceKind.JOURNAL_ARTICLE.value

    if has_book and not has_journal:
        return ReferenceSourceKind.BOOK.value

    if has_book and has_journal:
        return ReferenceSourceKind.JOURNAL_ARTICLE.value

    return ReferenceSourceKind.UNKNOWN.value


def _extract_author_fragment(raw: str) -> str | None:
    """Extract author fragment — text before first year or parenthesis."""
    match = re.match(r"^([^(]+?)[\s,]*\(?\d{4}", raw)
    if match:
        fragment = match.group(1).strip().rstrip(",").rstrip(".")
        if len(fragment) > 2:
            return fragment
    return None


def _extract_title_fragment(raw: str) -> str | None:
    """Extract probable title — text after year in parentheses, before period."""
    match = re.search(r"\(\d{4}[a-z]?\)\s*\.?\s*(.+?)(?:\.|$)", raw)
    if match:
        title = match.group(1).strip().rstrip(".")
        if len(title) > 5:
            return title
    match2 = re.search(r"\d{4}[a-z]?\)\s*\.?\s*(.+?)(?:\.|$)", raw)
    if match2:
        title = match2.group(1).strip().rstrip(".")
        if len(title) > 5:
            return title
    return None


def build_bibliography_profile(
    manuscript_text: str,
    *,
    manuscript_id: str | None = None,
    article_model_id: str | None = None,
) -> BibliographyProfile:
    """Build a BibliographyProfile from manuscript text."""
    section = extract_references_section(manuscript_text)
    unknowns: list[str] = []

    if not section:
        unknowns.append("No references section found in manuscript text")
        return BibliographyProfile(
            manuscript_id=manuscript_id,
            article_model_id=article_model_id,
            unknowns=unknowns,
        )

    ref_style = detect_reference_style(section)
    raw_refs = split_references(section)
    if not raw_refs:
        unknowns.append("References section found but no parseable items")
        return BibliographyProfile(
            manuscript_id=manuscript_id,
            article_model_id=article_model_id,
            unknowns=unknowns,
        )

    items = [parse_reference(r) for r in raw_refs]
    years = [item.year for item in items if item.year is not None]
    dois = [item for item in items if item.doi is not None]

    kind_dist: dict[str, int] = {}
    for item in items:
        kind_dist[item.source_kind] = kind_dist.get(item.source_kind, 0) + 1

    no_year = sum(1 for item in items if item.year is None)
    if no_year > 0:
        unknowns.append(f"{no_year} reference(s) without detectable year")

    unknown_kind = kind_dist.get("unknown", 0)
    if unknown_kind > 0:
        unknowns.append(f"{unknown_kind} reference(s) with undetectable source kind")

    recency = _assess_recency(years) if years else "unknown"
    if recency == "unknown":
        unknowns.append("Cannot assess recency — no years detected")

    return BibliographyProfile(
        manuscript_id=manuscript_id,
        article_model_id=article_model_id,
        total_references=len(items),
        references=[item.to_dict() for item in items],
        year_min=min(years) if years else None,
        year_max=max(years) if years else None,
        year_median=int(statistics.median(years)) if years else None,
        doi_count=len(dois),
        source_kind_distribution=kind_dist,
        recency_profile=recency,
        reference_style=ref_style,
        unknowns=unknowns,
    )


def _assess_recency(years: list[int]) -> str:
    if not years:
        return "unknown"
    median = statistics.median(years)
    max_year = max(years)
    if max_year >= 2020 and median >= 2010:
        return "recent"
    if max_year >= 2010 and median >= 2000:
        return "moderately_recent"
    if max_year >= 2000:
        return "dated"
    return "historical"
