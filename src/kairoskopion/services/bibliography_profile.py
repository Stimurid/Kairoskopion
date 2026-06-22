"""V2-E minimal-real BibliographyProfile builder.

Structural extraction of a manuscript's bibliography from raw text.
NEVER invents missing references, DOIs, titles, authors, or years.
NEVER calls external APIs (no Crossref/OpenAlex/OpenCitations dep
this pass). Reports verification_status = ``not_verified`` /
``structural_only`` / ``identifiers_detected`` only — claiming
``verified`` requires an external adapter that does not exist yet.

Inputs: raw article text (may be None). When raw text is unavailable
the builder honestly returns status=``unknown`` (NOT ``not_found``),
with verification_status=``blocked_missing_bibliography`` and a
verification_task pointing the operator to provide the manuscript.

Heading detection supports English + Russian conventions:
  - References
  - Bibliography
  - Works cited
  - Literature
  - Литература
  - Список литературы

No semantic claims about venue fit / venue expectations / "good for
this journal" — that belongs to CitationPlan which consumes this
profile.
"""

from __future__ import annotations

import re
from typing import Any

from ..ids import bibliography_profile_id, reference_item_id
from ..schema import BibliographyProfile


# ---------- status taxonomy (per V2-E brief Track C) ----------
STATUS_NOT_FOUND = "not_found"
STATUS_PRESENT_UNPARSED = "present_unparsed"
STATUS_PARSED_STRUCTURAL = "parsed_structural"
STATUS_PARTIAL = "partial"
STATUS_MALFORMED = "malformed"
STATUS_NEEDS_USER_INPUT = "needs_user_input"
STATUS_UNKNOWN = "unknown"

VERIFY_NOT_VERIFIED = "not_verified"
VERIFY_STRUCTURAL_ONLY = "structural_only"
VERIFY_IDENTIFIERS_DETECTED = "identifiers_detected"
VERIFY_NEEDS_EXTERNAL_LOOKUP = "needs_external_lookup"
VERIFY_PARTIALLY_VERIFIED = "partially_verified"
VERIFY_VERIFIED = "verified"
VERIFY_BLOCKED_MISSING = "blocked_missing_bibliography"

REF_PARSE_PARSED_MINIMAL = "parsed_minimal"
REF_PARSE_RAW_ONLY = "raw_only"
REF_PARSE_MALFORMED = "malformed"
REF_PARSE_EMPTY = "empty"
REF_PARSE_DUPLICATE_SUSPECT = "duplicate_suspect"

ID_DOI_DETECTED = "doi_detected"
ID_URL_DETECTED = "url_detected"
ID_NO_IDENTIFIER = "no_identifier_detected"
ID_AMBIGUOUS = "ambiguous_identifier"
ID_UNKNOWN = "unknown"


# ---------- heading detection ----------
_HEADING_PATTERNS = [
    r"список\s+литературы",
    r"литература",
    r"references?",
    r"bibliography",
    r"works\s+cited",
    r"cited\s+works",
    r"literature(\s+cited)?",
    r"библиограф\w*",
]
_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\d+\.?\s*)?(?:" + "|".join(_HEADING_PATTERNS) + r")\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


# ---------- identifier regexes ----------
# DOI: 10.xxxx/xxxxx (conservative; supports dx.doi.org and doi.org prefix)
_DOI_RE = re.compile(
    r"(?:doi[:.\s]+|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)",
    re.IGNORECASE,
)
# URL (non-DOI; conservative)
_URL_RE = re.compile(
    r"https?://[^\s<>\"]+",
    re.IGNORECASE,
)
# Year: 1900-2099 word-boundary
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

# Numbered reference line start: "1.", "1)", "[1]", "(1)"
_NUMBERED_LINE_RE = re.compile(r"^\s*(?:\[\(]?\d+[\.\)\]])\s+", re.MULTILINE)
# Bulleted line start
_BULLETED_LINE_RE = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)


