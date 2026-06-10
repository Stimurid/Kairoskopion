"""Article Modeling Service (spec §15.1).

Builds ArticleModel and ManuscriptModel from manuscript text.
MVP: deterministic heuristic extraction — no LLM calls.
"""

from __future__ import annotations

import re
from typing import Any

from ..enums import (
    ArticleStage,
    Genre,
    InputMode,
    LifecycleStatus,
    MethodStatus,
    NoveltyMode,
)
from ..ids import article_model_id, manuscript_id
from ..schema import ArticleModel, ManuscriptModel


def _extract_title(text: str) -> str | None:
    m = re.match(r"^#\s+(.+)", text.strip())
    return m.group(1).strip() if m else None


def _extract_abstract(text: str) -> str | None:
    m = re.search(r"##\s*Abstract\s*\n+(.+?)(?=\n##|\Z)", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None


def _extract_sections(text: str) -> list[str]:
    return re.findall(r"^##\s+\d*\.?\s*(.+)", text, re.MULTILINE)


def _extract_keywords(text: str) -> list[str]:
    m = re.search(r"\*\*Keywords?:\*\*\s*(.+)", text, re.IGNORECASE)
    if m:
        return [k.strip() for k in m.group(1).split(",")]
    return []


def _extract_references(text: str) -> list[str]:
    refs_section = re.search(r"##\s*References\s*\n(.+)", text, re.DOTALL | re.IGNORECASE)
    if not refs_section:
        return []
    return [
        line.strip().lstrip("- ")
        for line in refs_section.group(1).strip().splitlines()
        if line.strip() and line.strip() != "-"
    ]


def _count_words(text: str) -> int:
    return len(text.split())


def _detect_genre(text: str, sections: list[str]) -> str:
    lower = text.lower()
    # Philosophical/theoretical markers take priority — a theoretical article
    # may mention "review" or "empirical" in passing without being that genre
    philosophical_markers = [
        "conceptual argument", "philosophical argument", "philosophical",
        "epistemic", "ontological", "category error", "theoretical essay",
        "theory of", "legitimation", "institutional theory",
    ]
    review_markers = ["systematic review", "literature review", "meta-analysis"]
    # Count marker hits to disambiguate
    phil_hits = sum(1 for k in philosophical_markers if k in lower)
    review_hits = sum(1 for k in review_markers if k in lower)
    if phil_hits >= 2:
        return Genre.THEORETICAL_ESSAY.value
    if review_hits > 0 and phil_hits == 0:
        return Genre.SYSTEMATIC_REVIEW.value
    if any(k in lower for k in ["case study", "case-based", "empirical case"]):
        return Genre.RESEARCH_ARTICLE.value
    if phil_hits == 1:
        return Genre.THEORETICAL_ESSAY.value
    if review_hits > 0:
        return Genre.SYSTEMATIC_REVIEW.value
    if "commentary" in lower or "response to" in lower:
        return Genre.COMMENTARY.value
    return Genre.UNKNOWN.value


def _detect_method(text: str) -> str:
    lower = text.lower()
    conceptual_markers = [
        "conceptual analysis", "conceptual argument", "philosophical argument",
        "category error", "epistemic legitimation", "institutional analysis",
        "genealogy of", "historical genealogy", "philosophical",
    ]
    empirical_markers = ["experiment", "survey", "interview", "ethnograph",
                         "dataset", "sample size", "regression", "statistical"]
    # Count hits — a philosophical article may mention "empirical" in passing
    conceptual_hits = sum(1 for k in conceptual_markers if k in lower)
    empirical_hits = sum(1 for k in empirical_markers if k in lower)
    if conceptual_hits >= 2:
        return MethodStatus.CONCEPTUAL_METHOD.value
    if conceptual_hits > 0 and empirical_hits == 0:
        return MethodStatus.CONCEPTUAL_METHOD.value
    if empirical_hits >= 2 and conceptual_hits == 0:
        return MethodStatus.EMPIRICAL_METHOD.value
    if conceptual_hits > 0 and empirical_hits > 0:
        return MethodStatus.MIXED.value
    if empirical_hits > 0:
        return MethodStatus.EMPIRICAL_METHOD.value
    if "case" in lower and ("study" in lower or "based" in lower):
        return MethodStatus.CASE_BASED.value
    if "review" in lower and "method" in lower:
        return MethodStatus.REVIEW_METHOD.value
    return MethodStatus.UNKNOWN.value


def _detect_novelty(text: str) -> str:
    lower = text.lower()
    if "critique" in lower or "against" in lower or "impossibility" in lower:
        return NoveltyMode.CRITIQUE.value
    if "new framework" in lower or "new theory" in lower:
        return NoveltyMode.NEW_THEORY.value
    if "translation" in lower and "field" in lower:
        return NoveltyMode.TRANSLATION_BETWEEN_FIELDS.value
    return NoveltyMode.UNKNOWN.value


def build_manuscript_model(text: str, *, source_ref: str | None = None) -> ManuscriptModel:
    """Parse manuscript text into a ManuscriptModel."""
    title = _extract_title(text)
    abstract = _extract_abstract(text)
    sections = _extract_sections(text)
    keywords = _extract_keywords(text)
    refs = _extract_references(text)

    return ManuscriptModel(
        manuscript_id=manuscript_id(),
        source_file_refs=[source_ref] if source_ref else [],
        title=title,
        abstract=abstract,
        keywords=keywords,
        sections=sections,
        word_count=_count_words(text),
        language="en",
        bibliography_refs=refs,
        format="markdown",
        unknowns=_manuscript_unknowns(title, abstract, sections, refs),
    )


def _manuscript_unknowns(
    title: str | None, abstract: str | None, sections: list[str], refs: list[str]
) -> list[str]:
    unknowns: list[str] = []
    if not title:
        unknowns.append("title not extracted")
    if not abstract:
        unknowns.append("abstract not extracted")
    if not sections:
        unknowns.append("sections not extracted")
    if not refs:
        unknowns.append("bibliography not found")
    return unknowns


def build_article_model(
    manuscript: ManuscriptModel,
    text: str,
    *,
    source_ref: str | None = None,
) -> ArticleModel:
    """Build a preliminary ArticleModel from manuscript + raw text."""
    sections = manuscript.sections
    genre = _detect_genre(text, sections)
    method = _detect_method(text)
    novelty = _detect_novelty(text)

    has_sections = len(manuscript.sections) >= 3
    has_substantial_text = manuscript.word_count is not None and manuscript.word_count > 500
    has_full_text = has_sections and has_substantial_text
    stage = ArticleStage.FULL_MANUSCRIPT.value if has_full_text else ArticleStage.ABSTRACT.value
    input_mode = InputMode.FULL_MANUSCRIPT.value if has_full_text else InputMode.ABSTRACT_ONLY.value

    unknowns: list[str] = []
    if not manuscript.abstract:
        unknowns.append("abstract missing — article model is shallow")
    if genre == Genre.UNKNOWN.value:
        unknowns.append("genre not detected")
    if method == MethodStatus.UNKNOWN.value:
        unknowns.append("method not detected")
    if novelty == NoveltyMode.UNKNOWN.value:
        unknowns.append("novelty mode not detected")
    # Protected core cannot be auto-extracted — always mark unknown
    unknowns.append("protected core not confirmed by user")

    # Sprint 2: practical diagnostic fields
    lower_text = text.lower()
    sections_lower = [s.lower() for s in sections]
    has_refs_section = any("reference" in s or "bibliography" in s for s in sections_lower)
    has_methods_section = any("method" in s for s in sections_lower)
    has_data_stmt = "data availability" in lower_text or "data sharing" in lower_text
    ai_disclosure_patterns = [
        "ai disclosure", "ai was used", "ai tools were used",
        "generated by ai", "assisted by ai", "ai-assisted writing",
        "use of artificial intelligence in the preparation",
        "ai writing tool", "language model was used", "llm was used",
        "chatgpt was used", "used chatgpt",
    ]
    has_ai_disc = any(p in lower_text for p in ai_disclosure_patterns)
    abstract_text = manuscript.abstract or ""

    return ArticleModel(
        article_model_id=article_model_id(),
        source_refs=[source_ref] if source_ref else [],
        title_current=manuscript.title,
        abstract_current=manuscript.abstract,
        language=manuscript.language,
        input_mode=input_mode,
        article_stage=stage,
        genre_current=genre,
        method_status=method,
        novelty_mode=novelty,
        citation_ecology_current=(
            f"{len(manuscript.bibliography_refs)} references found"
            if manuscript.bibliography_refs
            else "no bibliography found"
        ),
        unknowns=unknowns,
        confidence="low",
        lifecycle_status=LifecycleStatus.PRELIMINARY.value,
        evidence_refs=[source_ref] if source_ref else [],
        # Sprint 2: practical diagnostic fields
        word_count=manuscript.word_count,
        section_count=len(sections),
        reference_count=len(manuscript.bibliography_refs),
        abstract_length=len(abstract_text.split()) if abstract_text else None,
        has_references_section=has_refs_section,
        has_methods_section=has_methods_section,
        has_data_availability_statement=has_data_stmt,
        has_ai_disclosure=has_ai_disc,
        manuscript_stage=stage,
        extraction_status="heuristic",
    )
