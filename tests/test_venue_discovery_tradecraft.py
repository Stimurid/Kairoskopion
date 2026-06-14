"""Tests for the venue discovery tradecraft helper module.

These tests verify that the codified primitives from the tradecraft
playbook are importable, return the right shapes, and protect the
known invariants (deterministic IDs, blocked-pattern detection).
"""

from __future__ import annotations

import pytest

from kairoskopion.services.venue_discovery_tradecraft import (
    AGGREGATOR_HOSTS,
    ISSUE_CURRENT_PATHS,
    KNOWN_BLOCKED_PATTERNS,
    OJS_EDITORIAL_BOARD_PATHS,
    STATIC_HTML_EDITORIAL_BOARD_PATHS,
    aggregator_for,
    candidate_eb_urls,
    claim_record_id,
    is_common_surname,
    is_known_blocked,
    slug,
    source_record_id,
    transliteration_variants,
    venue_record_id,
)


# --- Deterministic ID primitives ---

def test_slug_is_deterministic():
    assert slug("Stasis") == slug("Stasis")
    assert slug("Stasis") != slug("Logos")


def test_slug_default_length_is_12():
    assert len(slug("Stasis")) == 12


def test_slug_custom_length():
    assert len(slug("Stasis", length=8)) == 8


def test_venue_record_id_format():
    rid = venue_record_id("Stasis")
    assert rid.startswith("vrec_mavru_")
    assert len(rid.split("_")[2]) == 12


def test_venue_record_id_idempotent():
    assert venue_record_id("Stasis") == venue_record_id("Stasis")


def test_venue_record_id_scenario_prefix_isolates():
    assert venue_record_id("Stasis", "mavru") != venue_record_id("Stasis", "other")


def test_source_record_id_includes_venue_and_key():
    rid = source_record_id("vrec_mavru_abc", "homepage")
    assert rid.startswith("vsrc_mavru_")


def test_claim_record_id_sequence_disambiguates():
    sid = source_record_id("vrec_mavru_abc", "homepage")
    a = claim_record_id(sid, "aims_scope", sequence=1)
    b = claim_record_id(sid, "aims_scope", sequence=2)
    assert a != b


# --- URL pattern libraries ---

def test_ojs_eb_paths_have_locale_variants():
    """At least one OJS path must include the ?locale=en_US workaround,
    which was empirically necessary for Соц.власти."""
    assert any("?locale=en_US" in p for p in OJS_EDITORIAL_BOARD_PATHS)


def test_static_html_eb_paths_have_no_extension_variant():
    """At least one static-HTML path must lack a .html extension
    (Chelovek pattern)."""
    assert "/redkollegiya" in STATIC_HTML_EDITORIAL_BOARD_PATHS


def test_issue_current_includes_index_php_journal():
    """Stasis pattern: /index.php/journal/issue/current works publicly."""
    assert "/index.php/journal/issue/current" in ISSUE_CURRENT_PATHS


def test_candidate_eb_urls_orders_ojs_first():
    urls = candidate_eb_urls("https://example.com/")
    first_static = next(
        i for i, u in enumerate(urls)
        if any(p in u for p in STATIC_HTML_EDITORIAL_BOARD_PATHS)
    )
    last_ojs = max(
        i for i, u in enumerate(urls)
        if any(p in u for p in OJS_EDITORIAL_BOARD_PATHS)
    )
    assert last_ojs < first_static


def test_candidate_eb_urls_strips_trailing_slash():
    urls_a = candidate_eb_urls("https://example.com/")
    urls_b = candidate_eb_urls("https://example.com")
    assert urls_a == urls_b


# --- Aggregator allowlist ---

def test_aggregator_hosts_have_required_metadata():
    """Each aggregator entry must declare kind + use_for + reliability."""
    for host, meta in AGGREGATOR_HOSTS.items():
        assert "kind" in meta, f"{host} missing 'kind'"
        assert "use_for" in meta, f"{host} missing 'use_for'"
        assert "reliability" in meta, f"{host} missing 'reliability'"
        assert meta["reliability"] in {"high", "medium", "low"}


def test_aggregator_for_editor_publications_includes_scholar():
    hosts = aggregator_for("editor_publications")
    assert "scholar.google.com" in hosts
    assert "istina.msu.ru" in hosts


def test_aggregator_for_editorial_board_signal_includes_motto():
    hosts = aggregator_for("editorial_board_signal")
    assert "motto-distribution.com" in hosts


# --- Blocked pattern detection ---

def test_is_known_blocked_matches_praxema_redkollegiya():
    assert is_known_blocked("https://praxema.tspu.ru/redkollegiya.html")


def test_is_known_blocked_does_not_match_random_url():
    assert not is_known_blocked("https://example.com/random/path")


def test_known_blocked_patterns_are_non_empty():
    assert len(KNOWN_BLOCKED_PATTERNS) > 0


# --- Transliteration ---

def test_transliteration_variants_for_avanesov():
    out = transliteration_variants("Аванесов С.С.")
    assert "Avanesov" in out


def test_transliteration_variants_for_kurennoy():
    out = transliteration_variants("Куренной В.А.")
    assert "Kurennoy" in out
    # Kurennoj/Kurennoi are common alternate spellings
    assert any(v in out for v in ["Kurennoj", "Kurennoi"])


def test_transliteration_variants_empty_for_unknown():
    out = transliteration_variants("СовершенноНоваяФамилия")
    assert out == []


# --- Common surname detection ---

def test_is_common_surname_for_markov():
    assert is_common_surname("Aleksandr Markov")


def test_is_common_surname_for_smirnov():
    assert is_common_surname("Artem Smirnov")


def test_is_common_surname_negative():
    assert not is_common_surname("Artemy Magun")


def test_is_common_surname_handles_single_token():
    assert is_common_surname("Markov")
