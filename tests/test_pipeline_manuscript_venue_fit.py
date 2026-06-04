"""Tests for the manuscript × venue fit pipeline (spec §37)."""

import json
from pathlib import Path

from kairoskopion.enums import (
    FitAxisValue,
    FitLabel,
    LifecycleStatus,
    PipelineRunStatus,
)
from kairoskopion.pipelines.manuscript_venue_fit import (
    ManuscriptVenueFitPipeline,
    ManuscriptVenueFitResult,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _run_pipeline() -> tuple[ManuscriptVenueFitResult, "ManuscriptVenueFitPipeline"]:
    ms_text = (FIXTURES / "manuscript_sample.md").read_text(encoding="utf-8")
    gl_text = (FIXTURES / "venue_guidelines_sample.md").read_text(encoding="utf-8")
    sc_data = json.loads(
        (FIXTURES / "submission_scenario_sample.json").read_text(encoding="utf-8")
    )
    pipeline = ManuscriptVenueFitPipeline()
    result = pipeline.execute(
        manuscript_text=ms_text,
        venue_guidelines_text=gl_text,
        scenario_data=sc_data,
    )
    return result, pipeline


class TestPipelineCreatesAllEntities:
    def test_manuscript_created(self):
        r, _ = _run_pipeline()
        assert r.manuscript is not None
        assert r.manuscript.manuscript_id.startswith("ms_")

    def test_article_created(self):
        r, _ = _run_pipeline()
        assert r.article is not None
        assert r.article.article_model_id.startswith("art_")

    def test_venue_created(self):
        r, _ = _run_pipeline()
        assert r.venue is not None
        assert r.venue.venue_model_id.startswith("ven_")

    def test_regime_created(self):
        r, _ = _run_pipeline()
        assert r.regime is not None

    def test_scenario_created(self):
        r, _ = _run_pipeline()
        assert r.scenario is not None

    def test_fit_created(self):
        r, _ = _run_pipeline()
        assert r.fit is not None

    def test_mismatch_map_created(self):
        r, _ = _run_pipeline()
        assert r.mismatch_map is not None

    def test_rewrite_plan_created(self):
        r, _ = _run_pipeline()
        assert r.rewrite_plan is not None

    def test_risk_report_created(self):
        r, _ = _run_pipeline()
        assert r.risk_report is not None

    def test_compliance_created(self):
        r, _ = _run_pipeline()
        assert r.compliance is not None

    def test_fit_gate_created(self):
        r, _ = _run_pipeline()
        assert r.fit_gate is not None

    def test_evidence_gate_created(self):
        r, _ = _run_pipeline()
        assert r.evidence_gate is not None

    def test_artifact_created(self):
        r, _ = _run_pipeline()
        assert r.artifact_markdown is not None
        assert len(r.artifact_markdown) > 200


class TestFitAssessmentMultiAxis:
    """FitAssessment must have multiple axes, not a single score."""

    def test_multiple_axes(self):
        r, _ = _run_pipeline()
        assert len(r.fit.axes) >= 5

    def test_axes_are_qualitative(self):
        r, _ = _run_pipeline()
        valid = {v.value for v in FitAxisValue}
        for ax in r.fit.axes:
            assert ax["value"] in valid, f"Axis '{ax['axis']}' has non-qualitative value"

    def test_overall_label_is_valid(self):
        r, _ = _run_pipeline()
        assert r.fit.overall_label in {l.value for l in FitLabel}


class TestMismatchMapStructure:
    """MismatchMap items must have article_side and venue_side."""

    def test_has_mismatches(self):
        r, _ = _run_pipeline()
        assert len(r.mismatch_map.mismatches) > 0

    def test_mismatches_have_both_sides(self):
        r, _ = _run_pipeline()
        for mm in r.mismatch_map.mismatches:
            assert "article_side" in mm, f"Mismatch {mm.get('mismatch_id')} missing article_side"
            assert "venue_side" in mm, f"Mismatch {mm.get('mismatch_id')} missing venue_side"


class TestRewritePlanLinkage:
    """RewritePlan items must link to mismatches."""

    def test_changes_link_to_mismatches(self):
        r, _ = _run_pipeline()
        if r.rewrite_plan.changes:
            for ch in r.rewrite_plan.changes:
                assert "related_mismatch_id" in ch
                assert ch["related_mismatch_id"], "related_mismatch_id should not be empty"


class TestRiskReportCoverage:
    """RiskReport should cover formal, scope, citation, core risks."""

    def test_has_risk_items(self):
        r, _ = _run_pipeline()
        assert len(r.risk_report.risk_items) >= 3

    def test_covers_key_risk_types(self):
        r, _ = _run_pipeline()
        types = {ri.get("risk_type") for ri in r.risk_report.risk_items}
        # At least scope/method and citation/formal should appear
        assert len(types) >= 3, f"Only {len(types)} risk types: {types}"


class TestComplianceChecklist:
    """Checklist must have items with present/missing/unknown statuses."""

    def test_has_items(self):
        r, _ = _run_pipeline()
        assert len(r.compliance.checklist_items) >= 5

    def test_has_varied_statuses(self):
        r, _ = _run_pipeline()
        statuses = {item.get("status") for item in r.compliance.checklist_items}
        # Should have at least 2 different statuses
        assert len(statuses) >= 2, f"Only status(es): {statuses}"

    def test_missing_items_listed(self):
        r, _ = _run_pipeline()
        assert len(r.compliance.missing_items) > 0


class TestOperationTrace:
    """Pipeline must record operation trace."""

    def test_trace_has_entities(self):
        _, pipeline = _run_pipeline()
        assert len(pipeline.trace.entities_created) >= 8

    def test_trace_has_sources(self):
        _, pipeline = _run_pipeline()
        assert len(pipeline.trace.sources_accessed) >= 2

    def test_trace_has_timestamps(self):
        _, pipeline = _run_pipeline()
        assert pipeline.trace.started_at is not None
        assert pipeline.trace.ended_at is not None

    def test_pipeline_run_completed(self):
        _, pipeline = _run_pipeline()
        assert pipeline.run.status == PipelineRunStatus.COMPLETED.value
        assert pipeline.run.finished_at is not None


class TestArtifactContent:
    """Artifact should contain key sections."""

    def test_contains_article_model(self):
        r, _ = _run_pipeline()
        assert "ArticleModel" in r.artifact_markdown or "Artificial Subjectivity" in r.artifact_markdown

    def test_contains_venue_model(self):
        r, _ = _run_pipeline()
        assert "Social Studies of Science" in r.artifact_markdown

    def test_contains_fit_assessment(self):
        r, _ = _run_pipeline()
        assert "Fit Assessment" in r.artifact_markdown

    def test_contains_mismatch_map(self):
        r, _ = _run_pipeline()
        assert "Mismatch" in r.artifact_markdown

    def test_contains_risk_report(self):
        r, _ = _run_pipeline()
        assert "Risk" in r.artifact_markdown

    def test_contains_unknowns(self):
        r, _ = _run_pipeline()
        assert "Unknown" in r.artifact_markdown or "unknown" in r.artifact_markdown

    def test_contains_evidence_section(self):
        r, _ = _run_pipeline()
        assert "Evidence" in r.artifact_markdown


class TestArtifactWriteToFile:
    """Artifact can be written to tmp directory."""

    def test_write_to_tmp(self, tmp_path):
        r, _ = _run_pipeline()
        out = tmp_path / "fit_report.md"
        out.write_text(r.artifact_markdown, encoding="utf-8")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "Fit Assessment" in content


class TestNoExternalCalls:
    """Pipeline must not make any real network calls."""

    def test_no_network_imports_in_pipeline(self):
        import kairoskopion.pipelines.manuscript_venue_fit as mod
        source = open(mod.__file__, encoding="utf-8").read()
        for forbidden in ["import requests", "import urllib", "import httpx",
                          "import aiohttp", "urlopen", "fetch("]:
            assert forbidden not in source, f"Found '{forbidden}' in pipeline module"

    def test_no_network_imports_in_services(self):
        import kairoskopion.services as pkg
        import importlib
        import pkgutil
        for _, name, _ in pkgutil.iter_modules(pkg.__path__):
            mod = importlib.import_module(f"kairoskopion.services.{name}")
            source = open(mod.__file__, encoding="utf-8").read()
            for forbidden in ["import requests", "import urllib", "import httpx"]:
                assert forbidden not in source, f"Found '{forbidden}' in services.{name}"
