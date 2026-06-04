"""Negative-case and invariant tests for Kairoskopion MVP-0.

These tests verify domain rules from the spec:
- SubmissionPack cannot be ready without passing quality gate
- CitationPlan cannot silently promote unverified references
- FitAssessment cannot be evidence-backed without article/venue refs
- Unknowns survive serialization
- Evidence statuses survive serialization
"""

from kairoskopion.enums import (
    EvidenceStatus,
    FitLabel,
    LifecycleStatus,
    QualityGateStatus,
    SubmissionReadiness,
)
from kairoskopion.quality import evaluate_submission_gate
from kairoskopion.schema import (
    ArticleModel,
    CitationPlan,
    FitAssessment,
    SubmissionPack,
    VenueModel,
)


# --- SubmissionPack readiness invariants (spec §30.3, §6.25) ---

class TestSubmissionPackReadinessInvariant:
    """SubmissionPack should not be marked ready without passing gate."""

    def test_pack_without_guidelines_cannot_pass_gate(self):
        gate = evaluate_submission_gate(
            has_fresh_guidelines=False,
            has_metadata=True,
            has_files_list=True,
            has_statements=True,
            blocking_risks_resolved=True,
        )
        assert gate.status == QualityGateStatus.FAILED_BLOCKING.value
        assert any("guidelines" in issue.lower() for issue in gate.blocking_issues)

    def test_pack_without_metadata_cannot_pass_gate(self):
        gate = evaluate_submission_gate(
            has_fresh_guidelines=True,
            has_metadata=False,
            has_files_list=True,
            has_statements=True,
            blocking_risks_resolved=True,
        )
        assert gate.status == QualityGateStatus.FAILED_BLOCKING.value

    def test_pack_with_unresolved_risks_cannot_pass_gate(self):
        gate = evaluate_submission_gate(
            has_fresh_guidelines=True,
            has_metadata=True,
            has_files_list=True,
            has_statements=True,
            blocking_risks_resolved=False,
        )
        assert gate.status == QualityGateStatus.FAILED_BLOCKING.value

    def test_pack_default_is_not_ready(self):
        sp = SubmissionPack()
        assert sp.ready_status == SubmissionReadiness.NOT_READY.value

    def test_pack_with_blocking_issues_is_not_ready(self):
        sp = SubmissionPack(
            blocking_issues=["references not verified"],
            ready_status=SubmissionReadiness.NOT_READY.value,
        )
        assert sp.ready_status != SubmissionReadiness.READY_FOR_MANUAL_SUBMISSION.value


# --- CitationPlan cannot silently promote (spec §6.22, §26.4) ---

class TestCitationPlanUnverifiedInvariant:
    """Unverified references must not be silently treated as verified."""

    def test_default_bibliography_status_is_none(self):
        cp = CitationPlan()
        assert cp.current_bibliography_status is None

    def test_dangerous_padding_warnings_preserved(self):
        cp = CitationPlan(
            dangerous_padding_warnings=["Avoid adding irrelevant filler refs"],
        )
        d = cp.to_dict()
        cp2 = CitationPlan.from_dict(d)
        assert cp2.dangerous_padding_warnings == ["Avoid adding irrelevant filler refs"]

    def test_risk_flags_preserved(self):
        cp = CitationPlan(
            risk_flags=["unresolved_references_present"],
        )
        d = cp.to_dict()
        cp2 = CitationPlan.from_dict(d)
        assert "unresolved_references_present" in cp2.risk_flags

    def test_missing_bridges_preserved(self):
        cp = CitationPlan(
            missing_bridge_categories=["STS foundational", "AI ethics recent"],
        )
        d = cp.to_dict()
        cp2 = CitationPlan.from_dict(d)
        assert len(cp2.missing_bridge_categories) == 2


# --- FitAssessment cannot be evidence-backed without refs (spec §6.18, §37.7) ---

