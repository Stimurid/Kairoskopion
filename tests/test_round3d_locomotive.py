"""Locomotive Round III-D tests.

Pins the new doctrine: every semantic organ output carries
attempt_diagnostics + rubric_sources. needs_llm fallback is never
silent. Schema relaxation does not let deterministic prose leak.
"""

from __future__ import annotations


def _ok_outcome(parsed_dict):
    """Round III-F outcome envelope mock helper."""
    from kairoskopion.agents.base_shell import LLMAttemptOutcome
    return LLMAttemptOutcome(
        ok=True, parsed=parsed_dict, content_present=True,
        parse_status="parsed_ok",
    )


import unittest
from unittest.mock import MagicMock, patch

from kairoskopion.schema import (
    ArticleModel,
    FitAssessment,
    MismatchMap,
    VenueModel,
)
from kairoskopion.services.citation_plan_minimal import (
    build_minimal_citation_plan,
)
from kairoskopion.services.llm_attempt_diagnostics import (
    FALLBACK_EXCEPTION,
    FALLBACK_PARSE_FAILED,
    FALLBACK_PROVIDER_UNAVAILABLE,
    PROVIDER_CALLED_OK,
    PROVIDER_NOT_CONFIGURED,
)
from kairoskopion.services.llm_semantic_organs import (
    try_llm_risk_officer,
    try_llm_rewrite_planner,
    upgrade_citation_plan_with_llm,
)
from kairoskopion.services.writing_rubric import load_rubric, rubric_id


def _a(): return ArticleModel(
    language="ru", genre_current="theoretical_essay",
    disciplinary_register_current="philosophy of technology",
)


def _v(): return VenueModel(
    canonical_name="V", venue_type="journal",
    scope_summary="Russian philosophy",
)


def _f(): return FitAssessment(axes=[], overall_label="possible")
def _mm(): return MismatchMap(mismatches=[
    {"axis": "topic", "severity": "major", "article_side": "X",
     "venue_side": "", "description": "", "possible_actions": [],
     "field_core_risk": "unknown_core_impact"},
])


# ----------- Diagnostics never silent -----------

class TestDiagnosticsAlwaysAttached(unittest.TestCase):
    def test_risk_provider_none_has_diagnostics(self):
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), None)
        self.assertEqual(rr.attempt_diagnostics["fallback_reason"],
                         FALLBACK_PROVIDER_UNAVAILABLE)
        self.assertEqual(rr.attempt_diagnostics["provider_status"],
                         PROVIDER_NOT_CONFIGURED)
        self.assertEqual(rr.attempt_diagnostics["agent_role"], "risk_officer")

    def test_rewrite_provider_none_has_diagnostics(self):
        rp = try_llm_rewrite_planner(_a(), _v(), _f(), _mm(), None, None)
        self.assertEqual(rp.attempt_diagnostics["fallback_reason"],
                         FALLBACK_PROVIDER_UNAVAILABLE)

    def test_citation_provider_none_has_diagnostics(self):
        cp = build_minimal_citation_plan(_a(), _v(), _f(), _mm(), None, None)
        cp2 = upgrade_citation_plan_with_llm(cp, _a(), _v(), None, None)
        self.assertEqual(cp2.attempt_diagnostics["fallback_reason"],
                         FALLBACK_PROVIDER_UNAVAILABLE)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_risk_exception_has_diagnostics(self, mock):
        mock.side_effect = RuntimeError("provider exploded")
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        self.assertEqual(rr.attempt_diagnostics["fallback_reason"],
                         FALLBACK_EXCEPTION)
        # Redacted error summary present, no raw stack trace
        self.assertIn("RuntimeError",
                      rr.attempt_diagnostics["redacted_error_summary"])
        flat = str(rr.attempt_diagnostics)
        self.assertNotIn("Traceback", flat)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_risk_parse_failed_has_diagnostics(self, mock):
        mock.return_value = None
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        self.assertEqual(
            rr.attempt_diagnostics["parse_status"], "schema_validation_failed",
        )

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_risk_success_diagnostics_show_called_ok(self, mock):
        mock.return_value = _ok_outcome({
            "risk_items": [{"risk_type": "scope_mismatch", "severity": "high",
                            "description": "X", "evidence": "fit_axes"}],
            "unknowns": [], "confidence": "medium",
        })
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        self.assertEqual(rr.attempt_diagnostics["provider_status"],
                         PROVIDER_CALLED_OK)
        self.assertEqual(rr.attempt_diagnostics["fallback_reason"], "none")


