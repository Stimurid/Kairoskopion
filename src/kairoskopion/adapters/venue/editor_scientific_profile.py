"""Scientific-editor profiling adapter for Kairoskopion target-world builds.

Network access stays in the adapter layer. The adapter resolves public OpenAlex
author metadata and a bounded work sample. It does not infer private editorial
preferences.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from .editorial_board import DEFAULT_UA, openalex_author_lookup

OPENALEX_WORKS = "https://api.openalex.org/works"


def _http_json(url: str, timeout: int = 15) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def fetch_author_works(
    openalex_author_id: str,
    *,
    max_works: int = 12,
    timeout: int = 15,
) -> list[dict[str, Any]]:
    if not openalex_author_id:
        return []
    aid = openalex_author_id.rstrip("/").rsplit("/", 1)[-1]
    url = (
        f"{OPENALEX_WORKS}?filter=author.id:{urllib.parse.quote(aid)}"
        f"&sort=cited_by_count:desc&per_page={max_works}"
    )
    data = _http_json(url, timeout=timeout)
    return list((data or {}).get("results", []) or [])[:max_works]


def resolve_editor_scientific_record(
    *,
    name: str,
    affiliation_hint: str | None = None,
    role: str | None = None,
    max_works: int = 12,
    fixture_author: dict[str, Any] | None = None,
    fixture_works: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    author = fixture_author or openalex_author_lookup(name, affiliation_hint)
    if not author:
        return {
            "name": name,
            "role": role,
            "affiliation_hint": affiliation_hint,
            "evidence_status": "unknown",
            "unknowns": ["no OpenAlex author match"],
            "works": [],
        }

    author_id = author.get("id")
    works = fixture_works if fixture_works is not None else fetch_author_works(
        author_id or "", max_works=max_works
    )
    return {
        "name": author.get("display_name") or name,
        "role": role,
        "openalex_author_id": author_id,
        "orcid": author.get("orcid"),
        "affiliations": [
            x for x in [
                ((author.get("last_known_institution") or {}).get("display_name")),
                affiliation_hint,
            ] if x
        ],
        "x_concepts": [
            c.get("display_name")
            for c in (author.get("x_concepts") or [])
            if isinstance(c, dict) and c.get("display_name")
        ][:10],
        "works_count": author.get("works_count"),
        "cited_by_count": author.get("cited_by_count"),
        "works": works,
        "evidence_status": "metadata_api_openalex",
        "unknowns": [],
    }