class TestFitAssessmentEvidenceInvariant:
    """FitAssessment without article/venue refs must stay preliminary."""

    def test_default_is_preliminary(self):
        fa = FitAssessment()
        assert fa.lifecycle_status == LifecycleStatus.PRELIMINARY.value

    def test_no_article_ref_means_not_enough_data(self):
        fa = FitAssessment(
            article_model_id=None,
            venue_model_id="ven_123",
        )
        # Without article ref, overall label should reflect insufficient data
        assert fa.article_model_id is None
        assert fa.overall_label == FitLabel.NOT_ENOUGH_DATA.value

    def test_no_venue_ref_means_not_enough_data(self):
        fa = FitAssessment(
            article_model_id="art_123",
            venue_model_id=None,
        )
        assert fa.venue_model_id is None
        assert fa.overall_label == FitLabel.NOT_ENOUGH_DATA.value

    def test_fit_gate_blocks_without_both_sources(self):
        from kairoskopion.quality import evaluate_fit_gate

        gate = evaluate_fit_gate(
            has_article_source=False,
            has_venue_source=False,
        )
        assert gate.status == QualityGateStatus.FAILED_PRELIMINARY_ALLOWED.value
        assert len(gate.blocking_issues) >= 2


# --- Unknowns preservation (spec §6, universal requirement) ---

class TestUnknownsPreservation:
    """Unknowns must survive to_dict/from_dict roundtrip."""

    def test_article_unknowns_preserved(self):
        am = ArticleModel(unknowns=["method unclear", "audience uncertain"])
        d = am.to_dict()
        am2 = ArticleModel.from_dict(d)
        assert am2.unknowns == ["method unclear", "audience uncertain"]

    def test_venue_unknowns_preserved(self):
        vm = VenueModel(unknowns=["APC policy", "indexing status", "editorial board"])
        d = vm.to_dict()
        vm2 = VenueModel.from_dict(d)
        assert vm2.unknowns == ["APC policy", "indexing status", "editorial board"]

    def test_fit_unknowns_preserved(self):
        fa = FitAssessment(unknowns=["citation ecology not checked"])
        d = fa.to_dict()
        fa2 = FitAssessment.from_dict(d)
        assert fa2.unknowns == ["citation ecology not checked"]

    def test_empty_unknowns_preserved_as_empty(self):
        am = ArticleModel(unknowns=[])
        d = am.to_dict()
        am2 = ArticleModel.from_dict(d)
        assert am2.unknowns == []


# --- Evidence status preservation (spec §6.1) ---

class TestEvidenceStatusPreservation:
    """Evidence statuses must survive serialization without silent promotion."""

    def test_all_statuses_roundtrip(self):
        from kairoskopion.schema import EvidenceItem

        for status in EvidenceStatus:
            ei = EvidenceItem(
                claim_supported=f"test claim for {status.value}",
                evidence_status=status.value,
            )
            d = ei.to_dict()
            ei2 = EvidenceItem.from_dict(d)
            assert ei2.evidence_status == status.value, (
                f"Status {status.value} not preserved after roundtrip"
            )

    def test_tacit_signal_stays_tacit(self):
        """A tacit signal must not silently become a fact (spec §6.1)."""
        from kairoskopion.schema import EvidenceItem

        ei = EvidenceItem(
            claim_supported="editor prefers empirical work",
            evidence_status=EvidenceStatus.TACIT_SIGNAL.value,
        )
        d = ei.to_dict()
        ei2 = EvidenceItem.from_dict(d)
        assert ei2.evidence_status == "TACIT_SIGNAL"
        assert ei2.evidence_status != "FACT_FROM_SOURCE"

    def test_unknown_stays_unknown(self):
        """UNKNOWN must not silently become absent or negative (spec §2)."""
        from kairoskopion.schema import EvidenceItem

        ei = EvidenceItem(
            claim_supported="indexing status",
            evidence_status=EvidenceStatus.UNKNOWN.value,
        )
        d = ei.to_dict()
        ei2 = EvidenceItem.from_dict(d)
        assert ei2.evidence_status == "UNKNOWN"

    def test_venue_model_evidence_refs_preserved(self):
        vm = VenueModel(
            evidence_refs=["evi_001", "evi_002"],
            confidence="low",
        )
        d = vm.to_dict()
        vm2 = VenueModel.from_dict(d)
        assert vm2.evidence_refs == ["evi_001", "evi_002"]
        assert vm2.confidence == "low"