# ----------- Rewrite no-changes is explained -----------

class TestRewriteNoChangesExplained(unittest.TestCase):
    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_zero_actions_has_explicit_unknown(self, mock):
        mock.return_value = _ok_outcome({
            "overall_depth": "none", "actions": [],
            "unknowns": [], "confidence": "medium",
        })
        rp = try_llm_rewrite_planner(_a(), _v(), _f(), _mm(), None, MagicMock())
        joined = " ".join(rp.unknowns).lower()
        self.assertTrue(
            "returned no actions" in joined or "no rewrite" in joined,
            "Zero-actions rewrite must surface explicit reason in unknowns, "
            "not silently fall to needs_llm",
        )


# ----------- Citation safe-task path when bibliography missing -----------

class TestCitationSafeWhenBibliographyMissing(unittest.TestCase):
    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_bridges_and_gaps_populate_search_tasks(self, mock):
        mock.return_value = _ok_outcome({
            "tradition_match": "weak",
            "canonical_coverage": "missing",
            "bridge_references_needed": [
                "philosophy of technology recent debate markers",
                "russian tradition crossover with anglo-analytic",
            ],
            "tradition_gaps": ["postphenomenological turn references missing"],
            "risk_items": ["scope_mismatch_risk"],
            "unknowns": [], "confidence": "medium",
        })
        cp = build_minimal_citation_plan(_a(), _v(), _f(), _mm(), None, None)
        cp2 = upgrade_citation_plan_with_llm(cp, _a(), _v(), None, MagicMock())
        self.assertGreater(len(cp2.missing_bridge_categories), 0)
        self.assertGreater(len(cp2.recommended_reference_search_tasks), 0)
        self.assertIn("llm_citation_planner", cp2.created_from)

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_no_fake_doi_or_authoryear(self, mock):
        """DOIs filtered; author-year preserved (III-N fix)."""
        mock.return_value = _ok_outcome({
            "tradition_match": "weak",
            "bridge_references_needed": [
                "good category",
                "Smith 2024 paper",            # preserved (III-N)
                "https://doi.org/10.1234/x",   # DOI → filtered
            ],
            "unknowns": [], "confidence": "low",
        })
        cp = build_minimal_citation_plan(_a(), _v(), _f(), _mm(), None, None)
        cp2 = upgrade_citation_plan_with_llm(cp, _a(), _v(), None, MagicMock())
        joined = " ".join(cp2.missing_bridge_categories)
        self.assertIn("Smith 2024", joined)
        self.assertNotIn("10.1234", joined)


# ----------- Rubric integration -----------

class TestRubricIntegration(unittest.TestCase):
    def test_rubric_loads_and_marks_non_venue(self):
        r = load_rubric()
        self.assertIsNotNone(r)
        self.assertTrue(r["not_a_venue_profile"])
        self.assertTrue(r["not_journal_policy"])

    @patch("kairoskopion.services.llm_semantic_organs.try_llm_call_with_outcome")
    def test_rubric_active_records_as_source_on_llm_grounded(self, mock):
        mock.return_value = _ok_outcome({
            "risk_items": [{"risk_type": "scope_mismatch", "severity": "high",
                            "description": "X", "evidence": "fit"}],
            "unknowns": [], "confidence": "low",
        })
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), MagicMock())
        # Russian + philosophy → rubric should apply
        self.assertIn(rubric_id(), rr.rubric_sources)
        self.assertTrue(rr.attempt_diagnostics.get("rubric_active"))

    def test_rubric_does_not_apply_to_non_russian_non_phil(self):
        en_article = ArticleModel(language="en", genre_current="empirical",
                                  disciplinary_register_current="medicine")
        from kairoskopion.services.writing_rubric import rubric_applies_to_article
        self.assertFalse(rubric_applies_to_article(en_article))


# ----------- Schema relaxation does not let deterministic prose in -----------

class TestSchemaRelaxationDoctrine(unittest.TestCase):
    def test_no_deterministic_prose_in_provider_unavailable_output(self):
        rr = try_llm_risk_officer(_a(), _v(), None, _f(), _mm(), None)
        # Risk items empty, no semantic prose emitted by code
        self.assertEqual(rr.risk_items, [])
        self.assertEqual(rr.semantic_status, "needs_llm")
        # field_origins all=needs_llm (Round II-B placeholder doctrine)
        for f in ("risk_items", "blocking_risks", "warnings",
                  "overall_risk_label"):
            self.assertEqual(rr.field_origins.get(f), "needs_llm")


if __name__ == "__main__":
    unittest.main()
