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

_INSTITUTION_TAIL_TOKENS = {
    "Academy", "College", "University", "Institute", "Institution",
    "Department", "School", "Centre", "Center", "Faculty",
}

_COUNTRY_PREFIXES = (
    "USA ", "UK ", "China ", "Sweden ", "Austria ", "Australia ",
    "The Netherlands ", "Netherlands ", "Germany ", "Italy ",
)

_EXPLICIT_ROLE_NAME_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("editor_in_chief", re.compile(
        r"Editors?-in-Chief\s+([A-Z][A-Za-zÀ-ÿ'\.\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ'\.\-]+){1,3})",
        re.IGNORECASE,
    )),
    ("special_issues_editor", re.compile(
        r"Special\s+Issues?\s+Editor\s+([A-Z][A-Za-zÀ-ÿ'\.\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ'\.\-]+){1,3})",
        re.IGNORECASE,
    )),
    ("managing_editor", re.compile(
        r"Managing\s+Editor\s+([A-Z][A-Za-zÀ-ÿ'\.\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ'\.\-]+){1,3})",
        re.IGNORECASE,
    )),
    ("book_review_editor", re.compile(
        r"Book\s+Review\s+Editor\s+([A-Z][A-Za-zÀ-ÿ'\.\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ'\.\-]+){1,3})",
        re.IGNORECASE,
    )),
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



_CREDENTIAL_SUFFIX_RE = re.compile(
    r"\s+(?:PhD|DPhil|MD|MPhil|MSc|MA|MBA|LLM|JD|DDS|DSc)(?:\s*,?\s*(?:PhD|DPhil|MD|MPhil|MSc|MA|MBA|LLM|JD|DDS|DSc))*\s*$",
    re.IGNORECASE,
)


def _clean_editor_name(value: str) -> str:
    value = strip_html(value or "")
    value = _CREDENTIAL_SUFFIX_RE.sub("", value).strip(" ,;:-")
    return value


def _extract_structured_board_candidates(raw_html: str) -> list[dict[str, Any]]:
    """Publisher-aware extraction before the generic visible-text heuristic.

    Springer journal pages expose stable data-test attributes for role, name
    and affiliation. PDC/Techné exposes role headings followed by <ul> blocks.
    Structured extraction prevents role/country/credential text from being
    misclassified as person names.
    """
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    # Springer Nature Link editorial-board cards.
    springer_re = re.compile(
        r'<h2[^>]*data-test=["\']editorDisplayRole["\'][^>]*>(.*?)</h2>'
        r'.*?<h3[^>]*data-test=["\']editorListing["\'][^>]*>(.*?)</h3>'
        r'\s*<div[^>]*class=["\'][^"\']*u-text-default\s+u-line-height-tight[^"\']*["\'][^>]*>(.*?)</div>',
        re.IGNORECASE | re.DOTALL,
    )
    for role_html, name_html, affil_html in springer_re.findall(raw_html):
        role = strip_html(role_html).strip()
        name = _clean_editor_name(name_html)
        affil = strip_html(affil_html).strip()
        if len(name.split()) < 2 or len(name.split()) > 6:
            continue
        key = (name.lower(), role.lower())
        if key in seen:
            continue
        seen.add(key)
        candidates.append({
            "full_name": name,
            "affiliation_hint": affil or None,
            "role_hint": role or "editor",
            "extraction_mode": "springer_structured",
        })

    if candidates:
        return candidates

    # PDC/Techné leadership blocks: role heading + <ul> containing one or
    # more bold names followed by affiliation/address lines.
    role_block_re = re.compile(
        r'<b>\s*<p>\s*([^<]*?(?:Editor|Editors)[^<]*?)\s*</b>\s*</p>\s*<ul>(.*?)</ul>',
        re.IGNORECASE | re.DOTALL,
    )
    for role_html, block in role_block_re.findall(raw_html):
        role = strip_html(role_html).strip()
        name_matches = list(re.finditer(r'<b>\s*([^<]{3,100}?)\s*</b>\s*<br\s*/?>', block, re.IGNORECASE))
        for i, nm in enumerate(name_matches):
            name = _clean_editor_name(nm.group(1))
            if len(name.split()) < 2 or len(name.split()) > 6:
                continue
            start = nm.end()
            end = name_matches[i + 1].start() if i + 1 < len(name_matches) else len(block)
            tail = block[start:end]
            # First non-empty line before contact/address noise is usually
            # department/institution. Keep a bounded combined hint.
            tail = re.sub(r'<a\b.*?</a>', ' ', tail, flags=re.IGNORECASE | re.DOTALL)
            pieces = [
                strip_html(x).strip()
                for x in re.split(r'<br\s*/?>', tail, flags=re.IGNORECASE)
            ]
            pieces = [p for p in pieces if p and "@" not in p][:3]
            affil = ", ".join(pieces) if pieces else None
            key = (name.lower(), role.lower())
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "full_name": name,
                "affiliation_hint": affil,
                "role_hint": role or "editor",
                "extraction_mode": "pdc_structured",
            })

    return candidates


