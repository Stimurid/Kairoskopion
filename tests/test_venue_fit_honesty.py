"""Tests for the 10 small/high-leverage fixes shipped in
feature/real-cockpit-venue-fit-pass.

Track B (venue path):
- F1: _detect_regime returns None on unknown text, builds unknown into
      regime + unknowns list.
- F2: venue confidence requires both meaningful aims/scope AND name.
- F3: investigate_venue rejects text < 200 chars with needs_more_venue_text.
- F4: venue_type derived from regime; conference text → VenueType.CONFERENCE.
- F5: response surfaces venue_field_position + used_llm.

Track D (heuristic honesty):
- D1: _extract_*_policy honor negation ("we do NOT provide open access"
      no longer claims open_access).
- D2: mismatch_mapping emits empty venue_side + explicit unknown
      instead of literal "Venue expectation on {axis}" placeholder.
- D3: _assess_discipline_fit uses token equality with min length 4;
      "art" no longer matches "cartography".
- D4: _assess_regime_fit returns "unknown" unless adapter says
      type="journal"; works_count alone is no longer "likely".
- D5: _detect_bridge_references requires ≥2 discipline tokens AND
      ≥6-char tokens; common-word false positives suppressed.
"""

from __future__ import annotations

import importlib
import os
import shutil
import tempfile
import unittest


# ---------------------------------------------------------------------------
# Track B
# ---------------------------------------------------------------------------


class TestRegimeDetectorHonesty(unittest.TestCase):
    def test_unknown_text_returns_none(self):
        from kairoskopion.services.venue_profiling import _detect_regime
        self.assertIsNone(_detect_regime("Just some random journal text."))

    def test_special_issue_detected(self):
        from kairoskopion.services.venue_profiling import _detect_regime
        from kairoskopion.enums import RegimeType
        self.assertEqual(
            _detect_regime("Submit to our SPECIAL ISSUE on AI"),
            RegimeType.SPECIAL_ISSUE_ARTICLE.value,
        )

    def test_conference_proceedings_detected(self):
        from kairoskopion.services.venue_profiling import _detect_regime
        from kairoskopion.enums import RegimeType
        self.assertEqual(
            _detect_regime("Annual Conference Proceedings 2025"),
            RegimeType.CONFERENCE_PROCEEDINGS.value,
        )

    def test_mega_journal_detected(self):
        from kairoskopion.services.venue_profiling import _detect_regime
        from kairoskopion.enums import RegimeType
        self.assertEqual(
            _detect_regime("This mega-journal covers all of science"),
            RegimeType.MEGA_JOURNAL.value,
        )


class TestVenueModelConfidenceAndType(unittest.TestCase):
    def test_short_scope_low_confidence(self):
        from kairoskopion.services.venue_profiling import build_venue_model
        # Below the 200-char meaningful-scope floor
        text = "# Journal of X\n**Publisher:** Y\n## Aims and Scope\nShort."
        venue, _regime = build_venue_model(text)
        self.assertEqual(venue.confidence, "low")

    def test_meaningful_scope_and_name_medium(self):
        from kairoskopion.services.venue_profiling import build_venue_model
        scope = "About the journal. " * 30  # >200 chars
        text = f"# Journal of X\n**Publisher:** Y\n## Aims and Scope\n{scope}"
        venue, _regime = build_venue_model(text)
        self.assertEqual(venue.confidence, "medium")

    def test_meaningful_scope_no_name_still_low(self):
        from kairoskopion.services.venue_profiling import build_venue_model
        scope = "About the journal. " * 30
        text = f"## Aims and Scope\n{scope}"  # no # Title line
        venue, _regime = build_venue_model(text)
        self.assertEqual(venue.confidence, "low")

    def test_conference_text_yields_conference_venue_type(self):
        from kairoskopion.services.venue_profiling import build_venue_model
        from kairoskopion.enums import VenueType
        scope = "About the conference. " * 30
        text = (
            "# ACM Symposium 2025\n**Publisher:** ACM\n"
            f"## Aims and Scope\n{scope}\nWe publish conference proceedings."
        )
        venue, _ = build_venue_model(text)
        self.assertEqual(venue.venue_type, VenueType.CONFERENCE_PROCEEDINGS.value)

    def test_unknown_regime_in_unknowns(self):
        from kairoskopion.services.venue_profiling import build_venue_model
        scope = "Generic journal content. " * 30
        text = f"# J. of X\n**Publisher:** Y\n## Aims and Scope\n{scope}"
        venue, regime = build_venue_model(text)
        self.assertIsNone(regime.regime_type)
        self.assertTrue(any("publication regime" in u for u in venue.unknowns))


