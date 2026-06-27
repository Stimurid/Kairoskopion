"""Tests for P8 Verification / Promotion Gate."""

import pytest

from kairoskopion.registry.models import (
    EvidenceRef,
    VenueRegistryRecord,
    VenueSectionRecord,
    VenueMetricRecord,
    VenueClassificationRecord,
    DisciplineRecord,
)
from kairoskopion.registry.services import RegistryHub
from kairoskopion.services.verification_gate import (
    VERDICTS,
    GATE_VERSION,
    VerificationDecision,
    verify_record,
    verify_registry,
    summarize_verification,
)


@pytest.fixture
def hub(tmp_path):
    return RegistryHub(data_dir=tmp_path / "registry")


def _ref(status="corpus_grounded"):
    return EvidenceRef(evidence_status=status, source_type="test")


# ---------------------------------------------------------------------------
# VerificationDecision model
# ---------------------------------------------------------------------------

class TestVerificationDecision:
    def test_serializable(self):
        d = VerificationDecision(record_id="r1", verdict="keep_provisional")
        data = d.to_dict()
        assert data["record_id"] == "r1"
        assert data["verifier_version"] == GATE_VERSION


# ---------------------------------------------------------------------------
# Venue records
# ---------------------------------------------------------------------------

class TestVerifyVenueRecord:
    def test_venue_with_real_evidence_promoted(self):
        rec = VenueRegistryRecord(
            canonical_name="Test Journal",
            issn="1234-5678",
            source_status="provisional",
            evidence_refs=[_ref("corpus_grounded")],
        )
        d = verify_record(rec)
        assert d.verdict == "promote_local_evidence_supported"
        assert d.has_real_evidence is True

    def test_venue_with_adapter_evidence_verified(self):
        rec = VenueRegistryRecord(
            canonical_name="Test Journal",
            source_status="provisional",
            evidence_refs=[_ref("adapter_result")],
        )
        d = verify_record(rec)
        assert d.verdict == "promote_verified"

    def test_venue_no_evidence_stays_provisional(self):
        rec = VenueRegistryRecord(
            canonical_name="Test",
            source_status="provisional",
            evidence_refs=[],
        )
        d = verify_record(rec)
        assert d.verdict == "keep_provisional"
        assert d.after_status == "provisional"

    def test_venue_llm_only_not_promoted(self):
        rec = VenueRegistryRecord(
            canonical_name="Test",
            source_status="provisional",
            evidence_refs=[_ref("llm_inference")],
        )
        d = verify_record(rec)
        assert d.verdict == "keep_provisional"
        assert d.has_llm_only is True


# ---------------------------------------------------------------------------
# Venue metrics
# ---------------------------------------------------------------------------

class TestVerifyVenueMetric:
    def test_metric_with_evidence_promoted(self):
        rec = VenueMetricRecord(
            metric_system="sjr",
            metric_value="0.31",
            evidence_status="corpus_grounded",
        )
        d = verify_record(rec)
        assert d.verdict == "promote_local_evidence_supported"

    def test_metric_adapter_verified(self):
        rec = VenueMetricRecord(
            metric_system="sjr",
            metric_value="0.31",
            evidence_status="adapter_result",
        )
        d = verify_record(rec)
        assert d.verdict == "promote_verified"

    def test_metric_llm_stays_provisional(self):
        rec = VenueMetricRecord(
            metric_system="sjr",
            metric_value="0.31",
            evidence_status="llm_inference",
        )
        d = verify_record(rec)
        assert d.verdict == "keep_provisional"

    def test_metric_unknown_stays(self):
        rec = VenueMetricRecord(
            metric_system="sjr",
            evidence_status="unknown",
        )
        d = verify_record(rec)
        assert d.verdict == "keep_provisional"


# ---------------------------------------------------------------------------
# Venue classifications
# ---------------------------------------------------------------------------

class TestVerifyVenueClassification:
    def test_classification_with_evidence(self):
        rec = VenueClassificationRecord(
            classification_system_id="vak",
            evidence_status="corpus_grounded",
        )
        d = verify_record(rec)
        assert d.verdict == "promote_local_evidence_supported"

    def test_classification_no_evidence(self):
        rec = VenueClassificationRecord(
            evidence_status="unknown",
        )
        d = verify_record(rec)
        assert d.verdict == "keep_provisional"


# ---------------------------------------------------------------------------
# Disciplines
# ---------------------------------------------------------------------------

class TestVerifyDiscipline:
    def test_discipline_llm_seed_not_promoted(self):
        rec = DisciplineRecord(
            display_names={"ru": "Философия"},
            source_status="provisional",
            provenance="llm_draft from ru_seed.jsonl",
            evidence_refs=[_ref("llm_inference")],
        )
        d = verify_record(rec)
        assert d.verdict == "keep_provisional"

    def test_discipline_corroborated_promoted(self):
        rec = DisciplineRecord(
            display_names={"ru": "Философия"},
            source_status="provisional",
            provenance="llm_draft from ru_seed.jsonl",
            evidence_refs=[_ref("corpus_grounded")],
        )
        d = verify_record(rec)
        assert d.verdict == "promote_local_evidence_supported"


# ---------------------------------------------------------------------------
# Conflicting evidence
# ---------------------------------------------------------------------------

class TestConflictingEvidence:
    def test_vendor_only_needs_review(self):
        rec = VenueRegistryRecord(
            canonical_name="Test",
            source_status="provisional",
            evidence_refs=[_ref("vendor_claim")],
        )
        d = verify_record(rec)
        assert d.verdict == "needs_manual_review"


# ---------------------------------------------------------------------------
# Batch verification
# ---------------------------------------------------------------------------

class TestBatchVerification:
    def test_verify_registry_empty(self, hub):
        decisions = verify_registry(hub)
        assert len(decisions) == 0

    def test_verify_registry_with_records(self, hub):
        reg = hub.venues()
        rec = VenueRegistryRecord(
            canonical_name="Test",
            source_status="provisional",
            evidence_refs=[_ref("corpus_grounded")],
        )
        reg.add_provisional(rec)

        decisions = verify_registry(hub)
        assert len(decisions) >= 1
        assert decisions[0].verdict == "promote_local_evidence_supported"

    def test_summarize(self):
        decisions = [
            VerificationDecision(verdict="promote_verified"),
            VerificationDecision(verdict="keep_provisional"),
            VerificationDecision(verdict="keep_provisional"),
            VerificationDecision(verdict="promote_local_evidence_supported"),
        ]
        summary = summarize_verification(decisions)
        assert summary["total"] == 4
        assert summary["verdicts"]["promote_verified"] == 1
        assert summary["verdicts"]["keep_provisional"] == 2


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

class TestAuditTrail:
    def test_audit_trail_written(self):
        rec = VenueRegistryRecord(
            canonical_name="Test",
            source_status="provisional",
            evidence_refs=[_ref("corpus_grounded")],
        )
        d = verify_record(rec)
        assert d.before_status == "provisional"
        assert d.after_status is not None
        assert d.reason != ""
        assert d.verifier_version == GATE_VERSION
        assert d.verified_at is not None

    def test_audit_has_evidence_counts(self):
        rec = VenueRegistryRecord(
            canonical_name="Test",
            evidence_refs=[_ref("corpus_grounded"), _ref("adapter_result")],
        )
        d = verify_record(rec)
        assert d.evidence_refs_count == 2
        assert len(d.evidence_kinds) == 2
