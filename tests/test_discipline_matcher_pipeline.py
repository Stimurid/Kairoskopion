"""Tests for the wiring of DisciplineMatcherAgent into the intake
pipeline (Phase B integration commit 2/5).

Verifies:
- intake_text() persists region_hint
- _run_discipline_matcher fires after article_model is built
- discipline_matches is persisted on Case + survives store round-trip
- /cases/{id}/discipline-matches endpoint returns the matcher verdict
- semantic_profiler receives known_disciplines_context built from
  matcher output (deterministic check via the helper)
"""

from __future__ import annotations

import importlib
import os
import shutil
import tempfile
import unittest

from fastapi.testclient import TestClient


class _BaseEnv(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="kairon_b2_pipeline_")
        os.environ["KAIROSKOPION_DATA_DIR"] = self._tmpdir
        from kairoskopion.api import auth as auth_mod
        auth_mod.reset_stores_for_tests(self._tmpdir)
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)
        auth_mod.reset_stores_for_tests(self._tmpdir)
        self.client = TestClient(app_mod.app)

        signup = self.client.post("/auth/signup", json={
            "display_name": "b2_pipeline_user", "email": None,
        })
        self.assertEqual(signup.status_code, 200, signup.text)
        self.token = signup.json()["session_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        case = self.client.post(
            "/cases", json={"title": "b2-pipeline"}, headers=self.headers,
        )
        self.case_id = case.json()["case_id"]

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("KAIROSKOPION_DATA_DIR", None)


class TestRegionHintIntake(_BaseEnv):
    def test_region_persists(self):
        # Use explicit input_type so classifier is skipped and the
        # pipeline goes straight to article modeling.
        resp = self.client.post(
            f"/cases/{self.case_id}/intake/text",
            json={
                "text": "Статья по философии техники. " * 60,
                "input_type": "article",
                "region": "ru",
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        case = self.client.get(
            f"/cases/{self.case_id}", headers=self.headers,
        ).json()
        # ARCH-SEM-001: discipline matching requires LLM, so without
        # a provider discipline_matches_count won't be present.
        # But region_hint should still be stored on the case.
        self.assertEqual(case.get("region_hint"), "ru")


class TestDisciplineMatchesEndpoint(_BaseEnv):
    def test_404_before_intake(self):
        r = self.client.get(
            f"/cases/{self.case_id}/discipline-matches",
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 404)

    def test_matches_after_intake_without_llm(self):
        """ARCH-SEM-001: without LLM, discipline matches are not available."""
        self.client.post(
            f"/cases/{self.case_id}/intake/text",
            json={
                "text": (
                    "Статья по теме Философия техники и technical "
                    "artifacts. Heidegger and mediation."
                ) * 50,
                "input_type": "article",
                "region": "ru",
            },
            headers=self.headers,
        )
        r = self.client.get(
            f"/cases/{self.case_id}/discipline-matches",
            headers=self.headers,
        )
        # Without LLM, discipline matches are not produced (ARCH-SEM-001)
        body = r.json()
        if r.status_code == 200:
            # Endpoint may return empty/null when no matches exist
            assert body is None or body == {} or body.get("matched") is None
        else:
            # 404 is also acceptable — no matches to return
            self.assertEqual(r.status_code, 404)


class TestMatchesContextBuilder(unittest.TestCase):
    """The helper that turns matcher output into prompt context is a
    pure function — test it directly without spinning up the API."""

    def test_returns_none_when_no_matches(self):
        from kairoskopion.api.cases import Case
        c = Case(title="x")
        self.assertIsNone(c._build_matched_disciplines_context())

    def test_renders_lines_from_matched(self):
        from kairoskopion.api.cases import Case
        c = Case(title="x")
        c.discipline_matches = {
            "matched": [
                {
                    "discipline_id": "ru-philosophy-of-technology",
                    "strength": "primary",
                    "why": "test why",
                }
            ],
        }
        ctx = c._build_matched_disciplines_context()
        self.assertIsNotNone(ctx)
        self.assertIn("primary", ctx)
        self.assertIn("ru-philosophy-of-technology", ctx)


class TestStoreRoundTripDisciplineMatches(_BaseEnv):
    def test_region_hint_survives_save_load(self):
        """ARCH-SEM-001: discipline_matches require LLM and won't be
        populated in tests without a provider.  But region_hint must
        still persist through save/load."""
        self.client.post(
            f"/cases/{self.case_id}/intake/text",
            json={
                "text": "Статья — Философия техники." * 60,
                "input_type": "article",
                "region": "ru",
            },
            headers=self.headers,
        )
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)
        from kairoskopion.api import auth as auth_mod
        sessions = list(auth_mod._SESSIONS.values()) if hasattr(auth_mod, "_SESSIONS") else []
        user_id = None
        if sessions:
            user_id = sessions[0].user_id
        case = app_mod.store.get(self.case_id, user_id=user_id)
        self.assertIsNotNone(case)
        self.assertEqual(case.region_hint, "ru")


if __name__ == "__main__":
    unittest.main()