class TestInvestigateVenueMinimumGuard(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="kairon_venue_guard_")
        os.environ["KAIROSKOPION_DATA_DIR"] = self._tmpdir
        os.environ["KAIROSKOPION_LLM_PROVIDER"] = "none"
        from kairoskopion.api import auth as auth_mod
        auth_mod.reset_stores_for_tests(self._tmpdir)
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("KAIROSKOPION_DATA_DIR", None)
        os.environ.pop("KAIROSKOPION_LLM_PROVIDER", None)

    def test_short_text_returns_needs_more_venue_text(self):
        from kairoskopion.api.cases import Case
        case = Case(title="test")
        result = case.investigate_venue("Journal of X")
        self.assertEqual(result["status"], "needs_more_venue_text")
        self.assertIn("min_chars", result)
        self.assertIn("hint", result)
        self.assertIsNone(case.investigated_venue)

    def test_meaningful_text_runs_pipeline(self):
        from kairoskopion.api.cases import Case
        case = Case(title="test")
        text = (
            "# Journal of X\n**Publisher:** Y\n## Aims and Scope\n"
            + ("This journal covers the philosophy of technology. " * 20)
        )
        result = case.investigate_venue(text)
        self.assertNotIn("status", result)
        self.assertIn("venue", result)
        self.assertIn("used_llm", result)
        self.assertFalse(result["used_llm"])  # no provider configured
        self.assertIn("venue_field_position", result)
        self.assertIsNotNone(case.investigated_venue)


# ---------------------------------------------------------------------------
# Track D
# ---------------------------------------------------------------------------


class TestNegationGuardOnPolicies(unittest.TestCase):
    def test_open_access_negated(self):
        from kairoskopion.services.venue_profiling import _extract_open_access
        # Negation
        self.assertIsNone(_extract_open_access(
            "this journal does not provide open access to its content"))
        # Plain
        self.assertEqual(_extract_open_access(
            "this is an open access journal"), "open_access")

    def test_anonymization_negated(self):
        from kairoskopion.services.venue_profiling import _extract_anonymization
        self.assertIsNone(_extract_anonymization(
            "we do not use double-blind review"))
        self.assertEqual(_extract_anonymization(
            "all submissions undergo double-blind review"), "double_blind")

    def test_data_policy_negated(self):
        from kairoskopion.services.venue_profiling import _extract_data_policy
        self.assertIsNone(_extract_data_policy(
            "authors are not required to provide data availability statements"))
        self.assertEqual(_extract_data_policy(
            "all manuscripts must include a data availability statement"),
            "data_policy_present")

    def test_ai_policy_negated(self):
        from kairoskopion.services.venue_profiling import _extract_ai_policy
        self.assertIsNone(_extract_ai_policy(
            "we do not require ai disclosure from authors"))
        self.assertEqual(_extract_ai_policy(
            "authors must provide ai disclosure"), "ai_policy_present")

    def test_ethics_negated(self):
        from kairoskopion.services.venue_profiling import _extract_ethics_policy
        self.assertIsNone(_extract_ethics_policy(
            "we don't require ethics approval for theoretical work"))
        self.assertEqual(_extract_ethics_policy(
            "submissions require ethics approval"),
            "ethics_policy_present")


class TestMismatchVenueSidePlaceholderRemoved(unittest.TestCase):
    def test_venue_side_is_empty_not_placeholder(self):
        from kairoskopion.services.mismatch_mapping import build_mismatch_map
        from kairoskopion.schema import FitAssessment

        fa = FitAssessment(
            fit_assessment_id="fa_test",
            article_model_id="art",
            venue_model_id="ven",
            submission_scenario_id="scn",
            overall_label="possible_but_costly",
            axes=[
                {"axis": "topic", "value": "weak",
                 "notes": "Article uses concept X", "evidence_refs": []},
                {"axis": "method", "value": "bad",
                 "notes": "Article is conceptual", "evidence_refs": []},
            ],
            recommendation="ok",
            unknowns=[],
        )
        mm = build_mismatch_map(fa)
        # No placeholder string anywhere
        for m in mm.mismatches:
            self.assertEqual(m["venue_side"], "")
            self.assertNotIn("Venue expectation on", m["venue_side"])
        # Honest unknown per missing venue_side
        self.assertTrue(any(
            "venue-side description not available" in u for u in mm.unknowns
        ))


