"""Article semantic profile enrichment — deterministic heuristic builder.

Builds ArticleSemanticProfile from ArticleModel by extracting disciplinary
registers, schools/traditions, argument structure, and protected core
candidates from the article's existing fields.

MVP: keyword-based heuristics. LLM enrichment would improve quality.
"""

from __future__ import annotations

import re
from typing import Any

from ..schema import ArticleModel, ArticleSemanticProfile


_DISCIPLINE_KEYWORDS: dict[str, list[str]] = {
    "philosophy_of_technology": [
        "technology", "technics", "technical", "artifact", "artefact",
        "design", "engineering ethics", "philosophy of technology",
    ],
    "STS": [
        "science and technology studies", "STS", "sociotechnical",
        "actor-network", "ANT", "social construction",
    ],
    "philosophy_of_mind": [
        "consciousness", "mind", "mental", "qualia", "intentionality",
        "phenomenal", "cognition",
    ],
    "philosophy_of_science": [
        "scientific method", "falsification", "paradigm", "theory choice",
        "explanation", "causation", "realism",
    ],
    "ethics": [
        "ethics", "moral", "normative", "deontological", "consequentialism",
        "virtue ethics", "bioethics",
    ],
    "epistemology": [
        "knowledge", "epistemic", "justification", "belief", "skepticism",
        "epistemology",
    ],
    "phenomenology": [
        "phenomenology", "phenomenological", "lifeworld", "lebenswelt",
        "intentionality", "embodiment", "lived experience",
    ],
    "critical_theory": [
        "critical theory", "Frankfurt School", "ideology", "emancipation",
        "power", "hegemony", "Habermas",
    ],
}

_SCHOOL_KEYWORDS: dict[str, list[str]] = {
    "Simondonian": ["Simondon", "individuation", "transduction", "concretization"],
    "Heideggerian": ["Heidegger", "Dasein", "enframing", "Gestell", "ready-to-hand"],
    "Deleuzian": ["Deleuze", "assemblage", "rhizome", "deterritorialization"],
    "Stieglerian": ["Stiegler", "technics", "epiphylogenesis", "pharmacology"],
    "Latourian": ["Latour", "actor-network", "ANT", "translation"],
    "pragmatist": ["pragmatism", "Dewey", "James", "Peirce", "inquiry"],
    "analytic": ["analytic philosophy", "logical analysis", "conceptual analysis"],
    "continental": ["continental philosophy", "hermeneutics", "existentialism"],
    "feminist_technoscience": ["feminist", "Haraway", "situated knowledge", "cyborg"],
    "postphenomenology": ["postphenomenology", "Ihde", "human-technology", "multistability"],
}

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


def _detect_disciplines(text: str) -> list[str]:
    found: list[str] = []
    for discipline, keywords in _DISCIPLINE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                found.append(discipline)
                break
    return found


def _detect_schools(text: str) -> list[str]:
    found: list[str] = []
    for school, keywords in _SCHOOL_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                found.append(school)
                break
    return found


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
    if len(disciplines) > 2:
        return "interdisciplinary"
    if "ethics" in disciplines:
        return "applied ethics community"
    if "STS" in disciplines:
        return "STS scholars"
    return f"{disciplines[0]} researchers"


def build_article_semantic_profile(
    article: ArticleModel,
    *,
    manuscript_text: str | None = None,
) -> ArticleSemanticProfile:
    """Build an ArticleSemanticProfile from an ArticleModel.

    Uses keyword heuristics to detect disciplines, schools, argument moves,
    and protected core candidates. Optional manuscript_text broadens detection.
    """
    text = _text_pool(article)
    if manuscript_text:
        text += " " + manuscript_text.lower()

    disciplines = _detect_disciplines(text)
    schools = _detect_schools(text)
    argument_move = _detect_argument_move(text)
    core_candidates = _extract_protected_core_candidates(article)

    unknowns: list[str] = []
    if not disciplines:
        unknowns.append("Could not detect disciplinary registers — heuristic insufficient")
    if not schools:
        unknowns.append("Could not detect schools/traditions — heuristic insufficient")
    if not argument_move:
        unknowns.append("Could not detect argument move type — heuristic insufficient")

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
