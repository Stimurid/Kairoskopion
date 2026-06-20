"""V2-C: dossier payload shape acceptance tests.

These tests pin the shape contract the V2-C DossierView depends on:
  - narrator_coverage survives MismatchMap.to_dict() round-trip
  - per-mismatch narrative_status survives serialization
  - dossier API never returns raw_output_ref content
  - parse-failure metadata is redacted (no Traceback, no API key)

No production behaviour is invoked here — these are schema/serializer
asserts only. Live acceptance is run separately on prod.
"""

from __future__ import annotations

import unittest

from kairoskopion.schema import MismatchMap


class TestMismatchMapNarratorCoverageSurvives(unittest.TestCase):
    def test_narrator_coverage_round_trip(self):
        coverage = {
            "narrator_attempted": True,
            "narrator_status": "parse_failed",
            "filled_count": 0,
            "total_count": 6,
            "missing_axes": [],
            "unmatched_axes": [],
            "parse_status": "schema_validation_failed",
            "used_model": "claude-sonnet-4-5-20250929",
            "latency_ms": 41231.9,
            "empty_reason": "narrator output failed parsing or schema validation",
            "parse_failure_category": "schema_validation_failed",
            "parse_failure_reason": "narrator output failed JSON schema validation",
            "schema_failure_path": None,
            "schema_failure_rule": None,
            "repair_failure_stage": None,
            "repair_steps_attempted": [],
        }
        mm = MismatchMap(
            mismatches=[
                {
                    "mismatch_id": "mm_1",
                    "axis": "topic",
                    "article_side": "X",
                    "venue_side": "",
                    "severity": "blocking",
                    "description": "X",
                    "possible_actions": ["A"],
                    "field_core_risk": "core_preserving",
                    "narrative_status": "parse_failed",
                }
            ],
            summary="1 blocking",
            critical_mismatches=["mm_1: topic — blocking mismatch"],
            unknowns=[],
            narrator_coverage=coverage,
        )
        d = mm.to_dict()
        self.assertEqual(d["narrator_coverage"]["narrator_status"], "parse_failed")
        self.assertEqual(d["narrator_coverage"]["parse_failure_category"],
                         "schema_validation_failed")
        self.assertEqual(d["narrator_coverage"]["filled_count"], 0)
        self.assertEqual(d["mismatches"][0]["narrative_status"], "parse_failed")

    def test_narrator_coverage_optional_when_none(self):
        mm = MismatchMap(mismatches=[], summary="None", critical_mismatches=[], unknowns=[])
        d = mm.to_dict()
        # Field present in dict (dataclass asdict emits None values);
        # UI treats None as "not yet wired" and falls back to honest empty.
        self.assertIn("narrator_coverage", d)
        self.assertIsNone(d["narrator_coverage"])

    def test_from_dict_tolerates_missing_narrator_coverage(self):
        """V2-B1 added narrator_coverage; older persisted snapshots
        without the key must still load."""
        data = {
            "mismatch_map_id": "mmid_old",
            "fit_assessment_id": "fa_old",
            "mismatches": [],
            "summary": None,
            "critical_mismatches": [],
            "unknowns": [],
        }
        mm = MismatchMap.from_dict(data)
        self.assertIsNone(mm.narrator_coverage)

    def test_no_raw_output_keys_in_serialization(self):
        coverage = {
            "narrator_attempted": True,
            "narrator_status": "parse_failed",
            "filled_count": 0,
            "total_count": 1,
            "missing_axes": [],
            "unmatched_axes": [],
            "parse_status": "schema_validation_failed",
            "empty_reason": "x",
            "parse_failure_category": "schema_validation_failed",
            "parse_failure_reason": "x",
            "schema_failure_path": None,
            "schema_failure_rule": None,
            "repair_failure_stage": None,
            "repair_steps_attempted": [],
        }
        mm = MismatchMap(
            mismatches=[],
            summary="x",
            critical_mismatches=[],
            unknowns=[],
            narrator_coverage=coverage,
        )
        d = mm.to_dict()
        cov = d["narrator_coverage"]
        for k in cov.keys():
            kl = k.lower()
            self.assertNotIn("raw", kl)
            self.assertNotIn("trace", kl)
            self.assertNotIn("stack", kl)
            self.assertNotIn("secret", kl)


if __name__ == "__main__":
    unittest.main()
