"""Fit Assessment Service (spec §15.4).

Multi-axis comparison of ArticleModel × VenueModel × SubmissionScenario.
MVP: deterministic rule-based — no LLM, no numeric scores.
"""

from __future__ import annotations

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
    """Produce a multi-axis FitAssessment."""
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
        unknowns.append("topic fit unknown — venue scope missing")

    # --- Discipline fit ---
    discipline = (article.disciplinary_register_current or "").lower()
    if "sts" in scope or "science and technology studies" in scope:
        if "sts" in discipline or "sociology" in discipline:
            axes.append(_axis("discipline", "strong", "Article discipline matches STS venue"))
        elif "philosophy" in discipline or "ethics" in discipline:
            axes.append(_axis("discipline", "medium",
                              "Philosophy/ethics — adjacent to STS but not core"))
        else:
            axes.append(_axis("discipline", "weak", "Discipline mismatch with STS venue"))
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
    bib_count = len(article.citation_ecology_current or "")
    if article.citation_ecology_current and "references found" in article.citation_ecology_current:
        axes.append(_axis("citation_ecology", "unknown",
                          "Bibliography present but venue citation expectations not profiled"))
    else:
        axes.append(_axis("citation_ecology", "unknown", "Citation ecology not assessed"))
    unknowns.append("citation ecology not profiled against venue corpus")

    # --- Language/register fit ---
    if venue.language_policy and article.language:
        if article.language.lower() in venue.language_policy.lower():
            axes.append(_axis("language_register", "strong", "Language matches venue policy"))
        else:
            axes.append(_axis("language_register", "bad", "Language mismatch"))
    else:
        axes.append(_axis("language_register", "unknown", "Language policy unclear"))
        unknowns.append("language fit unknown")

    # --- Formal compliance fit ---
    axes.append(_axis("formal_compliance", "unknown",
                      "Formal compliance requires ComplianceChecklist — deferred"))
    unknowns.append("formal compliance not yet checked")

    # --- Publication regime fit ---
    if venue.publication_regime_id:
        axes.append(_axis("publication_regime", "medium",
                          "Classic journal regime — standard submission path"))
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
        parts.append("Strong candidate — proceed with compliance check and submission pack.")
    elif overall == FitLabel.POSSIBLE.value:
        parts.append("Possible fit — address weak axes before submission.")
    elif overall == FitLabel.POSSIBLE_BUT_COSTLY.value:
        parts.append("Possible but costly — significant adaptation needed.")
        weak = [a["axis"] for a in axes if a["value"] in ("weak", "bad")]
        if weak:
            parts.append(f"Weak axes: {', '.join(weak)}.")
    elif overall == FitLabel.POOR_FIT.value:
        parts.append("Poor fit — consider alternative venues.")
    else:
        parts.append("Insufficient data — collect more evidence before assessment.")
    return " ".join(parts)
