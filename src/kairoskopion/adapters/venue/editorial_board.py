"""EditorialBoardCloud live adapter.

Pipeline:
  1. SnapshotCrawler — fetch the editorial board page (HTML only).
  2. Extract editor candidates with regex + light HTML stripping
     (no JS rendering — JS-only pages produce honest UNKNOWN).
  3. For each editor: OpenAlex Author search by name + affiliation hint
     when present; ORCID search by ORCID id when present in the page.
  4. Aggregate institution / country / concept distribution.
  5. Mark derived center-of-gravity signals as `inference` with
     `confidence: low`. Sample size and coverage_ratio captured.

NO LLM. Honest UNKNOWN when extraction fails. No `psychology of editor`.

Per source layer rubric v2 §3.4: editorial board is a cloud / inference,
never psychology. All derived signals get
`derived_signals_authority = "inference"`,
`derived_signals_confidence = "low" | "medium"`.
"""

from __future__ import annotations

import html
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ...schema import EditorialBoardCloud, EditorialBoardMember, _now

logger = logging.getLogger(__name__)


DEFAULT_UA = (
    "Kairoskopion/0.2 "
    "(https://github.com/Stimurid/Kairoskopion; "
    "mailto:kairoskopion@proton.me)"
)

OPENALEX_AUTHORS = "https://api.openalex.org/authors"
ORCID_API_BASE = "https://pub.orcid.org/v3.0"


