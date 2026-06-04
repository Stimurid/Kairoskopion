"""Tests for vault / markdown artifact filesystem output."""

import json
from pathlib import Path

from kairoskopion.artifacts import (
    ensure_vault_root,
    write_article_card,
    write_fit_report,
    write_pipeline_artifact,
    write_pipeline_result_cards,
    write_risk_card,
    write_venue_card,
)


def _run_pipeline():
    from kairoskopion.pipelines.manuscript_venue_fit import ManuscriptVenueFitPipeline

    fixtures = Path(__file__).parent / "fixtures"
    ms_text = (fixtures / "manuscript_sample.md").read_text(encoding="utf-8")
    gl_text = (fixtures / "venue_guidelines_sample.md").read_text(encoding="utf-8")
    sc_data = json.loads(
        (fixtures / "submission_scenario_sample.json").read_text(encoding="utf-8")
    )
    pipeline = ManuscriptVenueFitPipeline()
    result = pipeline.execute(
        manuscript_text=ms_text,
        venue_guidelines_text=gl_text,
        scenario_data=sc_data,
    )
    return result, pipeline


class TestEnsureVaultRoot:
    def test_creates_dirs(self, tmp_path):
        root = ensure_vault_root(tmp_path / "s")
        assert root.exists()
        for sub in ("articles", "venues", "fits", "risks", "submissions", "traces"):
            assert (root / sub).is_dir(), f"Missing vault subdir: {sub}"

    def test_idempotent(self, tmp_path):
        ensure_vault_root(tmp_path / "s")
        ensure_vault_root(tmp_path / "s")
        assert (tmp_path / "s" / "vault").exists()


class TestWriteIndividualCards:
    def test_article_card(self, tmp_path):
        vault = ensure_vault_root(tmp_path / "s")
        data = {"article_model_id": "art_test", "title_current": "Test Article"}
        path = write_article_card(data, vault)
        assert path.exists()
        assert path.parent.name == "articles"
        content = path.read_text(encoding="utf-8")
        assert "art_test" in content
        assert "Test Article" in content

    def test_venue_card(self, tmp_path):
        vault = ensure_vault_root(tmp_path / "s")
        data = {"venue_model_id": "ven_test", "canonical_name": "Test Journal"}
        path = write_venue_card(data, vault)
        assert path.exists()
        assert "Test Journal" in path.read_text(encoding="utf-8")

    def test_fit_report(self, tmp_path):
        vault = ensure_vault_root(tmp_path / "s")
        data = {"fit_assessment_id": "fit_test", "overall_label": "possible"}
        path = write_fit_report(data, vault)
        assert path.exists()
        assert path.parent.name == "fits"

    def test_risk_card(self, tmp_path):
        vault = ensure_vault_root(tmp_path / "s")
        data = {"risk_report_id": "risk_test", "overall_risk_label": "medium"}
        path = write_risk_card(data, vault)
        assert path.exists()
        assert path.parent.name == "risks"

    def test_pipeline_artifact(self, tmp_path):
        vault = ensure_vault_root(tmp_path / "s")
        path = write_pipeline_artifact("# Report\nContent", "run_123", vault)
        assert path.exists()
        assert path.parent.name == "traces"
        assert "run_123" in path.name


class TestWritePipelineResultCards:
    def test_creates_all_cards(self, tmp_path):
        result, pipeline = _run_pipeline()
        root = tmp_path / "store"
        written = write_pipeline_result_cards(result, pipeline, storage_root=root)

        assert "article_card" in written
        assert "venue_card" in written
        assert "fit_card" in written
        assert "risk_card" in written
        assert "pipeline_artifact" in written

        for name, path in written.items():
            assert path.exists(), f"{name} not created"

    def test_article_card_contains_model(self, tmp_path):
        result, pipeline = _run_pipeline()
        written = write_pipeline_result_cards(result, pipeline, storage_root=tmp_path / "s")
        content = written["article_card"].read_text(encoding="utf-8")
        assert result.article.article_model_id in content

    def test_venue_card_contains_model(self, tmp_path):
        result, pipeline = _run_pipeline()
        written = write_pipeline_result_cards(result, pipeline, storage_root=tmp_path / "s")
        content = written["venue_card"].read_text(encoding="utf-8")
        assert "Social Studies of Science" in content

    def test_fit_card_contains_assessment(self, tmp_path):
        result, pipeline = _run_pipeline()
        written = write_pipeline_result_cards(result, pipeline, storage_root=tmp_path / "s")
        content = written["fit_card"].read_text(encoding="utf-8")
        assert result.fit.overall_label in content

    def test_artifact_contains_full_report(self, tmp_path):
        result, pipeline = _run_pipeline()
        written = write_pipeline_result_cards(result, pipeline, storage_root=tmp_path / "s")
        content = written["pipeline_artifact"].read_text(encoding="utf-8")
        assert "ArticleModel" in content or "Artificial Subjectivity" in content
        assert "VenueModel" in content or "Social Studies" in content
        assert "Fit Assessment" in content
        assert "Mismatch" in content
        assert "Risk" in content
        assert "unknown" in content.lower() or "Unknown" in content

    def test_vault_dirs_created(self, tmp_path):
        result, pipeline = _run_pipeline()
        write_pipeline_result_cards(result, pipeline, storage_root=tmp_path / "s")
        vault = tmp_path / "s" / "vault"
        assert vault.exists()
        for sub in ("articles", "venues", "fits", "risks", "traces"):
            assert (vault / sub).is_dir()
