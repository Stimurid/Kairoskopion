"""Tests for incident tracking service."""

from __future__ import annotations

import unittest

from kairoskopion.services.incident_tracking import (
    Incident,
    IncidentCategory,
    IncidentLog,
    IncidentSeverity,
    IncidentTracker,
    ResolutionStatus,
)


class TestIncidentTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = IncidentTracker(pipeline_run_id="run_test")

    def test_record_basic(self):
        inc = self.tracker.record(
            IncidentCategory.QUALITY_GATE_FAILURE.value,
            IncidentSeverity.ERROR.value,
            "Gate failed",
        )
        self.assertIn("inc_", inc.incident_id)
        self.assertEqual(inc.severity, "error")
        self.assertEqual(len(self.tracker.incidents), 1)

    def test_record_gate_failure(self):
        inc = self.tracker.record_gate_failure(
            "submission_pack",
            ["Missing metadata", "Blocking risks"],
        )
        self.assertEqual(inc.category, "quality_gate_failure")
        self.assertEqual(inc.source_gate, "submission_pack")
        self.assertIn("Missing metadata", inc.description)

    def test_record_review_block(self):
        inc = self.tracker.record_review_block(
            "ch_1", "Matches: thesis",
            matched_core_elements=["thesis"],
        )
        self.assertEqual(inc.category, "review_loop_blocked")
        self.assertEqual(inc.affected_entity_id, "ch_1")
        self.assertIn("thesis", inc.metadata["matched_core_elements"])

    def test_record_review_rejection(self):
        inc = self.tracker.record_review_rejection("ch_2", "author declines")
        self.assertEqual(inc.category, "review_loop_rejection")
        self.assertEqual(inc.severity, "info")

    def test_record_adapter_failure(self):
        inc = self.tracker.record_adapter_failure("doaj_venue", "timeout")
        self.assertEqual(inc.category, "adapter_failure")
        self.assertEqual(inc.source_agent, "doaj_venue")

    def test_record_reference_issue(self):
        inc = self.tracker.record_reference_issue("ref_001", "DOI unresolved")
        self.assertEqual(inc.category, "reference_integrity")
        self.assertEqual(inc.affected_entity_id, "ref_001")


class TestResolution(unittest.TestCase):
    def setUp(self):
        self.tracker = IncidentTracker()
        self.inc = self.tracker.record(
            IncidentCategory.AGENT_FAILURE.value,
            IncidentSeverity.ERROR.value,
            "Agent crashed",
        )

    def test_resolve_marks_resolved(self):
        result = self.tracker.resolve(self.inc.incident_id, "fixed")
        self.assertTrue(result)
        self.assertEqual(self.inc.resolution_status, "resolved")
        self.assertIsNotNone(self.inc.resolved_at)
        self.assertEqual(self.inc.resolution_note, "fixed")

    def test_resolve_nonexistent(self):
        result = self.tracker.resolve("inc_nonexistent")
        self.assertFalse(result)


class TestQueries(unittest.TestCase):
    def setUp(self):
        self.tracker = IncidentTracker()
        self.tracker.record_gate_failure("fit", ["issue1"])
        self.tracker.record_review_block("ch_1", "core match")
        self.tracker.record_review_rejection("ch_2", "declined")
        self.tracker.record_adapter_failure("doaj", "timeout")

    def test_by_category(self):
        gates = self.tracker.by_category("quality_gate_failure")
        self.assertEqual(len(gates), 1)

    def test_by_severity(self):
        errors = self.tracker.by_severity("error")
        self.assertEqual(len(errors), 2)  # gate + adapter

    def test_open_incidents(self):
        self.assertEqual(len(self.tracker.open_incidents()), 4)

    def test_has_blocking(self):
        self.assertTrue(self.tracker.has_blocking())

    def test_no_blocking_after_resolve(self):
        tracker = IncidentTracker()
        inc = tracker.record(
            IncidentCategory.AGENT_FAILURE.value,
            IncidentSeverity.ERROR.value,
            "error",
        )
        self.assertTrue(tracker.has_blocking())
        tracker.resolve(inc.incident_id)
        self.assertFalse(tracker.has_blocking())


class TestIncidentLog(unittest.TestCase):
    def test_log_counts(self):
        tracker = IncidentTracker(pipeline_run_id="run_log")
        tracker.record_gate_failure("fit", ["issue"])
        tracker.record_review_block("ch_1", "blocked")
        tracker.record_review_rejection("ch_2", "rejected")
        inc = tracker.record_adapter_failure("doaj", "timeout")
        tracker.resolve(inc.incident_id, "retried")

        log = tracker.to_log()
        self.assertEqual(log.total_count, 4)
        self.assertEqual(log.error_count, 2)
        self.assertEqual(log.warning_count, 1)
        self.assertEqual(log.info_count, 1)
        self.assertEqual(log.open_count, 3)
        self.assertEqual(log.resolved_count, 1)
        self.assertTrue(log.has_blocking_incidents)
        self.assertEqual(log.pipeline_run_id, "run_log")

    def test_empty_log(self):
        tracker = IncidentTracker()
        log = tracker.to_log()
        self.assertEqual(log.total_count, 0)
        self.assertFalse(log.has_blocking_incidents)

    def test_log_serialization(self):
        tracker = IncidentTracker()
        tracker.record_gate_failure("test", ["issue"])
        log = tracker.to_log()
        d = log.to_dict()
        self.assertIn("incidents", d)
        self.assertIn("total_count", d)
        self.assertEqual(len(d["incidents"]), 1)


class TestIncidentSerialization(unittest.TestCase):
    def test_incident_to_dict(self):
        inc = Incident(
            category="test",
            severity="info",
            title="test incident",
        )
        d = inc.to_dict()
        self.assertIn("incident_id", d)
        self.assertEqual(d["title"], "test incident")


class TestIntegrationWithReviewLoop(unittest.TestCase):
    def test_track_review_loop_incidents(self):
        from kairoskopion.schema import RewritePlan
        from kairoskopion.enums import FieldCoreImpact
        from kairoskopion.services.review_loop import (
            UserDecision, apply_user_decisions, extract_blocked_changes,
        )

        plan = RewritePlan(changes=[
            {
                "change_id": "ch_1",
                "target_block": "topic",
                "status": "blocked_pending_consent",
                "field_core_risk": FieldCoreImpact.CORE_TOUCHING.value,
                "_blocked_reason": "Matches: thesis",
                "_matched_core_elements": ["thesis"],
            },
        ])

        tracker = IncidentTracker(pipeline_run_id="test_run")

        # Record the block incident
        blocked = extract_blocked_changes(plan)
        for b in blocked:
            tracker.record_review_block(
                b["change_id"], b["blocked_reason"],
                matched_core_elements=b["matched_core_elements"],
            )

        # User rejects
        decisions = [UserDecision("ch_1", "reject", "author declines")]
        updated, iteration = apply_user_decisions(plan, decisions)

        # Record the rejection
        for d in decisions:
            if d.action == "reject":
                tracker.record_review_rejection(d.change_id, d.reason)

        log = tracker.to_log()
        self.assertEqual(log.total_count, 2)
        categories = [i["category"] for i in log.incidents]
        self.assertIn("review_loop_blocked", categories)
        self.assertIn("review_loop_rejection", categories)


if __name__ == "__main__":
    unittest.main()