class TestDisciplineFitTokenEquality(unittest.TestCase):
    def test_substring_false_positive_blocked(self):
        # "art" used to match "cartography" via substring
        from kairoskopion.services.venue_candidate_screening import (
            _assess_discipline_fit,
        )
        candidate = {
            "discovery_reasons": [],
            "raw_adapter_data": {
                "openalex": {"topics": ["cartography"]},
            },
        }
        profile = {"disciplinary_registers": ["art"]}
        # "art" is 3 chars → below min length 4 → won't match anyway,
        # but the broader fix is token-equality. Use a longer false-match.
        result = _assess_discipline_fit(candidate, profile, [])
        self.assertEqual(result, "unknown")

    def test_substring_false_positive_with_longer_tokens_blocked(self):
        # "tech" should NOT match "technology studies" via raw substring
        # under the new token-equality rule (whole-word match).
        from kairoskopion.services.venue_candidate_screening import (
            _assess_discipline_fit,
        )
        candidate = {
            "discovery_reasons": [],
            "raw_adapter_data": {
                "openalex": {"topics": ["catechism"]},
            },
        }
        profile = {"disciplinary_registers": ["tech"]}
        # "tech" alone is 4 chars but "catechism" tokens are {"catechism"};
        # no equality → unknown.
        result = _assess_discipline_fit(candidate, profile, [])
        self.assertEqual(result, "unknown")

    def test_real_token_overlap_still_matches(self):
        from kairoskopion.services.venue_candidate_screening import (
            _assess_discipline_fit,
        )
        candidate = {
            "discovery_reasons": [],
            "raw_adapter_data": {
                "openalex": {"topics": ["philosophy technology"]},
            },
        }
        profile = {"disciplinary_registers": ["philosophy technology"]}
        result = _assess_discipline_fit(candidate, profile, [])
        self.assertEqual(result, "match")


class TestRegimeFitHonest(unittest.TestCase):
    def test_works_count_alone_is_unknown(self):
        from kairoskopion.services.venue_candidate_screening import (
            _assess_regime_fit,
        )
        candidate = {}
        raw_data = {"openalex": {"works_count": 12345}}
        # Previously returned "likely"; now should return "unknown".
        self.assertEqual(_assess_regime_fit(candidate, raw_data), "unknown")

    def test_journal_type_still_likely(self):
        from kairoskopion.services.venue_candidate_screening import (
            _assess_regime_fit,
        )
        candidate = {}
        raw_data = {"openalex": {"type": "journal", "works_count": 12345}}
        self.assertEqual(_assess_regime_fit(candidate, raw_data), "likely")

    def test_no_info_is_unknown(self):
        from kairoskopion.services.venue_candidate_screening import (
            _assess_regime_fit,
        )
        self.assertEqual(_assess_regime_fit({}, {}), "unknown")


class TestBridgeReferencesTightened(unittest.TestCase):
    def test_single_word_overlap_no_longer_bridges(self):
        from kairoskopion.services.citation_ecology import (
            _detect_bridge_references,
        )
        from kairoskopion.schema import (
            ArticleModel, VenueModel, BibliographyProfile,
        )

        article = ArticleModel(
            article_model_id="art",
            disciplinary_register_current="social epistemology",
        )
        venue = VenueModel(
            venue_model_id="ven",
            scope_summary="social sciences research",
        )
        bib = BibliographyProfile(
            bibliography_profile_id="bib",
            total_references=2,
            references=[
                {"raw_text": "Smith. Social media studies. 2010",
                 "author_fragment": "Smith", "year": "2010",
                 "venue_fragment": ""},
                {"raw_text": "Jones. Cooking recipes. 2010",
                 "author_fragment": "Jones", "year": "2010",
                 "venue_fragment": ""},
            ],
        )
        bridges = _detect_bridge_references(bib, article, venue)
        # Old logic: "social" matched both — Smith returned.
        # New logic: requires ≥2 discipline tokens (≥6-char) overlap;
        # "social" is 6 chars OK, "epistemology" 12 chars OK, but
        # neither reference contains BOTH; also venue tokens require
        # ≥6 chars ("social" + "sciences" + "research").
        self.assertEqual(bridges, [])


if __name__ == "__main__":
    unittest.main()
