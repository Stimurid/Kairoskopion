"""Tests for Kairoskopion domain schema models."""

from kairoskopion.schema import (
    ArticleModel,
    CitationPlan,
    ComplianceChecklist,
    EvidenceItem,
    FitAssessment,
    ManuscriptModel,
    MismatchMap,
    PipelineRun,
    PublicationRegimeModel,
    RewritePlan,
    RiskReport,
    SourceSnapshot,
    SubmissionPack,
    SubmissionScenario,
    VenueModel,
)
from kairoskopion.enums import (
    ArticleStage,
    EvidenceStatus,
    FitLabel,
    Genre,
    LifecycleStatus,
    MethodStatus,
    NoveltyMode,
    PipelineRunStatus,
    RegimeType,
    SubmissionReadiness,
    VenueType,
)


class TestArticleModel:
    def test_create_default(self):
        am = ArticleModel()
        assert am.article_model_id.startswith("art_")
        assert am.lifecycle_status == LifecycleStatus.DRAFT.value
        assert am.genre_current == Genre.UNKNOWN.value
        assert am.unknowns == []

    def test_create_with_values(self):
        am = ArticleModel(
            title_current="On the Nature of AI Subjectivity",
            problem_statement="Can AI have subjectivity?",
            genre_current=Genre.THEORETICAL_ESSAY.value,
            core_claims=["AI cannot have genuine subjectivity"],
            protected_core=["central thesis", "philosophical stance"],
        )
        assert am.title_current == "On the Nature of AI Subjectivity"
        assert len(am.core_claims) == 1
        assert len(am.protected_core) == 2

    def test_to_dict_roundtrip(self):
        am = ArticleModel(title_current="Test", core_claims=["claim1"])
        d = am.to_dict()
        assert d["title_current"] == "Test"
        assert d["core_claims"] == ["claim1"]
        am2 = ArticleModel.from_dict(d)
        assert am2.title_current == "Test"
        assert am2.core_claims == ["claim1"]

    def test_unknown_fields_ignored_in_from_dict(self):
        d = {"title_current": "X", "nonexistent_field": "should be ignored"}
        am = ArticleModel.from_dict(d)
        assert am.title_current == "X"


class TestManuscriptModel:
    def test_create(self):
        ms = ManuscriptModel(title="Draft v1", word_count=5000)
        assert ms.manuscript_id.startswith("ms_")
        assert ms.word_count == 5000
        assert ms.version == 1


class TestVenueModel:
    def test_create_default(self):
        vm = VenueModel()
        assert vm.venue_model_id.startswith("ven_")
        assert vm.venue_type == VenueType.JOURNAL.value

    def test_create_special_issue(self):
        vm = VenueModel(
            canonical_name="AI Ethics Special Issue",
            venue_type=VenueType.SPECIAL_ISSUE.value,
            scope_summary="AI ethics in social contexts",
        )
        assert vm.venue_type == "special_issue"


class TestPublicationRegimeModel:
    def test_create(self):
        pr = PublicationRegimeModel(
            regime_type=RegimeType.HUMANITIES_SPECIAL_ISSUE.value,
            description="Humanities-oriented special issue with invited contributions",
        )
        assert pr.regime_type == "humanities_special_issue"


class TestSubmissionScenario:
    def test_create(self):
        ss = SubmissionScenario(
            goal="Publish in Q1 STS journal",
            target_indexing="Scopus",
            deadline="2026-09-01",
        )
        assert ss.submission_scenario_id.startswith("scn_")
        assert ss.goal == "Publish in Q1 STS journal"


class TestFitAssessment:
    def test_create_preliminary(self):
        fa = FitAssessment(
            overall_label=FitLabel.NOT_ENOUGH_DATA.value,
        )
        assert fa.overall_label == "not_enough_data"
        assert fa.lifecycle_status == LifecycleStatus.PRELIMINARY.value


class TestMismatchMap:
    def test_create(self):
        mm = MismatchMap(summary="3 major mismatches found")
        assert mm.mismatch_map_id.startswith("mm_")


class TestRewritePlan:
    def test_create(self):
        rp = RewritePlan(summary="Rewrite introduction for STS audience")
        assert rp.requires_user_acceptance is True


class TestCitationPlan:
    def test_create(self):
        cp = CitationPlan(
            missing_bridge_categories=["STS foundational texts"],
            dangerous_padding_warnings=["Avoid adding irrelevant Latour refs"],
        )
        assert len(cp.missing_bridge_categories) == 1


class TestRiskReport:
    def test_create(self):
        rr = RiskReport(
            overall_risk_label="medium",
            blocking_risks=["AI disclosure policy unclear"],
        )
        assert rr.risk_report_id.startswith("risk_")


class TestComplianceChecklist:
    def test_create(self):
        cc = ComplianceChecklist(
            missing_items=["data availability statement"],
        )
        assert cc.compliance_checklist_id.startswith("cc_")


class TestSubmissionPack:
    def test_create_not_ready(self):
        sp = SubmissionPack(
            missing_items=["cover letter", "figure captions"],
            ready_status=SubmissionReadiness.NOT_READY.value,
        )
        assert sp.ready_status == "not_ready"


class TestPipelineRun:
    def test_create(self):
        pr = PipelineRun(pipeline_type="one_target_venue")
        assert pr.pipeline_run_id.startswith("run_")
        assert pr.status == PipelineRunStatus.CREATED.value


class TestEvidenceItemSchema:
    def test_roundtrip(self):
        ei = EvidenceItem(
            claim_supported="Journal requires 250-word abstract",
            evidence_status=EvidenceStatus.FACT_FROM_SOURCE.value,
        )
        d = ei.to_dict()
        assert d["evidence_status"] == "FACT_FROM_SOURCE"
        ei2 = EvidenceItem.from_dict(d)
        assert ei2.claim_supported == "Journal requires 250-word abstract"


class TestSourceSnapshotSchema:
    def test_create(self):
        ss = SourceSnapshot(url="https://example.com/journal/scope")
        assert ss.snapshot_id.startswith("snap_")