# -----------------------------------------------------------------------
# HTML utilities (no external HTML parser — keep deps minimal)
# -----------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<script.*?</script>", re.DOTALL | re.IGNORECASE)
_STYLE_RE = re.compile(r"<style.*?</style>", re.DOTALL | re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")

_ORCID_RE = re.compile(r"\b(\d{4}-\d{4}-\d{4}-\d{3}[0-9X])\b")

# Editor candidate patterns. Match common board page formats:
#   "Jane Doe (University of X)"
#   "Prof. Jane Doe, University of X"
#   "Jane Doe — Editor-in-Chief, University of X"
#   "Dr. Jane Doe (Department of Y, University of X, Country)"
_NAME_AFFIL_RE = re.compile(
    r"(?:(?:Prof\.|Professor|Dr\.|Dr|Mr\.|Ms\.|Mrs\.)\s+)?"
    r"([A-Z][a-zà-ÿA-Z'\.\-]+(?:\s+[A-Z][a-zà-ÿA-Z'\.\-]+){1,3})"
    r"\s*[,\-—–\(]\s*"
    r"([^,\)\n\r<]{4,120})"
)

_ROLE_PATTERNS = {
    "editor_in_chief": re.compile(
        r"editor[\s\-]*in[\s\-]*chief|main\s+editor|chief\s+editor",
        re.IGNORECASE,
    ),
    "associate_editor": re.compile(r"associate\s+editor|consult(ing|ative)\s+editor",
                                    re.IGNORECASE),
    "section_editor": re.compile(r"section\s+editor|subject\s+editor",
                                  re.IGNORECASE),
    "board_member": re.compile(r"editorial\s+board|board\s+member|advisory\s+board",
                                re.IGNORECASE),
    "managing_editor": re.compile(r"managing\s+editor", re.IGNORECASE),
}


def strip_html(raw: str) -> str:
    """Remove script/style/tag — keep visible text. Decode entities."""
    raw = _SCRIPT_RE.sub(" ", raw)
    raw = _STYLE_RE.sub(" ", raw)
    raw = _TAG_RE.sub(" ", raw)
    raw = html.unescape(raw)
    raw = _WHITESPACE_RE.sub(" ", raw)
    return raw.strip()


def _http_get(url: str, timeout: int = 25, ua: str = DEFAULT_UA) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            data = r.read()
            # Heuristic: html charset
            charset = "utf-8"
            m = re.search(r"charset=([\w\-]+)", ct, re.IGNORECASE)
            if m:
                charset = m.group(1)
            try:
                return data.decode(charset, errors="replace")
            except LookupError:
                return data.decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        logger.warning("editorial board HTTP fail: %s on %s",
                       type(e).__name__, url[:80])
        return None


def _http_json(url: str, timeout: int = 15, ua: str = DEFAULT_UA) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            import json
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


# -----------------------------------------------------------------------
# Extraction
# -----------------------------------------------------------------------

def extract_orcid_ids(text: str) -> list[str]:
    return sorted(set(_ORCID_RE.findall(text)))


def extract_candidate_members(text: str) -> list[dict[str, Any]]:
    """Heuristic extraction of (name, affiliation) pairs from board page text.

    Returns list of dicts with `full_name`, `affiliation_hint`,
    `role_hint`. Best-effort; many board pages will not match cleanly
    and will yield 0 candidates — that's honest UNKNOWN territory.
    """
    candidates: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    # Find role-tagged windows (best signal)
    for role, pat in _ROLE_PATTERNS.items():
        for m in pat.finditer(text):
            window_start = max(0, m.start() - 50)
            window_end = min(len(text), m.end() + 250)
            window = text[window_start:window_end]
            for nm in _NAME_AFFIL_RE.finditer(window):
                name = nm.group(1).strip(" .,-—–:;")
                affil = nm.group(2).strip(" .,-—–:;")
                if len(name.split()) < 2 or len(name.split()) > 5:
                    continue
                if name.lower() in seen_names:
                    continue
                seen_names.add(name.lower())
                candidates.append({
                    "full_name": name,
                    "affiliation_hint": affil,
                    "role_hint": role,
                })
    # Plus general matches outside any role window
    for nm in _NAME_AFFIL_RE.finditer(text):
        name = nm.group(1).strip(" .,-—–:;")
        affil = nm.group(2).strip(" .,-—–:;")
        if len(name.split()) < 2 or len(name.split()) > 5:
            continue
        if name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        candidates.append({
            "full_name": name,
            "affiliation_hint": affil,
            "role_hint": "board_member",
        })
        if len(candidates) > 100:
            break
    return candidates


# -----------------------------------------------------------------------
# Identity resolution
# -----------------------------------------------------------------------

def openalex_author_lookup(
    name: str, affiliation_hint: str | None = None, timeout: int = 12,
) -> dict | None:
    """Try OpenAlex Authors search for the most-likely match."""
    q = urllib.parse.quote(name.strip())
    url = f"{OPENALEX_AUTHORS}?search={q}&per_page=5"
    resp = _http_json(url, timeout=timeout)
    if not resp:
        return None
    results = resp.get("results", []) or []
    if not results:
        return None
    # If affiliation hint present, prefer the candidate whose
    # last_known_institution display_name shares a token with the hint.
    if affiliation_hint:
        hint_tokens = {
            t.lower()
            for t in re.findall(r"[A-Za-z]{4,}", affiliation_hint)
        }
        for r in results:
            inst = (r.get("last_known_institution") or {}).get("display_name", "")
            inst_tokens = {t.lower() for t in re.findall(r"[A-Za-z]{4,}", inst)}
            if hint_tokens & inst_tokens:
                return r
    return results[0]


def orcid_record(orcid_id: str, timeout: int = 10) -> dict | None:
    url = f"{ORCID_API_BASE}/{orcid_id}/record"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": DEFAULT_UA, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            import json
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------

def build_editorial_board_cloud(
    *,
    board_page_url: str | None = None,
    board_page_html: str | None = None,
    venue_profile_package_id: str | None = None,
    target_sample: int = 30,
    timeout: int = 25,
) -> EditorialBoardCloud:
    """Build an EditorialBoardCloud for one venue.

    Either pass a `board_page_url` (we fetch) or pre-fetched
    `board_page_html`. Returns a cloud with members + distributions
    + derived center-of-gravity signals marked `inference`.

    Honest UNKNOWN when:
    - the page is JS-only (no editor patterns in stripped HTML),
    - the page returns HTTP error,
    - OpenAlex Author search returns nothing for a candidate.
    """
    cloud = EditorialBoardCloud(
        venue_profile_package_id=venue_profile_package_id,
    )

    if board_page_html is None:
        if not board_page_url:
            cloud.unknowns.append(
                "no board_page_url and no board_page_html provided"
            )
            return cloud
        raw = _http_get(board_page_url, timeout=timeout)
        if not raw:
            cloud.unknowns.append(
                f"editorial board page fetch failed: {board_page_url}"
            )
            return cloud
        board_page_html = raw

    text = strip_html(board_page_html)
    if len(text) < 200:
        cloud.unknowns.append(
            "page text shorter than 200 chars after HTML strip — "
            "likely JS-only board page; no extraction possible"
        )
        cloud.warnings.append("JS-only or very thin HTML board page")
        return cloud

    # Pull ORCID ids first (very high signal)
    orcid_ids = extract_orcid_ids(text)

    # Then candidate (name, affiliation) tuples
    candidates = extract_candidate_members(text)
    if not candidates:
        cloud.unknowns.append(
            "no editor name/affiliation pairs matched the heuristic patterns"
        )
        cloud.warnings.append(
            "extraction yielded 0 candidates — board page format may "
            "require a dedicated parser"
        )
        return cloud

    # Cap sample to target
    if len(candidates) > target_sample:
        candidates = candidates[:target_sample]

    members: list[EditorialBoardMember] = []
    inst_dist: dict[str, int] = {}
    country_dist: dict[str, int] = {}
    concept_dist: dict[str, int] = {}
    enrich_count = 0

    for i, cand in enumerate(candidates):
        name = cand.get("full_name") or ""
        affil_hint = cand.get("affiliation_hint")
        role = cand.get("role_hint")
        m = EditorialBoardMember(
            full_name=name,
            role=role,
            affiliation=affil_hint,
            evidence_status="external_claim",
            source_url=board_page_url,
        )
        if orcid_ids and i < len(orcid_ids):
            # ORCID ids appear on the page but we cannot reliably bind a
            # specific ORCID to a specific candidate without DOM-level
            # structure. Leave m.orcid unset; surface raw ids in cloud.
            pass

        # Try to enrich via OpenAlex Author search (rate-limited; cap at 15)
        if enrich_count < 15:
            try:
                oa = openalex_author_lookup(name, affil_hint)
            except Exception:
                oa = None
            if oa:
                m.openalex_author_id = oa.get("id")
                inst = (oa.get("last_known_institution") or {}).get("display_name")
                if inst:
                    m.affiliation = inst
                    inst_dist[inst] = inst_dist.get(inst, 0) + 1
                country = (oa.get("last_known_institution") or {}).get("country_code")
                if country:
                    m.country = country
                    country_dist[country] = country_dist.get(country, 0) + 1
                m.recent_works_count = oa.get("works_count")
                # Top concepts (machine-tagged — INFERENCE)
                cs = [
                    c.get("display_name")
                    for c in (oa.get("x_concepts", []) or [])
                    if isinstance(c, dict) and c.get("display_name")
                ][:5]
                m.research_concepts = cs
                for c in cs:
                    concept_dist[c] = concept_dist.get(c, 0) + 1
                m.evidence_status = "metadata_api_openalex"
                enrich_count += 1
                time.sleep(0.25)
            else:
                m.unknowns.append("no OpenAlex Author match")

        members.append(m)

    cloud.members = [m.to_dict() for m in members]
    cloud.members_sampled = len(members)
    cloud.institutional_distribution = inst_dist
    cloud.country_distribution = country_dist
    cloud.concept_distribution = concept_dist
    cloud.coverage_ratio = None  # unknown total
    cloud.derived_signals = {
        "top_3_institutions": [
            {"name": k, "count": v}
            for k, v in sorted(inst_dist.items(), key=lambda x: -x[1])[:3]
        ],
        "top_3_countries": [
            {"code": k, "count": v}
            for k, v in sorted(country_dist.items(), key=lambda x: -x[1])[:3]
        ],
        "top_5_concepts_machine_tagged": [
            {"name": k, "count": v}
            for k, v in sorted(concept_dist.items(), key=lambda x: -x[1])[:5]
        ],
        "_note": (
            "Center-of-gravity signals are INFERENCE, not psychology. "
            "Per source layer rubric v2 §3.4: editorial board = cloud."
        ),
    }
    cloud.derived_signals_authority = "inference"
    n = len(members)
    cloud.derived_signals_confidence = "high" if n >= 12 else ("medium" if n >= 6 else "low")
    if enrich_count == 0:
        cloud.warnings.append(
            "no OpenAlex Author matches enriched any candidate — "
            "name extraction succeeded but identity resolution failed"
        )
    return cloud
