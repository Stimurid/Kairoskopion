"""Tests for citation ecology service."""

from pathlib import Path

from kairoskopion.services.bibliography_parsing import build_bibliography_profile
from kairoskopion.services.citation_ecology import build_citation_ecology_report
from kairoskopion.schema import ArticleModel, VenueModel

FIXTURES = Path(__file__).parent / "fixtures"


def _make_article(**kwargs):
    defaults = dict(
        article_model_id="art_test",
        title_current="Test Article",
        disciplinary_register_current="philosophy",
    )
    defaults.update(kwargs)
    return ArticleModel(**defaults)


def _make_venue(**kwargs):
    defaults = dict(
        venue_model_id="ven_test",
        canonical_name="Test Journal",
        scope_summary="Science and technology studies, social construction",
    )
    defaults.update(kwargs)
    return VenueModel(**defaults)


class TestCitationEcologyReport:
    def test_basic_report(self):
        text = FIXTURES.joinpath("manuscript_sample.md").read_text(encoding="utf-8")
        guidelines = FIXTURES.joinpath("venue_guidelines_sample.md").read_text(encoding="utf-8")
        bib = build_bibliography_profile(text)
        article = _make_article()
        venue = _make_venue()
        report = build_citation_ecology_report(bib, article, venue, guidelines)
        assert report.citation_ecology_report_id.startswith("citeco_")
        assert report.article_model_id == "art_test"
        assert report.venue_model_id == "ven_test"
        assert report.bibliography_profile_id == bib.bibliography_profile_id
        assert report.summary is not None

    def test_disclaimer_present(self):
        text = FIXTURES.joinpath("manuscript_sample.md").read_text(encoding="utf-8")
        bib = build_bibliography_profile(text)
        report = build_citation_ecology_report(bib, _make_article(), _make_venue(), "")
        assert "not externally verified" in report.disclaimer.lower()

    def test_no_bibliography_handled(self):
        bib = build_bibliography_profile("# Paper\n\nNo refs here.")
        report = build_citation_ecology_report(bib, _make_article(), _make_venue(), "")
        assert report.summary is not None
        assert any("No bibliography" in u for u in report.unknowns)

    def test_unknowns_include_api_limitation(self):
        text = FIXTURES.joinpath("manuscript_sample.md").read_text(encoding="utf-8")
        bib = build_bibliography_profile(text)
        report = build_citation_ecology_report(bib, _make_article(), _make_venue(), "")
        assert any("external API" in u for u in report.unknowns)

    def test_gaps_and_tasks_are_dicts(self):
        text = FIXTURES.joinpath("manuscript_sample.md").read_text(encoding="utf-8")
        bib = build_bibliography_profile(text)
        report = build_citation_ecology_report(bib, _make_article(), _make_venue(), "")
        for gap in report.gaps:
            assert isinstance(gap, dict)
            assert "gap_type" in gap
        for task in report.tasks:
            assert isinstance(task, dict)
            assert "task_type" in task

    def test_low_ref_count_gap(self):
        text = "## References\n\n- Foo (2020). Title. Press.\n- Bar (2021). Other."
        bib = build_bibliography_profile(text)
        report = build_citation_ecology_report(bib, _make_article(), _make_venue(), "")
        gap_types = [g["gap_type"] for g in report.gaps]
        assert "insufficient_references" in gap_types

    def test_does_not_mark_verified(self):
        text = FIXTURES.joinpath("manuscript_sample.md").read_text(encoding="utf-8")
        bib = build_bibliography_profile(text)
        for ref in bib.references:
            assert ref.get("verification_status") == "not_verified"

    def test_reference_limit_warning(self):
        refs = "\n".join(f"- Author{i} (2020). Title{i}. Journal." for i in range(50))
        text = f"# Paper\n\n## References\n\n{refs}"
        guidelines = "Maximum 30 references allowed."
        bib = build_bibliography_profile(text)
        report = build_citation_ecology_report(bib, _make_article(), _make_venue(), guidelines)
        assert any("exceeds" in w for w in report.warning_signals)


class TestPipelineIntegration:
    def test_pipeline_includes_citation_ecology(self):
        from kairoskopion.pipelines.manuscript_venue_fit import ManuscriptVenueFitPipeline
        import json

        ms_text = FIXTURES.joinpath("manuscript_sample.md").read_text(encoding="utf-8")
        gl_text = FIXTURES.joinpath("venue_guidelines_sample.md").read_text(encoding="utf-8")
        sc_data = json.loads(FIXTURES.joinpath("submission_scenario_sample.json").read_text(encoding="utf-8"))

        pipeline = ManuscriptVenueFitPipeline()
        result = pipeline.execute(
            manuscript_text=ms_text,
            venue_guidelines_text=gl_text,
            scenario_data=sc_data,
        )
        assert result.bibliography_profile is not None
        assert result.bibliography_profile.total_references == 10
        assert result.citation_ecology is not None
        assert result.citation_ecology.summary is not None

    def test_pipeline_artifact_includes_citation(self):
        from kairoskopion.pipelines.manuscript_venue_fit import ManuscriptVenueFitPipeline
        import json

        ms_text = FIXTURES.joinpath("manuscript_sample.md").read_text(encoding="utf-8")
        gl_text = FIXTURES.joinpath("venue_guidelines_sample.md").read_text(encoding="utf-8")
        sc_data = json.loads(FIXTURES.joinpath("submission_scenario_sample.json").read_text(encoding="utf-8"))

        pipeline = ManuscriptVenueFitPipeline()
        result = pipeline.execute(
            manuscript_text=ms_text,
            venue_guidelines_text=gl_text,
            scenario_data=sc_data,
        )
        assert "Citation Ecology" in result.artifact_markdown


class TestPersistenceIntegration:
    def test_run_fixture_persists_citation_registries(self, tmp_path):
        from kairoskopion.cli import main
        code = main(["--storage-root", str(tmp_path / "s"), "run-fixture"])
        assert code == 0
        reg_dir = tmp_path / "s" / "registries"
        assert (reg_dir / "bibliography_profiles.jsonl").exists()
        assert (reg_dir / "citation_ecology_reports.jsonl").exists()

    def test_run_fixture_creates_citation_vault_card(self, tmp_path):
        from kairoskopion.cli import main
        code = main(["--storage-root", str(tmp_path / "s"), "run-fixture"])
        assert code == 0
        cit_dir = tmp_path / "s" / "vault" / "citations"
        assert cit_dir.exists()
        md_files = list(cit_dir.glob("*.md"))
        assert len(md_files) >= 1

    def test_run_local_persists_citation_registries(self, tmp_path):
        from kairoskopion.cli import main
        code = main([
            "--storage-root", str(tmp_path / "s"),
            "run-local",
            "--manuscript", str(FIXTURES / "manuscript_sample.md"),
            "--venue-guidelines", str(FIXTURES / "venue_guidelines_sample.md"),
            "--scenario", str(FIXTURES / "submission_scenario_sample.json"),
        ])
        assert code == 0
        reg_dir = tmp_path / "s" / "registries"
        assert (reg_dir / "bibliography_profiles.jsonl").exists()
        assert (reg_dir / "citation_ecology_reports.jsonl").exists()


class TestNoNetwork:
    def test_no_network_imports(self):
        import kairoskopion.services.citation_ecology as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in ["import requests", "import urllib", "import httpx", "import aiohttp"]:
            assert forbidden not in source
