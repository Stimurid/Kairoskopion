"""Venue discovery tradecraft helpers — codifies the lifehacks in
`docs/VENUE_DISCOVERY_TRADECRAFT.md` as reusable Python primitives.

Use this module when writing new discovery code (VF-C5 navigator,
VF-C6 agent, VF-C8 adapters) so the workarounds accumulated in
real-session experience don't get re-derived from scratch every time.

The doc is normative; this module is a thin convenience wrapper. If
they disagree, the doc wins.
"""

from __future__ import annotations

import hashlib
from typing import Iterable


# ---------------------------------------------------------------------------
# URL-pattern fallback library (per tradecraft §2)
# ---------------------------------------------------------------------------

OJS_EDITORIAL_BOARD_PATHS: tuple[str, ...] = (
    # Tried in order. First success wins.
    "/about/editorialTeam",
    "/about/editorialTeam?locale=en_US",     # ?locale workaround
    "/jour/about/editorialTeam",
    "/jour/about/editorialTeam?locale=en_US",
    "/about/displayMembership/9",            # OJS membership list ID
    "/about/displayMembership/8",
    "/about/displayMembership/7",
    "/jour/pages/view/EditorialC",
    "/jour/pages/view/EditorialC?locale=en_US",  # RANEPA pattern
    "/jour/pages/view/EditorialS",
)
"""Editorial-board page paths to try for OJS-based RU academic journals."""


STATIC_HTML_EDITORIAL_BOARD_PATHS: tuple[str, ...] = (
    "/redkollegiya",            # без .html — Chelovek pattern
    "/redkollegiya.html",
    "/redaktsionnaya-kollegiya.html",
    "/editorial-board",
    "/editorial-board.html",
    "/board",
    "/board/",
    "/council",
    "/council/",
    "/redaktor-staff.html",
    "/about/board",
    "/the-editorial-council-and-the-editorial-board.php",  # RGGU pattern
)
"""Editorial-board page paths to try for hand-maintained static-HTML
RU academic journal sites."""


ISSUE_CURRENT_PATHS: tuple[str, ...] = (
    "/issue/current",
    "/jour/issue/current",
    "/index.php/journal/issue/current",  # PKP-OJS pattern (Stasis)
    "/index.php/jourssa/issue/current",  # ЖССА pattern
    "/current",
)
"""Current-issue page paths. /index.php/journal/issue/current works
publicly even when archive issues paywall (verified: Stasis)."""


# ---------------------------------------------------------------------------
# Aggregator allowlist (per tradecraft §4)
# ---------------------------------------------------------------------------

AGGREGATOR_HOSTS: dict[str, dict[str, str]] = {
    "motto-distribution.com": {
        "kind": "catalogue_listing",
        "use_for": "editorial_board_signal",
        "reliability": "high",
        "notes": "Surfaced full Stasis editorial board when journal site 403'd",
    },
    "cyberleninka.ru": {
        "kind": "fulltext_mirror",
        "use_for": "article_corpus + editor_publications",
        "reliability": "high",
        "notes": "Most-comprehensive RU paper mirror",
    },
    "istina.msu.ru": {
        "kind": "author_publication_list",
        "use_for": "editor_publications",
        "reliability": "high",
        "notes": "Definitive for RU researcher publication traces (Markov, 31 titles via Istina)",
    },
    "elibrary.ru": {
        "kind": "author_publication_list",
        "use_for": "editor_publications + RINTs",
        "reliability": "high",
        "notes": "РИНЦ canonical author profiles",
    },
    "vse-svobodny.com": {
        "kind": "bookshop_catalogue",
        "use_for": "issue_toc",
        "reliability": "medium",
        "notes": "RU academic bookshop with full issue ToCs",
    },
    "podpisnie.ru": {
        "kind": "subscription_service",
        "use_for": "issue_toc",
        "reliability": "medium",
    },
    "shop.kunstkamera.ru": {
        "kind": "publication_shop",
        "use_for": "issue_toc + thread_authors",
        "reliability": "high",
        "notes": "Surfaced AnthroForum №60 full Forum thread authors",
    },
    "rusneb.ru": {
        "kind": "national_electronic_library",
        "use_for": "metadata + sometimes_toc",
        "reliability": "medium",
    },
    "ges-2.org": {
        "kind": "art_foundation_announcements",
        "use_for": "joint_special_issue_confirmation",
        "reliability": "high",
        "notes": "Confirmed Logos №1/2024 dispositif-active issue",
    },
    "books.google.com": {
        "kind": "book_catalogue",
        "use_for": "monograph_publication_confirmation",
        "reliability": "high",
    },
    "scholar.google.com": {
        "kind": "publication_search",
        "use_for": "editor_publications + citation_counts",
        "reliability": "high",
        "notes": "Direct profile URLs require known user_id; search-by-name works without auth",
    },
}


# ---------------------------------------------------------------------------
# Failed-pattern blacklist (per tradecraft §9 + verified-broken in §2)
# ---------------------------------------------------------------------------

KNOWN_BLOCKED_PATTERNS: tuple[str, ...] = (
    # Add specific URL patterns that empirically fail across multiple
    # tries. New entries: append after verifying twice.
    "praxema.tspu.ru/redkollegiya.html",
    "praxema.tspu.ru/redaktsionnaya-kollegiya.html",
    "praxema.tspu.ru/praxema-redactor-staff.html",
    "scholar.google.com/citations?user=",       # direct user_id w/o session
    "publications.hse.ru/articles/?author=",    # JS-rendered shell
)


