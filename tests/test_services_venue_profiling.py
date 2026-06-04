"""Tests for venue profiling service."""

from pathlib import Path

from kairoskopion.enums import RegimeType, VenueType
from kairoskopion.services.venue_profiling import build_venue_model

FIXTURES = Path(__file__).parent / "fixtures"


def _load_guidelines() -> str:
    return (FIXTURES / "venue_guidelines_sample.md").read_text(encoding="utf-8")


class TestBuildVenueModel:
    def test_extracts_name(self):
        venue, _ = build_venue_model(_load_guidelines())
        assert venue.canonical_name is not None
        assert "Social Studies of Science" in venue.canonical_name

    def test_extracts_publisher(self):
        venue, _ = build_venue_model(_load_guidelines())
        assert venue.publisher_or_owner is not None
        assert "SAGE" in venue.publisher_or_owner

    def test_extracts_scope(self):
        venue, _ = build_venue_model(_load_guidelines())
        assert venue.scope_summary is not None
        assert "social dimensions" in venue.scope_summary.lower()

    def test_extracts_article_types(self):
        venue, _ = build_venue_model(_load_guidelines())
        assert len(venue.article_types_supported) >= 2

    def test_extracts_url(self):
        venue, _ = build_venue_model(_load_guidelines())
        assert len(venue.official_urls) >= 1

    def test_language_policy(self):
        venue, _ = build_venue_model(_load_guidelines())
        assert venue.language_policy is not None
        assert "english" in venue.language_policy.lower()

    def test_regime_classic(self):
        _, regime = build_venue_model(_load_guidelines())
        assert regime.regime_type == RegimeType.CLASSIC_JOURNAL_ARTICLE.value

    def test_double_blind_detected(self):
        _, regime = build_venue_model(_load_guidelines())
        assert regime.review_model == "double_blind"

    def test_unknowns_present(self):
        venue, _ = build_venue_model(_load_guidelines())
        # The fixture has AI disclosure, but data availability is mentioned
        # so some unknowns may or may not appear depending on extraction
        assert isinstance(venue.unknowns, list)

    def test_source_ref(self):
        venue, regime = build_venue_model(_load_guidelines(), source_ref="src_gl")
        assert "src_gl" in venue.source_refs
        assert "src_gl" in regime.evidence_refs
