"""Compliance Service (spec §6.24, §15.7).

Generates ComplianceChecklist from venue guidelines + article/manuscript data.
MVP: deterministic extraction from guidelines text.
"""

from __future__ import annotations

import re

from ..enums import LifecycleStatus
from ..ids import compliance_checklist_id
from ..schema import ArticleModel, ComplianceChecklist, ManuscriptModel, VenueModel


def _extract_article_word_limit(gl: str) -> tuple[int, int] | None:
    """Extract article body word limit, ignoring abstract word limits.

    Returns (lo, hi) if an article-level word limit is found, None otherwise.
    A word range that appears on the same line as 'abstract' is skipped.
    """
    for m in re.finditer(r"(\d[\d,]*)\s*[-–]\s*(\d[\d,]*)\s*words?", gl):
        line_start = gl.rfind("\n", 0, m.start()) + 1
        line_end = gl.find("\n", m.end())
        if line_end == -1:
            line_end = len(gl)
        line = gl[line_start:line_end]
        if "abstract" in line:
            continue
        lo = int(m.group(1).replace(",", ""))
        hi = int(m.group(2).replace(",", ""))
        if hi >= 1000:
            return (lo, hi)
    return None


def _check(category: str, requirement: str, status: str,
           source_ref: str = "", notes: str = "") -> dict:
    return {
        "item_id": f"cc_{category}",
        "category": category,
        "requirement": requirement,
        "status": status,
        "source_ref": source_ref,
        "user_action_needed": status in ("missing", "unknown"),
        "notes": notes,
    }


def build_compliance_checklist(
    article: ArticleModel,
    manuscript: ManuscriptModel,
    venue: VenueModel,
    guidelines_text: str,
) -> ComplianceChecklist:
    """Build checklist by matching manuscript against venue guidelines."""
    items: list[dict] = []
    missing: list[str] = []
    blocking: list[str] = []
    warnings: list[str] = []
    gl = guidelines_text.lower()

    # --- Abstract ---
    abstract_match = re.search(r"abstract.*?(\d+)\s*[-–]\s*(\d+)\s*words?", gl)
    if abstract_match:
        lo, hi = int(abstract_match.group(1)), int(abstract_match.group(2))
        if manuscript.abstract:
            wc = len(manuscript.abstract.split())
            if lo <= wc <= hi:
                items.append(_check("abstract", f"Abstract {lo}–{hi} words", "present",
                                    notes=f"Current: {wc} words"))
            else:
                items.append(_check("abstract", f"Abstract {lo}–{hi} words", "non_compliant",
                                    notes=f"Current: {wc} words — out of range"))
                warnings.append(f"Abstract word count ({wc}) outside {lo}–{hi} range")
        else:
            items.append(_check("abstract", f"Abstract {lo}–{hi} words", "missing"))
            missing.append("abstract")
    else:
        items.append(_check("abstract", "Abstract required (limits unknown)", "unknown"))

    # --- Keywords ---
    kw_match = re.search(r"keywords?.*?(\d+)\s*[-–]\s*(\d+)", gl)
    if kw_match:
        lo, hi = int(kw_match.group(1)), int(kw_match.group(2))
        kw_count = len(manuscript.keywords)
        if lo <= kw_count <= hi:
            items.append(_check("keywords", f"Keywords {lo}–{hi}", "present",
                                notes=f"Current: {kw_count}"))
        else:
            items.append(_check("keywords", f"Keywords {lo}–{hi}", "non_compliant",
                                notes=f"Current: {kw_count}"))
            warnings.append(f"Keyword count ({kw_count}) outside {lo}–{hi}")
    elif manuscript.keywords:
        items.append(_check("keywords", "Keywords", "present",
                            notes=f"{len(manuscript.keywords)} keywords"))
    else:
        items.append(_check("keywords", "Keywords", "missing"))
        missing.append("keywords")

    # --- Word count (article body limit, NOT abstract limit) ---
    article_wc = _extract_article_word_limit(gl)
    if article_wc and manuscript.word_count:
        lo, hi = article_wc
        if lo <= manuscript.word_count <= hi:
            items.append(_check("word_count", f"Word count {lo}–{hi}", "present",
                                notes=f"Current: {manuscript.word_count}"))
        else:
            items.append(_check("word_count", f"Word count {lo}–{hi}", "non_compliant",
                                notes=f"Current: {manuscript.word_count}"))
            if manuscript.word_count > hi:
                warnings.append(f"Manuscript too long ({manuscript.word_count} > {hi})")
    else:
        items.append(_check("word_count", "Word count limits", "unknown"))

    # --- References format ---
    if "chicago" in gl:
        items.append(_check("references", "Chicago 17th edition author-date",
                            "unknown", notes="Reference format not verified"))
    elif "apa" in gl:
        items.append(_check("references", "APA style", "unknown"))
    else:
        items.append(_check("references", "Reference format", "unknown"))

    # --- Data availability ---
    if "data availability" in gl:
        items.append(_check("data_availability", "Data availability statement",
                            "missing" if article.method_status != "no_method" else "not_applicable",
                            notes="Required for empirical research per guidelines"))
        if article.method_status != "no_method":
            missing.append("data availability statement")
    else:
        items.append(_check("data_availability", "Data availability", "unknown"))

    # --- Ethics statement ---
    if "ethics" in gl:
        items.append(_check("ethics", "Ethics statement", "unknown",
                            notes="Required where applicable"))

    # --- AI disclosure ---
    if "ai" in gl and ("disclos" in gl or "writing tool" in gl):
        items.append(_check("AI_disclosure", "AI writing tool disclosure", "missing",
                            notes="Authors must disclose AI tool usage"))
        missing.append("AI disclosure statement")
    else:
        items.append(_check("AI_disclosure", "AI disclosure", "unknown",
                            notes="Policy not found in guidelines"))

    # --- COI ---
    if "conflict of interest" in gl or "coi" in gl:
        items.append(_check("COI", "Conflict of interest declaration", "missing"))
        missing.append("COI declaration")

    # --- Anonymization ---
    if "blind" in gl and ("double" in gl or "anonym" in gl):
        items.append(_check("anonymization", "Double-blind anonymization", "unknown",
                            notes="Manuscript must be anonymized for review"))

    # --- Cover letter ---
    if "cover letter" in gl:
        items.append(_check("cover_letter", "Cover letter", "missing"))
        missing.append("cover letter")

    return ComplianceChecklist(
        compliance_checklist_id=compliance_checklist_id(),
        venue_model_id=venue.venue_model_id,
        article_model_id=article.article_model_id,
        publication_regime_id=venue.publication_regime_id,
        checklist_items=items,
        guideline_sources=venue.author_guidelines_refs,
        missing_items=missing,
        blocking_items=blocking,
        warnings=warnings,
        lifecycle_status=LifecycleStatus.DRAFT.value,
    )
