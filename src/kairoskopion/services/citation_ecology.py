"""Citation ecology analysis — bibliography vs venue expectations.

Compares a BibliographyProfile against VenueModel/guidelines to find
gaps, warning signals, and adaptation tasks. No external API calls.
"""

from __future__ import annotations

import re
from typing import Any

from ..enums import CitationGapSeverity
from ..ids import citation_ecology_report_id
from ..schema import (
    ArticleModel,
    BibliographyProfile,
    CitationEcologyReport,
    CitationGap,
    CitationTask,
    VenueModel,
)


def build_citation_ecology_report(
    bib_profile: BibliographyProfile,
    article: ArticleModel,
    venue: VenueModel,
    venue_guidelines_text: str,
) -> CitationEcologyReport:
    """Analyze citation ecology: gaps, tasks, warnings."""
    gaps: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    warnings: list[str] = []
    unknowns: list[str] = []
    bridges: list[str] = []

    if bib_profile.total_references == 0:
        unknowns.append("No bibliography data available")
        return CitationEcologyReport(
            article_model_id=article.article_model_id,
            venue_model_id=venue.venue_model_id,
            bibliography_profile_id=bib_profile.bibliography_profile_id,
            gaps=gaps,
            tasks=tasks,
            unknowns=unknowns,
            summary="No bibliography to analyze.",
        )

    # Reference count analysis
    _check_reference_count(bib_profile, venue_guidelines_text, gaps, tasks, warnings)

    # Recency analysis
    _check_recency(bib_profile, venue_guidelines_text, gaps, tasks, warnings)

    # Source kind diversity
    _check_source_diversity(bib_profile, gaps, tasks, warnings)

    # DOI coverage
    _check_doi_coverage(bib_profile, gaps, tasks, unknowns)

    # Bridge references (discipline crossover)
    bridges = _detect_bridge_references(bib_profile, article, venue)

    # Venue-specific expectations
    _check_venue_expectations(bib_profile, venue, venue_guidelines_text, gaps, tasks, unknowns)

    # Unknowns from profile
    unknowns.extend(bib_profile.unknowns)
    unknowns.append("Reference verification requires external API (not available in MVP)")

    summary = _build_summary(bib_profile, gaps, tasks, warnings)

    return CitationEcologyReport(
        article_model_id=article.article_model_id,
        venue_model_id=venue.venue_model_id,
        bibliography_profile_id=bib_profile.bibliography_profile_id,
        gaps=gaps,
        tasks=tasks,
        bridge_references_detected=bridges,
        warning_signals=warnings,
        unknowns=unknowns,
        summary=summary,
    )


def _check_reference_count(
    bib: BibliographyProfile,
    guidelines: str,
    gaps: list,
    tasks: list,
    warnings: list,
) -> None:
    ref_limit = _extract_reference_limit(guidelines)
    total = bib.total_references

    if total < 5:
        gaps.append(CitationGap(
            gap_id="gap_low_ref_count",
            gap_type="insufficient_references",
            description=f"Only {total} references — most journals expect significantly more",
            severity=CitationGapSeverity.MAJOR.value,
            suggested_action="Add relevant references to strengthen literature grounding",
        ).to_dict())

    if ref_limit and total > ref_limit:
        warnings.append(
            f"Reference count ({total}) exceeds venue limit ({ref_limit})"
        )
        tasks.append(CitationTask(
            task_id="task_trim_refs",
            task_type="trim_bibliography",
            description=f"Reduce references from {total} to at most {ref_limit}",
            priority="high",
            related_gap_id=None,
        ).to_dict())


def _check_recency(
    bib: BibliographyProfile,
    guidelines: str,
    gaps: list,
    tasks: list,
    warnings: list,
) -> None:
    if bib.recency_profile in ("dated", "historical"):
        gaps.append(CitationGap(
            gap_id="gap_dated_refs",
            gap_type="outdated_bibliography",
            description=f"Bibliography recency: {bib.recency_profile} (median year: {bib.year_median})",
            severity=CitationGapSeverity.MAJOR.value,
            suggested_action="Add recent publications (last 5 years) relevant to the topic",
        ).to_dict())
        tasks.append(CitationTask(
            task_id="task_add_recent",
            task_type="add_recent_references",
            description="Search for and add recent publications to update bibliography",
            priority="high",
            requires_external_api=True,
        ).to_dict())

    if bib.year_min and bib.year_max:
        span = bib.year_max - bib.year_min
        if span < 5 and bib.total_references > 3:
            warnings.append(
                f"Narrow year range ({bib.year_min}–{bib.year_max}): "
                "may signal limited literature coverage"
            )


