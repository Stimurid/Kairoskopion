"""Venue corpus miner: real OpenAlex Works → corpus → analysis → hull.

Closes the wiring gap: existing `corpus_sampler` consumed only fixture
inputs; `corpus_analyzer` consumed only the result; `corpus_hull_builder`
consumed only the analysis result. This service pulls the chain
together for a real venue identified by its OpenAlex source id.

NO LLM. NO HTTP at the service layer — HTTP lives in
`adapters.venue.openalex_works`, per the architectural invariant
that services must not import network clients.
"""

from __future__ import annotations

import logging
from typing import Any

from ..adapters.venue.openalex_works import (
    ensure_oa_source_id,
    fetch_works_for_venue,
    reconstruct_abstract,
)
from ..schema import (
    FieldPositionModel,
    PublishedArticleCorpus,
    PublishedCorpusHull,
)
from .corpus_analyzer import analyze_venue_corpus
from .corpus_hull_builder import build_venue_corpus_hull

# Re-export so existing callers stay working.
_reconstruct_abstract = reconstruct_abstract
_ensure_oa_source_id = ensure_oa_source_id

logger = logging.getLogger(__name__)


def works_to_article_texts(works: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Materialise OpenAlex Works as the `article_texts` format
    `corpus_analyzer.analyze_venue_corpus` expects."""
    out = []
    for w in works:
        title = w.get("title") or ""
        abstract = w.get("_reconstructed_abstract") or ""
        concepts = [c.get("display_name") for c in (w.get("concepts", []) or [])
                    if isinstance(c, dict) and c.get("display_name")]
        keywords = concepts[:10]
        ref_count = (
            w.get("referenced_works_count")
            or len(w.get("referenced_works", []) or [])
            or 0
        )
        year = w.get("publication_year")
        out.append({
            "title": title,
            "abstract": abstract,
            "keywords": keywords,
            "references_count": ref_count,
            "year": year,
            "_concepts_machine_tagged": concepts,
        })
    return out


def mine_venue_corpus(
    openalex_source_id: str,
    *,
    venue_model_id: str | None = None,
    max_works: int = 50,
) -> tuple[FieldPositionModel, PublishedCorpusHull]:
    """End-to-end: OpenAlex source id → works → analysis → hull.

    Returns `(venue_fpm, hull_metadata)`. Either may carry honest
    UNKNOWN markers when the upstream data is missing.
    """
    sid = ensure_oa_source_id(openalex_source_id)
    logger.info("Mining corpus for OpenAlex source %s (max_works=%d)",
                sid, max_works)
    works = fetch_works_for_venue(sid, max_works=max_works)
    article_texts = works_to_article_texts(works)
    abstracts_available = sum(
        1 for t in article_texts if (t.get("abstract") or "").strip()
    )
    refs_available = sum(1 for t in article_texts if t.get("references_count"))
    years = [t.get("year") for t in article_texts if t.get("year")]

    corpus = PublishedArticleCorpus(
        venue_model_id=venue_model_id,
        corpus_size=len(article_texts),
        collection_period=(
            f"{min(years)}-{max(years)}" if years else None
        ),
    )

    analysis = analyze_venue_corpus(corpus, article_texts)
    venue_fpm = build_venue_corpus_hull(analysis, venue_model_id=venue_model_id)

    hull = PublishedCorpusHull(
        venue_field_position_id=venue_fpm.field_position_id,
        works_fetched=len(works),
        abstracts_available=abstracts_available,
        references_available=refs_available,
        year_range_min=min(years) if years else None,
        year_range_max=max(years) if years else None,
        source_used=sid,
        corpus_analysis_summary={
            "corpus_size": analysis.corpus_size,
            "confidence": analysis.confidence,
            "method_patterns_n": len(analysis.method_patterns),
            "school_patterns_n": len(analysis.school_patterns),
            "warnings": analysis.warnings,
        },
        warnings=list(analysis.warnings),
        unknowns=list(analysis.unknowns),
    )
    if not works:
        hull.unknowns.append(
            f"OpenAlex returned no works for source {sid} — "
            "venue may have no OpenAlex coverage at this tier"
        )
    if abstracts_available == 0 and works:
        hull.warnings.append(
            "no abstracts available from OpenAlex; "
            "school/method patterns rely on titles only — confidence reduced"
        )
    return venue_fpm, hull
