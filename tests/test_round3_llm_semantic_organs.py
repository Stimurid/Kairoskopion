"""Round III LLM-semantic-organ wiring tests.

Pins the brief's contract: LLM helpers ALWAYS fall back to needs_llm
placeholders on provider failure — NEVER to deterministic prose.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from kairoskopion.schema import (
    ArticleModel,
    BibliographyProfile,
    FitAssessment,
    MismatchMap,
    SubmissionScenario,
    VenueModel,
)
from kairoskopion.services.citation_plan_minimal import (
    build_minimal_citation_plan,
)
from kairoskopion.services.llm_semantic_organs import (
    try_llm_risk_officer,
    try_llm_rewrite_planner,
    upgrade_citation_plan_with_llm,
)
from kairoskopion.services.semantic_provenance import (
    ORIGIN_LLM,
    SEMANTIC_STATUS_LLM_GROUNDED,
    SEMANTIC_STATUS_NEEDS_LLM,
)


def _a(): return ArticleModel(title_current="X", genre_current="theoretical_essay")
def _v(): return VenueModel(canonical_name="V", venue_type="journal", scope_summary="scope")
def _f(): return FitAssessment(axes=[], overall_label="possible")
def _mm(): return MismatchMap(mismatches=[
    {"axis": "topic", "severity": "major", "article_side": "X",
     "venue_side": "", "description": "", "possible_actions": [],
     "field_core_risk": "unknown_core_impact"},
])


# ---------------- RiskOfficer ----------------

class TestRiskOfficerWiring(unittest.TestCase):
    def test_provider_none_yields_needs_llm(self):
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), None)
        self.assertEqual(rr.semantic_status, SEMANTIC_STATUS_NEEDS_LLM)
        self.assertEqual(rr.risk_items, [])

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_llm_success_yields_llm_grounded(self, mock_call):
        mock_call.return_value = ({
            "risk_items": [
                {"risk_type": "scope_mismatch", "severity": "high",
                 "description": "out of scope", "evidence": "scope doesn't match"},
                {"risk_type": "compliance_gap", "severity": "critical",
                 "description": "missing data statement", "evidence": "policy"},
            ],
            "unknowns": ["author eligibility unknown"],
            "confidence": "medium",
        }, MagicMock())
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        self.assertEqual(rr.semantic_status, SEMANTIC_STATUS_LLM_GROUNDED)
        self.assertEqual(len(rr.risk_items), 2)
        # Severity normalized
        sevs = {r["severity"] for r in rr.risk_items}
        self.assertEqual(sevs, {"major", "blocking"})  # high→major, critical→blocking
        self.assertEqual(len(rr.blocking_risks), 1)
        for f in ("risk_items", "blocking_risks", "warnings",
                  "overall_risk_label", "unknowns"):
            self.assertEqual(rr.field_origins.get(f), ORIGIN_LLM)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_llm_returns_none_yields_needs_llm(self, mock_call):
        mock_call.return_value = None
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        self.assertEqual(rr.semantic_status, SEMANTIC_STATUS_NEEDS_LLM)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_llm_exception_yields_needs_llm(self, mock_call):
        mock_call.side_effect = RuntimeError("provider fail")
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        self.assertEqual(rr.semantic_status, SEMANTIC_STATUS_NEEDS_LLM)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_no_deterministic_prose_present(self, mock_call):
        """Empty risk_items from LLM must NOT trigger deterministic fallback."""
        mock_call.return_value = ({"risk_items": [], "unknowns": [], "confidence": "low"}, MagicMock())
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        import json as _json
        flat = _json.dumps(rr.to_dict(), ensure_ascii=False).lower()
        forbidden = ["scope risk", "method risk", "desk-reject"]
        for phrase in forbidden:
            self.assertNotIn(phrase, flat)


# ---------------- RewritePlanner ----------------

class TestRewritePlannerWiring(unittest.TestCase):
    def test_provider_none_yields_needs_llm(self):
        rp = try_llm_rewrite_planner(_a(), _v(), _f(), _mm(), None, None)
        self.assertEqual(rp.semantic_status, SEMANTIC_STATUS_NEEDS_LLM)
        self.assertEqual(rp.changes, [])

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_llm_success_marks_core_touching(self, mock_call):
        mock_call.return_value = ({
            "overall_depth": "major",
            "actions": [
                {"action_id": 1, "target_mismatch": "topic",
                 "description": "Reframe thesis to fit venue",
                 "effort": "high", "field_core_impact": "core_touching"},
            ],
            "unknowns": [],
            "confidence": "medium",
        }, MagicMock())
        rp = try_llm_rewrite_planner(_a(), _v(), _f(), _mm(), None, MagicMock())
        self.assertEqual(rp.semantic_status, SEMANTIC_STATUS_LLM_GROUNDED)
        self.assertTrue(rp.requires_user_acceptance)
        self.assertEqual(rp.field_core_risk, "core_touching")
        # Unknowns should mention core-touching consent requirement
        self.assertTrue(any("user acceptance" in u.lower() for u in rp.unknowns))

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_unknown_field_core_normalized(self, mock_call):
        mock_call.return_value = ({
            "overall_depth": "medium",
            "actions": [
                {"action_id": 1, "target_mismatch": "method",
                 "description": "tweak", "effort": "low",
                 "field_core_impact": "weird_unknown_value"},
            ],
            "unknowns": [],
            "confidence": "low",
        }, MagicMock())
        rp = try_llm_rewrite_planner(_a(), _v(), _f(), _mm(), None, MagicMock())
        self.assertEqual(rp.changes[0]["field_core_risk"], "unknown_core_impact")

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_llm_exception_yields_needs_llm(self, mock_call):
        mock_call.side_effect = RuntimeError("fail")
        rp = try_llm_rewrite_planner(_a(), _v(), _f(), _mm(), None, MagicMock())
        self.assertEqual(rp.semantic_status, SEMANTIC_STATUS_NEEDS_LLM)


# ---------------- CitationPlanner ----------------

class TestCitationPlannerWiring(unittest.TestCase):
    def _base_plan(self):
        return build_minimal_citation_plan(
            _a(), _v(), _f(), _mm(), None, None,
            bibliography_profile=None,
        )

    def test_provider_none_keeps_structural(self):
        cp = upgrade_citation_plan_with_llm(
            self._base_plan(), _a(), _v(), None, None,
        )
        # Stays needs_llm because no LLM augmented anything
        self.assertEqual(cp.semantic_status, SEMANTIC_STATUS_NEEDS_LLM)
        self.assertEqual(cp.citation_gap_categories, [])

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_llm_success_populates_semantic_fields(self, mock_call):
        mock_call.return_value = ({
            "tradition_match": "weak",
            "canonical_coverage": "partial",
            "bridge_references_needed": [
                "philosophy of technology recent debate markers",
                "russian tradition crossover with anglo-analytic",
            ],
            "tradition_gaps": ["postphenomenological turn references missing"],
            "risk_items": ["scope_mismatch_risk"],
            "unknowns": ["venue corpus not available"],
            "confidence": "medium",
        }, MagicMock())
        cp = upgrade_citation_plan_with_llm(
            self._base_plan(), _a(), _v(), None, MagicMock(),
        )
        self.assertGreater(len(cp.citation_gap_categories), 0)
        self.assertGreater(len(cp.missing_bridge_categories), 0)
        self.assertGreater(len(cp.recommended_reference_search_tasks), 0)
        self.assertEqual(cp.field_origins["citation_gap_categories"], ORIGIN_LLM)
        self.assertEqual(cp.field_origins["missing_bridge_categories"], ORIGIN_LLM)
        self.assertIn("llm_citation_planner", cp.created_from)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_llm_dois_filtered(self, mock_call):
        """Anti-fake: any LLM-emitted bridge/gap containing DOI or
        author-year is stripped."""
        mock_call.return_value = ({
            "tradition_match": "weak",
            "bridge_references_needed": [
                "philosophy bridges",         # safe
                "Smith 2024 paper",            # author-year → filtered
                "https://doi.org/10.1234/x",   # DOI → filtered
            ],
            "tradition_gaps": ["safe gap category"],
            "unknowns": [],
            "confidence": "low",
        }, MagicMock())
        cp = upgrade_citation_plan_with_llm(
            self._base_plan(), _a(), _v(), None, MagicMock(),
        )
        joined = " ".join(cp.missing_bridge_categories)
        self.assertNotIn("Smith 2024", joined)
        self.assertNotIn("10.1234", joined)
        self.assertIn("philosophy bridges", joined)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_llm_failure_keeps_needs_llm(self, mock_call):
        mock_call.return_value = None
        cp = upgrade_citation_plan_with_llm(
            self._base_plan(), _a(), _v(), None, MagicMock(),
        )
        self.assertEqual(cp.semantic_status, SEMANTIC_STATUS_NEEDS_LLM)


if __name__ == "__main__":
    unittest.main()
