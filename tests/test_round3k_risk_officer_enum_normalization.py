"""Round III-K — RiskOfficer enum normalization tests.

Pin the _normalize_risk_type() function against LLM output variants.
"""

from __future__ import annotations

import unittest

from kairoskopion.services.llm_semantic_organs import _normalize_risk_type
from kairoskopion.services.risk_reporting import RISK_TYPES


class TestNormalizeRiskType(unittest.TestCase):

    def test_canonical_values_pass_through(self):
        for rt in RISK_TYPES:
            self.assertEqual(_normalize_risk_type(rt), rt)

    def test_title_case_normalized(self):
        self.assertEqual(
            _normalize_risk_type("Scope Mismatch"), "scope_mismatch",
        )

    def test_title_case_with_underscores(self):
        self.assertEqual(
            _normalize_risk_type("Desk_Reject_Risk"), "desk_reject_risk",
        )

    def test_hyphens_normalized(self):
        self.assertEqual(
            _normalize_risk_type("scope-mismatch"), "scope_mismatch",
        )

    def test_upper_case_normalized(self):
        self.assertEqual(
            _normalize_risk_type("CITATION_GAP"), "citation_gap",
        )

    def test_mixed_spaces_and_hyphens(self):
        self.assertEqual(
            _normalize_risk_type("Core Transformation-Risk"),
            "core_transformation_risk",
        )

    def test_trailing_risk_suffix_added(self):
        self.assertEqual(
            _normalize_risk_type("desk_reject"), "desk_reject_risk",
        )

    def test_trailing_risk_suffix_not_doubled(self):
        self.assertEqual(
            _normalize_risk_type("timeline_risk"), "timeline_risk",
        )

    def test_unknown_enum_passes_through(self):
        result = _normalize_risk_type("completely_novel_risk_category")
        self.assertEqual(result, "completely_novel_risk_category")

    def test_empty_string_returns_unknown(self):
        self.assertEqual(_normalize_risk_type(""), "unknown")

    def test_whitespace_only_returns_unknown(self):
        self.assertEqual(_normalize_risk_type("   "), "unknown")

    def test_padded_whitespace_stripped(self):
        self.assertEqual(
            _normalize_risk_type("  scope_mismatch  "), "scope_mismatch",
        )

    def test_ai_policy_risk_variants(self):
        self.assertEqual(
            _normalize_risk_type("AI Policy Risk"), "ai_policy_risk",
        )
        self.assertEqual(
            _normalize_risk_type("ai-policy-risk"), "ai_policy_risk",
        )

    def test_predatory_venue_variant(self):
        self.assertEqual(
            _normalize_risk_type("Predatory Venue"), "predatory_venue",
        )

    def test_all_18_risk_types_covered(self):
        self.assertEqual(len(RISK_TYPES), 18)
        for rt in RISK_TYPES:
            title = rt.replace("_", " ").title()
            self.assertEqual(
                _normalize_risk_type(title), rt,
                f"Title-case '{title}' should normalize to '{rt}'",
            )


class TestRiskOfficerSeverityMapExists(unittest.TestCase):
    """Sanity: severity mapping is still wired."""

    def test_severity_map_has_expected_keys(self):
        from kairoskopion.services.llm_semantic_organs import _RISK_SEVERITY_MAP
        self.assertIn("critical", _RISK_SEVERITY_MAP)
        self.assertIn("high", _RISK_SEVERITY_MAP)
        self.assertIn("low", _RISK_SEVERITY_MAP)


if __name__ == "__main__":
    unittest.main()