# ---------------------------------------------------------------------------
# Deterministic ID generation (per tradecraft §10)
# ---------------------------------------------------------------------------

def slug(text: str, length: int = 12) -> str:
    """Stable sha1-slug of text. Same input → same output → idempotent
    seed corpus generation across sessions and operators."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def venue_record_id(canonical_name: str, scenario_prefix: str = "mavru") -> str:
    """Deterministic venue_record_id derived from canonical_name.

    `scenario_prefix` scopes IDs to a specific discovery scenario
    (e.g., "mavru" for Mavrinsky-RU). Different prefixes prevent
    cross-scenario collisions if two corpora reference the same venue.
    """
    return f"vrec_{scenario_prefix}_{slug(canonical_name)}"


def source_record_id(venue_id: str, source_key: str,
                     scenario_prefix: str = "mavru") -> str:
    return f"vsrc_{scenario_prefix}_{slug(venue_id + ':' + source_key)}"


def claim_record_id(source_id: str, claim_path: str, sequence: int = 0,
                    scenario_prefix: str = "mavru") -> str:
    return f"vclm_{scenario_prefix}_{slug(source_id + ':' + claim_path + ':' + str(sequence))}"


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------

def candidate_eb_urls(journal_base_url: str) -> list[str]:
    """Return ordered list of URLs to try for an editorial board page,
    given a journal's base URL. Tries OJS patterns first (more common),
    then static-HTML fallbacks.

    Caller should fetch them in order and take first 2xx response.
    """
    base = journal_base_url.rstrip("/")
    return [base + path for path in OJS_EDITORIAL_BOARD_PATHS] + \
           [base + path for path in STATIC_HTML_EDITORIAL_BOARD_PATHS]


def is_known_blocked(url: str) -> bool:
    """Check whether a URL matches a known-broken pattern. If so, skip
    rather than retry."""
    return any(blocked in url for blocked in KNOWN_BLOCKED_PATTERNS)


def aggregator_for(use_case: str) -> list[str]:
    """Return aggregator hosts useful for a given use_case.

    use_case examples: 'editorial_board_signal', 'editor_publications',
    'issue_toc', 'monograph_publication_confirmation'.
    """
    return [
        host for host, meta in AGGREGATOR_HOSTS.items()
        if use_case in meta.get("use_for", "")
    ]


def transliteration_variants(cyrillic_name: str) -> list[str]:
    """Return likely Latin transliteration variants of a Cyrillic name.

    Useful when querying Google Scholar etc. — combining Cyrillic +
    Latin variants surfaces more matches than either alone.

    Trivial heuristic for the most common ambiguities; not a full
    transliteration library.
    """
    # The cheap-and-cheerful map. Production-grade would use a library.
    # We list only the variations that actually mattered in this corpus.
    out: list[str] = []
    if "Аванесов" in cyrillic_name:
        out += ["Avanesov", "Avansov"]
    if "Хестанов" in cyrillic_name:
        out += ["Khestanov", "Hestanov"]
    if "Куренной" in cyrillic_name:
        out += ["Kurennoy", "Kurennoi", "Kurennoj"]
    if "Шиповалова" in cyrillic_name:
        out += ["Shipovalova", "Shipovalov"]
    if "Филиппов" in cyrillic_name:
        out += ["Filippov", "Phillipov"]
    if "Соколов" in cyrillic_name:
        out += ["Sokolov"]
    if "Магун" in cyrillic_name:
        out += ["Magun"]
    if "Регев" in cyrillic_name:
        out += ["Regev", "Regev Y."]
    if "Тимофеева" in cyrillic_name:
        out += ["Timofeeva", "Timofeyeva"]
    if "Хестанов" in cyrillic_name:
        out += ["Khestanov"]
    if "Куракин" in cyrillic_name:
        out += ["Kurakin"]
    if "Павлов" in cyrillic_name:
        out += ["Pavlov"]
    if "Анашвили" in cyrillic_name:
        out += ["Anashvili"]
    if "Писарев" in cyrillic_name:
        out += ["Pisarev"]
    if "Кралечкин" in cyrillic_name:
        out += ["Kralechkin"]
    if "Шиповалова" in cyrillic_name:
        out += ["Shipovalova"]
    if "Сюткин" in cyrillic_name:
        out += ["Syutkin"]
    if "Марков" in cyrillic_name:
        out += ["Markov"]
    return out


def is_common_surname(latin_name: str) -> bool:
    """Common RU surnames where English-only Scholar searches return
    too many false matches. For these, require Cyrillic + topic + venue
    in the query."""
    return latin_name.split()[-1].lower() in {
        "markov", "smirnov", "petrov", "ivanov", "sokolov", "pavlov",
        "popov", "vasiliev", "andreev", "alekseev",
    }


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    "OJS_EDITORIAL_BOARD_PATHS",
    "STATIC_HTML_EDITORIAL_BOARD_PATHS",
    "ISSUE_CURRENT_PATHS",
    "AGGREGATOR_HOSTS",
    "KNOWN_BLOCKED_PATTERNS",
    "slug",
    "venue_record_id",
    "source_record_id",
    "claim_record_id",
    "candidate_eb_urls",
    "is_known_blocked",
    "aggregator_for",
    "transliteration_variants",
    "is_common_surname",
]
