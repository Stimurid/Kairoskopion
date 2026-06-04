"""Tests for Kairoskopion quality gates."""

from kairoskopion.enums import QualityGateStatus
from kairoskopion.quality import (
    QualityGateResult,
    evaluate_fit_gate,
    evaluate_submission_gate,
)


class TestFitGate:
    def test_all_present(self):
        result = evaluate_fit_gate(
            has_article_source=True,
            has_venue_source=True,
            has_scenario=True,
            has_evidence_per_axis=True,
            has_context_pack=True,
        )
        assert result.status == QualityGateStatus.PASSED.value
        assert result.blocking_issues == []

    def test_missing_article(self):
        result = evaluate_fit_gate(
            has_article_source=False,
            has_venue_source=True,
        )
        assert result.status == QualityGateStatus.FAILED_PRELIMINARY_ALLOWED.value
        assert "article" in result.blocking_issues[0].lower()

    def test_missing_venue(self):
        result = evaluate_fit_gate(
            has_article_source=True,
            has_venue_source=False,
        )
        assert result.status == QualityGateStatus.FAILED_PRELIMINARY_ALLOWED.value

    def test_missing_scenario_is_warning(self):
        result = evaluate_fit_gate(
            has_article_source=True,
            has_venue_source=True,
            has_scenario=False,
            has_evidence_per_axis=True,
            has_context_pack=True,
        )
        assert result.status == QualityGateStatus.PASSED_WITH_WARNINGS.value
        assert any("scenario" in w.lower() for w in result.warnings)

    def test_light_profile(self):
        result = evaluate_fit_gate(
            has_article_source=True,
            has_venue_source=True,
            has_scenario=True,
            has_evidence_per_axis=False,
            has_context_pack=False,
        )
        assert result.status == QualityGateStatus.PASSED_WITH_WARNINGS.value


class TestSubmissionGate:
    def test_all_present(self):
        result = evaluate_submission_gate(
            has_fresh_guidelines=True,
            has_metadata=True,
            has_files_list=True,
            has_statements=True,
            blocking_risks_resolved=True,
        )
        assert result.status == QualityGateStatus.PASSED.value

    def test_stale_guidelines_blocks(self):
        result = evaluate_submission_gate(
            has_fresh_guidelines=False,
            has_metadata=True,
            has_files_list=True,
            has_statements=True,
            blocking_risks_resolved=True,
        )
        assert result.status == QualityGateStatus.FAILED_BLOCKING.value

    def test_missing_files_warns(self):
        result = evaluate_submission_gate(
            has_fresh_guidelines=True,
            has_metadata=True,
            has_files_list=False,
            has_statements=True,
            blocking_risks_resolved=True,
        )
        assert result.status == QualityGateStatus.PASSED_WITH_WARNINGS.value


class TestQualityGateResultModel:
    def test_to_dict(self):
        qgr = QualityGateResult(gate_name="test_gate")
        d = qgr.to_dict()
        assert d["gate_name"] == "test_gate"
        assert d["gate_id"].startswith("gate_")
