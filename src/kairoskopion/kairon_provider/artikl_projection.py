"""Bind canonical Artikl semantics into Kairoskopion ArticleModel projections."""

from __future__ import annotations

from copy import deepcopy

from ..schema import ArticleModel
from .models import ArtiklArticleProjection


def bind_artikl_projection(
    base: ArticleModel | None,
    projection: ArtiklArticleProjection,
) -> ArticleModel:
    """Return an ArticleModel projection governed by canonical Artikl state.

    Standalone extraction may supply low-level manuscript diagnostics such as
    word/section/reference counts. Semantic fields listed here are overwritten
    by Artikl and cannot be silently re-inferred by Kairoskopion.
    """
    article = deepcopy(base) if base is not None else ArticleModel()

    article.title_current = projection.title or article.title_current
    article.abstract_current = projection.abstract or article.abstract_current
    article.problem_statement = projection.problem_statement
    article.research_question = projection.research_question
    article.object_of_inquiry = projection.object_of_inquiry
    article.core_claims = list(projection.core_claims)
    article.genre_current = projection.genre
    article.disciplinary_register_current = projection.disciplinary_register
    article.novelty_mode = projection.novelty_mode
    article.method_status = projection.method_status
    article.method_description = projection.method_description
    article.theoretical_shoulders = list(projection.theoretical_shoulders)
    article.citation_ecology_current = projection.citation_ecology
    article.protected_core = list(projection.protected_core)
    article.mutable_zones = list(projection.mutable_zones)
    article.language = projection.language or article.language

    authority_ref = (
        f"artikl-state:{projection.artikl_state.state_id}"
        f"@{projection.artikl_state.version or 'unversioned'}"
    )
    article.source_refs = list(dict.fromkeys(
        list(article.source_refs or [])
        + list(projection.artikl_state.source_refs)
        + list(projection.evidence_refs)
        + [authority_ref]
    ))
    article.evidence_refs = list(dict.fromkeys(
        list(article.evidence_refs or [])
        + list(projection.evidence_refs)
        + [authority_ref]
    ))
    article.protected_core_status = "confirmed_by_artikl_projection"
    article.extraction_status = "derived_from_artikl"
    article.confidence = "high"
    article.unknowns = [
        u for u in list(article.unknowns or [])
        if not any(marker in u.lower() for marker in (
            "abstract missing",
            "genre not detected",
            "method not detected",
            "novelty mode not detected",
            "protected core not confirmed",
            "discipline",
        ))
    ]
    return article