def _normalize_for_dedup(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def _extract_bibliography_block(text: str) -> tuple[str | None, int]:
    """Find the bibliography section and return its body + start offset.

    Returns (block_text, start_offset) or (None, -1) if no heading found.
    """
    m = _HEADING_RE.search(text)
    if m is None:
        return None, -1
    start = m.end()
    # Try to find the NEXT top-level heading after this one (markdown
    # # or ##). If none, take the rest of the document.
    after = text[start:]
    next_h = re.search(
        r"\n\s*(?:#{1,6}\s+\S|appendix|appendices)",
        after,
        re.IGNORECASE,
    )
    if next_h is not None:
        return after[: next_h.start()], start
    return after, start


def _split_into_reference_candidates(block: str) -> list[str]:
    """Conservatively split a bibliography block into candidate refs.

    Strategy (try in order, pick the one that yields the most items):
      1. Numbered list (1. / 1) / [1] / (1))
      2. Bulleted list (-, *, •)
      3. Newline-separated (one ref per line, after filtering blanks)
      4. Semicolon-separated FALLBACK only when others produced ≤1
    Returns a list of candidate ref strings (raw, possibly with
    leading numbers stripped).
    """
    # Strategy 1: numbered
    numbered_starts = list(_NUMBERED_LINE_RE.finditer(block))
    if len(numbered_starts) >= 2:
        items: list[str] = []
        for i, m in enumerate(numbered_starts):
            start = m.start()
            end = (
                numbered_starts[i + 1].start()
                if i + 1 < len(numbered_starts)
                else len(block)
            )
            items.append(block[start:end].strip())
        if items:
            return items

    # Strategy 2: bulleted
    bulleted_starts = list(_BULLETED_LINE_RE.finditer(block))
    if len(bulleted_starts) >= 2:
        items: list[str] = []
        for i, m in enumerate(bulleted_starts):
            start = m.start()
            end = (
                bulleted_starts[i + 1].start()
                if i + 1 < len(bulleted_starts)
                else len(block)
            )
            items.append(block[start:end].strip())
        if items:
            return items

    # Strategy 3: newline-separated. Only take lines that look like
    # references (length ≥ 20 chars, contain at least one year or
    # identifier or comma).
    lines = [ln.strip() for ln in block.split("\n")]
    candidates: list[str] = []
    buf: list[str] = []
    for ln in lines:
        if not ln:
            if buf:
                candidates.append(" ".join(buf).strip())
                buf = []
            continue
        # Heuristic: if line starts with what looks like a continuation
        # (lowercase, no number prefix), join to previous.
        if buf and re.match(r"^[a-zа-я]", ln):
            buf.append(ln)
        else:
            if buf:
                candidates.append(" ".join(buf).strip())
            buf = [ln]
    if buf:
        candidates.append(" ".join(buf).strip())
    # Filter
    candidates = [
        c for c in candidates
        if len(c) >= 20 and (
            _YEAR_RE.search(c) or _DOI_RE.search(c)
            or _URL_RE.search(c) or "," in c or "." in c[5:]
        )
    ]
    if len(candidates) >= 2:
        return candidates

    # Strategy 4: semicolon fallback (very last resort)
    if ";" in block and len(candidates) <= 1:
        semi = [s.strip() for s in block.split(";") if len(s.strip()) >= 20]
        if len(semi) >= 2:
            return semi

    return candidates  # may be empty or single-item


def _parse_reference(raw: str) -> dict[str, Any]:
    """Extract minimal structural fields from a raw reference string.

    NEVER invents missing fields. Returns None values when not detectable.
    """
    warnings: list[str] = []
    text = raw.strip()
    if not text:
        return {
            "reference_id": reference_item_id(),
            "raw_text": "",
            "authors_text": None,
            "year": None,
            "title_text": None,
            "venue_text": None,
            "doi": None,
            "url": None,
            "identifier_status": ID_UNKNOWN,
            "parse_status": REF_PARSE_EMPTY,
            "verification_status": VERIFY_NOT_VERIFIED,
            "warnings": ["empty reference"],
        }

    # DOI
    doi_m = _DOI_RE.search(text)
    doi = doi_m.group(1) if doi_m else None

    # URL (non-DOI)
    url_m = _URL_RE.search(text)
    url = url_m.group(0) if url_m else None
    if url and doi and doi in url:
        url = None  # DOI URL — collapse

    # Year (first match)
    year_matches = _YEAR_RE.findall(text)
    year = int(year_matches[0]) if year_matches else None
    if year and len(year_matches) > 1:
        warnings.append("multiple years detected; first taken")

    # Identifier status
    if doi:
        ident_status = ID_DOI_DETECTED
    elif url:
        ident_status = ID_URL_DETECTED
    else:
        ident_status = ID_NO_IDENTIFIER

    # Parse status: minimal if at least year OR identifier present
    if doi or url or year:
        parse_status = REF_PARSE_PARSED_MINIMAL
    elif len(text) < 30:
        parse_status = REF_PARSE_MALFORMED
        warnings.append("very short reference — possibly malformed")
    else:
        parse_status = REF_PARSE_RAW_ONLY

    return {
        "reference_id": reference_item_id(),
        "raw_text": text[:600],
        "authors_text": None,  # we do not invent author parsing
        "year": year,
        "title_text": None,    # we do not invent title parsing
        "venue_text": None,    # we do not invent venue parsing
        "doi": doi,
        "url": url,
        "identifier_status": ident_status,
        "parse_status": parse_status,
        "verification_status": VERIFY_NOT_VERIFIED,
        "warnings": warnings,
    }


def build_minimal_bibliography_profile(
    raw_text: str | None,
    article_model_id: str | None = None,
    manuscript_id: str | None = None,
    source: str | None = None,
) -> BibliographyProfile:
    """Build a minimal-real BibliographyProfile from raw article text.

    - raw_text=None → status=unknown, blocked_missing_bibliography.
    - heading not found → status=not_found (raw text WAS available
      but no recognized bibliography section).
    - heading found but block parses to 0 refs → status=present_unparsed.
    - refs parsed → status=parsed_structural (or partial if some
      malformed).
    """
    # Round-II: BibliographyProfile is structural-only by construction.
    from .semantic_provenance import (
        ORIGIN_STRUCTURAL_EXTRACTION,
        SEMANTIC_STATUS_STRUCTURAL_ONLY,
    )
    _STRUCTURAL_ORIGINS = {
        "status": ORIGIN_STRUCTURAL_EXTRACTION,
        "reference_count": ORIGIN_STRUCTURAL_EXTRACTION,
        "doi_count": ORIGIN_STRUCTURAL_EXTRACTION,
        "url_count": ORIGIN_STRUCTURAL_EXTRACTION,
        "references": ORIGIN_STRUCTURAL_EXTRACTION,
        "year_distribution": ORIGIN_STRUCTURAL_EXTRACTION,
        "verification_status": ORIGIN_STRUCTURAL_EXTRACTION,
        "verification_tasks": ORIGIN_STRUCTURAL_EXTRACTION,
        "warnings": ORIGIN_STRUCTURAL_EXTRACTION,
        "unknowns": ORIGIN_STRUCTURAL_EXTRACTION,
        "malformed_count": ORIGIN_STRUCTURAL_EXTRACTION,
        "duplicate_suspect_count": ORIGIN_STRUCTURAL_EXTRACTION,
    }
    if raw_text is None:
        return BibliographyProfile(
            article_model_id=article_model_id,
            manuscript_id=manuscript_id,
            source=source,
            status=STATUS_UNKNOWN,
            bibliography_text_available=False,
            bibliography_section_detected=False,
            reference_count=0,
            verification_status=VERIFY_BLOCKED_MISSING,
            verification_tasks=[
                "Provide the manuscript's raw text so the bibliography "
                "section can be located and parsed structurally."
            ],
            warnings=["raw article text unavailable to bibliography parser"],
            unknowns=["bibliography presence unknown — no raw text supplied"],
            created_from=["unavailable_raw_text"],
            confidence="low",
            field_origins=dict(_STRUCTURAL_ORIGINS),
            semantic_status=SEMANTIC_STATUS_STRUCTURAL_ONLY,
        )

    block, _ = _extract_bibliography_block(raw_text)
    if block is None:
        return BibliographyProfile(
            article_model_id=article_model_id,
            manuscript_id=manuscript_id,
            source=source,
            status=STATUS_NOT_FOUND,
            bibliography_text_available=True,
            bibliography_section_detected=False,
            reference_count=0,
            verification_status=VERIFY_BLOCKED_MISSING,
            verification_tasks=[
                "Add a recognizable bibliography section "
                "('References' / 'Bibliography' / 'Список литературы') "
                "to the manuscript before citation readiness can be "
                "assessed."
            ],
            warnings=[
                "no bibliography heading detected in supplied text"
            ],
            unknowns=[
                "manuscript may have references but no recognized "
                "heading was found"
            ],
            created_from=["raw_text_heading_scan"],
            confidence="medium",
            field_origins=dict(_STRUCTURAL_ORIGINS),
            semantic_status=SEMANTIC_STATUS_STRUCTURAL_ONLY,
        )

    candidates = _split_into_reference_candidates(block)
    references: list[dict[str, Any]] = []
    seen_norm: set[str] = set()
    duplicate_count = 0
    malformed_count = 0
    parsed_minimal_count = 0
    raw_only_count = 0
    empty_count = 0
    doi_count = 0
    url_count = 0
    year_dist: dict[str, int] = {}
    identifier_dist: dict[str, int] = {}

    for cand in candidates:
        ref = _parse_reference(cand)
        norm = _normalize_for_dedup(ref["raw_text"])
        if norm and norm in seen_norm:
            duplicate_count += 1
            ref["parse_status"] = REF_PARSE_DUPLICATE_SUSPECT
            ref.setdefault("warnings", []).append("duplicate_suspect")
        else:
            seen_norm.add(norm)
        if ref["parse_status"] == REF_PARSE_PARSED_MINIMAL:
            parsed_minimal_count += 1
        elif ref["parse_status"] == REF_PARSE_RAW_ONLY:
            raw_only_count += 1
        elif ref["parse_status"] == REF_PARSE_MALFORMED:
            malformed_count += 1
        elif ref["parse_status"] == REF_PARSE_EMPTY:
            empty_count += 1
        if ref["doi"]:
            doi_count += 1
        if ref["url"]:
            url_count += 1
        if ref["year"]:
            y = str(ref["year"])
            year_dist[y] = year_dist.get(y, 0) + 1
        ist = ref["identifier_status"]
        identifier_dist[ist] = identifier_dist.get(ist, 0) + 1
        references.append(ref)

    total = len(references)
    parsed_count = parsed_minimal_count
    unparsed_count = raw_only_count + malformed_count + empty_count

    # Status
    if total == 0:
        status = STATUS_PRESENT_UNPARSED
        warnings = ["bibliography heading found but no references parsed"]
        verify_status = VERIFY_BLOCKED_MISSING
    elif malformed_count >= max(1, total // 2):
        status = STATUS_MALFORMED
        warnings = [
            f"{malformed_count}/{total} references look malformed"
        ]
        verify_status = VERIFY_STRUCTURAL_ONLY
    elif raw_only_count > 0 and parsed_count > 0:
        status = STATUS_PARTIAL
        warnings = [
            f"{raw_only_count}/{total} references have no DOI/URL/year "
            "and were kept as raw_only"
        ]
        verify_status = (
            VERIFY_IDENTIFIERS_DETECTED if doi_count > 0 else VERIFY_STRUCTURAL_ONLY
        )
    else:
        status = STATUS_PARSED_STRUCTURAL
        warnings = []
        verify_status = (
            VERIFY_IDENTIFIERS_DETECTED if doi_count > 0 else VERIFY_STRUCTURAL_ONLY
        )

    # Verification tasks (never invent verified=yes)
    verify_tasks: list[str] = []
    if total > 0 and verify_status != VERIFY_BLOCKED_MISSING:
        if doi_count < total:
            verify_tasks.append(
                f"Verify {total - doi_count}/{total} references via "
                "external lookup (Crossref / OpenAlex / OpenCitations) "
                "— no external adapter active in V2-E so this is a "
                "manual task today."
            )
        verify_tasks.append(
            f"Structural parse complete for {total} references; "
            "external metadata verification not performed."
        )

    unknowns: list[str] = []
    if doi_count == 0 and total > 0:
        unknowns.append(
            "no DOI detected in any reference — external lookup "
            "needed before per-reference metadata can be trusted"
        )
    if total > 0 and total < 5:
        warnings.append(
            f"only {total} references parsed — suspiciously low"
        )

    # Year stats
    years = sorted(int(y) for y in year_dist.keys())
    year_min = years[0] if years else None
    year_max = years[-1] if years else None
    year_median = years[len(years) // 2] if years else None

    return BibliographyProfile(
        article_model_id=article_model_id,
        manuscript_id=manuscript_id,
        source=source or "raw_article_text",
        status=status,
        bibliography_text_available=True,
        bibliography_section_detected=True,
        reference_count=total,
        total_references=total,
        parsed_reference_count=parsed_count,
        unparsed_reference_count=unparsed_count,
        references=references,
        detected_identifiers=identifier_dist,
        year_distribution=year_dist,
        year_min=year_min,
        year_max=year_max,
        year_median=year_median,
        doi_count=doi_count,
        url_count=url_count,
        possibly_incomplete=(
            unparsed_count > 0 or duplicate_count > 0 or total < 5
        ),
        malformed_count=malformed_count,
        duplicate_suspect_count=duplicate_count,
        verification_status=verify_status,
        verification_tasks=verify_tasks,
        warnings=warnings,
        unknowns=unknowns,
        created_from=["raw_article_text"],
        confidence=(
            "medium" if status == STATUS_PARSED_STRUCTURAL else "low"
        ),
        field_origins=dict(_STRUCTURAL_ORIGINS),
        semantic_status=SEMANTIC_STATUS_STRUCTURAL_ONLY,
    )
