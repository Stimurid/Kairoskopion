"""OpenAlex Works adapter — fetch latest published works for a venue.

This is the HTTP layer the corpus miner service calls. Services
themselves must not import urllib/requests; per the architectural
invariant in tests/test_pipeline_manuscript_venue_fit.py.

Free, no auth. Rate-limit polite (200ms between page fetches).
Reconstructs OpenAlex's `abstract_inverted_index` into plain text.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


OPENALEX_WORKS = "https://api.openalex.org/works"
DEFAULT_UA = (
    "Kairoskopion/0.2 "
    "(https://github.com/Stimurid/Kairoskopion; "
    "mailto:kairoskopion@proton.me)"
)


def _http_json(url: str, timeout: int = 20, ua: str = DEFAULT_UA) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        logger.warning("OpenAlex Works fetch failed: %s on %s",
                       type(e).__name__, url[:80])
        return None


def reconstruct_abstract(inv_index: dict[str, list[int]] | None) -> str | None:
    """Reconstruct an OpenAlex abstract from its inverted index."""
    if not inv_index or not isinstance(inv_index, dict):
        return None
    positions: list[tuple[int, str]] = []
    for word, pos_list in inv_index.items():
        if not isinstance(pos_list, list):
            continue
        for p in pos_list:
            if isinstance(p, int):
                positions.append((p, word))
    if not positions:
        return None
    positions.sort()
    return " ".join(w for _, w in positions)


def ensure_oa_source_id(raw: str) -> str:
    """Accept either bare S-id or full OpenAlex URL, return bare id."""
    if not raw:
        return raw
    if raw.startswith("http"):
        return raw.rstrip("/").rsplit("/", 1)[-1]
    return raw


def fetch_works_for_venue(
    openalex_source_id: str,
    *,
    per_page: int = 25,
    max_works: int = 50,
    timeout: int = 20,
) -> list[dict[str, Any]]:
    """Fetch up to `max_works` latest works for a venue.

    Returns the OpenAlex `results` array entries verbatim, with
    `_reconstructed_abstract` added per work where available.
    """
    sid = ensure_oa_source_id(openalex_source_id)
    works: list[dict[str, Any]] = []
    page = 1
    while len(works) < max_works:
        url = (
            f"{OPENALEX_WORKS}?filter=primary_location.source.id:{sid}"
            f"&per_page={min(per_page, max_works - len(works))}"
            f"&sort=publication_year:desc&page={page}"
        )
        resp = _http_json(url, timeout=timeout)
        if not resp:
            break
        batch = resp.get("results", []) or []
        if not batch:
            break
        for w in batch:
            inv = w.get("abstract_inverted_index")
            w["_reconstructed_abstract"] = reconstruct_abstract(inv)
        works.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
        time.sleep(0.3)
    return works[:max_works]