def _check_source_diversity(
    bib: BibliographyProfile,
    gaps: list,
    tasks: list,
    warnings: list,
) -> None:
    dist = bib.source_kind_distribution
    total = bib.total_references
    if total == 0:
        return

    kinds_present = {k for k, v in dist.items() if v > 0 and k != "unknown"}

    if len(kinds_present) == 1:
        only_kind = next(iter(kinds_present))
        warnings.append(f"All references are {only_kind} — limited source diversity")

    book_count = dist.get("book", 0) + dist.get("edited_volume", 0)
    journal_count = dist.get("journal_article", 0)

    if total >= 5 and journal_count == 0:
        gaps.append(CitationGap(
            gap_id="gap_no_journal_refs",
            gap_type="no_journal_articles",
            description="No journal article references detected — most venues expect peer-reviewed sources",
            severity=CitationGapSeverity.MINOR.value,
            suggested_action="Add peer-reviewed journal articles",
        ).to_dict())


def _check_doi_coverage(
    bib: BibliographyProfile,
    gaps: list,
    tasks: list,
    unknowns: list,
) -> None:
    if bib.total_references == 0:
        return

    doi_ratio = bib.doi_count / bib.total_references
    if doi_ratio == 0:
        unknowns.append("No DOIs detected — cannot verify references without external API")
    elif doi_ratio < 0.3:
        unknowns.append(
            f"Low DOI coverage ({bib.doi_count}/{bib.total_references}) — "
            "many references cannot be machine-verified"
        )


def _detect_bridge_references(
    bib: BibliographyProfile,
    article: ArticleModel,
    venue: VenueModel,
) -> list[str]:
    """Detect references that might serve as discipline bridges."""
    bridges: list[str] = []
    venue_scope = (venue.scope_summary or "").lower()
    article_discipline = (article.disciplinary_register_current or "").lower()

    if not venue_scope or not article_discipline:
        return bridges

    for ref_dict in bib.references:
        raw = ref_dict.get("raw_text", "").lower()
        venue_name = ref_dict.get("venue_fragment", "") or ""
        combined = raw + " " + venue_name.lower()

        in_article_field = any(w in combined for w in article_discipline.split() if len(w) > 3)
        in_venue_scope = any(w in combined for w in venue_scope.split() if len(w) > 3)

        if in_article_field and in_venue_scope:
            author = ref_dict.get("author_fragment", "")
            year = ref_dict.get("year", "")
            if author:
                bridges.append(f"{author} ({year})" if year else author)

    return bridges


def _check_venue_expectations(
    bib: BibliographyProfile,
    venue: VenueModel,
    guidelines: str,
    gaps: list,
    tasks: list,
    unknowns: list,
) -> None:
    lower_guidelines = guidelines.lower()

    if "recent" in lower_guidelines or "current" in lower_guidelines:
        if bib.recency_profile not in ("recent", None):
            gaps.append(CitationGap(
                gap_id="gap_venue_wants_recent",
                gap_type="venue_recency_mismatch",
                description="Venue guidelines emphasize recent/current literature but bibliography is not recent",
                severity=CitationGapSeverity.MINOR.value,
                venue_expectation="Recent literature expected",
            ).to_dict())

    if re.search(r"reference\s+format|citation\s+style|apa|chicago|harvard|vancouver", lower_guidelines):
        unknowns.append("Venue specifies citation style — format compliance not checked (needs manual review)")

    if "data availability" in lower_guidelines or "data sharing" in lower_guidelines:
        has_data_refs = any(
            "dataset" in r.get("raw_text", "").lower() or "data" in r.get("title_fragment", "").lower()
            for r in bib.references
            if r.get("title_fragment")
        )
        if not has_data_refs:
            unknowns.append("Venue may expect data references — none detected in bibliography")


def _extract_reference_limit(guidelines: str) -> int | None:
    match = re.search(
        r"(?:maximum|max|up\s+to|no\s+more\s+than|limit)\s*[:\s]*(\d+)\s*references",
        guidelines.lower(),
    )
    if match:
        return int(match.group(1))
    return None


def _build_summary(
    bib: BibliographyProfile,
    gaps: list,
    tasks: list,
    warnings: list,
) -> str:
    parts = [
        f"{bib.total_references} references parsed",
        f"years {bib.year_min}–{bib.year_max}" if bib.year_min else "no years detected",
        f"{bib.doi_count} DOIs" if bib.doi_count else "no DOIs",
        f"recency: {bib.recency_profile}" if bib.recency_profile else "",
    ]
    summary = "; ".join(p for p in parts if p)

    if gaps:
        summary += f". {len(gaps)} gap(s) found"
    if tasks:
        summary += f", {len(tasks)} task(s) suggested"
    if warnings:
        summary += f", {len(warnings)} warning(s)"

    return summary + "."
