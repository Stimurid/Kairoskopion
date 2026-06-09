"""Tests for Sprint 6: SubmissionPack + Reports."""

from __future__ import annotations

import pytest

from kairoskopion.enums import SubmissionReadiness
from kairoskopion.services.submission_pack import (
    build_submission_pack,
    _assess_readiness,
    _collect_required_statements,
    _generate_cover_letter,
)
from kairoskopion.schema import (
    ArticleModel,
    ComplianceChecklist,
    FitAssessment,
    PublicationTrajectoryReport,
    RiskReport,
    SubmissionPack,
    SubmissionScenario,
    VenueModel,
)
from kairoskopion.ids import (
    article_model_id,
    fit_assessment_id,
    risk_report_id,
    submission_scenario_id,
    venue_model_id,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _minimal_article(**kw) -> ArticleModel:
    defaults = dict(
        article_model_id=article_model_id(),
        source_refs=["local:test"],
        title_current="Test Manuscript Title",
        language="en",
        input_mode="full_manuscript",
        article_stage="full_manuscript",
        genre_current="research_article",
        method_status="conceptual_method",
        novelty_mode="critique",
        citation_ecology_current="5 references found",
        unknowns=[],
        confidence="medium",
        lifecycle_status="preliminary",
        evidence_refs=[],
    )
    defaults.update(kw)
    return ArticleModel(**defaults)


def _minimal_venue(**kw) -> VenueModel:
    defaults = dict(
        venue_model_id=venue_model_id(),
        canonical_name="Test Journal of Science",
        venue_type="journal",
        official_urls=["https://example.com"],
        scope_summary="Science and technology",
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


def _minimal_scenario(**kw) -> SubmissionScenario:
    defaults = dict(
        submission_scenario_id=submission_scenario_id(),
        article_model_id="art_test",
        target_venue_ids=["ven_test"],
        goal="Publish research",
        deadline=None,
    )
    defaults.update(kw)
    return SubmissionScenario(**defaults)


def _minimal_fit(**kw) -> FitAssessment:
    defaults = dict(
        fit_assessment_id=fit_assessment_id(),
        article_model_id="art_test",
        venue_model_id="ven_test",
        overall_label="possible",
        axes=[
            {"axis": "topic", "value": "strong", "notes": "good match"},
            {"axis": "discipline", "value": "strong", "notes": "good match"},
        ],
        unknowns=[],
    )
    defaults.update(kw)
    return FitAssessment(**defaults)


def _minimal_risk(**kw) -> RiskReport:
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


def _minimal_compliance(**kw) -> ComplianceChecklist:
    defaults = dict(
        venue_model_id="ven_test",
        article_model_id="art_test",
        checklist_items=[
            {"item": "word_count", "status": "ok"},
        ],
        missing_items=[],
    )
    defaults.update(kw)
    return ComplianceChecklist(**defaults)


# ---------------------------------------------------------------------------
# Cover letter
# ---------------------------------------------------------------------------


class TestCoverLetter:
    def test_cover_letter_is_template(self):
        """Cover letter must contain [AUTHOR:] placeholders — not final text."""
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        letter = _generate_cover_letter(art, ven, sc)
        assert "[AUTHOR:" in letter

    def test_cover_letter_contains_title(self):
        art = _minimal_article(title_current="My Paper Title")
        ven = _minimal_venue()
        sc = _minimal_scenario()
        letter = _generate_cover_letter(art, ven, sc)
        assert "My Paper Title" in letter

    def test_cover_letter_contains_journal_name(self):
        art = _minimal_article()
        ven = _minimal_venue(canonical_name="Nature Reviews")
        sc = _minimal_scenario()
        letter = _generate_cover_letter(art, ven, sc)
        assert "Nature Reviews" in letter

    def test_cover_letter_no_title_uses_placeholder(self):
        art = _minimal_article(title_current=None)
        ven = _minimal_venue()
        sc = _minimal_scenario()
        letter = _generate_cover_letter(art, ven, sc)
        assert "[TITLE]" in letter

    def test_cover_letter_multiple_author_placeholders(self):
        """There must be multiple author-action placeholders."""
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        letter = _generate_cover_letter(art, ven, sc)
        count = letter.count("[AUTHOR:")
        assert count >= 3, f"Expected >=3 [AUTHOR:] placeholders, got {count}"


# ---------------------------------------------------------------------------
# Required statements
# ---------------------------------------------------------------------------


class TestRequiredStatements:
    def test_data_policy_triggers_statement(self):
        art = _minimal_article()
        ven = _minimal_venue(data_policy="Authors must provide data availability statement.")
        stmts = _collect_required_statements(art, ven)
        assert any("Data availability" in s for s in stmts)

    def test_ai_policy_triggers_statement(self):
        art = _minimal_article()
        ven = _minimal_venue(ai_policy="Authors must disclose AI usage.")
        stmts = _collect_required_statements(art, ven)
        assert any("AI disclosure" in s for s in stmts)

    def test_no_policies_no_statements(self):
        art = _minimal_article()
        ven = _minimal_venue()
        stmts = _collect_required_statements(art, ven)
        assert len(stmts) == 0

    def test_missing_data_statement_flagged(self):
        art = _minimal_article(has_data_availability_statement=False)
        ven = _minimal_venue(data_policy="Required")
        stmts = _collect_required_statements(art, ven)
        required = [s for s in stmts if "REQUIRED" in s]
        assert len(required) >= 1

    def test_present_data_statement_not_flagged(self):
        art = _minimal_article(has_data_availability_statement=True)
        ven = _minimal_venue(data_policy="Required")
        stmts = _collect_required_statements(art, ven)
        required = [s for s in stmts if "REQUIRED" in s]
        assert len(required) == 0

    def test_no_fake_declarations(self):
        """Statements must never claim compliance that wasn't verified."""
        art = _minimal_article()
        ven = _minimal_venue(
            data_policy="Required",
            ai_policy="Required",
            ethics_policy="Required",
        )
        stmts = _collect_required_statements(art, ven)
        for s in stmts:
            # No statement should say "compliant" or "meets" without evidence
            assert "compliant" not in s.lower()
            assert "meets requirement" not in s.lower()


# ---------------------------------------------------------------------------
# Readiness assessment
# ---------------------------------------------------------------------------


class TestReadinessAssessment:
    def test_blocking_issues_mean_not_ready(self):
        status = _assess_readiness(
            compliance=None, risk=None, fit=None,
            missing=[], blocking=["bad axis"],
        )
        assert status == SubmissionReadiness.NOT_READY.value

    def test_missing_items_mean_needs_update(self):
        status = _assess_readiness(
            compliance=None, risk=None, fit=None,
            missing=["data statement"], blocking=[],
        )
        assert status == SubmissionReadiness.NEEDS_FILE_UPDATE.value

    def test_poor_fit_means_not_ready(self):
        fit = _minimal_fit(overall_label="poor_fit")
        status = _assess_readiness(
            compliance=None, risk=None, fit=fit,
            missing=[], blocking=[],
        )
        assert status == SubmissionReadiness.NOT_READY.value

    def test_high_risk_means_needs_input(self):
        risk = _minimal_risk(overall_risk_label="high")
        status = _assess_readiness(
            compliance=None, risk=risk, fit=None,
            missing=[], blocking=[],
        )
        assert status == SubmissionReadiness.NEEDS_USER_INPUT.value

    def test_compliance_missing_means_needs_check(self):
        comp = _minimal_compliance(missing_items=["word_count"])
        fit = _minimal_fit(overall_label="strong_candidate")
        status = _assess_readiness(
            compliance=comp, risk=None, fit=fit,
            missing=[], blocking=[],
        )
        assert status == SubmissionReadiness.NEEDS_COMPLIANCE_CHECK.value

    def test_all_clear_strong_fit_means_ready(self):
        fit = _minimal_fit(overall_label="strong_candidate")
        comp = _minimal_compliance()
        status = _assess_readiness(
            compliance=comp, risk=None, fit=fit,
            missing=[], blocking=[],
        )
        assert status == SubmissionReadiness.READY_FOR_MANUAL_SUBMISSION.value

    def test_possible_fit_means_ready(self):
        fit = _minimal_fit(overall_label="possible")
        comp = _minimal_compliance()
        status = _assess_readiness(
            compliance=comp, risk=None, fit=fit,
            missing=[], blocking=[],
        )
        assert status == SubmissionReadiness.READY_FOR_MANUAL_SUBMISSION.value


# ---------------------------------------------------------------------------
# Full build_submission_pack
# ---------------------------------------------------------------------------


class TestBuildSubmissionPack:
    def test_basic_pack(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        pack = build_submission_pack(art, ven, sc)
        assert isinstance(pack, SubmissionPack)
        assert pack.submission_pack_id.startswith("sp_")
        assert pack.article_model_id == art.article_model_id
        assert pack.venue_model_id == ven.venue_model_id

    def test_pack_has_cover_letter(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        pack = build_submission_pack(art, ven, sc)
        assert pack.cover_letter is not None
        assert "[AUTHOR:" in pack.cover_letter

    def test_pack_files_include_manuscript(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        pack = build_submission_pack(art, ven, sc)
        assert "manuscript" in pack.files

    def test_pack_without_compliance_warns(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        pack = build_submission_pack(art, ven, sc)
        assert any("Compliance" in w for w in pack.warnings)

    def test_pack_with_compliance_missing(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        comp = _minimal_compliance(missing_items=["abstract length"])
        pack = build_submission_pack(art, ven, sc, compliance=comp)
        assert any("abstract length" in m for m in pack.missing_items)

    def test_pack_with_bad_fit_axis_blocks(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        fit = _minimal_fit(axes=[
            {"axis": "topic", "value": "bad", "notes": "total mismatch"},
        ])
        pack = build_submission_pack(art, ven, sc, fit=fit)
        assert len(pack.blocking_issues) > 0
        assert any("topic" in b for b in pack.blocking_issues)

    def test_pack_with_blocking_risk(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        risk = _minimal_risk(risk_items=[
            {"risk_type": "desk_reject", "severity": "blocking",
             "description": "paper too short"},
        ])
        pack = build_submission_pack(art, ven, sc, risk=risk)
        assert len(pack.blocking_issues) > 0

    def test_pack_serialization_roundtrip(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        pack = build_submission_pack(art, ven, sc)
        d = pack.to_dict()
        restored = SubmissionPack.from_dict(d)
        assert restored.submission_pack_id == pack.submission_pack_id
        assert restored.ready_status == pack.ready_status
        assert restored.cover_letter == pack.cover_letter

    def test_pack_ready_status_not_ready_when_blocked(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        fit = _minimal_fit(axes=[
            {"axis": "topic", "value": "bad", "notes": "mismatch"},
        ])
        pack = build_submission_pack(art, ven, sc, fit=fit)
        assert pack.ready_status == SubmissionReadiness.NOT_READY.value

    def test_pack_ready_when_all_clear(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        fit = _minimal_fit(overall_label="strong_candidate")
        risk = _minimal_risk(overall_risk_label="low")
        comp = _minimal_compliance()
        pack = build_submission_pack(art, ven, sc, fit=fit, risk=risk, compliance=comp)
        assert pack.ready_status == SubmissionReadiness.READY_FOR_MANUAL_SUBMISSION.value

    def test_venue_policies_produce_required_statements(self):
        art = _minimal_article()
        ven = _minimal_venue(
            data_policy="Must include data availability statement",
            ai_policy="Must disclose AI tools",
        )
        sc = _minimal_scenario()
        pack = build_submission_pack(art, ven, sc)
        assert len(pack.statements) >= 2

    def test_missing_title_flagged(self):
        art = _minimal_article(title_current=None)
        ven = _minimal_venue()
        sc = _minimal_scenario()
        pack = build_submission_pack(art, ven, sc)
        assert any("title" in m.lower() for m in pack.missing_items)

    def test_metadata_contains_fit_label(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        fit = _minimal_fit(overall_label="possible")
        pack = build_submission_pack(art, ven, sc, fit=fit)
        assert pack.metadata.get("fit_label") == "possible"

    def test_metadata_contains_risk_label(self):
        art = _minimal_article()
        ven = _minimal_venue()
        sc = _minimal_scenario()
        risk = _minimal_risk(overall_risk_label="moderate")
        pack = build_submission_pack(art, ven, sc, risk=risk)
        assert pack.metadata.get("risk_label") == "moderate"
