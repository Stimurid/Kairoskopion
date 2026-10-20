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

    # A short bibliography is not evidence of poor scholarship.
    # Require the venue's actual numeric rule before creating a gap.
    minimum = _extract_reference_minimum(guidelines)
    if minimum is not None and total < minimum:
        gaps.append(CitationGap(
            gap_id="gap_venue_reference_minimum",
            gap_type="venue_reference_minimum_unmet",
            description=(
                f"{total} references; venue explicitly requires "
                f"at least {minimum}"
            ),
            severity=CitationGapSeverity.MAJOR.value,
            suggested_action=(
                "Check the actual requirement and seek only genuinely "
                "relevant, verified sources; do not pad references"
            ),
        ).to_dict())
        tasks.append(CitationTask(
            task_id="task_review_reference_minimum",
            task_type="review_reference_requirement",
            description="Resolve the explicit minimum without adding irrelevant sources",
            priority="high",
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
    """Descriptive dates do not create a scholarly deficit by themselves.

    Venue-specific actionable recency requirements belong to
    _check_venue_expectations. Old primary texts can be required sources.
    """
    if bib.recency_profile == "dated" and re.search(
        r"\b(?:recent|current|last\s+\d+\s+years)\b",
        guidelines.lower(),
    ):
        warnings.append(
            "Venue mentions recent work; review the precise requirement "
            "and the manuscript's research question"
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
        unknowns.append(
            "No DOIs found: DOI-based matching unavailable; books, archival "
            "sources and critical editions can use other catalogues and witnesses"
        )
    elif doi_ratio < 0.3:
        unknowns.append(
            f"Limited DOI coverage ({bib.doi_count}/{bib.total_references}): "
            "use other identifiers, editions and source witnesses"
        )


def _detect_bridge_references(
    bib: BibliographyProfile,
    article: ArticleModel,
    venue: VenueModel,
) -> list[str]:
    """Detect references that might serve as discipline bridges.

    Track D fix: previous logic matched any reference whose ``raw_text``
    contained ANY >3-char word from either article_discipline or
    venue_scope. Cockpit symptom: common words like "social" matched
    every reference in social-anything venues, producing a "bridge
    references" list of mostly irrelevant authors.

    New rule: require BOTH overlaps to be on ≥6-char tokens AND at
    least 2 distinct discipline tokens must appear in the reference.
    Anything weaker is honest-unknown — real bridge detection needs
    CitationBridgeAgent (backlog).
    """
    bridges: list[str] = []
    venue_scope = (venue.scope_summary or "").lower()
    article_discipline = (article.disciplinary_register_current or "").lower()

    if not venue_scope or not article_discipline:
        return bridges

    discipline_tokens = {w for w in article_discipline.replace("-", " ").split()
                          if len(w) >= 6}
    venue_tokens = {w for w in venue_scope.replace("-", " ").split()
                     if len(w) >= 6}
    if not discipline_tokens or not venue_tokens:
        return bridges

    for ref_dict in bib.references:
        raw = ref_dict.get("raw_text", "").lower()
        venue_name = ref_dict.get("venue_fragment", "") or ""
        combined_tokens = set((raw + " " + venue_name.lower()).split())

        article_hits = discipline_tokens & combined_tokens
        venue_hits = venue_tokens & combined_tokens

        # Require ≥2 distinct discipline tokens AND ≥1 venue token.
        if len(article_hits) >= 2 and venue_hits:
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


def _extract_reference_minimum(guidelines: str) -> int | None:
    """Return a numeric minimum only when venue text actually states one."""
    match = re.search(
        r"(?:minimum|min|at\s+least|no\s+fewer\s+than)"
        r"\s*[:\s]*(\d+)\s*(?:references|citations)\b",
        guidelines.lower(),
    )
    return int(match.group(1)) if match else None


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
