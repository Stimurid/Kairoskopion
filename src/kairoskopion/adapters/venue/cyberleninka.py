"""CyberLeninka adapter — Russian humanities/philosophy journals.

cyberleninka.ru has a free public search at:
  POST https://cyberleninka.ru/api/search

Request body (JSON):
  {"mode": "articles", "q": "<query>", "size": <int>, "from": <int>}

Returns articles with `journal` field (name) and other metadata.
We aggregate by `journal` to get a venue candidate list.

This is one third of the missing Russian-regime layer the rubric calls
"C indexers and registries (ВАК/РИНЦ)". CyberLeninka itself is **not**
ВАК / РИНЦ, but its coverage substantially overlaps Russian humanities
journals indexed by ВАК. For a true ВАК authority signal you need
elibrary.ru access, which requires auth (deferred per operator
instruction).

NO LLM. NO scraping beyond the public JSON API.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from collections import Counter
from typing import Any

from .base import (
    VenueAdapter,
    VenueAdapterError,
    VenueAdapterMode,
    VenueAdapterResult,
    VenueAdapterStatus,
    _now_iso,
)

logger = logging.getLogger(__name__)


CYBERLENINKA_API = "https://cyberleninka.ru/api/search"
DEFAULT_UA = (
    "Kairoskopion/0.2 "
    "(https://github.com/Stimurid/Kairoskopion; "
    "mailto:kairoskopion@proton.me)"
)


CYBERLENINKA_FIXTURE = {
    "articles": [
        {
            "name": "Тестовая статья по философии техники",
            "year": "2023",
            "journal": "Вопросы философии",
            "authors": ["Иванов И.И."],
            "annotation": "Тестовая аннотация",
            "link": "https://example.com/article",
        },
    ],
    "found": 1,
    "size": 1,
}


def _post_json(url: str, body: dict, timeout: int = 20) -> dict | None:
    try:
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": DEFAULT_UA,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        logger.warning("CyberLeninka fetch failed: %s on %s",
                       type(e).__name__, url)
        return None


def search_journals(
    query: str, sample_articles: int = 50, mode: str = "live"
) -> list[dict[str, Any]]:
    """Aggregate journal records from a CyberLeninka article search.

    Returns a list of dicts with `canonical_name`, `article_sample`,
    `language`, `evidence_status`.
    """
    if mode == "fixture":
        articles = CYBERLENINKA_FIXTURE.get("articles", []) or []
    else:
        resp = _post_json(CYBERLENINKA_API, {
            "mode": "articles",
            "q": query,
            "size": sample_articles,
            "from": 0,
        })
        if not resp:
            return []
        articles = resp.get("articles") or []

    # Aggregate by journal
    by_journal: dict[str, list[dict[str, Any]]] = {}
    for a in articles:
        jname = (a.get("journal") or "").strip()
        if not jname:
            continue
        by_journal.setdefault(jname, []).append(a)

    out: list[dict[str, Any]] = []
    for jname, arts in by_journal.items():
        years = [a.get("year") for a in arts if a.get("year")]
        out.append({
            "canonical_name": jname,
            "language": "ru",
            "language_evidence_status": "external_claim_cyberleninka",
            "article_sample_count": len(arts),
            "article_titles_sample": [a.get("name") for a in arts[:5]],
            "year_range": [min(years), max(years)] if years else None,
            "first_article_link": arts[0].get("link") if arts else None,
            "venue_type": "journal",
            "source": "CyberLeninka",
            "discovery_query": query,
            "evidence_status": "external_claim",
            "unknowns": [
                "ISSN not provided by CyberLeninka article-level API",
                "VAK / RINTS status requires elibrary.ru auth — UNKNOWN_NOT_VERIFIED",
                "publisher field is not in the article-level response",
            ],
        })
    out.sort(key=lambda x: -x["article_sample_count"])
    return out


def mine_journal_articles(
    journal_name: str,
    *,
    size: int = 30,
    timeout: int = 25,
    mode: str = "live",
) -> dict[str, Any]:
    """Fetch and aggregate article-level hits FOR ONE JOURNAL.

    Strategy: query CyberLeninka with the journal name as `q`; keep only
    hits whose `journal` field equals the queried name (case-insensitive,
    whitespace-normalized).

    Returns a dict with `articles` (list of {title, year, link}),
    `years` (set), `unique_titles` count, `topic_terms` (extracted from
    titles), `evidence_status`, `unknowns`.

    NOT a full corpus_analyzer-compatible blob: CyberLeninka does not
    expose abstracts or references via the search API. Marked
    explicitly as `CYBERLENINKA_SEARCH_DERIVED`.
    """
    if mode == "fixture":
        body = CYBERLENINKA_FIXTURE
    else:
        body = _post_json(CYBERLENINKA_API, {
            "mode": "articles",
            "q": journal_name,
            "size": size,
            "from": 0,
        }, timeout=timeout) or {}

    raw_articles = body.get("articles") or []
    name_norm = re.sub(r"\s+", " ", journal_name.strip().lower())
    matched: list[dict[str, Any]] = []
    for a in raw_articles:
        jname = a.get("journal") or ""
        if re.sub(r"\s+", " ", jname.strip().lower()) == name_norm:
            matched.append(a)

    titles = [a.get("name") for a in matched if a.get("name")]
    years_raw = [a.get("year") for a in matched if a.get("year")]
    years: list[int] = []
    for y in years_raw:
        try:
            years.append(int(y))
        except (TypeError, ValueError):
            pass

    # Lightweight topic term extraction from titles
    topic_counter: dict[str, int] = {}
    for t in titles:
        for tok in re.findall(r"[A-Za-zА-Яа-яЁё]{4,}", t or ""):
            low = tok.lower()
            if low in _RU_STOPWORDS or low in _EN_STOPWORDS:
                continue
            topic_counter[low] = topic_counter.get(low, 0) + 1
    top_terms = sorted(topic_counter.items(), key=lambda x: -x[1])[:15]

    out = {
        "journal_name": journal_name,
        "articles": [
            {"title": a.get("name"), "year": a.get("year"),
             "link": a.get("link"),
             "annotation": a.get("annotation")}
            for a in matched
        ],
        "matched_count": len(matched),
        "years": sorted(set(years)),
        "year_range": [min(years), max(years)] if years else None,
        "unique_titles": len(set(titles)),
        "top_topic_terms": [{"term": t, "count": c} for t, c in top_terms],
        "evidence_status": "CYBERLENINKA_SEARCH_DERIVED",
        "source": "CyberLeninka",
        "unknowns": [
            "no abstracts in article-level search API",
            "no references in article-level search API",
            "topic terms are bag-of-words from titles, not corpus_analyzer patterns",
        ],
    }
    if not matched:
        out["unknowns"].append(
            f"no exact-name matches for {journal_name!r} in CyberLeninka "
            f"(out of {len(raw_articles)} raw search hits)"
        )
    return out


_RU_STOPWORDS = {
    "вопросы", "журнал", "наука", "статья", "статьи", "вестник",
    "номер", "тема", "ред", "проблема", "проблемы", "анализ",
    "теория", "понятие", "понятия", "значение", "роль", "место",
    "опыт", "автор", "обзор", "основные", "научный", "научной",
    "научного", "исследования", "исследование",
}
_EN_STOPWORDS = {
    "study", "studies", "review", "article", "analysis", "case",
    "based", "between", "across", "through", "introduction",
    "theory", "approach", "research", "perspective", "from",
    "within", "without",
}


class CyberLeninkaAdapter(VenueAdapter):
    """VenueAdapter wrapper for the standalone module functions."""

    adapter_id = "cyberleninka"
    source_role = "russian_journal_registry"
    source_access_mode = "public_search_api"

    def __init__(self, mode: VenueAdapterMode = VenueAdapterMode.OFFLINE_STUB) -> None:
        super().__init__(mode)

    def lookup_venue(
        self,
        *,
        name: str | None = None,
        issn: str | None = None,
        url: str | None = None,
    ) -> VenueAdapterResult:
        if not name:
            return VenueAdapterResult(
                adapter_id=self.adapter_id,
                mode=self._mode.value,
                query={"name": name, "issn": issn, "url": url},
                status=VenueAdapterStatus.NO_RESULTS.value,
                error=VenueAdapterError.NOT_FOUND.value,
                evidence_status="UNKNOWN",
                source_role=self.source_role,
                unknowns=["CyberLeninka lookup requires name"],
                fetched_at=_now_iso(),
            )
        live = self._mode == VenueAdapterMode.LIVE_API
        results = search_journals(
            name, sample_articles=20, mode="live" if live else "fixture"
        )
        # Find the exact-match journal
        match = next(
            (r for r in results if r["canonical_name"].lower() == name.lower()),
            None,
        )
        if not match:
            return VenueAdapterResult(
                adapter_id=self.adapter_id,
                mode=self._mode.value,
                query={"name": name},
                status=VenueAdapterStatus.NO_RESULTS.value,
                evidence_status="UNKNOWN",
                source_role=self.source_role,
                unknowns=[f"no CyberLeninka match for journal name {name!r}"],
                fetched_at=_now_iso(),
            )
        return VenueAdapterResult(
            adapter_id=self.adapter_id,
            mode=self._mode.value,
            query={"name": name},
            status=VenueAdapterStatus.SUCCESS.value,
            evidence_status="external_claim_cyberleninka",
            source_role=self.source_role,
            raw_data=match,
            fetched_at=_now_iso(),
        )
