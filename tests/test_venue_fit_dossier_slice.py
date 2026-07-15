"""Tests for the venue-fit dossier vertical slice."""

from __future__ import annotations

import importlib
import os
import shutil
import tempfile
import unittest


def _meaningful_venue_text(name: str = "Journal of X") -> str:
    return (
        f"# {name}\n"
        "**Publisher:** Test Press\n"
        "**ISSN:** 1234-5678\n"
        "\n"
        "## Aims and Scope\n"
        "The journal publishes peer-reviewed theoretical and conceptual "
        "research on the philosophy of technology, postphenomenology, "
        "and STS. Authors should address both technical and philosophical "
        "dimensions of their work. We accept theoretical essays and "
        "conceptual articles spanning multiple disciplinary registers.\n"
        "\n"
        "## Article Types\n"
        "- Research Article (8000–12000 words)\n"
        "- Theoretical Essay (6000–9000 words)\n"
        "\n"
        "## Review Process\nDouble-blind peer review.\n"
        "## Language\nEnglish.\n"
    )


class TestScenarioPreliminaryFlag(unittest.TestCase):
    """When fit runs without operator-provided scenario, the synthesized
    SubmissionScenario must be marked scenario_preliminary=True."""

    def test_scenario_preliminary_default_false(self):
        from kairoskopion.schema import SubmissionScenario
        s = SubmissionScenario(article_model_id="art_x")
        self.assertFalse(s.scenario_preliminary)

    def test_scenario_preliminary_round_trip(self):
        from kairoskopion.schema import SubmissionScenario
        s = SubmissionScenario(
            article_model_id="art_x", scenario_preliminary=True,
            unknowns=["operator pending"],
        )
        d = s.to_dict()
        self.assertTrue(d["scenario_preliminary"])
        restored = SubmissionScenario.from_dict(d)
        self.assertTrue(restored.scenario_preliminary)


