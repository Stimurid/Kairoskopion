"""Tests for Sprint 7: Litops Compatibility Bridge."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from kairoskopion.integrations.litops_bridge import (
    article_to_litops_source,
    bibliography_to_litops_artifact,
    build_litops_export_pack,
    fit_to_litops_artifact,
    pack_to_litops_artifact,
    risk_to_litops_artifact,
    trajectory_to_litops_artifact,
    venue_to_litops_source,
    write_litops_export,
)
from kairoskopion.schema import (
    ArticleModel,
    BibliographyProfile,
    ComplianceChecklist,
    FitAssessment,
    PublicationTrajectoryReport,
    RiskReport,
    SubmissionPack,
    VenueModel,
)
from kairoskopion.ids import (
    article_model_id,
    fit_assessment_id,
    risk_report_id,
    venue_model_id,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _article(**kw) -> ArticleModel:
    defaults = dict(
        article_model_id=article_model_id(),
        source_refs=["local:test"],
        title_current="Test Paper",
        language="en",
        input_mode="full_manuscript",
        article_stage="full_manuscript",
        genre_current="research_article",
        method_status="conceptual_method",
        novelty_mode="critique",
        citation_ecology_current="5 refs",
        unknowns=[],
        confidence="medium",
        lifecycle_status="preliminary",
        evidence_refs=[],
    )
    defaults.update(kw)
    return ArticleModel(**defaults)


def _venue(**kw) -> VenueModel:
    defaults = dict(
        venue_model_id=venue_model_id(),
        canonical_name="Test Journal",
        venue_type="journal",
        official_urls=["https://example.com"],
        scope_summary="Science",
        author_guidelines_refs=[],
        article_types_supported=["research_article"],
        language_policy="English",
        publication_regime_id="regime_1",
        publisher_or_owner="Test Publisher",
        source_refs=["local:test"],
        unknowns=[],
        confidence="medium",
        staleness_status="fresh",
        lifecycle_status="draft",
    )
    defaults.update(kw)
    return VenueModel(**defaults)


def _fit(**kw) -> FitAssessment:
    defaults = dict(
        fit_assessment_id=fit_assessment_id(),
        article_model_id="art_test",
        venue_model_id="ven_test",
        overall_label="possible",
        axes=[
            {"axis": "topic", "value": "strong", "notes": "good"},
        ],
        unknowns=[],
    )
    defaults.update(kw)
    return FitAssessment(**defaults)


def _risk(**kw) -> RiskReport:
    defaults = dict(
        risk_report_id=risk_report_id(),
        article_model_id="art_test",
        venue_model_id="ven_test",
        overall_risk_label="low",
        risk_items=[],
        unknowns=[],
    )
    defaults.update(kw)
    return RiskReport(**defaults)


# ---------------------------------------------------------------------------
# Article → Litops Source
# ---------------------------------------------------------------------------


class TestArticleToSource:
    def test_source_id_format(self):
        art = _article()
        rec = article_to_litops_source(art)
        assert rec["source_id"].startswith("src-")

    def test_title_preserved(self):
        art = _article(title_current="My Paper")
        rec = article_to_litops_source(art)
        assert rec["title"] == "My Paper"

    def test_kairoskopion_id_included(self):
        art = _article()
        rec = article_to_litops_source(art)
        assert rec["kairoskopion_id"] == art.article_model_id

    def test_bridge_version_tag(self):
        art = _article()
        rec = article_to_litops_source(art)
        assert rec["bridge_version"] == "kairoskopion-litops-v1"

    def test_body_type_is_markdown(self):
        art = _article()
        rec = article_to_litops_source(art)
        assert rec["body_type"] == "markdown"

    def test_genre_mapped(self):
        art = _article(genre_current="review_article")
        rec = article_to_litops_source(art)
        assert rec["content_genre"] == "review_article"


# ---------------------------------------------------------------------------
# Venue → Litops Source
# ---------------------------------------------------------------------------


class TestVenueToSource:
    def test_source_id_format(self):
        ven = _venue()
        rec = venue_to_litops_source(ven)
        assert rec["source_id"].startswith("src-")

    def test_title_preserved(self):
        ven = _venue(canonical_name="Nature")
        rec = venue_to_litops_source(ven)
        assert rec["title"] == "Nature"

    def test_body_type_is_json(self):
        ven = _venue()
        rec = venue_to_litops_source(ven)
        assert rec["body_type"] == "json"

    def test_facets_include_venue_type(self):
        ven = _venue(venue_type="conference")
        rec = venue_to_litops_source(ven)
        assert rec["facets"]["venue_type"] == "conference"


# ---------------------------------------------------------------------------
# Fit → Litops Artifact
# ---------------------------------------------------------------------------


class TestFitToArtifact:
    def test_artifact_id_format(self):
        fit = _fit()
        rec = fit_to_litops_artifact(fit)
        assert rec["artifact_id"].startswith("art-")

    def test_artifact_type(self):
        fit = _fit()
        rec = fit_to_litops_artifact(fit)
        assert rec["artifact_type"] == "fit_assessment"

    def test_overall_label_in_facets(self):
        fit = _fit(overall_label="strong_candidate")
        rec = fit_to_litops_artifact(fit)
        assert rec["facets"]["overall_label"] == "strong_candidate"

    def test_source_entity_ids_present(self):
        fit = _fit(article_model_id="art_123", venue_model_id="ven_456")
        rec = fit_to_litops_artifact(fit)
        assert len(rec["source_entity_ids"]) == 2


# ---------------------------------------------------------------------------
# Risk → Litops Artifact
# ---------------------------------------------------------------------------


class TestRiskToArtifact:
    def test_artifact_type(self):
        risk = _risk()
        rec = risk_to_litops_artifact(risk)
        assert rec["artifact_type"] == "risk_report"

    def test_risk_label_in_facets(self):
        risk = _risk(overall_risk_label="high")
        rec = risk_to_litops_artifact(risk)
        assert rec["facets"]["overall_risk_label"] == "high"


# ---------------------------------------------------------------------------
# Export pack
# ---------------------------------------------------------------------------


class TestExportPack:
    def test_empty_pack(self):
        pack = build_litops_export_pack()
        assert pack["sources"] == []
        assert pack["artifacts"] == []

    def test_article_only(self):
        art = _article()
        pack = build_litops_export_pack(article=art)
        assert len(pack["sources"]) == 1
        assert len(pack["artifacts"]) == 0

    def test_full_pack(self):
        art = _article()
        ven = _venue()
        fit = _fit()
        risk = _risk()
        pack = build_litops_export_pack(
            article=art, venue=ven, fit=fit, risk=risk,
        )
        assert len(pack["sources"]) == 2
        assert len(pack["artifacts"]) == 2

    def test_all_records_are_json_serializable(self):
        art = _article()
        ven = _venue()
        fit = _fit()
        risk = _risk()
        pack = build_litops_export_pack(
            article=art, venue=ven, fit=fit, risk=risk,
        )
        for records in pack.values():
            for rec in records:
                # Must not raise
                json.dumps(rec, default=str)


# ---------------------------------------------------------------------------
# JSONL file writing
# ---------------------------------------------------------------------------


class TestWriteExport:
    def test_write_creates_files(self):
        art = _article()
        fit = _fit()
        pack = build_litops_export_pack(article=art, fit=fit)
        with tempfile.TemporaryDirectory() as tmpdir:
            written = write_litops_export(pack, Path(tmpdir))
            assert "sources" in written
            assert "artifacts" in written
            assert written["sources"].exists()
            assert written["artifacts"].exists()

    def test_written_files_are_valid_jsonl(self):
        art = _article()
        ven = _venue()
        fit = _fit()
        pack = build_litops_export_pack(article=art, venue=ven, fit=fit)
        with tempfile.TemporaryDirectory() as tmpdir:
            written = write_litops_export(pack, Path(tmpdir))
            for path in written.values():
                with open(path, encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines:
                        parsed = json.loads(line)
                        assert isinstance(parsed, dict)

    def test_source_records_count(self):
        art = _article()
        ven = _venue()
        pack = build_litops_export_pack(article=art, venue=ven)
        with tempfile.TemporaryDirectory() as tmpdir:
            written = write_litops_export(pack, Path(tmpdir))
            with open(written["sources"], encoding="utf-8") as f:
                lines = [l for l in f if l.strip()]
            assert len(lines) == 2

    def test_empty_registry_not_written(self):
        """If no artifacts, artifacts.jsonl should not be created."""
        art = _article()
        pack = build_litops_export_pack(article=art)
        with tempfile.TemporaryDirectory() as tmpdir:
            written = write_litops_export(pack, Path(tmpdir))
            assert "artifacts" not in written

    def test_append_mode(self):
        """Writing twice should append, not overwrite."""
        art1 = _article(title_current="Paper 1")
        art2 = _article(title_current="Paper 2")
        pack1 = build_litops_export_pack(article=art1)
        pack2 = build_litops_export_pack(article=art2)
        with tempfile.TemporaryDirectory() as tmpdir:
            write_litops_export(pack1, Path(tmpdir))
            write_litops_export(pack2, Path(tmpdir))
            with open(Path(tmpdir) / "sources.jsonl", encoding="utf-8") as f:
                lines = [l for l in f if l.strip()]
            assert len(lines) == 2

    def test_all_records_have_bridge_version(self):
        art = _article()
        fit = _fit()
        pack = build_litops_export_pack(article=art, fit=fit)
        for registry_records in pack.values():
            for rec in registry_records:
                assert rec.get("bridge_version") == "kairoskopion-litops-v1"

    def test_no_litops_import_required(self):
        """Bridge must not import litops as a dependency."""
        import kairoskopion.integrations.litops_bridge as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        # Should not import from litops package
        assert "import litops" not in source
        assert "from litops" not in source
