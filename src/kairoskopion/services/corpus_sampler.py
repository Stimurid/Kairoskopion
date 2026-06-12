"""Corpus sampler — builds PublishedArticleCorpus from fixtures or API data.

No live downloads by default. Accepts explicit article fixtures or seed refs.
"""

from __future__ import annotations

import dataclasses as dc
from typing import Any

from ..ids import published_article_corpus_id
from ..schema import PublishedArticleCorpus


@dc.dataclass
class CorpusSampleConfig:
    target_sample_size: int = 30
    selection_strategy: str = "recent_first"  # recent_first | random | cited_first
    require_fulltext: bool = False
    max_age_years: int = 5


@dc.dataclass
class CorpusSampleResult:
    corpus: PublishedArticleCorpus
    representativeness_notes: list[str]
    bias_notes: list[str]
    missing_fulltext_notes: list[str]
    selection_strategy_used: str
    fixture_source: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "corpus": self.corpus.to_dict(),
            "representativeness_notes": self.representativeness_notes,
            "bias_notes": self.bias_notes,
            "missing_fulltext_notes": self.missing_fulltext_notes,
            "selection_strategy_used": self.selection_strategy_used,
            "fixture_source": self.fixture_source,
        }


def sample_venue_corpus(
    *,
    venue_model_id: str | None = None,
    article_fixtures: list[dict[str, Any]] | None = None,
    config: CorpusSampleConfig | None = None,
) -> CorpusSampleResult:
    """Build a PublishedArticleCorpus from provided fixtures.

    Does not make network calls. For live sampling, use adapter layer.
    """
    cfg = config or CorpusSampleConfig()
    articles = article_fixtures or []

    representativeness = []
    bias = []
    missing_ft = []

    if not articles:
        corpus = PublishedArticleCorpus(
            venue_model_id=venue_model_id,
            corpus_size=0,
            collection_period="none",
        )
        representativeness.append("No articles provided — corpus is empty")
        return CorpusSampleResult(
            corpus=corpus,
            representativeness_notes=representativeness,
            bias_notes=["Cannot assess bias on empty corpus"],
            missing_fulltext_notes=["No articles to check"],
            selection_strategy_used=cfg.selection_strategy,
            fixture_source=True,
        )

    # Build distributions from article metadata
    genres: dict[str, int] = {}
    methods: dict[str, int] = {}
    topics: dict[str, int] = {}
    languages: dict[str, int] = {}
    word_counts: list[int] = []
    ref_counts: list[int] = []
    years: list[int] = []

    for art in articles[:cfg.target_sample_size]:
        g = art.get("genre", "unknown")
        genres[g] = genres.get(g, 0) + 1

        m = art.get("method", "unknown")
        methods[m] = methods.get(m, 0) + 1

        for t in art.get("topics", []):
            topics[t] = topics.get(t, 0) + 1

        lang = art.get("language", "en")
        languages[lang] = languages.get(lang, 0) + 1

        if art.get("word_count"):
            word_counts.append(art["word_count"])
        if art.get("reference_count"):
            ref_counts.append(art["reference_count"])
        if art.get("year"):
            years.append(art["year"])

        if not art.get("has_fulltext"):
            missing_ft.append(f"Article '{art.get('title', '?')}' — metadata only")

    n = len(articles[:cfg.target_sample_size])

    genre_dist = [{"genre": k, "count": v, "fraction": round(v / n, 2)} for k, v in sorted(genres.items(), key=lambda x: -x[1])]
    method_dist = [{"method": k, "count": v, "fraction": round(v / n, 2)} for k, v in sorted(methods.items(), key=lambda x: -x[1])]
    topic_clusters = [{"topic": k, "count": v} for k, v in sorted(topics.items(), key=lambda x: -x[1])[:10]]
    lang_dist = [{"language": k, "count": v} for k, v in sorted(languages.items(), key=lambda x: -x[1])]

    avg_wc = int(sum(word_counts) / len(word_counts)) if word_counts else None
    avg_rc = int(sum(ref_counts) / len(ref_counts)) if ref_counts else None

    period = "unknown"
    if years:
        period = f"{min(years)}-{max(years)}"

    corpus = PublishedArticleCorpus(
        venue_model_id=venue_model_id,
        corpus_size=n,
        collection_period=period,
        genre_distribution=genre_dist,
        method_distribution=method_dist,
        topic_clusters=topic_clusters,
        average_word_count=avg_wc,
        average_reference_count=avg_rc,
        language_distribution=lang_dist,
    )

    if n < 10:
        representativeness.append(f"Small sample ({n} articles) — distributions may not be representative")
    if n < 5:
        bias.append(f"Very small sample ({n}) — high risk of selection bias")
    if len(genres) == 1:
        bias.append(f"Only one genre represented: {list(genres.keys())[0]}")
    if not missing_ft:
        representativeness.append("All articles have fulltext available")
    else:
        representativeness.append(f"{len(missing_ft)}/{n} articles are metadata-only")

    return CorpusSampleResult(
        corpus=corpus,
        representativeness_notes=representativeness,
        bias_notes=bias,
        missing_fulltext_notes=missing_ft,
        selection_strategy_used=cfg.selection_strategy,
        fixture_source=True,
    )
