"""Tests for evidence audit service."""

from kairoskopion.enums import FitLabel, QualityGateStatus
from kairoskopion.schema import (
    ArticleModel,
    ComplianceChecklist,
    FitAssessment,
    MismatchMap,
    RiskReport,
    VenueModel,
)
from kairoskopion.services.evidence_audit import audit_pipeline_evidence


class TestEvidenceAudit:
    def test_warns_on_missing_article_sources(self):
        result = audit_pipeline_evidence(
            article=ArticleModel(source_refs=[]),
            venue=VenueModel(source_refs=["src_1"]),
            fit=FitAssessment(axes=[{"axis": "topic", "value": "strong"}]),
            mismatch_map=MismatchMap(),
            risk=RiskReport(risk_items=[{"risk_type": "test"}]),
            compliance=ComplianceChecklist(checklist_items=[{"category": "test"}]),
        )
        assert any("ArticleModel" in s for s in result.missing_sources)

    def test_warns_on_missing_venue_sources(self):
        result = audit_pipeline_evidence(
            article=ArticleModel(source_refs=["src_1"]),
            venue=VenueModel(source_refs=[]),
            fit=FitAssessment(axes=[]),
            mismatch_map=MismatchMap(),
            risk=RiskReport(risk_items=[{"risk_type": "test"}]),
            compliance=ComplianceChecklist(checklist_items=[{"category": "test"}]),
        )
        assert any("VenueModel" in s for s in result.missing_sources)

    def test_warns_on_empty_risk_report(self):
        result = audit_pipeline_evidence(
            article=ArticleModel(source_refs=["s1"]),
            venue=VenueModel(source_refs=["s2"]),
            fit=FitAssessment(axes=[]),
            mismatch_map=MismatchMap(),
            risk=RiskReport(risk_items=[]),
            compliance=ComplianceChecklist(checklist_items=[{"c": "t"}]),
        )
        assert any("RiskReport" in w for w in result.warnings)

    def test_passes_with_full_data(self):
        result = audit_pipeline_evidence(
            article=ArticleModel(source_refs=["s1"]),
            venue=VenueModel(source_refs=["s2"]),
            fit=FitAssessment(
                overall_label=FitLabel.STRONG_CANDIDATE.value,
                axes=[{"axis": "topic", "value": "strong", "evidence_refs": ["e1"]}],
            ),
            mismatch_map=MismatchMap(),
            risk=RiskReport(risk_items=[{"risk_type": "test"}]),
            compliance=ComplianceChecklist(checklist_items=[{"category": "test"}]),
        )
        assert result.status in (
            QualityGateStatus.PASSED.value,
            QualityGateStatus.PASSED_WITH_WARNINGS.value,
        )

    def test_no_external_calls(self):
        """Verify evidence audit is purely local — no network, no imports of requests/urllib."""
        import kairoskopion.services.evidence_audit as mod
        source = open(mod.__file__, encoding="utf-8").read()
        assert "import requests" not in source
        assert "urllib" not in source
        assert "httpx" not in source
