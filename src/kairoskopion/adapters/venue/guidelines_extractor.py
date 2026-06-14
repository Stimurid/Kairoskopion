"""Minimal FormalSubmissionProfile extractor from author guidelines HTML.

Reads an "instructions for authors" / "author guidelines" page and
pulls out:
  - word_limits (min/max where stated)
  - abstract_word_limit
  - language requirement
  - article_types listed
  - reference_style ('apa' / 'chicago' / 'vancouver' / 'harvard' / 'numeric' / None)
  - open_access status (mentions of OA / hybrid / gold)
  - APC mentions (amount + currency where parseable)
  - AI policy presence

Strict rules:
  - Absent fact = UNKNOWN_NOT_FOUND, NOT a `False` / `None` guess.
  - JS-only / 4xx / unreachable = INACCESSIBLE.
  - All extracted facts carry `evidence_status: external_claim_html`.

NO LLM. NO scraping beyond direct HTTP. Same UA as other adapters.
"""

from __future__ import annotations

import html
import logging
import re
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


DEFAULT_UA = (
    "Kairoskopion/0.2 "
    "(https://github.com/Stimurid/Kairoskopion; "
    "mailto:kairoskopion@proton.me)"
)

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<script.*?</script>", re.DOTALL | re.IGNORECASE)
_STYLE_RE = re.compile(r"<style.*?</style>", re.DOTALL | re.IGNORECASE)
_WS_RE = re.compile(r"\s+")

_WORD_LIMIT_RE = re.compile(
    r"(?:word\s+(?:limit|count|length)|maximum|max\.?|up\s+to)"
    r"[^0-9]{0,30}(\d{3,6})(?:\s*[-–—to]\s*(\d{3,6}))?\s*words?",
    re.IGNORECASE,
)
_ABSTRACT_LIMIT_RE = re.compile(
    r"abstract[^.]{0,80}?(\d{2,4})\s*words?",
    re.IGNORECASE,
)
_REF_STYLE_PATTERNS = {
    "apa": re.compile(r"\bAPA(?:\s+\d+(?:th|st|rd|nd)?\s+edition)?\b", re.IGNORECASE),
    "chicago": re.compile(r"\bChicago(?:\s+(?:manual|style))?\b", re.IGNORECASE),
    "vancouver": re.compile(r"\bVancouver\s+style\b", re.IGNORECASE),
    "harvard": re.compile(r"\bHarvard\s+(?:referenc|style)", re.IGNORECASE),
    "mla": re.compile(r"\bMLA(?:\s+(?:style|format))?\b", re.IGNORECASE),
    "numeric": re.compile(r"numeric(?:al)?\s+reference\s+style", re.IGNORECASE),
}
_ARTICLE_TYPE_HINTS = [
    "research article", "review article", "review",
    "original article", "case study", "case report",
    "commentary", "editorial", "perspective",
    "letter to the editor", "book review", "short communication",
    "rapid communication", "essay", "theoretical essay",
    "conceptual article", "position paper", "methods paper",
    "systematic review", "meta-analysis",
]
_APC_RE = re.compile(
    r"(?:APC|article\s+processing\s+charge|publication\s+fee)[^0-9\$€£]{0,80}"
    r"([\$€£]|USD|EUR|GBP)?\s*(\d{2,5}(?:[,.]\d{3})?)",
    re.IGNORECASE,
)
_AI_POLICY_RE = re.compile(
    r"(generative\s+AI|ChatGPT|large\s+language\s+model(?:s)?|"
    r"AI\s+(?:assistance|tools|disclosure|policy))",
    re.IGNORECASE,
)
_LANGUAGE_HINTS_RE = re.compile(
    r"manuscripts?\s+(?:must|should)\s+be\s+(?:submitted\s+)?in\s+([A-Za-z]+)",
    re.IGNORECASE,
)
_OPEN_ACCESS_RE = re.compile(
    r"(open\s+access|gold\s+open\s+access|hybrid\s+(?:OA|open\s+access)|"
    r"diamond\s+open\s+access)",
    re.IGNORECASE,
)


