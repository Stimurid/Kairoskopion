"""Staging soft-auth + workspace isolation tests.

Covers the task spec section F isolation checklist + the storage
roundtrip required for "case data survives server restart".
"""

from __future__ import annotations

import importlib
import os
import shutil
import tempfile
import unittest

from fastapi.testclient import TestClient


class _BaseTestEnv(unittest.TestCase):
    """Each test class spins up a fresh data dir + fresh app + fresh
    auth stores so isolation between tests is exact."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="kairon_auth_test_")
        os.environ["KAIROSKOPION_DATA_DIR"] = self._tmpdir
        # Force re-import of modules that pin a data_dir at import time.
        from kairoskopion.api import auth as auth_mod
        auth_mod.reset_stores_for_tests(self._tmpdir)
        # Rebuild the FastAPI app with a CaseStore rooted in the new tmpdir.
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)
        # The reloaded app picks up the new store via the env var.
        auth_mod.reset_stores_for_tests(self._tmpdir)
        self.app = app_mod.app
        self.client = TestClient(self.app)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("KAIROSKOPION_DATA_DIR", None)


# ---------------------------------------------------------------------------
# Signup / continue / me flows
# ---------------------------------------------------------------------------

class TestSignup(_BaseTestEnv):
    def test_signup_with_display_name_only(self):
        r = self.client.post("/auth/signup", json={"display_name": "Alice"})
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertIn("user", d)
        self.assertIn("session_token", d)
        self.assertTrue(d["user"]["user_id"].startswith("user_"))
        self.assertEqual(d["user"]["display_name"], "Alice")
        self.assertIsNone(d["user"]["email"])

    def test_signup_with_email_is_lowercased_and_stripped(self):
        r = self.client.post(
            "/auth/signup",
            json={"display_name": "Bob", "email": "  Bob@Example.ORG "},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["user"]["email"], "bob@example.org")

    def test_signup_rejects_empty_display_name(self):
        r = self.client.post(
            "/auth/signup", json={"display_name": "   "},
        )
        self.assertEqual(r.status_code, 400)

    def test_signup_duplicate_email_returns_existing_user(self):
        r1 = self.client.post(
            "/auth/signup",
            json={"display_name": "Cara", "email": "cara@example.org"},
        )
        self.assertEqual(r1.status_code, 200)
        user1_id = r1.json()["user"]["user_id"]
        r2 = self.client.post(
            "/auth/signup",
            json={"display_name": "Cara2", "email": "cara@example.org"},
        )
        self.assertEqual(r2.status_code, 200)
        # Returns the same user, not a new one
        self.assertEqual(r2.json()["user"]["user_id"], user1_id)
        # Original display name preserved
        self.assertEqual(r2.json()["user"]["display_name"], "Cara")

    def test_signup_invalid_email_treated_as_none(self):
        r = self.client.post(
            "/auth/signup",
            json={"display_name": "Dan", "email": "not-an-email"},
        )
        # Invalid email is silently dropped; user is created with email=None
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIsNone(r.json()["user"]["email"])


class TestContinue(_BaseTestEnv):
    def _signup(self, name, email=None):
        r = self.client.post(
            "/auth/signup",
            json={"display_name": name, "email": email},
        )
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_continue_known_email_returns_new_token_same_user(self):
        d1 = self._signup("Eve", "eve@example.org")
        r = self.client.post("/auth/continue", json={"email": "eve@example.org"})
        self.assertEqual(r.status_code, 200, r.text)
        d2 = r.json()
        self.assertEqual(d2["user"]["user_id"], d1["user"]["user_id"])
        # A NEW token, not the old one
        self.assertNotEqual(d2["session_token"], d1["session_token"])

    def test_continue_unknown_email_returns_404(self):
        r = self.client.post(
            "/auth/continue", json={"email": "ghost@nowhere.example"},
        )
        self.assertEqual(r.status_code, 404)
        self.assertIn("not_found", r.text.lower())

    def test_continue_requires_email(self):
        r = self.client.post("/auth/continue", json={"email": ""})
        self.assertEqual(r.status_code, 400)


class TestMe(_BaseTestEnv):
    def test_me_returns_user_for_valid_token(self):
        d = self.client.post(
            "/auth/signup",
            json={"display_name": "Faye", "email": "faye@example.org"},
        ).json()
        token = d["session_token"]
        r = self.client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["user"]["user_id"], d["user"]["user_id"])

    def test_me_rejects_missing_auth(self):
        r = self.client.get("/auth/me")
        self.assertEqual(r.status_code, 401)

    def test_me_rejects_malformed_auth(self):
        r = self.client.get(
            "/auth/me", headers={"Authorization": "garbage"},
        )
        self.assertEqual(r.status_code, 401)

    def test_me_rejects_unknown_bearer(self):
        r = self.client.get(
            "/auth/me", headers={"Authorization": "Bearer no-such-token"},
        )
        self.assertEqual(r.status_code, 401)


class TestLogout(_BaseTestEnv):
    def test_logout_revokes_token(self):
        d = self.client.post(
            "/auth/signup",
            json={"display_name": "Gus", "email": "gus@example.org"},
        ).json()
        token = d["session_token"]
        r = self.client.post(
            "/auth/logout", headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["revoked"])
        # The revoked token no longer works
        r2 = self.client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(r2.status_code, 401)

    def test_logout_without_token_is_noop(self):
        r = self.client.post("/auth/logout")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["revoked"])


# ---------------------------------------------------------------------------
# Workspace isolation
# ---------------------------------------------------------------------------

class TestWorkspaceIsolation(_BaseTestEnv):
    def _signup(self, name, email=None):
        r = self.client.post(
            "/auth/signup",
            json={"display_name": name, "email": email},
        )
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_user_a_creates_case_user_b_cannot_see_it(self):
        a = self._signup("UserA", "a@example.org")
        b = self._signup("UserB", "b@example.org")

        # A creates a case
        r = self.client.post(
            "/cases", headers=self._auth(a["session_token"]),
            json={"title": "A's secret article"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        case_id = r.json()["case_id"]

        # B's listing is empty
        rb = self.client.get(
            "/cases", headers=self._auth(b["session_token"]),
        )
        self.assertEqual(rb.status_code, 200)
        self.assertEqual(rb.json(), [])

        # B's direct fetch by case_id is a 404 (no info leak)
        rb2 = self.client.get(
            f"/cases/{case_id}", headers=self._auth(b["session_token"]),
        )
        self.assertEqual(rb2.status_code, 404)

        # B's delete attempt fails
        rb3 = self.client.delete(
            f"/cases/{case_id}", headers=self._auth(b["session_token"]),
        )
        self.assertEqual(rb3.status_code, 404)

        # A still sees their case
        ra = self.client.get(
            "/cases", headers=self._auth(a["session_token"]),
        )
        self.assertEqual(ra.status_code, 200)
        self.assertEqual(len(ra.json()), 1)
        self.assertEqual(ra.json()[0]["case_id"], case_id)

    def test_continue_session_can_access_existing_case(self):
        a = self._signup("UserA", "a2@example.org")
        # A creates a case
        r = self.client.post(
            "/cases", headers=self._auth(a["session_token"]),
            json={"title": "A's article"},
        )
        case_id = r.json()["case_id"]

        # A "loses" the token, continues by email — gets new token
        cr = self.client.post(
            "/auth/continue", json={"email": "a2@example.org"},
        )
        self.assertEqual(cr.status_code, 200)
        new_token = cr.json()["session_token"]
        self.assertNotEqual(new_token, a["session_token"])

        # New token sees the same case
        r2 = self.client.get(
            f"/cases/{case_id}", headers=self._auth(new_token),
        )
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertEqual(r2.json()["case_id"], case_id)

    def test_unauth_endpoints_require_bearer(self):
        # No token at all
        for path, method in [
            ("/cases", "GET"),
            ("/cases", "POST"),
            ("/cases/case_anything", "GET"),
            ("/cases/case_anything", "DELETE"),
            ("/auth/me", "GET"),
        ]:
            r = self.client.request(method, path, json={})
            self.assertEqual(
                r.status_code, 401,
                f"{method} {path} should require auth, got {r.status_code}",
            )

    def test_health_does_not_require_auth(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)


# ---------------------------------------------------------------------------
# Persistence across restart
# ---------------------------------------------------------------------------

class TestPersistenceAcrossRestart(_BaseTestEnv):
    def test_user_case_survives_app_reimport(self):
        # Signup + create case
        d = self.client.post(
            "/auth/signup",
            json={"display_name": "Hank", "email": "hank@example.org"},
        ).json()
        case_id = self.client.post(
            "/cases",
            headers={"Authorization": f"Bearer {d['session_token']}"},
            json={"title": "Survive"},
        ).json()["case_id"]

        # Simulate restart: re-import app module, rebuild client, BUT
        # keep KAIROSKOPION_DATA_DIR pointing at the same tmpdir.
        from kairoskopion.api import app as app_mod
        from kairoskopion.api import auth as auth_mod
        importlib.reload(app_mod)
        auth_mod.reset_stores_for_tests(self._tmpdir)
        new_client = TestClient(app_mod.app)

        # User must re-authenticate (token store also reloaded from disk —
        # the token IS persisted, so it still works).
        r = new_client.get(
            f"/cases/{case_id}",
            headers={"Authorization": f"Bearer {d['session_token']}"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["case_id"], case_id)
        self.assertEqual(r.json()["title"], "Survive")

    def test_user_can_continue_after_restart(self):
        d = self.client.post(
            "/auth/signup",
            json={"display_name": "Ivy", "email": "ivy@example.org"},
        ).json()
        case_id = self.client.post(
            "/cases",
            headers={"Authorization": f"Bearer {d['session_token']}"},
            json={"title": "Ivy's"},
        ).json()["case_id"]

        # Restart with same data dir
        from kairoskopion.api import app as app_mod
        from kairoskopion.api import auth as auth_mod
        importlib.reload(app_mod)
        auth_mod.reset_stores_for_tests(self._tmpdir)
        new_client = TestClient(app_mod.app)

        # Imagine the operator cleared browser localStorage. They
        # /continue by email and get a new token.
        cr = new_client.post(
            "/auth/continue", json={"email": "ivy@example.org"},
        )
        self.assertEqual(cr.status_code, 200, cr.text)
        new_token = cr.json()["session_token"]

        # New token sees the persisted case
        r = new_client.get(
            f"/cases/{case_id}",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        self.assertEqual(r.status_code, 200)


# ---------------------------------------------------------------------------
# Storage layout sanity
# ---------------------------------------------------------------------------

class TestStorageLayout(_BaseTestEnv):
    def test_user_cases_live_under_users_dir(self):
        d = self.client.post(
            "/auth/signup",
            json={"display_name": "Joe", "email": "joe@example.org"},
        ).json()
        user_id = d["user"]["user_id"]
        case_id = self.client.post(
            "/cases",
            headers={"Authorization": f"Bearer {d['session_token']}"},
            json={"title": "T"},
        ).json()["case_id"]

        from pathlib import Path
        user_case_path = Path(
            self._tmpdir
        ) / "users" / user_id / "cases" / f"{case_id}.json"
        self.assertTrue(
            user_case_path.exists(),
            f"user case file not found at {user_case_path}",
        )
        # Legacy cases dir does NOT contain user-scoped cases
        legacy = Path(self._tmpdir) / "cases" / f"{case_id}.json"
        self.assertFalse(legacy.exists())


if __name__ == "__main__":
    unittest.main()