def _clean_name(name: str) -> str:
    out = name.strip(" .,-—–:;")
    for prefix in _COUNTRY_PREFIXES:
        if out.startswith(prefix):
            out = out[len(prefix):].strip()
            break
    parts = out.split()
    while parts and parts[-1] in _INSTITUTION_TAIL_TOKENS:
        parts.pop()
    return " ".join(parts)


def _explicit_role_candidates(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for role, pattern in _EXPLICIT_ROLE_NAME_PATTERNS:
        for m in pattern.finditer(text):
            name = _clean_name(m.group(1))
            if 2 <= len(name.split()) <= 4 and name.lower() not in seen:
                seen.add(name.lower())
                out.append({
                    "full_name": name,
                    "affiliation_hint": None,
                    "role_hint": role,
                })
    # Multi-editor headings often list another editor after the first contact
    # block. Capture a proper-name sequence immediately after an email marker,
    # but only before the next explicit role heading.
    for m in re.finditer(
        r"(?:\[email\s*protected\]|[\w.+-]+@[\w.-]+\.\w+)\s+"
        r"([A-Z][A-Za-zÀ-ÿ'\.\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ'\.\-]+){1,3})",
        text,
    ):
        name = _clean_name(m.group(1))
        if any(x.lower() in name.lower() for x in ("editorial", "overview", "special issues")):
            continue
        if 2 <= len(name.split()) <= 4 and name.lower() not in seen:
            seen.add(name.lower())
            out.append({
                "full_name": name,
                "affiliation_hint": None,
                "role_hint": "editor_in_chief",
            })
    return out


def extract_candidate_members(text: str) -> list[dict[str, Any]]:
    """Heuristic extraction of (name, affiliation) pairs from board page text.

    Returns list of dicts with `full_name`, `affiliation_hint`,
    `role_hint`. Best-effort; many board pages will not match cleanly
    and will yield 0 candidates — that's honest UNKNOWN territory.
    """
    candidates: list[dict[str, Any]] = _explicit_role_candidates(text)
    seen_names: set[str] = {c["full_name"].lower() for c in candidates}
    # Find role-tagged windows (best signal)
    for role, pat in _ROLE_PATTERNS.items():
        for m in pat.finditer(text):
            window_start = max(0, m.start() - 50)
            window_end = min(len(text), m.end() + 250)
            window = text[window_start:window_end]
            for nm in _NAME_AFFIL_RE.finditer(window):
                name = _clean_name(nm.group(1))
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
        name = _clean_name(nm.group(1))
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




def _clean_html_text(fragment: str) -> str:
    return _WHITESPACE_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", fragment))).strip(" ,;:-")


def extract_candidate_members_html(raw_html: str) -> list[dict[str, Any]]:
    """Extract editor names/roles before HTML flattening.

    Role headings define bounded sections. Names are read from bold tags or
    list rows inside each section, so adjacent addresses/countries cannot be
    glued onto the person's name by whitespace flattening.
    """
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    body = raw_html
    marker = re.search(r"EDITORIAL\s+TEAM", body, re.I)
    if marker:
        body = body[marker.start():]

    role_specs = [
        (r"Editors?-in-Chief", "editor_in_chief"),
        (r"Special Issues? Editor", "special_issue_editor"),
        (r"Managing Editor", "managing_editor"),
        (r"Book Review Editor", "book_review_editor"),
        (r"Editorial Assistants?", "editorial_assistant"),
        (r"Editorial Advisory Board", "board_member"),
    ]
    role_re = re.compile(
        "|".join(f"(?P<R{i}>{pat})" for i, (pat, _) in enumerate(role_specs)),
        re.I,
    )
    role_matches = list(role_re.finditer(body))

    def role_for(match: re.Match) -> str:
        for i, (_, role_name) in enumerate(role_specs):
            if match.groupdict().get(f"R{i}"):
                return role_name
        return "board_member"

    def add(name: str, affiliation: str | None, role: str) -> None:
        name = _clean_html_text(name)
        if not (2 <= len(name.split()) <= 5) or len(name) > 100:
            return
        low = name.lower()
        if any(x in low for x in (
            "editorial team", "submission", "journal", "copyright",
            "special issue", "managing editor", "book review editor",
        )):
            return
        if low in seen:
            return
        seen.add(low)
        out.append({
            "full_name": name,
            "affiliation_hint": _clean_html_text(affiliation or "")[:180] or None,
            "role_hint": role,
        })

    if role_matches:
        for i, rm in enumerate(role_matches):
            role = role_for(rm)
            section_end = role_matches[i + 1].start() if i + 1 < len(role_matches) else len(body)
            section = body[rm.end():section_end]

            # Advisory-board style rows.
            for lm in re.finditer(r"<li[^>]*>(.*?)(?=<li|</ul>)", section, re.I | re.S):
                txt = _clean_html_text(lm.group(1))
                if "," in txt:
                    name, rest = [x.strip() for x in txt.split(",", 1)]
                    add(name, rest, role)

            # Named staff in bold tags; multiple names can live in one <ul>.
            bolds = list(re.finditer(
                r"<(?:b|strong)(?:\s[^>]*)?>(.*?)</(?:b|strong)>",
                section, re.I | re.S,
            ))
            for j, bm in enumerate(bolds):
                name = _clean_html_text(bm.group(1))
                tail_end = bolds[j + 1].start() if j + 1 < len(bolds) else len(section)
                tail = section[bm.end():tail_end]
                chunks = [
                    _clean_html_text(x)
                    for x in re.split(r"<br\s*/?>", tail, flags=re.I)
                ]
                chunks = [
                    x for x in chunks
                    if x and "email" not in x.lower() and "@" not in x
                ]
                affiliation = chunks[0] if chunks else None
                add(name, affiliation, role)
        return out

    # Generic fallback for pages without recognizable role headings.
    for m in re.finditer(r"<li[^>]*>(.*?)(?=<li|</ul>)", body, re.I | re.S):
        txt = _clean_html_text(m.group(1))
        if "," in txt:
            name, rest = [x.strip() for x in txt.split(",", 1)]
            add(name, rest, "board_member")
    return out


# -----------------------------------------------------------------------
# Identity resolution
# -----------------------------------------------------------------------

_AFFIL_STOP = {
    "university", "college", "institute", "school", "department", "faculty",
    "centre", "center", "research", "professor", "emeritus", "the", "of",
}


def _norm_person_name(value: str) -> list[str]:
    return [
        t.lower()
        for t in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+", value or "")
        if len(t) >= 1
    ]


def _name_identity_ok(query_name: str, candidate_name: str) -> bool:
    """Conservative person-name gate.

    Require exact surname plus compatible given-name evidence. Initial forms
    are accepted only when the remaining unmatched given-name tokens are also
    initials. This prevents a query like "Dhiraj Murthy" from accepting
    "D. N. Prabhakar Murthy" merely because the surname and first initial match.
    Search rank alone is never accepted as identity.
    """
    q = _norm_person_name(query_name)
    c = _norm_person_name(candidate_name)
    if not q or not c or q[-1] != c[-1]:
        return False

    q_given, c_given = q[:-1], c[:-1]
    if not q_given or not c_given:
        return False
    if q_given == c_given:
        return True

    q_first, c_first = q_given[0], c_given[0]
    first_compatible = (
        q_first == c_first
        or (len(q_first) == 1 and c_first.startswith(q_first))
        or (len(c_first) == 1 and q_first.startswith(c_first))
    )
    if not first_compatible:
        return False

    # Extra given-name evidence may be initials ("Matt J Zook" vs
    # "M. J. Zook"), but an unmatched full name is a different person signal.
    q_extra = q_given[1:]
    c_extra = c_given[1:]
    if any(len(t) > 1 for t in q_extra + c_extra):
        # Full middle names are safe only when they occur on both sides
        # at the same ordinal position.
        common = min(len(q_extra), len(c_extra))
        for i in range(common):
            a, b = q_extra[i], c_extra[i]
            if len(a) > 1 or len(b) > 1:
                if not (
                    a == b
                    or (len(a) == 1 and b.startswith(a))
                    or (len(b) == 1 and a.startswith(b))
                ):
                    return False
        if any(len(t) > 1 for t in q_extra[common:] + c_extra[common:]):
            return False
    return True


def _affiliation_identity_ok(hint: str | None, candidate_inst: str | None) -> bool:
    if not hint:
        return True
    if not candidate_inst:
        return False
    def tokens(value: str) -> set[str]:
        return {
            t.lower()
            for t in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]{3,}", value or "")
            if t.lower() not in _AFFIL_STOP
        }
    h, c = tokens(hint), tokens(candidate_inst)
    return bool(h and c and (h & c))


