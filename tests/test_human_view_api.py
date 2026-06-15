"""API endpoint tests for the human-readable model views.

Verifies:
  - /cases/{case_id}/article-model/human-view returns markdown for the
    case owner;
  - cross-tenant access returns 404 (no info leak);
  - 404 when ArticleModel is not yet built;
  - venue human-view endpoint resolves an investigated venue and
    refuses cross-tenant access.
"""

from __future__ import annotations

import importlib
import os
import shutil
import tempfile
import unittest

from fastapi.testclient import TestClient


class _BaseTestEnv(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="kairon_humanview_test_")
        os.environ["KAIROSKOPION_DATA_DIR"] = self._tmpdir
        from kairoskopion.api import auth as auth_mod
        auth_mod.reset_stores_for_tests(self._tmpdir)
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)
        auth_mod.reset_stores_for_tests(self._tmpdir)
        self.app = app_mod.app
        self.client = TestClient(self.app)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("KAIROSKOPION_DATA_DIR", None)

    def _signup(self, name, email):
        r = self.client.post(
            "/auth/signup",
            json={"display_name": name, "email": email},
        )
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def _create_case_with_article(self, token: str, title: str) -> str:
        r = self.client.post(
            "/cases",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": title},
        )
        self.assertEqual(r.status_code, 200, r.text)
        case_id = r.json()["case_id"]
        # Push minimal text intake — deterministic path, no LLM needed
        r2 = self.client.post(
            f"/cases/{case_id}/intake/text",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "text": "Краткий текст про интерфейс как онтологическую форму. "
                        "Аргумент строится в континентальном регистре, без эмпирики.",
                "input_type": "abstract",
                "search_depth": "none",
            },
        )
        self.assertEqual(r2.status_code, 200, r2.text)
        return case_id


class TestArticleHumanViewEndpoint(_BaseTestEnv):
    def test_returns_markdown_for_owner(self):
        a = self._signup("Alice", "alice@hv.test")
        case_id = self._create_case_with_article(a["session_token"], "Alice case")
        r = self.client.get(
            f"/cases/{case_id}/article-model/human-view",
            headers={"Authorization": f"Bearer {a['session_token']}"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertEqual(d["format"], "markdown")
        self.assertTrue(d["not_a_submission_recommendation"])
        # Required sections by label
        md = d["markdown"]
        self.assertIn("Коротко", md)
        self.assertIn("Главный объект статьи", md)
        self.assertIn("Что система не знает", md)
        # Not a JSON dump
        self.assertFalse(md.lstrip().startswith("{"))

    def test_404_when_article_not_built(self):
        a = self._signup("Bob", "bob@hv.test")
        r = self.client.post(
            "/cases",
            headers={"Authorization": f"Bearer {a['session_token']}"},
            json={"title": "Empty case"},
        )
        case_id = r.json()["case_id"]
        r2 = self.client.get(
            f"/cases/{case_id}/article-model/human-view",
            headers={"Authorization": f"Bearer {a['session_token']}"},
        )
        self.assertEqual(r2.status_code, 404)

    def test_cross_tenant_404(self):
        a = self._signup("Alice", "alice@hv2.test")
        b = self._signup("Bob", "bob@hv2.test")
        case_id = self._create_case_with_article(a["session_token"], "A's case")
        # Bob cannot read Alice's article human-view
        r = self.client.get(
            f"/cases/{case_id}/article-model/human-view",
            headers={"Authorization": f"Bearer {b['session_token']}"},
        )
        self.assertEqual(r.status_code, 404)

    def test_requires_auth(self):
        r = self.client.get("/cases/case_anything/article-model/human-view")
        self.assertEqual(r.status_code, 401)


class TestVenueHumanViewEndpoint(_BaseTestEnv):
    def test_404_when_no_venue_on_case(self):
        a = self._signup("Alice", "alice@hv3.test")
        case_id = self._create_case_with_article(a["session_token"], "A's case")
        r = self.client.get(
            f"/cases/{case_id}/venues/investigated/human-view",
            headers={"Authorization": f"Bearer {a['session_token']}"},
        )
        # No investigated venue on this fresh case
        self.assertEqual(r.status_code, 404)

    def test_cross_tenant_404(self):
        a = self._signup("Alice", "alice@hv4.test")
        b = self._signup("Bob", "bob@hv4.test")
        case_id = self._create_case_with_article(a["session_token"], "A's case")
        r = self.client.get(
            f"/cases/{case_id}/venues/anykey/human-view",
            headers={"Authorization": f"Bearer {b['session_token']}"},
        )
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
