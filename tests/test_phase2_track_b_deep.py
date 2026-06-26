"""Phase 2: Track B Deep — VenueProfilePackage, compliance, submission pack API."""

from __future__ import annotations

import unittest

from kairoskopion.api.cases import Case, _case_to_snapshot, _case_from_snapshot
from kairoskopion.schema import VenueModel, ArticleModel, PublicationRegimeModel


def _make_venue_case() -> Case:
    """Case with a venue already investigated."""
    case = Case(case_id="test_p2", user_id="u1")
    text = "Philosophy journal about continental philosophy and STS. " * 20
    case.investigate_venue(text)
    return case


def _make_full_case() -> Case:
    """Case with both article and venue."""
    case = Case(case_id="test_p2_full", user_id="u1")
    article_text = "This article examines the philosophy of technology. " * 50
    case.intake_text(article_text, input_type="article")
    venue_text = "A journal devoted to continental philosophy. " * 20
    case.investigate_venue(venue_text)
    return case


class TestEnrichVenue(unittest.TestCase):
    """2.1–2.6: enrich-venue builds VenueProfilePackage."""

    def test_enrich_no_venue_returns_error(self):
        case = Case(case_id="test_ev", user_id="u1")
        result = case.enrich_venue()
        self.assertEqual(result["status"], "no_venue")

    def test_enrich_builds_package(self):
        case = _make_venue_case()
        result = case.enrich_venue()
        self.assertEqual(result["status"], "ok")
        self.assertIn("venue_profile_package", result)
        self.assertIsNotNone(case.venue_profile_package)

    def test_enrich_completeness_has_identity(self):
        case = _make_venue_case()
        case.enrich_venue()
        completeness = case.venue_profile_package.completeness
        self.assertIn("VenueIdentity", completeness)

    def test_enrich_wires_venue_field_position(self):
        case = _make_venue_case()
        case.enrich_venue()
        vpkg = case.venue_profile_package
        if case.venue_field_position:
            self.assertEqual(
                vpkg.venue_field_position_id,
                case.venue_field_position.field_position_id,
            )
            self.assertEqual(vpkg.completeness["VenueFieldPosition"], "present")

    def test_enrich_wires_publication_regime(self):
        case = _make_venue_case()
        case.enrich_venue()
        vpkg = case.venue_profile_package
        if case.publication_regime:
            self.assertEqual(
                vpkg.publication_regime_id,
                case.publication_regime.publication_regime_id,
            )
            self.assertEqual(vpkg.completeness["FormalSubmissionProfile"], "present")

    def test_enrich_offline_mode_no_corpus(self):
        case = _make_venue_case()
        self.assertEqual(case.adapter_mode, "offline_stub")
        case.enrich_venue()
        vpkg = case.venue_profile_package
        self.assertEqual(vpkg.completeness.get("PublishedCorpusHull", "missing"), "missing")


class TestGetVenueProfilePackage(unittest.TestCase):
    def test_not_built_returns_hint(self):
        case = Case(case_id="test_gvpp", user_id="u1")
        result = case.get_venue_profile_package()
        self.assertEqual(result["status"], "not_built")

    def test_returns_package_after_enrich(self):
        case = _make_venue_case()
        case.enrich_venue()
        result = case.get_venue_profile_package()
        self.assertIn("venue_profile_package_id", result)


class TestCompliance(unittest.TestCase):
    def test_compliance_not_ready_no_article(self):
        case = _make_venue_case()
        result = case.get_compliance()
        self.assertEqual(result["status"], "not_ready")

    def test_compliance_builds_with_article_and_venue(self):
        case = _make_full_case()
        result = case.get_compliance()
        self.assertIn("compliance_checklist_id", result)

    def test_compliance_cached_on_second_call(self):
        case = _make_full_case()
        r1 = case.get_compliance()
        r2 = case.get_compliance()
        self.assertEqual(r1["compliance_checklist_id"], r2["compliance_checklist_id"])


class TestSubmissionPackAPI(unittest.TestCase):
    def test_not_ready_without_article(self):
        case = Case(case_id="test_sp", user_id="u1")
        result = case.build_submission_pack_api()
        self.assertEqual(result["status"], "not_ready")

    def test_builds_with_article_and_venue(self):
        case = _make_full_case()
        result = case.build_submission_pack_api()
        self.assertIn("submission_pack_id", result)

    def test_pack_has_readiness_status(self):
        case = _make_full_case()
        result = case.build_submission_pack_api()
        self.assertIn("ready_status", result)


class TestPhase2Persistence(unittest.TestCase):
    def test_venue_profile_package_roundtrip(self):
        case = _make_venue_case()
        case.enrich_venue()
        snap = _case_to_snapshot(case)
        restored = _case_from_snapshot(snap)
        self.assertIsNotNone(restored.venue_profile_package)
        self.assertEqual(
            restored.venue_profile_package.venue_profile_package_id,
            case.venue_profile_package.venue_profile_package_id,
        )


if __name__ == "__main__":
    unittest.main()
