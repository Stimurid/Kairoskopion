"""Round III-E tests: contract normalizer + rubric Cyrillic gate.

Pins the new doctrine:
  - Container normalization is allowed (alternative top-level keys).
  - Semantic invention is not.
  - Anti-fake filter survives.
  - Rubric applies to Russian-content articles even when language=None.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from kairoskopion.schema import (
    ArticleModel,
    BibliographyProfile,
    FitAssessment,
    MismatchMap,
    VenueModel,
)
from kairoskopion.services.citation_plan_minimal import (
    build_minimal_citation_plan,
)
from kairoskopion.services.llm_contract_normalizer import (
    CITATION_BRIDGE_ALIASES,
    CITATION_GAP_ALIASES,
    REWRITE_ITEM_ALIASES,
    RISK_ITEM_ALIASES,
    find_list_under_aliases,
    shape_summary,
)
from kairoskopion.services.llm_semantic_organs import (
    try_llm_rewrite_planner,
    try_llm_risk_officer,
    upgrade_citation_plan_with_llm,
)
from kairoskopion.services.semantic_provenance import (
    SEMANTIC_STATUS_LLM_GROUNDED,
    SEMANTIC_STATUS_NEEDS_LLM,
)
from kairoskopion.services.writing_rubric import (
    _cyrillic_ratio,
    rubric_applies_to_article,
)


def _a(): return ArticleModel(title_current="X", genre_current="theoretical_essay")
def _v(): return VenueModel(canonical_name="V", venue_type="journal", scope_summary="scope")
def _f(): return FitAssessment(axes=[], overall_label="possible")
def _mm(): return MismatchMap(mismatches=[
    {"axis": "topic", "severity": "major", "article_side": "X",
     "venue_side": "", "description": "", "possible_actions": [],
     "field_core_risk": "unknown_core_impact"},
])


# ---------------- Container normalizer ----------------

class TestNormalizer(unittest.TestCase):
    def test_canonical_key(self):
        out, k = find_list_under_aliases({"risk_items": [1, 2]}, RISK_ITEM_ALIASES)
        self.assertEqual(out, [1, 2])
        self.assertEqual(k, "risk_items")

    def test_alternative_key(self):
        out, k = find_list_under_aliases({"risks": [{"x": 1}]}, RISK_ITEM_ALIASES)
        self.assertEqual(out, [{"x": 1}])
        self.assertEqual(k, "risks")

    def test_nested_envelope(self):
        out, k = find_list_under_aliases(
            {"risk_report": {"risk_items": [1]}}, RISK_ITEM_ALIASES,
        )
        self.assertEqual(out, [1])
        self.assertEqual(k, "risk_report.risk_items")

    def test_bare_list(self):
        out, k = find_list_under_aliases([1, 2, 3], RISK_ITEM_ALIASES)
        self.assertEqual(out, [1, 2, 3])
        self.assertEqual(k, "<root>")

    def test_not_found(self):
        out, k = find_list_under_aliases({"foo": 1}, RISK_ITEM_ALIASES)
        self.assertIsNone(out)
        self.assertIsNone(k)

    def test_rewrite_aliases(self):
        out, k = find_list_under_aliases({"changes": [{"a": 1}]}, REWRITE_ITEM_ALIASES)
        self.assertEqual(out, [{"a": 1}])
        self.assertEqual(k, "changes")

    def test_citation_gap_aliases(self):
        out, k = find_list_under_aliases({"gaps": ["x"]}, CITATION_GAP_ALIASES)
        self.assertEqual(out, ["x"])

    def test_shape_summary_redacted(self):
        s = shape_summary({"risks": [1, 2], "extra": "SECRET_VALUE_AAA"})
        self.assertEqual(s["top_level_type"], "object")
        self.assertIn("risks", s["top_level_keys"])
        # Values must never be echoed in the structural summary
        self.assertNotIn("SECRET_VALUE_AAA", str(s))


# ---------------- Risk: alternative top-level key ----------------

class TestRiskOfficerAlternativeKey(unittest.TestCase):
    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_risks_instead_of_risk_items(self, mock_call):
        mock_call.return_value = ({
            "risks": [  # alternative top-level key
                {"risk_type": "scope_mismatch", "severity": "high",
                 "description": "x", "evidence": "y"},
            ],
            "unknowns": [], "confidence": "medium",
        }, MagicMock())
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        self.assertEqual(rr.semantic_status, SEMANTIC_STATUS_LLM_GROUNDED)
        self.assertEqual(len(rr.risk_items), 1)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_nested_risk_report_envelope(self, mock_call):
        mock_call.return_value = ({
            "risk_report": {"risk_items": [
                {"risk_type": "method_gap", "severity": "medium",
                 "description": "x", "evidence": "y"},
            ]},
        }, MagicMock())
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        self.assertEqual(rr.semantic_status, SEMANTIC_STATUS_LLM_GROUNDED)
        self.assertEqual(len(rr.risk_items), 1)


# ---------------- Rewrite: alternative top-level key ----------------

class TestRewritePlannerAlternativeKey(unittest.TestCase):
    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_changes_instead_of_actions(self, mock_call):
        mock_call.return_value = ({
            "changes": [
                {"action_id": 1, "target_mismatch": "topic",
                 "description": "reframe intro",
                 "field_core_impact": "core_touching"},
            ],
            "unknowns": [], "confidence": "medium",
        }, MagicMock())
        rp = try_llm_rewrite_planner(_a(), _v(), _f(), _mm(), None, MagicMock())
        self.assertEqual(rp.semantic_status, SEMANTIC_STATUS_LLM_GROUNDED)
        self.assertEqual(len(rp.changes), 1)
        self.assertTrue(rp.requires_user_acceptance)


# ---------------- Citation: gaps/risks/tasks alternative keys ----------------

class TestCitationPlannerAlternativeKeys(unittest.TestCase):
    def _base_plan(self):
        return build_minimal_citation_plan(
            _a(), _v(), _f(), _mm(), None, None,
            bibliography_profile=None,
        )

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_gaps_instead_of_tradition_gaps(self, mock_call):
        mock_call.return_value = ({
            "gaps": ["postphenomenological turn missing"],
            "bridges": ["postphenomenology + russian tradition"],
            "unknowns": [],
            "confidence": "low",
        }, MagicMock())
        cp = upgrade_citation_plan_with_llm(
            self._base_plan(), _a(), _v(), None, MagicMock(),
        )
        self.assertGreater(len(cp.citation_gap_categories), 0)
        self.assertGreater(len(cp.missing_bridge_categories), 0)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_search_tasks_emitted_when_bibliography_missing(self, mock_call):
        mock_call.return_value = ({
            "tradition_gaps": ["gap1"],
            "source_work_tasks": [
                "Provide a bibliography section in the manuscript",
                "Build a primary-source set of 5 anchors",
            ],
            "unknowns": [], "confidence": "low",
        }, MagicMock())
        cp = upgrade_citation_plan_with_llm(
            self._base_plan(), _a(), _v(), None, MagicMock(),
        )
        # search_tasks should include the LLM-emitted source-work tasks
        joined = " ".join(cp.recommended_reference_search_tasks)
        self.assertIn("bibliography section", joined)
        self.assertIn("primary-source set", joined)


# ---------------- Rubric Cyrillic-ratio fallback ----------------

class TestRubricCyrillicGate(unittest.TestCase):
    def test_cyrillic_ratio_pure_russian(self):
        r = _cyrillic_ratio("Это русский текст о философии техники.")
        self.assertGreater(r, 0.8)

    def test_cyrillic_ratio_pure_english(self):
        self.assertLess(
            _cyrillic_ratio("This is plain English about philosophy of tech."),
            0.05,
        )

    def test_rubric_applies_to_russian_article_with_no_language(self):
        a = ArticleModel(
            title_current="Постфеноменологический подход",
            abstract_current="Статья о философии техники",
            problem_statement="Проблема технологического опосредования",
            language=None,  # modeler didn't detect
            genre_current="unknown",
        )
        self.assertTrue(rubric_applies_to_article(a))

    def test_rubric_does_not_apply_to_english_article(self):
        a = ArticleModel(
            title_current="Postphenomenological approach",
            abstract_current="Article on philosophy of technology",
            problem_statement="Technology mediation problem",
            language="en",
            genre_current="empirical",
        )
        self.assertFalse(rubric_applies_to_article(a))

    def test_rubric_applies_when_raw_text_cyrillic(self):
        a = ArticleModel(language=None, genre_current="unknown")
        self.assertTrue(
            rubric_applies_to_article(
                a, raw_article_text="Русский текст " * 100,
            ),
        )


# ---------------- Anti-fake survives all paths ----------------

class TestAntiFakeStillStripsRefs(unittest.TestCase):
    def _base_plan(self):
        return build_minimal_citation_plan(
            _a(), _v(), _f(), _mm(), None, None,
            bibliography_profile=None,
        )

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call")
    def test_doi_in_alternative_key_still_filtered(self, mock_call):
        mock_call.return_value = ({
            "gaps": [
                "safe gap category",                # safe
                "10.1234/example-doi",              # DOI → filtered
                "Smith 2024 reference",             # author-year → filtered
            ],
            "unknowns": [],
        }, MagicMock())
        cp = upgrade_citation_plan_with_llm(
            self._base_plan(), _a(), _v(), None, MagicMock(),
        )
        joined = " ".join(cp.citation_gap_categories)
        self.assertNotIn("10.1234", joined)
        self.assertNotIn("Smith 2024", joined)
        self.assertIn("safe gap category", joined)


if __name__ == "__main__":
    unittest.main()
