"""Controlled homepage -> guidelines/board/scope URL hop.

For a venue that already carries `homepage_url` we fetch the homepage
ONCE and scan for links that match well-known patterns for:

  - author guidelines / instructions for authors;
  - submission / how-to-submit info;
  - editorial board;
  - aims and scope;
  - open access / APC policy.

Caps:
  - 1 homepage fetch + at most 4 follow-up fetches per venue (one per
    discovered category) — bounded.
  - only same-domain links are followed (publisher-internal navigation).
  - timeout 15s per request.

Returns explicit `access_status` per category:
  - `opened`     : fetched OK;
  - `inaccessible` : 4xx/5xx;
  - `js_only`    : page text <200 chars after strip (JS-rendered);
  - `not_found_after_search` : no link matched the patterns;
  - `unknown`    : missing homepage_url or other prerequisite gap.

Never infers absent policy as "NO" — always UNKNOWN_NOT_FOUND if the
page does not state it. NO LLM.
"""

from __future__ import annotations

import html
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_UA = (
    "Kairoskopion/0.2 "
    "(https://github.com/Stimurid/Kairoskopion; "
    "mailto:kairoskopion@proton.me)"
)

_SCRIPT_RE = re.compile(r"<script.*?</script>", re.DOTALL | re.IGNORECASE)
_STYLE_RE = re.compile(r"<style.*?</style>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_LINK_RE = re.compile(
    r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)
_WS_RE = re.compile(r"\s+")

# Pattern bag per category — match against link href OR visible anchor text.
CATEGORY_PATTERNS: dict[str, list[re.Pattern]] = {
    "guidelines": [
        re.compile(r"author[-_ ]?guidelin", re.IGNORECASE),
        re.compile(r"instructions?[-_ ]?for[-_ ]?authors?", re.IGNORECASE),
        re.compile(r"submission[-_ ]?(?:guidelin|requirement|info)", re.IGNORECASE),
        re.compile(r"manuscript[-_ ]?(?:preparation|guideline)", re.IGNORECASE),
        re.compile(r"\bauthor[-_ ]?info", re.IGNORECASE),
    ],
    "submission_info": [
        re.compile(r"submit[-_ ]?(?:manuscript|article|paper)", re.IGNORECASE),
        re.compile(r"how[-_ ]?to[-_ ]?submit", re.IGNORECASE),
        re.compile(r"\bsubmission[-_ ]?process\b", re.IGNORECASE),
    ],
    "editorial_board": [
        re.compile(r"editorial[-_ ]?board", re.IGNORECASE),
        re.compile(r"\beditors\b", re.IGNORECASE),
        re.compile(r"editorial[-_ ]?team", re.IGNORECASE),
    ],
    "aims_scope": [
        re.compile(r"aims?[-_ ]?(?:and|&)?[-_ ]?scope", re.IGNORECASE),
        re.compile(r"about[-_ ]?(?:the[-_ ]?)?journal", re.IGNORECASE),
        re.compile(r"\bjournal[-_ ]?info\b", re.IGNORECASE),
    ],
    "policy_oa_apc": [
        re.compile(r"open[-_ ]?access", re.IGNORECASE),
        re.compile(r"article[-_ ]?processing[-_ ]?charge", re.IGNORECASE),
        re.compile(r"\bAPC\b"),
        re.compile(r"publication[-_ ]?fee", re.IGNORECASE),
    ],
}


def _strip_text(s: str) -> str:
    s = _SCRIPT_RE.sub(" ", s)
    s = _STYLE_RE.sub(" ", s)
    s = _TAG_RE.sub(" ", s)
    s = html.unescape(s)
    return _WS_RE.sub(" ", s).strip()


def _fetch(url: str, *, timeout: int = 15) -> tuple[str | None, str]:
    """Return (body, access_status). Polite-pool not relevant here."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            data = r.read()
            cs = "utf-8"
            m = re.search(r"charset=([\w\-]+)", ct, re.IGNORECASE)
            if m:
                cs = m.group(1)
            try:
                body = data.decode(cs, errors="replace")
            except LookupError:
                body = data.decode("utf-8", errors="replace")
            return body, "opened"
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return None, f"network_{type(e).__name__}"


def _same_host(url: str, host: str) -> bool:
    try:
        return urllib.parse.urlparse(url).netloc.endswith(host)
    except Exception:  # noqa: BLE001
        return False


def _resolve(base: str, href: str) -> str:
    try:
        return urllib.parse.urljoin(base, href)
    except Exception:  # noqa: BLE001
        return href


def discover_urls_from_homepage(
    homepage_url: str, *, per_category_cap: int = 1,
) -> dict[str, Any]:
    """Fetch a journal homepage once and extract per-category URLs.

    Per-category list is capped to `per_category_cap` (default 1).
    Returns:
      {
        "homepage_access_status": "opened" | "http_<code>" | "network_<kind>",
        "discovered": {
            "guidelines": ["url1", ...],
            "editorial_board": [...],
            ...
        },
        "homepage_text_len": int,
        "outgoing_link_count": int,
        "warnings": [...],
      }
    """
    result: dict[str, Any] = {
        "homepage_access_status": "unknown",
        "discovered": {k: [] for k in CATEGORY_PATTERNS.keys()},
        "homepage_text_len": 0,
        "outgoing_link_count": 0,
        "warnings": [],
    }
    if not homepage_url:
        result["warnings"].append("no homepage_url supplied")
        return result

    body, status = _fetch(homepage_url)
    result["homepage_access_status"] = status
    if body is None:
        return result

    text = _strip_text(body)
    result["homepage_text_len"] = len(text)
    if len(text) < 200:
        result["warnings"].append("homepage_text shorter than 200 chars — JS-only?")
        result["homepage_access_status"] = "js_only"
        return result

    host = urllib.parse.urlparse(homepage_url).netloc
    seen_urls: set[str] = set()
    matches: dict[str, list[tuple[int, str]]] = {
        k: [] for k in CATEGORY_PATTERNS
    }
    score_idx = 0
    for m in _LINK_RE.finditer(body):
        score_idx += 1
        href = m.group(1).strip()
        anchor = _strip_text(m.group(2) or "")
        if not href or href.startswith("#"):
            continue
        full = _resolve(homepage_url, href)
        if full in seen_urls:
            continue
        seen_urls.add(full)
        if not full.startswith("http"):
            continue
        if not _same_host(full, host):
            continue
        for cat, patterns in CATEGORY_PATTERNS.items():
            for pat in patterns:
                if pat.search(href) or pat.search(anchor):
                    matches[cat].append((score_idx, full))
                    break
    result["outgoing_link_count"] = len(seen_urls)
    for cat, lst in matches.items():
        # Stable order: first match wins; cap to per_category_cap
        # Use a seen-url filter to avoid same URL twice
        deduped: list[str] = []
        seen: set[str] = set()
        for _, u in lst:
            if u in seen:
                continue
            seen.add(u)
            deduped.append(u)
            if len(deduped) >= per_category_cap:
                break
        result["discovered"][cat] = deduped
        if not deduped:
            result["warnings"].append(f"{cat}: not_found_after_search")
    return result
