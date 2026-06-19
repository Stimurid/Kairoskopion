"""Article semantic profile enrichment — last-resort deterministic builder.

Builds ``ArticleSemanticProfile`` from ``ArticleModel`` when the
LLM-backed ``ArticleSemanticProfilerAgent`` is unavailable.

Phase B refactor (commit 3/5)
-----------------------------
The Anglo-biased hardcoded keyword tables (``_DISCIPLINE_KEYWORDS`` /
``_SCHOOL_KEYWORDS``) have been REMOVED. The deterministic path now
consumes the disciplinary landscape registry built in B0/B1:

* Disciplines are surfaced via
  ``DisciplineRegistry.candidates_keyword`` (substring pre-filter
  over display names + aliases + legitimate_objects + ontologies).
* Schools/traditions are surfaced by matching ``key_authors[].name``
  across registry cards. This keeps the deterministic path useful
  for the most obvious cases (Latour → Latourian / ANT) without
  hardcoded Anglo-philosophy assumptions.

Argument-move detection still uses the small keyword table below
(``_ARGUMENT_MOVE_PATTERNS``). Move detection is style-based, not
discipline-based — distinct concern from the discipline registry.
That deterministic table is acceptable for the fallback path; the
LLM-driven semantic profiler does this properly when available.
"""

from __future__ import annotations

from typing import Any

from ..schema import ArticleModel, ArticleSemanticProfile


_ARGUMENT_MOVE_PATTERNS: dict[str, list[str]] = {
    "conceptual_analysis": ["conceptual analysis", "concept of", "notion of", "what is"],
    "critique": ["critique", "against", "problematic", "shortcoming", "limitation"],
    "extension": ["extend", "building on", "elaborating", "developing further"],
    "synthesis": ["synthesis", "combining", "integrating", "bridging"],
    "case_study": ["case study", "example of", "illustration", "instantiation"],
    "empirical_contribution": ["empirical", "data", "findings", "experiment", "survey"],
    "historical_reconstruction": ["history of", "genealogy", "development of", "evolution of"],
    "normative_proposal": ["should", "ought", "proposal", "recommendation", "framework for"],
}


def _text_pool(article: ArticleModel) -> str:
    parts = []
    if article.title_current:
        parts.append(article.title_current)
    if article.abstract_current:
        parts.append(article.abstract_current)
    if article.problem_statement:
        parts.append(article.problem_statement)
    if article.research_question:
        parts.append(article.research_question)
    for claim in (article.core_claims or []):
        parts.append(claim)
    if article.method_description:
        parts.append(article.method_description)
    if article.object_of_inquiry:
        parts.append(article.object_of_inquiry)
    return " ".join(parts).lower()


def _load_registry_silently():
    """Return a DisciplineRegistry or None. The deterministic fallback
    must not crash when the registry data dir is missing (tests with
    isolated tmp dirs may not include it)."""
    try:
        from .discipline_registry import load_default_registry
        return load_default_registry()
    except Exception:  # noqa: BLE001
        return None


def _detect_disciplines_via_registry(text: str) -> list[str]:
    """Return discipline_ids surfaced by the keyword pre-filter.
    Empty list when the registry is unavailable or text is empty.
    """
    reg = _load_registry_silently()
    if reg is None or not text.strip():
        return []
    candidates = reg.candidates_keyword(text, region="auto", limit=6)
    return [d.discipline_id for d in candidates]


def _detect_schools_via_registry(text: str) -> list[str]:
    """Return display names of authors found in the text by scanning
    ``key_authors[].name`` across all registry cards. The returned
    list is deduplicated and ordered by first occurrence.

    NOT a school taxonomy — just a "which canonical authors are
    explicitly named here" signal. The LLM-backed semantic profiler
    handles real school detection when available.
    """
    reg = _load_registry_silently()
    if reg is None or not text.strip():
        return []
    lower = text.lower()
    seen: set[str] = set()
    out: list[str] = []
    for d in reg.all():
        for author in d.key_authors:
            name = (author.name or "").strip()
            if not name or name in seen:
                continue
            # Match by last-word token — robust across "Bruno Latour" /
            # "B. Latour" / "Latour, Bruno". Skip very short tokens.
            last = name.split()[-1].lower().strip(",.")
            if len(last) >= 4 and last in lower:
                seen.add(name)
                out.append(name)
                if len(out) >= 8:
                    return out
    return out


def _detect_argument_move(text: str) -> str | None:
    best_match: str | None = None
    best_count = 0
    for move, keywords in _ARGUMENT_MOVE_PATTERNS.items():
        count = sum(1 for kw in keywords if kw.lower() in text)
        if count > best_count:
            best_count = count
            best_match = move
    return best_match if best_count >= 1 else None


def _extract_protected_core_candidates(article: ArticleModel) -> list[str]:
    candidates: list[str] = list(article.protected_core or [])
    if article.object_of_inquiry and article.object_of_inquiry not in candidates:
        candidates.append(f"object of inquiry: {article.object_of_inquiry}")
    for claim in (article.core_claims or []):
        if claim not in candidates:
            candidates.append(claim)
    return candidates


def _infer_audience(disciplines: list[str], text: str) -> str | None:
    if not disciplines:
        return None
    if len(disciplines) >= 3:
        return "interdisciplinary"
    return f"{disciplines[0]} readership"


def build_article_semantic_profile(
    article: ArticleModel,
    *,
    manuscript_text: str | None = None,
) -> ArticleSemanticProfile:
    """Build an ``ArticleSemanticProfile`` from an ``ArticleModel``.

    Last-resort deterministic builder. Uses the disciplinary landscape
    registry for discipline/author detection; argument moves stay on
    a small keyword table. Returns a profile marked
    ``confidence="low"`` if no disciplines surfaced (matches the
    LLM-fallback convention).
    """
    text = _text_pool(article)
    if manuscript_text:
        text += " " + manuscript_text.lower()

    disciplines = _detect_disciplines_via_registry(text)
    schools = _detect_schools_via_registry(text)
    argument_move = _detect_argument_move(text)
    core_candidates = _extract_protected_core_candidates(article)

    unknowns: list[str] = []
    if not disciplines:
        unknowns.append(
            "Could not surface any registry discipline — text needs LLM-driven matching"
        )
    if not schools:
        unknowns.append(
            "Could not surface canonical authors from registry — text needs LLM-driven matching"
        )
    if not argument_move:
        unknowns.append("Could not detect argument move type — keyword heuristic insufficient")

    profile = ArticleSemanticProfile(
        article_model_id=article.article_model_id,
        disciplinary_registers=disciplines,
        primary_discipline=disciplines[0] if disciplines else None,
        schools_and_traditions=schools,
        theoretical_shoulders=list(article.theoretical_shoulders or []),
        argument_move_type=argument_move,
        citation_ecology_description=article.citation_ecology_current,
        protected_core_candidates=core_candidates,
        mutable_zones=list(article.mutable_zones or []),
        intended_audience=_infer_audience(disciplines, text),
        unknowns=unknowns,
        confidence="low" if unknowns else "medium",
        evidence_refs=[f"article:{article.article_model_id}"],
    )
    return profile