def openalex_author_lookup(
    name: str, affiliation_hint: str | None = None, timeout: int = 12,
) -> dict | None:
    """Resolve an OpenAlex Author conservatively.

    A search result is accepted only when person-name identity is compatible
    and, when an affiliation hint is supplied, the current institution shares
    a discriminating token. A top-ranked search hit is not identity evidence.
    """
    q = urllib.parse.quote(name.strip())
    url = f"{OPENALEX_AUTHORS}?search={q}&per_page=10"
    resp = _http_json(url, timeout=timeout)
    if not resp:
        return None
    results = resp.get("results", []) or []
    for r in results:
        display = str(r.get("display_name") or "")
        if not _name_identity_ok(name, display):
            continue
        inst = (r.get("last_known_institution") or {}).get("display_name")
        if not _affiliation_identity_ok(affiliation_hint, inst):
            continue
        return r
    return None


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

    structured_candidates = extract_candidate_members_html(board_page_html)
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

    # Prefer publisher-structured extraction. Generic text heuristics are a
    # fallback only; they are too permissive for modern board pages where
    # roles, degrees, cities and countries appear adjacent to names.
    candidates = _extract_structured_board_candidates(board_page_html)
    if not candidates:
        candidates = structured_candidates or extract_candidate_members(text)
        cloud.warnings.append("editor extraction used generic text fallback")
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
