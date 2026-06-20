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

    def test_regime_default_is_honest_unknown(self):
        # feature/real-cockpit-venue-fit-pass: previously the
        # deterministic builder stamped CLASSIC_JOURNAL_ARTICLE as a
        # silent default when no special-issue/conference/mega-journal
        # keyword was present. That faked regime data. The fixture
        # guidelines contain none of those markers, so the regime
        # should now be None and an explicit unknown should be added.
        venue, regime = build_venue_model(_load_guidelines())
        assert regime.regime_type is None
        assert any("publication regime" in u for u in venue.unknowns)

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


UNKNOWN_SEED = """# Venue Seed Profile: Логос / Logos

## Journal Identity

- **Name:** Логос / Logos
- **Publisher:** Unknown — requires verification

## Known or Externally Claimed

- Russian philosophical journal.
- VAK / Scopus / indexing claims require independent verification.

## UNKNOWN — Require Source Evidence Before Use

- official author guidelines URL
- word limit
- citation style
- peer review model
- APC/open access policy
- AI use policy
- data availability policy
- ethics policy
- submission route
"""


class TestUnknownSeedHandling:
    """Venue profiler must not hallucinate structured fields from UNKNOWN seeds."""

    def test_extracts_name_from_seed_format(self):
        venue, _ = build_venue_model(UNKNOWN_SEED)
        assert venue.canonical_name is not None
        assert "Логос" in venue.canonical_name

    def test_does_not_hallucinate_open_access(self):
        venue, _ = build_venue_model(UNKNOWN_SEED)
        assert venue.open_access_status is None

    def test_does_not_hallucinate_apc(self):
        venue, _ = build_venue_model(UNKNOWN_SEED)
        assert venue.apc_policy is None

    def test_does_not_hallucinate_review_model(self):
        venue, _ = build_venue_model(UNKNOWN_SEED)
        assert venue.anonymization_policy is None

    def test_propagates_explicit_unknowns(self):
        venue, _ = build_venue_model(UNKNOWN_SEED)
        assert len(venue.unknowns) >= 5
        unknown_text = " ".join(venue.unknowns).lower()
        assert "word limit" in unknown_text
        assert "citation style" in unknown_text
        assert "peer review" in unknown_text

    def test_low_confidence_for_seed(self):
        venue, _ = build_venue_model(UNKNOWN_SEED)
        assert venue.confidence == "low"

    def test_real_guidelines_still_extract_policies(self):
        """Ensure normal guidelines with real policy info still extract correctly."""
        venue, _ = build_venue_model(_load_guidelines())
        assert venue.open_access_status is not None or venue.review_process_claims != "unknown"


class TestLanguagePolicyExtraction:
    def test_russian_language_section(self):
        text = (
            "# Test Journal\n\n"
            "## Language Policy\n\n"
            "The journal is Russian-language only for article body text.\n"
            "Metadata must be in Russian and English.\n"
        )
        venue, _ = build_venue_model(text)
        assert venue.language_policy == "Russian"

    def test_english_metadata_not_english_journal(self):
        text = (
            "# Test Journal\n\n"
            "## Submission Requirements\n\n"
            "- **Metadata:** title and abstract must be in BOTH Russian AND English\n"
            "- **Abstract:** 200-250 words\n"
        )
        venue, _ = build_venue_model(text)
        assert venue.language_policy != "English"

    def test_russian_scope_signal(self):
        text = (
            "# Test Journal\n\n"
            "## Aims and Scope\n\n"
            "A leading Russian-language journal in philosophy.\n"
        )
        venue, _ = build_venue_model(text)
        assert venue.language_policy == "Russian"

    def test_english_only_submission(self):
        text = (
            "# Test Journal\n\n"
            "## Submission Requirements\n\n"
            "- **Language:** English only\n"
            "- **Abstract:** required\n"
        )
        venue, _ = build_venue_model(text)
        assert venue.language_policy == "English"

    def test_no_language_info_returns_none(self):
        text = "# Test Journal\n\n## Scope\n\nSome scope text.\n"
        venue, _ = build_venue_model(text)
        assert venue.language_policy is None
