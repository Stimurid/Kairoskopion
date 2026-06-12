"""Tests for Kairoskopion evidence layer."""

from kairoskopion.enums import EvidenceStatus
from kairoskopion.evidence import (
    create_evidence_item,
    create_source_snapshot,
    validate_evidence_status,
)


class TestCreateEvidenceItem:
    def test_basic(self):
        ei = create_evidence_item(
            claim="Journal accepts research articles",
            status=EvidenceStatus.FACT_FROM_SOURCE,
            url_or_file_ref="https://example.com/journal/guidelines",
        )
        assert ei.evidence_id.startswith("evi_")
        assert ei.claim_supported == "Journal accepts research articles"
        assert ei.evidence_status == "FACT_FROM_SOURCE"

    def test_unknown_status(self):
        ei = create_evidence_item(claim="Something unknown")
        assert ei.evidence_status == "UNKNOWN"

    def test_with_excerpt(self):
        ei = create_evidence_item(
            claim="Abstract limit is 250 words",
            status=EvidenceStatus.FACT_FROM_SOURCE,
            excerpt="Abstracts should not exceed 250 words",
        )
        assert ei.excerpt_or_locator == "Abstracts should not exceed 250 words"


class TestCreateSourceSnapshot:
    def test_basic(self):
        ss = create_source_snapshot(
            url="https://example.com/journal",
            content_type="text/html",
        )
        assert ss.snapshot_id.startswith("snap_")
        assert ss.extraction_status == "pending"

    def test_with_source_id(self):
        ss = create_source_snapshot(source_id="src_123")
        assert ss.source_id == "src_123"


class TestValidateEvidenceStatus:
    def test_valid(self):
        assert validate_evidence_status("FACT_FROM_SOURCE") is True
        assert validate_evidence_status("UNKNOWN") is True
        assert validate_evidence_status("TACIT_SIGNAL") is True

    def test_invalid(self):
        assert validate_evidence_status("MADE_UP") is False
        assert validate_evidence_status("") is False


class TestEvidenceStatusEnum:
    def test_all_statuses_present(self):
        expected = {
            "FACT_FROM_SOURCE", "FACT_FROM_API_METADATA",
            "VENDOR_CLAIM", "CORPUS_OBSERVATION",
            "INFERENCE", "TACIT_SIGNAL", "USER_NOTE", "PRIOR_OUTCOME",
            "UNKNOWN", "INACCESSIBLE", "STALE", "CONFLICTING_EVIDENCE",
        }
        actual = {s.value for s in EvidenceStatus}
        assert actual == expected