class TestSelectInvestigatedVenue(unittest.TestCase):
    """select_venue must accept investigated_venue, not only pool venues."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="kairon_dossier_")
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

    def _set_venue(self, case):
        """ARCH-SEM-001: set venue directly instead of investigate_venue."""
        from kairoskopion.schema import VenueModel
        case.investigated_venue = VenueModel(
            canonical_name="Journal of X",
            scope_summary="Philosophy of technology, postphenomenology, STS",
        )

    def test_select_investigated_token(self):
        from kairoskopion.api.cases import Case
        case = Case(title="t")
        case.intake_text("Article body. " * 60, input_type="article")
        self.assertIsNotNone(case.article_model)
        self._set_venue(case)
        self.assertIsNotNone(case.investigated_venue)
        result = case.select_venue("investigated")
        self.assertEqual(case.selected_venue, case.investigated_venue)
        self.assertEqual(result["selected_venue_id"], "investigated")
        self.assertTrue(result["fit_available"])
        self.assertIsNotNone(case.fit_assessment)

    def test_select_investigated_by_real_venue_id(self):
        from kairoskopion.api.cases import Case
        case = Case(title="t")
        case.intake_text("Article body. " * 60, input_type="article")
        self._set_venue(case)
        real_id = case.investigated_venue.venue_model_id
        result = case.select_venue(real_id)
        self.assertEqual(case.selected_venue, case.investigated_venue)
        self.assertTrue(result["fit_available"])


class TestFitChainSynthesizesPreliminaryScenario(unittest.TestCase):
    def test_preliminary_scenario_marker_set(self):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import VenueModel
        case = Case(title="t")
        case.intake_text("Article body. " * 60, input_type="article")
        case.investigated_venue = VenueModel(
            canonical_name="Journal of X",
            scope_summary="Philosophy of technology, postphenomenology, STS",
        )
        case.select_venue("investigated")
        self.assertIsNotNone(case.fit_assessment)
        self.assertIsNotNone(case.risk_report)


class TestVenueStatusInIntakeResult(unittest.TestCase):
    """intake_text now surfaces venue_status / venue_hint when the venue
    pipeline returned needs_more_venue_text."""

    def test_short_venue_text_surfaces_status(self):
        from kairoskopion.api.cases import Case
        case = Case(title="t")
        result = case.intake_text(
            "Journal of X",  # < 200 chars
            input_type="journal_or_venue",
        )
        self.assertEqual(result.get("venue_status"), "needs_more_venue_text")
        self.assertIn("venue_hint", result)
        self.assertIn("venue_min_chars", result)
        self.assertEqual(result["venue_min_chars"], 200)

    def test_meaningful_venue_text_without_llm(self):
        """ARCH-SEM-001: without LLM, venue investigation returns llm_required."""
        from kairoskopion.api.cases import Case
        case = Case(title="t")
        result = case.intake_text(
            _meaningful_venue_text(),
            input_type="journal_or_venue",
        )
        self.assertNotIn("venue_status", result)
        self.assertIsNone(result.get("venue_used_llm"))
        self.assertFalse(result["venue_investigated"])


class TestRiskReportPopulatedByFitChain(unittest.TestCase):
    def test_risk_report_built(self):
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import VenueModel
        case = Case(title="t")
        case.intake_text("Article body. " * 60, input_type="article")
        case.investigated_venue = VenueModel(
            canonical_name="Journal of X",
            scope_summary="Philosophy of technology, postphenomenology, STS",
        )
        case.select_venue("investigated")
        self.assertIsNotNone(case.risk_report)


class TestAntiLeakInDossierSlice(unittest.TestCase):
    """No raw output / Traceback in any new field."""

    def test_no_leak_in_intake_result(self):
        import json
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import VenueModel
        case = Case(title="t")
        case.intake_text("Article body. " * 60, input_type="article")
        case.investigated_venue = VenueModel(
            canonical_name="Journal of X",
            scope_summary="Philosophy of technology",
        )
        result = case.select_venue("investigated")
        blob = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("Traceback", blob)
        self.assertNotIn("raw_output_ref", blob)


class TestDossierAPI(unittest.TestCase):
    """End-to-end dossier endpoint over FastAPI."""

    def setUp(self):
        from fastapi.testclient import TestClient
        self._tmpdir = tempfile.mkdtemp(prefix="kairon_dossier_api_")
        os.environ["KAIROSKOPION_DATA_DIR"] = self._tmpdir
        os.environ["KAIROSKOPION_LLM_PROVIDER"] = "none"
        from kairoskopion.api import auth as auth_mod
        auth_mod.reset_stores_for_tests(self._tmpdir)
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)
        auth_mod.reset_stores_for_tests(self._tmpdir)
        self.client = TestClient(app_mod.app)
        self.token = self.client.post(
            "/auth/signup", json={"display_name": "dossier_test", "email": None},
        ).json()["session_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("KAIROSKOPION_DATA_DIR", None)
        os.environ.pop("KAIROSKOPION_LLM_PROVIDER", None)

    def test_dossier_after_full_chain(self):
        """ARCH-SEM-001: venue is set directly since investigate_venue requires LLM."""
        from kairoskopion.api import app as app_mod
        from kairoskopion.schema import VenueModel

        case_resp = self.client.post(
            "/cases", json={"title": "dossier-chain"}, headers=self.headers,
        ).json()
        cid = case_resp["case_id"]
        # 1. intake article
        self.client.post(
            f"/cases/{cid}/intake/text",
            json={"text": "Article body. " * 60, "input_type": "article"},
            headers=self.headers,
        )
        # 2. set venue directly (investigate_venue requires LLM)
        case = app_mod.store.get(cid)
        case.investigated_venue = VenueModel(
            canonical_name="Journal of X",
            scope_summary="Philosophy of technology, postphenomenology, STS",
        )
        app_mod.store.save(case)
        # 3. select investigated venue
        r2 = self.client.post(
            f"/cases/{cid}/select-venue/investigated",
            headers=self.headers,
        )
        self.assertEqual(r2.status_code, 200)
        body = r2.json()
        self.assertTrue(body["fit_available"])

        # 4. dossier
        d = self.client.get(f"/cases/{cid}/dossier", headers=self.headers)
        self.assertEqual(d.status_code, 200)
        dossier = d.json()
        self.assertIsNotNone(dossier.get("selected_venue"))
        self.assertIsNotNone(dossier.get("fit_assessment"))
        self.assertIsNotNone(dossier.get("risk_report"))

        import json
        blob = json.dumps(dossier, ensure_ascii=False)
        self.assertNotIn("Traceback", blob)


if __name__ == "__main__":
    unittest.main()
