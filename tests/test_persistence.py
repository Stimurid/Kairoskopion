"""Tests for persistence layer."""

import json
from pathlib import Path

from kairoskopion.persistence import (
    ensure_registry_root,
    ensure_storage_root,
    list_registries,
    read_registry,
    registries_exist,
    save_pipeline_result,
    storage_exists,
    vault_exists,
)


def _run_pipeline():
    """Helper: run fixture pipeline and return (result, pipeline)."""
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


class TestStorageRoot:
    def test_ensure_creates_dir(self, tmp_path):
        root = tmp_path / "test_storage"
        result = ensure_storage_root(root)
        assert result.exists()
        assert result.is_dir()

    def test_ensure_idempotent(self, tmp_path):
        root = tmp_path / "test_storage"
        ensure_storage_root(root)
        ensure_storage_root(root)
        assert root.exists()

    def test_storage_exists(self, tmp_path):
        root = tmp_path / "s"
        assert not storage_exists(root)
        ensure_storage_root(root)
        assert storage_exists(root)


class TestRegistryRoot:
    def test_ensure_creates_registries_subdir(self, tmp_path):
        reg_root = ensure_registry_root(tmp_path / "s")
        assert reg_root.exists()
        assert reg_root.name == "registries"

    def test_registries_exist(self, tmp_path):
        root = tmp_path / "s"
        assert not registries_exist(root)
        ensure_registry_root(root)
        assert registries_exist(root)


class TestSavePipelineResult:
    def test_writes_all_expected_registries(self, tmp_path):
        result, pipeline = _run_pipeline()
        root = tmp_path / "store"
        written = save_pipeline_result(result, pipeline, storage_root=root)

        expected = {
            "article_models", "manuscripts", "venue_models",
            "publication_regimes", "submission_scenarios",
            "fit_assessments", "mismatch_maps", "rewrite_plans",
            "risk_reports", "compliance_checklists",
            "pipeline_runs", "operation_traces", "quality_gates",
        }
        assert expected.issubset(set(written.keys())), (
            f"Missing registries: {expected - set(written.keys())}"
        )

    def test_jsonl_files_contain_valid_json(self, tmp_path):
        result, pipeline = _run_pipeline()
        root = tmp_path / "store"
        written = save_pipeline_result(result, pipeline, storage_root=root)

        for name, path in written.items():
            assert path.exists(), f"{name} file does not exist"
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
                if line.strip():
                    try:
                        json.loads(line)
                    except json.JSONDecodeError:
                        raise AssertionError(f"Invalid JSON in {name} line {i+1}")

    def test_entity_ids_preserved(self, tmp_path):
        result, pipeline = _run_pipeline()
        root = tmp_path / "store"
        save_pipeline_result(result, pipeline, storage_root=root)

        articles = read_registry("article_models", storage_root=root)
        assert len(articles) == 1
        assert articles[0]["article_model_id"] == result.article.article_model_id

        venues = read_registry("venue_models", storage_root=root)
        assert len(venues) == 1
        assert venues[0]["venue_model_id"] == result.venue.venue_model_id

        fits = read_registry("fit_assessments", storage_root=root)
        assert len(fits) == 1
        assert fits[0]["fit_assessment_id"] == result.fit.fit_assessment_id

    def test_operation_trace_persisted(self, tmp_path):
        result, pipeline = _run_pipeline()
        root = tmp_path / "store"
        save_pipeline_result(result, pipeline, storage_root=root)

        traces = read_registry("operation_traces", storage_root=root)
        assert len(traces) == 1
        assert traces[0]["operation_id"] == pipeline.trace.operation_id
        assert traces[0]["ended_at"] is not None

    def test_quality_gates_persisted(self, tmp_path):
        result, pipeline = _run_pipeline()
        root = tmp_path / "store"
        save_pipeline_result(result, pipeline, storage_root=root)

        gates = read_registry("quality_gates", storage_root=root)
        assert len(gates) == 2  # fit_gate + evidence_gate

    def test_append_behavior(self, tmp_path):
        """Running pipeline twice should append, not overwrite."""
        root = tmp_path / "store"

        r1, p1 = _run_pipeline()
        save_pipeline_result(r1, p1, storage_root=root)

        r2, p2 = _run_pipeline()
        save_pipeline_result(r2, p2, storage_root=root)

        articles = read_registry("article_models", storage_root=root)
        assert len(articles) == 2
        assert articles[0]["article_model_id"] != articles[1]["article_model_id"]

    def test_list_registries(self, tmp_path):
        result, pipeline = _run_pipeline()
        root = tmp_path / "store"
        save_pipeline_result(result, pipeline, storage_root=root)

        regs = list_registries(root)
        assert "article_models" in regs
        assert "venue_models" in regs
        assert "pipeline_runs" in regs
