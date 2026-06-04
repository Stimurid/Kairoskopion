"""Tests for article modeling service."""

from pathlib import Path

from kairoskopion.enums import ArticleStage, Genre, LifecycleStatus, MethodStatus
from kairoskopion.services.article_modeling import build_article_model, build_manuscript_model

FIXTURES = Path(__file__).parent / "fixtures"


def _load_manuscript() -> str:
    return (FIXTURES / "manuscript_sample.md").read_text(encoding="utf-8")


class TestBuildManuscriptModel:
    def test_extracts_title(self):
        ms = build_manuscript_model(_load_manuscript())
        assert ms.title is not None
        assert "Artificial Subjectivity" in ms.title

    def test_extracts_abstract(self):
        ms = build_manuscript_model(_load_manuscript())
        assert ms.abstract is not None
        assert "category error" in ms.abstract

    def test_extracts_sections(self):
        ms = build_manuscript_model(_load_manuscript())
        assert len(ms.sections) >= 4
        assert any("Introduction" in s for s in ms.sections)

    def test_extracts_references(self):
        ms = build_manuscript_model(_load_manuscript())
        assert len(ms.bibliography_refs) >= 5
        assert any("Chalmers" in r for r in ms.bibliography_refs)

    def test_word_count(self):
        ms = build_manuscript_model(_load_manuscript())
        assert ms.word_count is not None
        assert ms.word_count > 500

    def test_source_ref_stored(self):
        ms = build_manuscript_model(_load_manuscript(), source_ref="src_test")
        assert "src_test" in ms.source_file_refs


class TestBuildArticleModel:
    def test_creates_from_manuscript(self):
        text = _load_manuscript()
        ms = build_manuscript_model(text)
        am = build_article_model(ms, text)
        assert am.article_model_id.startswith("art_")
        assert am.title_current is not None

    def test_detects_genre(self):
        text = _load_manuscript()
        ms = build_manuscript_model(text)
        am = build_article_model(ms, text)
        assert am.genre_current == Genre.THEORETICAL_ESSAY.value

    def test_detects_method(self):
        text = _load_manuscript()
        ms = build_manuscript_model(text)
        am = build_article_model(ms, text)
        assert am.method_status == MethodStatus.CONCEPTUAL_METHOD.value

    def test_full_manuscript_stage(self):
        text = _load_manuscript()
        ms = build_manuscript_model(text)
        am = build_article_model(ms, text)
        assert am.article_stage == ArticleStage.FULL_MANUSCRIPT.value

    def test_preliminary_lifecycle(self):
        text = _load_manuscript()
        ms = build_manuscript_model(text)
        am = build_article_model(ms, text)
        assert am.lifecycle_status == LifecycleStatus.PRELIMINARY.value

    def test_protected_core_unknown(self):
        """Protected core cannot be auto-extracted — must remain unknown."""
        text = _load_manuscript()
        ms = build_manuscript_model(text)
        am = build_article_model(ms, text)
        assert any("protected core" in u.lower() for u in am.unknowns)

    def test_abstract_only_stays_preliminary(self):
        """Abstract-only input should not produce full_manuscript stage."""
        short = "# Test\n\n## Abstract\n\nA short abstract only."
        ms = build_manuscript_model(short)
        am = build_article_model(ms, short)
        assert am.article_stage == ArticleStage.ABSTRACT.value
        assert am.lifecycle_status == LifecycleStatus.PRELIMINARY.value
