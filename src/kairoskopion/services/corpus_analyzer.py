"""Corpus analyzer — extracts patterns from PublishedArticleCorpus.

Deterministic heuristic analysis. No LLM required.
Detects: article type hints, method presence, theory/school keywords,
citation density, abstract structure patterns.
"""

from __future__ import annotations

import dataclasses as dc
import re
from typing import Any

from ..schema import PublishedArticleCorpus


METHOD_KEYWORDS = {
    "empirical": ["survey", "interview", "experiment", "case study", "ethnograph",
                   "observation", "field work", "participant", "sample", "data collect"],
    "conceptual": ["concept", "framework", "theoretical", "argument", "reconstruct",
                    "genealogy", "critique", "philosophy", "normative", "ontolog"],
    "review": ["systematic review", "literature review", "meta-analysis", "survey of",
               "state of the art", "mapping"],
    "mixed": ["mixed method", "quali-quanti", "triangulat"],
}

SCHOOL_KEYWORDS = {
    "phenomenology": ["phenomenol", "husserl", "heidegger", "merleau-ponty", "ihde", "verbeek"],
    "pragmatism": ["pragmatis", "dewey", "james", "peirce", "rorty"],
    "critical_theory": ["critical theory", "habermas", "adorno", "horkheimer", "frankfurt school"],
    "postphenomenology": ["postphenomenol", "ihde", "verbeek", "rosenberger", "technology mediation"],
    "sts": ["science and technology studies", "sts", "actor-network", "latour", "callon"],
    "ai_ethics": ["ai ethics", "artificial intelligence ethics", "machine learning ethics",
                  "algorithmic", "fairness", "bias", "accountab", "transparen"],
    "philosophy_of_technology": ["philosophy of technology", "techno-", "technological"],
    "analytic": ["analytic philosophy", "logical", "formal", "modal"],
}


@dc.dataclass
class CorpusPattern:
    """Detected pattern in a published article corpus."""

    pattern_type: str
    pattern_key: str
    frequency: float
    confidence: str  # low | medium | high
    evidence: list[str] = dc.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dc.asdict(self)


@dc.dataclass
class CorpusAnalysisResult:
    """Result of analyzing a venue's published article corpus."""

    venue_model_id: str | None
    corpus_size: int
    method_patterns: list[CorpusPattern]
    school_patterns: list[CorpusPattern]
    genre_summary: dict[str, float]
    citation_stats: dict[str, Any]
    abstract_patterns: list[str]
    warnings: list[str]
    confidence: str  # low | medium | high
    unknowns: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue_model_id": self.venue_model_id,
            "corpus_size": self.corpus_size,
            "method_patterns": [p.to_dict() for p in self.method_patterns],
            "school_patterns": [p.to_dict() for p in self.school_patterns],
            "genre_summary": self.genre_summary,
            "citation_stats": self.citation_stats,
            "abstract_patterns": self.abstract_patterns,
            "warnings": self.warnings,
            "confidence": self.confidence,
            "unknowns": self.unknowns,
        }


