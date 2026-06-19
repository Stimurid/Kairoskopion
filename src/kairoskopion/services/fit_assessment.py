"""Fit Assessment Service (spec §15.4).

Multi-axis comparison of ArticleModel x VenueModel x SubmissionScenario.
MVP: deterministic rule-based -- no LLM, no numeric scores.

Sprint 2: expanded from 8 to 12 axes:
  topic, discipline, genre, argument_structure, method, citation_ecology,
  novelty_positioning, language_register, audience, formal_compliance,
  author_eligibility, publication_regime.

Phase B refactor (commit 3/5)
-----------------------------
The Anglo-biased ``_DISCIPLINE_KEYWORDS`` (13 buckets) and
``_ADJACENCY`` (hardcoded discipline graph) have been REMOVED. The
deterministic discipline-fit axis now consumes the disciplinary
landscape registry built in B0/B1:

* ``_detect_disciplines`` returns discipline_ids surfaced by
  ``DisciplineRegistry.candidates_keyword``.
* ``_adjacent_disciplines`` walks one hop along the registry's
  ``adjacent`` + ``international_mapping`` graph instead of the
  hardcoded set.

When the registry is unavailable (test isolation, data dir missing),
both helpers return empty sets. The discipline axis then comes back
``unknown`` — honest fallback, not a fabricated value.
"""

from __future__ import annotations

import re

from ..enums import (
    AssessmentLevel,
    FitAxisValue,
    FitLabel,
    Genre,
    LifecycleStatus,
    MethodStatus,
)
from ..ids import fit_assessment_id
from ..schema import ArticleModel, FitAssessment, SubmissionScenario, VenueModel


def _load_registry_silently():
    try:
        from .discipline_registry import load_default_registry
        return load_default_registry()
    except Exception:  # noqa: BLE001
        return None


def _detect_disciplines(text: str) -> set[str]:
    """Return discipline_ids surfaced by the registry's keyword pre-filter."""
    if not text or not text.strip():
        return set()
    reg = _load_registry_silently()
    if reg is None:
        return set()
    cands = reg.candidates_keyword(text, region="auto", limit=8)
    return {d.discipline_id for d in cands}


def _adjacent_disciplines(disciplines: set[str]) -> set[str]:
    """Walk one hop along the registry adjacency + international_mapping."""
    reg = _load_registry_silently()
    if reg is None or not disciplines:
        return set()
    adj: set[str] = set()
    for d in disciplines:
        for n in reg.adjacent_of(d):
            adj.add(n.discipline_id)
    return adj


def _axis(name: str, value: str, notes: str, evidence: list[str] | None = None) -> dict:
    return {
        "axis": name,
        "value": value,
        "notes": notes,
        "evidence_refs": evidence or [],
        "unknowns": [] if value != FitAxisValue.UNKNOWN.value else [f"{name} not assessed"],
    }


