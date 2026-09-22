"""Deterministic target-model extraction from a venue corpus.

This first slice intentionally extracts inspectable, low-claim patterns from
metadata/abstract material. It is designed to be replaced or enriched by LLM
and full-text passes without changing the Kairon provider contract.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .models import TargetModelBundle


_METHOD_TERMS = {
    "empirical": ("survey", "experiment", "interview", "dataset", "case study", "empirical"),
    "conceptual": ("conceptual", "theoretical", "framework", "philosophical", "argument"),
    "review": ("review", "systematic review", "literature review", "meta-analysis"),
    "computational": ("model", "simulation", "algorithm", "machine learning", "computational"),
}

_ARGUMENT_TERMS = {
    "critique": ("critique", "challenge", "problem with", "limits of", "against"),
    "proposal": ("propose", "introduce", "develop", "framework", "model"),
    "comparison": ("compare", "comparison", "versus", "contrast"),
    "case_based": ("case study", "case of", "case analysis"),
}

_GENRE_TERMS = {
    "research_article": ("we investigate", "we examine", "study", "results"),
    "conceptual_article": ("conceptual", "theoretical", "argument", "framework"),
    "review_article": ("review", "systematic review", "literature"),
    "position_or_essay": ("position", "essay", "commentary", "perspective"),
}


def _joined(work: dict[str, Any]) -> str:
    title = str(work.get("title") or "")
    abstract = str(work.get("_reconstructed_abstract") or work.get("abstract") or "")
    return f"{title} {abstract}".lower()


def _patterns(works: list[dict[str, Any]], vocab: dict[str, tuple[str, ...]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    for work in works:
        text = _joined(work)
        title = str(work.get("title") or "")
        for label, terms in vocab.items():
            if any(term in text for term in terms):
                counts[label] += 1
                examples.setdefault(label, [])
                if title and len(examples[label]) < 3:
                    examples[label].append(title)
    n = max(len(works), 1)
    return [
        {
            "label": label,
            "count": count,
            "share": round(count / n, 3),
            "examples": examples.get(label, []),
            "evidence_status": "corpus_observation",
        }
        for label, count in counts.most_common()
    ]


def extract_target_models(
    works: list[dict[str, Any]],
    *,
    evidence_refs: list[str] | None = None,
) -> TargetModelBundle:
    refs = list(evidence_refs or [])
    reference_counts = [
        int(w.get("referenced_works_count") or len(w.get("referenced_works") or []))
        for w in works
        if (w.get("referenced_works_count") is not None or w.get("referenced_works"))
    ]
    lengths = []
    for w in works:
        abstract = str(w.get("_reconstructed_abstract") or w.get("abstract") or "")
        if abstract:
            lengths.append(len(re.findall(r"\w+", abstract)))

    limitations = []
    if not works:
        limitations.append("empty corpus")
    if works and not lengths:
        limitations.append("no abstracts available; model extraction relies on titles/metadata")
    confidence = "medium" if len(works) >= 12 and lengths else ("low" if works else "unknown")

    citation = {
        "articles_with_reference_counts": len(reference_counts),
        "median_reference_count": (
            sorted(reference_counts)[len(reference_counts) // 2] if reference_counts else None
        ),
        "mean_reference_count": (
            round(sum(reference_counts) / len(reference_counts), 2) if reference_counts else None
        ),
        "evidence_status": "corpus_observation" if reference_counts else "unknown",
    }

    register_terms = Counter()
    for w in works:
        for token in re.findall(r"[a-zA-Z][a-zA-Z\-]{4,}", _joined(w)):
            if token not in {"about", "using", "their", "these", "which", "study", "paper"}:
                register_terms[token] += 1
    register = [
        {"term": term, "count": count, "evidence_status": "corpus_observation"}
        for term, count in register_terms.most_common(20)
    ]

    return TargetModelBundle(
        genre_patterns=_patterns(works, _GENRE_TERMS),
        argument_patterns=_patterns(works, _ARGUMENT_TERMS),
        method_patterns=_patterns(works, _METHOD_TERMS),
        citation_patterns=citation,
        register_patterns=register,
        novelty_patterns=[],
        evidence_refs=refs,
        confidence=confidence,
        limitations=limitations,
    )
