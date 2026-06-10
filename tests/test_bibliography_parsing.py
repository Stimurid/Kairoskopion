"""Tests for bibliography parsing service."""

from pathlib import Path

from kairoskopion.services.bibliography_parsing import (
    build_bibliography_profile,
    extract_references_section,
    parse_reference,
    split_references,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestExtractReferencesSection:
    def test_finds_references(self):
        text = FIXTURES.joinpath("manuscript_sample.md").read_text(encoding="utf-8")
        section = extract_references_section(text)
        assert section is not None
        assert "Chalmers" in section

    def test_returns_none_for_no_references(self):
        assert extract_references_section("# Title\n\nSome text.") is None

    def test_case_insensitive(self):
        text = "# REFERENCES\n\n- Foo (2020). Bar."
        assert extract_references_section(text) is not None

    def test_bibliography_header(self):
        text = "## Bibliography\n\n- Foo (2020). Bar."
        assert extract_references_section(text) is not None


class TestSplitReferences:
    def test_splits_dash_prefixed(self):
        section = "- Foo (2020). Title.\n- Bar (2021). Other."
        refs = split_references(section)
        assert len(refs) == 2

    def test_splits_numbered(self):
        section = "1. Foo (2020). Title.\n2. Bar (2021). Other."
        refs = split_references(section)
        assert len(refs) == 2

    def test_skips_short_lines(self):
        section = "- Foo (2020). Title.\n- ab\n- Bar (2021). Other."
        refs = split_references(section)
        assert len(refs) == 2

    def test_empty_section(self):
        assert split_references("") == []
        assert split_references("\n\n") == []


class TestParseReference:
    def test_extracts_year(self):
        ref = parse_reference("Chalmers, D. (1996). The Conscious Mind. Oxford University Press.")
        assert ref.year == 1996

    def test_extracts_doi(self):
        ref = parse_reference("Smith, J. (2020). Title. Journal, 10.1234/abc123")
        assert ref.doi == "10.1234/abc123"

    def test_no_year(self):
        ref = parse_reference("Anonymous. Some obscure text without dates.")
        assert ref.year is None

    def test_detects_book(self):
        ref = parse_reference("Chalmers, D. (1996). The Conscious Mind. Oxford University Press.")
        assert ref.source_kind == "book"

    def test_detects_journal_article(self):
        ref = parse_reference("Nagel, T. (1974). What Is It Like to Be a Bat? Philosophical Review, 83(4).")
        assert ref.source_kind == "journal_article"

    def test_unknown_kind(self):
        ref = parse_reference("Some Author (2020). Some Title.")
        assert ref.source_kind == "unknown"

    def test_not_verified(self):
        ref = parse_reference("Anything (2020). Title.")
        assert ref.verification_status == "not_verified"

    def test_extracts_author_fragment(self):
        ref = parse_reference("Chalmers, D. (1996). The Conscious Mind.")
        assert ref.author_fragment is not None
        assert "Chalmers" in ref.author_fragment

    def test_detects_conference(self):
        ref = parse_reference("Smith (2019). Title. Proceedings of ICML 2019.")
        assert ref.source_kind == "conference_paper"

    def test_detects_web(self):
        ref = parse_reference("Author (2021). Title. Retrieved from https://example.com")
        assert ref.source_kind == "web_source"


class TestBuildBibliographyProfile:
    def test_fixture_manuscript(self):
        text = FIXTURES.joinpath("manuscript_sample.md").read_text(encoding="utf-8")
        profile = build_bibliography_profile(text)
        assert profile.total_references == 10
        assert profile.year_min == 1913
        assert profile.year_max == 2023
        assert profile.year_median is not None
        assert profile.bibliography_profile_id.startswith("bib_")
        assert profile.doi_count == 0
        assert len(profile.source_kind_distribution) > 0

    def test_no_references_section(self):
        profile = build_bibliography_profile("# Paper\n\nJust text, no refs.")
        assert profile.total_references == 0
        assert len(profile.unknowns) > 0
        assert any("No references section" in u for u in profile.unknowns)

    def test_empty_references(self):
        text = "# Paper\n\n## References\n\n"
        profile = build_bibliography_profile(text)
        assert profile.total_references == 0

    def test_disclaimer_present(self):
        text = FIXTURES.joinpath("manuscript_sample.md").read_text(encoding="utf-8")
        profile = build_bibliography_profile(text)
        assert "not externally verified" in profile.disclaimer.lower()

    def test_ids_set(self):
        text = "## References\n\n- Foo (2020). Title. Press."
        profile = build_bibliography_profile(
            text, manuscript_id="ms_123", article_model_id="art_456",
        )
        assert profile.manuscript_id == "ms_123"
        assert profile.article_model_id == "art_456"

    def test_recency_profile(self):
        text = FIXTURES.joinpath("manuscript_sample.md").read_text(encoding="utf-8")
        profile = build_bibliography_profile(text)
        assert profile.recency_profile in ("recent", "moderately_recent", "dated", "historical")

    def test_handles_malformed_references(self):
        text = "## References\n\n- ??? broken stuff\n- @#$%^&\n- Foo (2020). Real ref."
        profile = build_bibliography_profile(text)
        assert profile.total_references >= 1


class TestTitleFragmentExtraction:
    """D8: title_fragment must be extracted from Chicago/APA/author-date references."""

    def test_apa_style(self):
        ref = parse_reference("Chalmers, D. (1996). The Conscious Mind. Oxford University Press.")
        assert ref.title_fragment is not None
        assert "Conscious Mind" in ref.title_fragment

    def test_chicago_author_date(self):
        ref = parse_reference("Clark, Burton. 1998. Creating Entrepreneurial Universities. Pergamon Press.")
        assert ref.title_fragment is not None
        assert "Entrepreneurial" in ref.title_fragment

    def test_chicago_with_subtitle(self):
        ref = parse_reference(
            "Vygotsky, Lev. 1978. Mind in Society: The Development of Higher Psychological Processes. "
            "Harvard University Press."
        )
        assert ref.title_fragment is not None
        assert "Mind in Society" in ref.title_fragment

    def test_apa_with_journal(self):
        ref = parse_reference(
            "Nagel, T. (1974). What Is It Like to Be a Bat? Philosophical Review, 83(4), 435-450."
        )
        assert ref.title_fragment is not None
        assert "Bat" in ref.title_fragment

    def test_numbered_reference(self):
        ref = parse_reference(
            "Brown, T. et al. 2020. Language Models are Few-Shot Learners. NeurIPS 2020."
        )
        assert ref.title_fragment is not None
        assert "Few-Shot" in ref.title_fragment

    def test_quoted_title(self):
        ref = parse_reference(
            'Floridi, L. 2023. "AI as Agency Without Intelligence." Philosophy & Technology, 36(1).'
        )
        assert ref.title_fragment is not None
        assert "Agency" in ref.title_fragment


class TestSourceKindClassification:
    """D9: source_kind should correctly classify obvious cases."""

    def test_doi_with_journal_markers(self):
        ref = parse_reference(
            "Smith, J. (2020). Title. Journal of X, 10(2). 10.1234/jx.2020.001"
        )
        assert ref.source_kind == "journal_article"

    def test_doi_alone_implies_journal(self):
        ref = parse_reference("Author (2020). Title. 10.1234/abc123")
        assert ref.source_kind == "journal_article"

    def test_publisher_implies_book(self):
        ref = parse_reference(
            "Clark, Burton. 1998. Creating Entrepreneurial Universities. Pergamon Press."
        )
        assert ref.source_kind == "book"

    def test_unesco_report(self):
        ref = parse_reference("UNESCO. 2021. Reimagining Our Futures Together. UNESCO Report.")
        assert ref.source_kind == "report"

    def test_world_bank_report(self):
        ref = parse_reference("World Bank. 2019. World Development Report 2019.")
        assert ref.source_kind == "report"

    def test_working_paper(self):
        ref = parse_reference("Author (2022). Title. NBER Working Paper No. 30000.")
        assert ref.source_kind == "report"

    def test_conference_paper(self):
        ref = parse_reference("Smith (2019). Title. Proceedings of ICML 2019.")
        assert ref.source_kind == "conference_paper"

    def test_chapter_in_edited_volume(self):
        ref = parse_reference(
            "Author (2020). Chapter Title. In: Editor (ed.). Book Title. Publisher."
        )
        assert ref.source_kind == "book_chapter"

    def test_existing_book_detection_preserved(self):
        ref = parse_reference("Chalmers, D. (1996). The Conscious Mind. Oxford University Press.")
        assert ref.source_kind == "book"


class TestNoNetwork:
    def test_no_network_imports(self):
        import kairoskopion.services.bibliography_parsing as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in ["import requests", "import urllib", "import httpx", "import aiohttp"]:
            assert forbidden not in source