def assess_fit(
    article: ArticleModel,
    venue: VenueModel,
    scenario: SubmissionScenario,
) -> FitAssessment:
    """Produce a multi-axis FitAssessment (12 axes, no single score)."""
    axes: list[dict] = []
    unknowns: list[str] = []

    # --- Topic fit ---
    scope = (venue.scope_summary or "").lower()
    title = (article.title_current or "").lower()
    abstract = (article.abstract_current or "").lower()
    article_text = f"{title} {abstract}"

    if scope:
        overlap_keywords = ["science", "technology", "social", "sts", "ethics"]
        hits = sum(1 for kw in overlap_keywords if kw in article_text and kw in scope)
        if hits >= 3:
            axes.append(_axis("topic", "strong", "Multiple keyword overlaps with venue scope"))
        elif hits >= 1:
            axes.append(_axis("topic", "medium", "Partial topic overlap with venue scope"))
        else:
            axes.append(_axis("topic", "weak", "Low keyword overlap with venue scope"))
    else:
        axes.append(_axis("topic", "unknown", "Venue scope not available"))
        unknowns.append("topic fit unknown -- venue scope missing")

    # --- Discipline fit ---
    discipline = (article.disciplinary_register_current or "").lower()
    venue_disciplines = _detect_disciplines(scope)
    article_disciplines = _detect_disciplines(f"{discipline} {article_text}")
    if venue_disciplines and article_disciplines:
        overlap = venue_disciplines & article_disciplines
        if overlap:
            axes.append(_axis("discipline", "strong",
                              f"Discipline overlap: {', '.join(sorted(overlap))}"))
        elif venue_disciplines & _adjacent_disciplines(article_disciplines):
            axes.append(_axis("discipline", "medium",
                              "Article discipline is adjacent to venue focus"))
        else:
            axes.append(_axis("discipline", "weak",
                              f"Discipline mismatch: article={', '.join(sorted(article_disciplines))}, "
                              f"venue={', '.join(sorted(venue_disciplines))}"))
    elif venue_disciplines:
        axes.append(_axis("discipline", "unknown",
                          "Article discipline not detected"))
        unknowns.append("discipline fit unknown -- article discipline unclear")
    else:
        axes.append(_axis("discipline", "unknown", "Venue discipline focus unclear"))
        unknowns.append("discipline fit unknown")

    # --- Genre fit ---
    supported = [t.lower() for t in venue.article_types_supported]
    genre = article.genre_current
    if genre and any(genre in t for t in supported):
        axes.append(_axis("genre", "strong", f"Genre '{genre}' supported by venue"))
    elif genre in (Genre.THEORETICAL_ESSAY.value, Genre.CONCEPTUAL_ARTICLE.value):
        if any("research" in t for t in supported):
            axes.append(_axis("genre", "medium",
                              "Theoretical essays uncommon but not excluded"))
        else:
            axes.append(_axis("genre", "weak", "Venue does not list theoretical articles"))
    else:
        axes.append(_axis("genre", "unknown", "Genre fit not assessable"))
        unknowns.append("genre fit unknown")

    # --- Argument structure fit (Sprint 2) ---
    if article.core_claims:
        if article.problem_statement and article.research_question:
            axes.append(_axis("argument_structure", "strong",
                              "Article has problem, question, and claims"))
        elif article.problem_statement or article.research_question:
            axes.append(_axis("argument_structure", "medium",
                              "Partial argument structure detected"))
        else:
            axes.append(_axis("argument_structure", "weak",
                              "Claims present but no clear problem/question framing"))
    else:
        axes.append(_axis("argument_structure", "unknown",
                          "Argument structure not extracted"))
        unknowns.append("argument structure unknown")

    # --- Method fit ---
    method = article.method_status
    if "empiric" in scope:
        if method in (MethodStatus.EMPIRICAL_METHOD.value, MethodStatus.CASE_BASED.value):
            axes.append(_axis("method", "strong", "Empirical method matches venue preference"))
        elif method == MethodStatus.CONCEPTUAL_METHOD.value:
            axes.append(_axis("method", "weak",
                              "Venue prefers empirical work; article is conceptual only"))
        else:
            axes.append(_axis("method", "unknown", "Method fit unclear"))
            unknowns.append("method fit unclear")
    else:
        if method == MethodStatus.UNKNOWN.value:
            axes.append(_axis("method", "unknown", "Method not detected in article"))
            unknowns.append("method not detected")
        else:
            axes.append(_axis("method", "medium", "No strong method preference detected in venue"))

    # --- Citation ecology fit ---
    cite_text = (article.citation_ecology_current or "").lower()
    if cite_text and "references found" in cite_text:
        ref_match = re.search(r"(\d+)\s+references?\s+found", cite_text)
        ref_count = int(ref_match.group(1)) if ref_match else 0
        if ref_count >= 15:
            axes.append(_axis("citation_ecology", "medium",
                              f"Bibliography present ({ref_count} refs) but venue expectations not profiled"))
        elif ref_count >= 8:
            axes.append(_axis("citation_ecology", "medium",
                              f"Moderate bibliography ({ref_count} refs) — may need strengthening for some venues"))
        elif ref_count > 0:
            axes.append(_axis("citation_ecology", "weak",
                              f"Thin bibliography ({ref_count} refs) -- may need strengthening"))
        else:
            axes.append(_axis("citation_ecology", "unknown", "Citation ecology not assessed"))
            unknowns.append("citation ecology not profiled against venue corpus")
    else:
        axes.append(_axis("citation_ecology", "unknown", "Citation ecology not assessed"))
        unknowns.append("citation ecology not profiled against venue corpus")

    # --- Novelty positioning fit (Sprint 2) ---
    novelty = article.novelty_mode
    if novelty and novelty != "unknown":
        # Most venues accept various novelty modes
        axes.append(_axis("novelty_positioning", "medium",
                          f"Novelty mode '{novelty}' detected; venue novelty expectations not profiled"))
    else:
        axes.append(_axis("novelty_positioning", "unknown",
                          "Novelty positioning not detected in article"))
        unknowns.append("novelty positioning unknown")

    # --- Language/register fit ---
    if venue.language_policy and article.language:
        if article.language.lower() in venue.language_policy.lower():
            axes.append(_axis("language_register", "strong", "Language matches venue policy"))
        else:
            axes.append(_axis("language_register", "bad", "Language mismatch"))
    else:
        axes.append(_axis("language_register", "unknown", "Language policy unclear"))
        unknowns.append("language fit unknown")

    # --- Audience fit (Sprint 2) ---
    if venue_disciplines and article_disciplines:
        audience_overlap = venue_disciplines & (article_disciplines | _adjacent_disciplines(article_disciplines))
        if audience_overlap:
            axes.append(_axis("audience", "medium",
                              "Article discipline overlaps venue audience"))
        else:
            axes.append(_axis("audience", "weak",
                              "Article discipline outside venue's core audience"))
    elif scope and article_text:
        axes.append(_axis("audience", "unknown",
                          "Audience alignment not assessable from available data"))
        unknowns.append("audience fit unknown")
    else:
        axes.append(_axis("audience", "unknown", "Audience fit not assessable"))
        unknowns.append("audience fit unknown")

    # --- Formal compliance fit ---
    axes.append(_axis("formal_compliance", "unknown",
                      "Formal compliance requires ComplianceChecklist -- deferred"))
    unknowns.append("formal compliance not yet checked")

    # --- Author eligibility fit (Sprint 2) ---
    # Cannot be assessed without author metadata; mark unknown
    axes.append(_axis("author_eligibility", "unknown",
                      "Author eligibility requires author metadata -- not available"))
    unknowns.append("author eligibility unknown -- no author metadata")

    # --- Publication regime fit ---
    if venue.publication_regime_id:
        axes.append(_axis("publication_regime", "medium",
                          "Classic journal regime -- standard submission path"))
    else:
        axes.append(_axis("publication_regime", "unknown", "Publication regime not profiled"))
        unknowns.append("publication regime unknown")

    # --- Overall label ---
    values = [a["value"] for a in axes]
    bad_count = values.count(FitAxisValue.BAD.value)
    weak_count = values.count(FitAxisValue.WEAK.value)
    strong_count = values.count(FitAxisValue.STRONG.value)
    unknown_count = values.count(FitAxisValue.UNKNOWN.value)

    if bad_count > 0:
        overall = FitLabel.POOR_FIT.value
    elif weak_count >= 2:
        overall = FitLabel.POSSIBLE_BUT_COSTLY.value
    elif unknown_count > len(axes) // 2:
        overall = FitLabel.NOT_ENOUGH_DATA.value
    elif strong_count >= 3 and weak_count == 0:
        overall = FitLabel.STRONG_CANDIDATE.value
    elif strong_count >= 2:
        overall = FitLabel.POSSIBLE.value
    else:
        overall = FitLabel.POSSIBLE_BUT_COSTLY.value

    # Determine lifecycle
    has_refs = bool(article.source_refs and venue.source_refs)
    lifecycle = (LifecycleStatus.PRELIMINARY.value if not has_refs or unknown_count > 2
                 else LifecycleStatus.ANALYZED.value)

    recommendation = _build_recommendation(overall, axes)

    return FitAssessment(
        fit_assessment_id=fit_assessment_id(),
        article_model_id=article.article_model_id,
        venue_model_id=venue.venue_model_id,
        submission_scenario_id=scenario.submission_scenario_id,
        assessment_level=AssessmentLevel.LIGHT_PROFILE.value,
        overall_label=overall,
        axes=axes,
        confidence="low" if unknown_count > 3 else "medium",
        unknowns=unknowns,
        recommendation=recommendation,
        lifecycle_status=lifecycle,
    )


def _build_recommendation(overall: str, axes: list[dict]) -> str:
    parts: list[str] = []
    if overall == FitLabel.STRONG_CANDIDATE.value:
        parts.append("Strong candidate -- proceed with compliance check and submission pack.")
    elif overall == FitLabel.POSSIBLE.value:
        parts.append("Possible fit -- address weak axes before submission.")
    elif overall == FitLabel.POSSIBLE_BUT_COSTLY.value:
        parts.append("Possible but costly -- significant adaptation needed.")
        weak = [a["axis"] for a in axes if a["value"] in ("weak", "bad")]
        if weak:
            parts.append(f"Weak axes: {', '.join(weak)}.")
    elif overall == FitLabel.POOR_FIT.value:
        parts.append("Poor fit -- consider alternative venues.")
    else:
        parts.append("Insufficient data -- collect more evidence before assessment.")
    return " ".join(parts)