def _fetch_html(url: str, timeout: int = 25, ua: str = DEFAULT_UA) -> tuple[str | None, str]:
    """Return (html_or_None, access_status)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            data = r.read()
            cs = "utf-8"
            m = re.search(r"charset=([\w\-]+)", ct, re.IGNORECASE)
            if m:
                cs = m.group(1)
            try:
                return data.decode(cs, errors="replace"), "opened"
            except LookupError:
                return data.decode("utf-8", errors="replace"), "opened"
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return None, f"network_{type(e).__name__}"


def _strip(raw: str) -> str:
    raw = _SCRIPT_RE.sub(" ", raw)
    raw = _STYLE_RE.sub(" ", raw)
    raw = _TAG_RE.sub(" ", raw)
    raw = html.unescape(raw)
    return _WS_RE.sub(" ", raw).strip()


def extract_formal_submission_profile(
    *,
    guidelines_url: str | None = None,
    guidelines_html: str | None = None,
) -> dict[str, Any]:
    """Build a FormalSubmissionProfile-shaped dict from the page."""
    result: dict[str, Any] = {
        "source_url": guidelines_url,
        "evidence_status": "external_claim_html",
        "access_status": "unknown",
        "fields_present": {},
        "unknowns": [],
        "warnings": [],
    }

    if guidelines_html is None:
        if not guidelines_url:
            result["access_status"] = "unknown"
            result["unknowns"].append(
                "no guidelines_url and no guidelines_html supplied"
            )
            return result
        guidelines_html, status = _fetch_html(guidelines_url)
        result["access_status"] = status
        if guidelines_html is None:
            result["unknowns"].append(
                f"guidelines page inaccessible: {status}"
            )
            return result

    text = _strip(guidelines_html)
    if len(text) < 200:
        result["access_status"] = "js_only_or_thin"
        result["unknowns"].append(
            "page text shorter than 200 chars after HTML strip — "
            "likely JS-only guidelines; no extraction possible"
        )
        result["warnings"].append("JS-only guidelines page")
        return result

    result["access_status"] = result.get("access_status", "opened") or "opened"

    # Word limits
    wl = _WORD_LIMIT_RE.search(text)
    if wl:
        lo = int(wl.group(1))
        hi = int(wl.group(2)) if wl.group(2) else None
        result["fields_present"]["word_limit"] = {
            "min": lo if hi else None, "max": hi or lo,
            "evidence": "external_claim_html",
        }
    else:
        result["unknowns"].append("word_limit: UNKNOWN_NOT_FOUND")

    abl = _ABSTRACT_LIMIT_RE.search(text)
    if abl:
        result["fields_present"]["abstract_word_limit"] = {
            "max": int(abl.group(1)),
            "evidence": "external_claim_html",
        }
    else:
        result["unknowns"].append("abstract_word_limit: UNKNOWN_NOT_FOUND")

    # Reference style
    styles_hit = [k for k, p in _REF_STYLE_PATTERNS.items() if p.search(text)]
    if styles_hit:
        result["fields_present"]["reference_style"] = {
            "value": styles_hit[0],
            "all_mentions": styles_hit,
            "evidence": "external_claim_html",
        }
    else:
        result["unknowns"].append("reference_style: UNKNOWN_NOT_FOUND")

    # Article types
    text_low = text.lower()
    types_hit = [
        t for t in _ARTICLE_TYPE_HINTS if t in text_low
    ]
    if types_hit:
        result["fields_present"]["article_types"] = {
            "list": types_hit,
            "evidence": "external_claim_html",
        }
    else:
        result["unknowns"].append("article_types: UNKNOWN_NOT_FOUND")

    # Language
    lang_match = _LANGUAGE_HINTS_RE.search(text)
    if lang_match:
        result["fields_present"]["language"] = {
            "value": lang_match.group(1).lower(),
            "evidence": "external_claim_html",
        }
    else:
        result["unknowns"].append("language: UNKNOWN_NOT_FOUND")

    # OA
    oa = _OPEN_ACCESS_RE.search(text)
    if oa:
        result["fields_present"]["open_access"] = {
            "value": oa.group(1).lower(),
            "evidence": "external_claim_html",
        }
    else:
        result["unknowns"].append("open_access: UNKNOWN_NOT_FOUND")

    # APC
    apc = _APC_RE.search(text)
    if apc:
        amount_raw = apc.group(2).replace(",", "")
        try:
            amount = float(amount_raw.replace(".", "")) if amount_raw.count(".") > 1 \
                else float(amount_raw)
        except ValueError:
            amount = None
        result["fields_present"]["apc"] = {
            "currency": apc.group(1),
            "amount": amount,
            "evidence": "external_claim_html",
        }
    else:
        result["unknowns"].append("apc: UNKNOWN_NOT_FOUND")

    # AI policy
    if _AI_POLICY_RE.search(text):
        result["fields_present"]["ai_policy_mentioned"] = {
            "value": True,
            "evidence": "external_claim_html",
        }
    else:
        result["unknowns"].append("ai_policy: UNKNOWN_NOT_FOUND")

    return result
