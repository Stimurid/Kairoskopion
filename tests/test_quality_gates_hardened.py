"""Tests for hardened quality gates (evidence completeness, reference integrity, protected core)."""

from __future__ import annotations

import unittest

from kairoskopion.enums import QualityGateStatus
from kairoskopion.quality import (
    evaluate_evidence_completeness_gate,
    evaluate_protected_core_gate,
    evaluate_reference_integrity_gate,
)


class TestEvidenceCompletenessGate(unittest.TestCase):
    def test_no_results_fails(self):
        gate = evaluate_evidence_completeness_gate(adapter_results=[])
        self.assertEqual(gate.status, QualityGateStatus.FAILED_PRELIMINARY_ALLOWED.value)
        self.assertIn("No evidence sources provided", gate.blocking_issues)

    def test_all_good_passes(self):
        results = [
            {"adapter_id": "doaj_venue", "status": "success", "evidence_status": "FACT_FROM_API_METADATA"},
            {"adapter_id": "openalex_venue", "status": "success", "evidence_status": "FACT_FROM_API_METADATA"},
        ]
        gate = evaluate_evidence_completeness_gate(adapter_results=results)
        self.assertEqual(gate.status, QualityGateStatus.PASSED.value)

    def test_errored_source_fails(self):
        results = [
            {"adapter_id": "doaj_venue", "status": "error"},
        ]
        gate = evaluate_evidence_completeness_gate(adapter_results=results)
        self.assertEqual(gate.status, QualityGateStatus.FAILED_PRELIMINARY_ALLOWED.value)

    def test_missing_required_source_warns(self):
        results = [
            {"adapter_id": "doaj_venue", "status": "success", "evidence_status": "OK"},
        ]
        gate = evaluate_evidence_completeness_gate(
            adapter_results=results,
            required_sources=["doaj_venue", "sherpa_policy"],
        )
        self.assertEqual(gate.status, QualityGateStatus.PASSED_WITH_WARNINGS.value)
        self.assertIn("sherpa_policy", gate.missing_sources)

    def test_unknown_evidence_status_warns(self):
        results = [
            {"adapter_id": "test", "status": "success", "evidence_status": "UNKNOWN"},
        ]
        gate = evaluate_evidence_completeness_gate(adapter_results=results)
        self.assertEqual(gate.status, QualityGateStatus.PASSED_WITH_WARNINGS.value)

    def test_stale_source_warns(self):
        results = [
            {
                "adapter_id": "test",
                "status": "success",
                "evidence_status": "OK",
                "fetched_at": "2020-01-01T00:00:00+00:00",
            },
        ]
        gate = evaluate_evidence_completeness_gate(
            adapter_results=results, stale_threshold_days=90,
        )
        self.assertEqual(gate.status, QualityGateStatus.PASSED_WITH_WARNINGS.value)
        self.assertIn("test", gate.stale_sources)

    def test_stale_source_naive_timestamp_still_detected(self):
        # Naive ISO timestamps (no tz) must not silently skip staleness check
        results = [
            {
                "adapter_id": "test",
                "status": "success",
                "evidence_status": "OK",
                "fetched_at": "2020-01-01T00:00:00",
            },
        ]
        gate = evaluate_evidence_completeness_gate(
            adapter_results=results, stale_threshold_days=90,
        )
        self.assertIn("test", gate.stale_sources)


class TestReferenceIntegrityGate(unittest.TestCase):
    def test_no_verification_not_applicable(self):
        gate = evaluate_reference_integrity_gate()
        self.assertEqual(gate.status, QualityGateStatus.NOT_APPLICABLE.value)

    def test_zero_references_warns(self):
        gate = evaluate_reference_integrity_gate(
            verification_result={"total_references": 0}
        )
        self.assertEqual(gate.status, QualityGateStatus.PASSED_WITH_WARNINGS.value)

    def test_good_coverage_passes(self):
        gate = evaluate_reference_integrity_gate(
            verification_result={
                "total_references": 20,
                "padding_risk_count": 0,
                "doi_unresolved_count": 0,
                "aggregate_metrics": {
                    "doi_coverage": 0.8,
                    "retraction_checked": False,
                    "pubpeer_checked": False,
                },
            },
        )
        self.assertEqual(gate.status, QualityGateStatus.PASSED.value)
        self.assertIn("retraction_status", gate.unknown_fields)

    def test_low_doi_coverage_warns(self):
        gate = evaluate_reference_integrity_gate(
            verification_result={
                "total_references": 10,
                "padding_risk_count": 0,
                "doi_unresolved_count": 0,
                "aggregate_metrics": {"doi_coverage": 0.1},
            },
        )
        self.assertIn("DOI coverage", gate.warnings[0])

    def test_high_padding_fails(self):
        gate = evaluate_reference_integrity_gate(
            verification_result={
                "total_references": 10,
                "padding_risk_count": 5,
                "doi_unresolved_count": 0,
                "aggregate_metrics": {"doi_coverage": 0.5},
            },
        )
        self.assertEqual(gate.status, QualityGateStatus.FAILED_PRELIMINARY_ALLOWED.value)
        self.assertIn("Padding risk", gate.blocking_issues[0])

    def test_unresolved_dois_warn(self):
        gate = evaluate_reference_integrity_gate(
            verification_result={
                "total_references": 10,
                "padding_risk_count": 0,
                "doi_unresolved_count": 3,
                "aggregate_metrics": {"doi_coverage": 0.8},
            },
        )
        self.assertTrue(any("could not be resolved" in w for w in gate.warnings))


class TestProtectedCoreGate(unittest.TestCase):
    def test_no_validation_not_applicable(self):
        gate = evaluate_protected_core_gate()
        self.assertEqual(gate.status, QualityGateStatus.NOT_APPLICABLE.value)

    def test_no_consent_needed_passes(self):
        gate = evaluate_protected_core_gate(
            core_validation={"blocked_count": 0, "requires_user_consent": False}
        )
        self.assertEqual(gate.status, QualityGateStatus.PASSED.value)

    def test_consent_needed_blocks(self):
        gate = evaluate_protected_core_gate(
            core_validation={"blocked_count": 2, "requires_user_consent": True}
        )
        self.assertEqual(gate.status, QualityGateStatus.FAILED_BLOCKING.value)
        self.assertIn("2 change(s)", gate.blocking_issues[0])
        self.assertGreater(len(gate.required_user_decisions), 0)

    def test_result_is_dict_serializable(self):
        gate = evaluate_protected_core_gate(
            core_validation={"blocked_count": 1, "requires_user_consent": True}
        )
        d = gate.to_dict()
        self.assertIn("gate_name", d)
        self.assertEqual(d["gate_name"], "protected_core")


if __name__ == "__main__":
    unittest.main()
