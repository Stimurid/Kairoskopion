"""Crossref journal-works fallback for target-world corpus acquisition.

Used when OpenAlex Works is unavailable on shared runtimes. Crossref is a
publisher-metadata source: titles, authors, DOI, dates, links and sometimes
abstracts are useful evidence, but absence of an abstract/fulltext is preserved.
"""

from __future__ import annotations

import html
import re
import urllib.parse
from pathlib import Path
from typing import Any

from ..crossref import _CROSSREF_BASE
from ..http_client import HttpError, fetch_json


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_abstract(raw: str | None) -> str | None:
    if not raw:
        return None
    text = html.unescape(_TAG_RE.sub(" ", raw))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def fetch_crossref_works_for_issn(
    issn: str,
    *,
    max_works: int = 50,
    cache_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    if not issn:
        return []
    params = urllib.parse.urlencode({
        "rows": min(max(max_works, 1), 100),
        "sort": "published",
        "order": "desc",
        "filter": "type:journal-article",
    })
    url = f"{_CROSSREF_BASE}/journals/{urllib.parse.quote(issn, safe='')}/works?{params}"
    try:
        data = fetch_json(url, cache_dir=Path(cache_dir) if cache_dir else None)
    except HttpError:
        return []

    items = list((data.get("message") or {}).get("items") or [])
    out: list[dict[str, Any]] = []
    for item in items[:max_works]:
        title_parts = item.get("title") or []
        title = title_parts[0] if title_parts else None
        authors = []
        for a in item.get("author") or []:
            name = " ".join(x for x in [a.get("given"), a.get("family")] if x)
            if name:
                authors.append(name)
        year = None
        for field in ("published-print", "published-online", "issued", "created"):
            parts = ((item.get(field) or {}).get("date-parts") or [[]])
            if parts and parts[0] and parts[0][0]:
                year = parts[0][0]
                break
        links = list(item.get("link") or [])
        pdf_url = None
        landing = item.get("URL")
        for link in links:
            ctype = str(link.get("content-type") or "").lower()
            if ctype == "application/pdf" and link.get("URL"):
                pdf_url = link["URL"]
                break
        out.append({
            "id": f"https://doi.org/{item.get('DOI')}" if item.get("DOI") else landing,
            "title": title,
            "publication_year": year,
            "doi": f"https://doi.org/{item.get('DOI')}" if item.get("DOI") else None,
            "_reconstructed_abstract": _strip_abstract(item.get("abstract")),
            "referenced_works_count": item.get("reference-count"),
            "authorships": [{"author": {"display_name": n}} for n in authors],
            "primary_location": {
                "landing_page_url": landing,
                "pdf_url": pdf_url,
            },
            "open_access": {},
            "_provider": "crossref",
            "_raw_crossref_type": item.get("type"),
        })
    return out