def analyze_venue_corpus(
    corpus: PublishedArticleCorpus,
    article_texts: list[dict[str, Any]] | None = None,
) -> CorpusAnalysisResult:
    """Analyze a venue corpus to extract publication patterns.

    article_texts: list of dicts with keys like 'title', 'abstract', 'keywords',
    'references_count', 'year', 'genre', 'method'. Optional fulltext in 'text'.
    """
    texts = article_texts or []
    n = corpus.corpus_size or len(texts)

    warnings: list[str] = []
    unknowns: list[str] = []

    if n == 0:
        return CorpusAnalysisResult(
            venue_model_id=corpus.venue_model_id,
            corpus_size=0,
            method_patterns=[],
            school_patterns=[],
            genre_summary={},
            citation_stats={},
            abstract_patterns=[],
            warnings=["Empty corpus — no patterns to detect"],
            confidence="none",
            unknowns=["All corpus-derived fields unknown due to empty corpus"],
        )

    if n < 5:
        warnings.append(f"Very small corpus ({n} articles) — patterns may be unreliable")
    elif n < 15:
        warnings.append(f"Small corpus ({n} articles) — moderate confidence only")

    # Method detection from text
    method_counts: dict[str, int] = {}
    school_counts: dict[str, int] = {}
    ref_counts: list[int] = []
    abstract_lengths: list[int] = []

    for art in texts:
        searchable = " ".join([
            (art.get("title") or ""),
            (art.get("abstract") or ""),
            " ".join(art.get("keywords", [])),
            (art.get("text") or "")[:2000],
        ]).lower()

        for method_type, keywords in METHOD_KEYWORDS.items():
            if any(kw in searchable for kw in keywords):
                method_counts[method_type] = method_counts.get(method_type, 0) + 1

        for school, keywords in SCHOOL_KEYWORDS.items():
            if any(kw in searchable for kw in keywords):
                school_counts[school] = school_counts.get(school, 0) + 1

        if art.get("reference_count") or art.get("references_count"):
            rc = art.get("reference_count") or art.get("references_count")
            if isinstance(rc, int):
                ref_counts.append(rc)

        if art.get("abstract"):
            abstract_lengths.append(len(art["abstract"]))

    text_n = len(texts) or 1

    method_patterns = [
        CorpusPattern(
            pattern_type="method",
            pattern_key=method,
            frequency=round(count / text_n, 2),
            confidence="medium" if count >= 3 else "low",
            evidence=[f"{count}/{text_n} articles match keywords"],
        )
        for method, count in sorted(method_counts.items(), key=lambda x: -x[1])
    ]

    school_patterns = [
        CorpusPattern(
            pattern_type="school",
            pattern_key=school,
            frequency=round(count / text_n, 2),
            confidence="medium" if count >= 3 else "low",
            evidence=[f"{count}/{text_n} articles match keywords"],
        )
        for school, count in sorted(school_counts.items(), key=lambda x: -x[1])
    ]

    # Genre summary from corpus distributions
    genre_summary: dict[str, float] = {}
    if corpus.genre_distribution:
        for item in corpus.genre_distribution:
            if isinstance(item, dict):
                genre_summary[item.get("genre", "unknown")] = item.get("fraction", 0.0)

    # Citation stats
    citation_stats: dict[str, Any] = {}
    if ref_counts:
        citation_stats["median_references"] = sorted(ref_counts)[len(ref_counts) // 2]
        citation_stats["mean_references"] = round(sum(ref_counts) / len(ref_counts), 1)
        citation_stats["min_references"] = min(ref_counts)
        citation_stats["max_references"] = max(ref_counts)

    # Abstract patterns
    abstract_patterns: list[str] = []
    if abstract_lengths:
        avg_abs = int(sum(abstract_lengths) / len(abstract_lengths))
        abstract_patterns.append(f"Average abstract length: {avg_abs} chars")
        if avg_abs > 1500:
            abstract_patterns.append("Long abstracts suggest structured/extended abstract style")
        elif avg_abs < 500:
            abstract_patterns.append("Short abstracts suggest concise style")

    if not method_patterns:
        unknowns.append("No method patterns detected — insufficient text data or non-standard methods")
    if not school_patterns:
        unknowns.append("No school/tradition patterns detected")
    if not citation_stats:
        unknowns.append("Citation statistics unavailable — no reference counts in article data")
    if not texts:
        unknowns.append("No article texts provided — analysis based on corpus metadata only")

    confidence = "high" if n >= 20 and texts else ("medium" if n >= 5 else "low")

    return CorpusAnalysisResult(
        venue_model_id=corpus.venue_model_id,
        corpus_size=n,
        method_patterns=method_patterns,
        school_patterns=school_patterns,
        genre_summary=genre_summary,
        citation_stats=citation_stats,
        abstract_patterns=abstract_patterns,
        warnings=warnings,
        confidence=confidence,
        unknowns=unknowns,
    )
