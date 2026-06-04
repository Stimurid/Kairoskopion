"""Tests that fixtures load and pass spec §158 acceptance criteria."""

from .fixtures import (
    sample_article_model,
    sample_fit_assessment_preliminary,
    sample_manuscript_model,
    sample_publication_regime,
    sample_submission_scenario,
    sample_venue_model,
)
from kairoskopion import registry
from kairoskopion.cards import generate_card
from kairoskopion.enums import FitLabel, LifecycleStatus
from kairoskopion.schema import ArticleModel, VenueModel


class TestFixturesLoad:
    """Spec §158: fixtures load."""

    def test_all_fixtures_instantiate(self):
        am = sample_article_model()
        assert am.title_current is not None
        vm = sample_venue_model()
        assert vm.canonical_name is not None
        ms = sample_manuscript_model()
        assert ms.word_count == 8500
        ss = sample_submission_scenario()
        assert ss.goal is not None
        fa = sample_fit_assessment_preliminary()
        assert fa.overall_label == FitLabel.POSSIBLE_BUT_COSTLY.value
        pr = sample_publication_regime()
        assert pr.review_model == "single_blind"


class TestFixtureWriteRead:
    """Spec §158: sample ArticleModel and VenueModel can be written/read."""

    def test_article_model_write_read(self, tmp_path):
        am = sample_article_model()
        registry.append("article_models", am.to_dict(), base_dir=tmp_path)
        records = registry.read_all("article_models", base_dir=tmp_path)
        assert len(records) == 1
        am2 = ArticleModel.from_dict(records[0])
        assert am2.title_current == am.title_current
        assert am2.protected_core == am.protected_core
        assert am2.unknowns == am.unknowns

    def test_venue_model_write_read(self, tmp_path):
        vm = sample_venue_model()
        registry.append("venue_models", vm.to_dict(), base_dir=tmp_path)
        records = registry.read_all("venue_models", base_dir=tmp_path)
        assert len(records) == 1
        vm2 = VenueModel.from_dict(records[0])
        assert vm2.canonical_name == vm.canonical_name
        assert vm2.unknowns == vm.unknowns


class TestFixtureFitPreliminary:
    """Spec §158: sample FitAssessment can be created with preliminary status."""

    def test_preliminary_status(self):
        fa = sample_fit_assessment_preliminary()
        assert fa.lifecycle_status == LifecycleStatus.PRELIMINARY.value
        assert fa.overall_label != FitLabel.STRONG_CANDIDATE.value
        assert len(fa.unknowns) > 0


class TestFixtureCardGeneration:
    """Spec §158: sample card can be generated."""

    def test_article_card(self):
        am = sample_article_model()
        md = generate_card("ArticleModel", am.to_dict())
        assert md is not None
        assert "Impossibility" in md
        assert "category error" in md

    def test_venue_card(self):
        vm = sample_venue_model()
        md = generate_card("VenueModel", vm.to_dict())
        assert md is not None
        assert "Social Studies of Science" in md

    def test_fit_card(self):
        fa = sample_fit_assessment_preliminary()
        md = generate_card("FitAssessment", fa.to_dict())
        assert md is not None
        assert "possible_but_costly" in md
